"""Decision engine: validation, constraints, penalties, and ranking."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from decisionkit.exceptions import (
    DuplicateAlternativeError,
    DuplicateCriterionError,
    EmptyAlternativesError,
    InvalidValueError,
    MissingValueError,
    UnknownMethodError,
    ValidationError,
)
from decisionkit.explanations import build_explanation
from decisionkit.methods import METHODS
from decisionkit.models import (
    Alternative,
    Constraint,
    Criterion,
    DecisionResult,
    Penalty,
    RankedAlternative,
    _validate_finite_number,
)
from decisionkit.typing import AlternativeInput, AlternativeList, MethodName


def _parse_alternative(raw: AlternativeInput) -> Alternative:
    if not isinstance(raw, dict):
        raise ValidationError(
            f"Each alternative must be a mapping, got {type(raw).__name__}"
        )
    if "id" not in raw:
        raise ValidationError("Each alternative must include an 'id' field")

    alt_id = raw["id"]
    if alt_id is None or (isinstance(alt_id, str) and not alt_id.strip()):
        raise ValidationError("Alternative id must be a non-empty string")

    values: dict[str, float] = {}
    for key, value in raw.items():
        if key == "id":
            continue
        values[str(key)] = _validate_finite_number(
            value, context=f"Alternative '{alt_id}' value for '{key}'"
        )
    return Alternative(id=str(alt_id), values=values)


def _apply_constraints(
    alternatives: list[Alternative],
    constraints: list[Constraint],
    criteria_names: set[str],
) -> tuple[list[Alternative], list[tuple[str, str]]]:
    if not constraints:
        return alternatives, []

    for constraint in constraints:
        if constraint.criterion not in criteria_names:
            raise ValidationError(
                f"Constraint '{constraint.name}' references unknown criterion "
                f"'{constraint.criterion}'"
            )

    kept: list[Alternative] = []
    excluded: list[tuple[str, str]] = []
    for alt in alternatives:
        failed: list[str] = []
        for constraint in constraints:
            value = alt.values[constraint.criterion]
            if not constraint.is_satisfied(value):
                detail = constraint.description or (
                    f"{constraint.criterion} "
                    f"{constraint.operator} {constraint.threshold}"
                )
                failed.append(f"{constraint.name} ({detail})")
        if failed:
            excluded.append((alt.id, "; ".join(failed)))
        else:
            kept.append(alt)
    return kept, excluded


def _apply_penalties(
    score: float,
    values: dict[str, float],
    penalties: list[Penalty],
) -> tuple[float, tuple[str, ...]]:
    triggered: list[str] = []
    adjusted = score
    for penalty in penalties:
        value = values[penalty.criterion]
        if penalty.is_triggered(value):
            adjusted -= penalty.amount
            triggered.append(penalty.name)
    return adjusted, tuple(triggered)


@dataclass
class DecisionModel:
    """Configure criteria and rank alternatives with explanations.

    Example
    -------
    >>> from decisionkit import DecisionModel, Criterion
    >>> model = DecisionModel(
    ...     criteria=[
    ...         Criterion("relevance", weight=0.5, direction="max"),
    ...         Criterion("rating", weight=0.3, direction="max"),
    ...         Criterion("workload", weight=0.2, direction="min"),
    ...     ],
    ...     method="weighted_sum",
    ... )
    >>> result = model.rank([
    ...     {"id": "a", "relevance": 0.9, "rating": 4.8, "workload": 7},
    ...     {"id": "b", "relevance": 0.8, "rating": 4.5, "workload": 2},
    ... ])
    >>> result.best.id in {"a", "b"}
    True
    """

    criteria: list[Criterion]
    method: MethodName = "weighted_sum"
    explain: bool = True
    constraints: list[Constraint] = field(default_factory=list)
    penalties: list[Penalty] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.criteria:
            raise ValidationError("DecisionModel requires at least one criterion")

        names = [c.name for c in self.criteria]
        if len(names) != len(set(names)):
            raise DuplicateCriterionError(
                f"Criterion names must be unique, got {names}"
            )

        if self.method not in METHODS:
            supported = ", ".join(sorted(METHODS))
            raise UnknownMethodError(
                f"Unknown method {self.method!r}. Supported methods: {supported}"
            )

        criteria_names = set(names)
        for penalty in self.penalties:
            if penalty.criterion not in criteria_names:
                raise ValidationError(
                    f"Penalty '{penalty.name}' references unknown criterion "
                    f"'{penalty.criterion}'"
                )
        for constraint in self.constraints:
            if constraint.criterion not in criteria_names:
                raise ValidationError(
                    f"Constraint '{constraint.name}' references unknown criterion "
                    f"'{constraint.criterion}'"
                )

        # Defensive copies so callers cannot mutate configuration after init.
        self.criteria = list(self.criteria)
        self.constraints = list(self.constraints)
        self.penalties = list(self.penalties)

    def rank(self, alternatives: AlternativeList) -> DecisionResult:
        """Score and rank alternatives.

        Parameters
        ----------
        alternatives:
            Sequence of mappings with an ``id`` key and one numeric value
            per configured criterion.
        """
        if alternatives is None:
            raise EmptyAlternativesError("alternatives must be a non-empty sequence")
        parsed = [_parse_alternative(raw) for raw in alternatives]
        if not parsed:
            raise EmptyAlternativesError("At least one alternative is required")

        ids = [alt.id for alt in parsed]
        if len(ids) != len(set(ids)):
            raise DuplicateAlternativeError(
                f"Alternative ids must be unique, got {ids}"
            )

        self._validate_values(parsed)

        criteria_names = {c.name for c in self.criteria}
        eligible, excluded = _apply_constraints(
            parsed, self.constraints, criteria_names
        )
        if not eligible:
            raise ValidationError(
                "All alternatives were excluded by constraints; nothing to rank"
            )

        method_fn = METHODS[self.method]
        scored = method_fn(eligible, self.criteria)

        ranked: list[RankedAlternative] = []
        for index, row in enumerate(scored, start=1):
            score, triggered = _apply_penalties(row.score, row.values, self.penalties)
            explanation = None
            if self.explain:
                explanation = build_explanation(
                    alternative_id=row.alternative_id,
                    rank=index,
                    score=score,
                    method=self.method,
                    criteria=self.criteria,
                    normalized_values=row.normalized_values,
                    contributions=row.contributions,
                    triggered_penalties=triggered,
                )
            ranked.append(
                RankedAlternative(
                    id=row.alternative_id,
                    score=score,
                    rank=index,
                    values=row.values,
                    normalized_values=row.normalized_values,
                    contributions=row.contributions,
                    triggered_penalties=triggered,
                    explanation=explanation,
                )
            )

        # Re-sort if penalties changed relative order.
        if self.penalties:
            ranked.sort(key=lambda item: (-item.score, item.id))
            reranked: list[RankedAlternative] = []
            for new_rank, item in enumerate(ranked, start=1):
                explanation = item.explanation
                if self.explain:
                    explanation = build_explanation(
                        alternative_id=item.id,
                        rank=new_rank,
                        score=item.score,
                        method=self.method,
                        criteria=self.criteria,
                        normalized_values=item.normalized_values,
                        contributions=item.contributions,
                        triggered_penalties=item.triggered_penalties,
                    )
                reranked.append(
                    RankedAlternative(
                        id=item.id,
                        score=item.score,
                        rank=new_rank,
                        values=item.values,
                        normalized_values=item.normalized_values,
                        contributions=item.contributions,
                        triggered_penalties=item.triggered_penalties,
                        explanation=explanation,
                    )
                )
            ranked = reranked

        return DecisionResult(
            ranking=tuple(ranked),
            method=self.method,
            excluded=tuple(excluded),
        )

    def _validate_values(self, alternatives: list[Alternative]) -> None:
        required = [c.name for c in self.criteria]
        for alt in alternatives:
            for name in required:
                if name not in alt.values:
                    raise MissingValueError(
                        f"Alternative '{alt.id}' is missing required criterion '{name}'"
                    )
                # Values already validated as finite numbers during parse,
                # but re-check in case Alternative was constructed directly.
                try:
                    _validate_finite_number(
                        alt.values[name],
                        context=f"Alternative '{alt.id}' value for '{name}'",
                    )
                except InvalidValueError:
                    raise

    def to_dict(self) -> dict[str, Any]:
        """Serialize model configuration to a JSON-friendly dictionary."""
        return {
            "method": self.method,
            "explain": self.explain,
            "criteria": [
                {
                    "name": c.name,
                    "weight": c.weight,
                    "direction": c.direction,
                    "description": c.description,
                }
                for c in self.criteria
            ],
            "constraints": [
                {
                    "name": c.name,
                    "criterion": c.criterion,
                    "operator": c.operator,
                    "threshold": c.threshold,
                    "description": c.description,
                }
                for c in self.constraints
            ],
            "penalties": [
                {
                    "name": p.name,
                    "criterion": p.criterion,
                    "operator": p.operator,
                    "threshold": p.threshold,
                    "amount": p.amount,
                    "description": p.description,
                }
                for p in self.penalties
            ],
        }
