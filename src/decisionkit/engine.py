"""Decision engine: validation, rules, scoring, and ranking."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from decisionkit.config import (
    model_from_dict,
    model_from_json,
    model_from_yaml,
    model_to_dict,
    model_to_json,
    model_to_yaml,
)
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
    Bonus,
    Constraint,
    Criterion,
    DecisionResult,
    Penalty,
    RankedAlternative,
    _validate_finite_number,
)
from decisionkit.typing import (
    AlternativeInput,
    AlternativeList,
    ContextMapping,
    MethodName,
)


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

    values: dict[str, Any] = {}
    for key, value in raw.items():
        if key == "id":
            continue
        values[str(key)] = value
    return Alternative(id=str(alt_id), values=values)


def _apply_constraints(
    alternatives: list[Alternative],
    constraints: list[Constraint],
    context: ContextMapping,
) -> tuple[list[Alternative], list[tuple[str, str]]]:
    if not constraints:
        return alternatives, []

    kept: list[Alternative] = []
    excluded: list[tuple[str, str]] = []
    for alt in alternatives:
        failed: list[str] = []
        for constraint in constraints:
            if not constraint.matches(alt.values, context):
                detail = constraint.reason or constraint.name
                failed.append(f"{constraint.name} ({detail})")
        if failed:
            excluded.append((alt.id, "; ".join(failed)))
        else:
            kept.append(alt)
    return kept, excluded


def _apply_adjustments(
    score: float,
    values: Mapping[str, Any],
    penalties: list[Penalty],
    bonuses: list[Bonus],
    context: ContextMapping,
) -> tuple[float, tuple[str, ...], tuple[str, ...], float, float]:
    triggered_penalties: list[str] = []
    triggered_bonuses: list[str] = []
    penalty_total = 0.0
    bonus_total = 0.0
    adjusted = score

    for penalty in penalties:
        if penalty.matches(values, context):
            adjusted -= penalty.amount
            penalty_total += penalty.amount
            triggered_penalties.append(penalty.name)

    for bonus in bonuses:
        if bonus.matches(values, context):
            adjusted += bonus.amount
            bonus_total += bonus.amount
            triggered_bonuses.append(bonus.name)

    return (
        adjusted,
        tuple(triggered_penalties),
        tuple(triggered_bonuses),
        penalty_total,
        bonus_total,
    )


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
    bonuses: list[Bonus] = field(default_factory=list)

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

        # Defensive copies so callers cannot mutate configuration after init.
        self.criteria = list(self.criteria)
        self.constraints = list(self.constraints)
        self.penalties = list(self.penalties)
        self.bonuses = list(self.bonuses)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> DecisionModel:
        """Build a model from a configuration mapping."""
        return model_from_dict(data)

    @classmethod
    def from_json(cls, payload: str | bytes) -> DecisionModel:
        """Build a model from a JSON string."""
        return model_from_json(payload)

    @classmethod
    def from_yaml(cls, payload: str | bytes) -> DecisionModel:
        """Build a model from a YAML string (requires ``decisionkit[yaml]``)."""
        return model_from_yaml(payload)

    def to_dict(self) -> dict[str, Any]:
        """Serialize model configuration to a JSON-friendly dictionary."""
        return model_to_dict(self)

    def to_json(self, *, indent: int | None = 2) -> str:
        """Serialize model configuration to a JSON string."""
        return model_to_json(self, indent=indent)

    def to_yaml(self) -> str:
        """Serialize model configuration to YAML (requires ``decisionkit[yaml]``)."""
        return model_to_yaml(self)

    def rank(
        self,
        alternatives: AlternativeList,
        context: ContextMapping | None = None,
    ) -> DecisionResult:
        """Score and rank alternatives.

        Parameters
        ----------
        alternatives:
            Sequence of mappings with an ``id`` key and values for criteria
            plus any fields referenced by rules.
        context:
            Optional shared context values for rule evaluation
            (for example ``{"max_workload": 5}``).
        """
        if alternatives is None:
            raise EmptyAlternativesError(
                "alternatives must be a non-empty sequence"
            )
        parsed = [_parse_alternative(raw) for raw in alternatives]
        if not parsed:
            raise EmptyAlternativesError("At least one alternative is required")

        ids = [alt.id for alt in parsed]
        if len(ids) != len(set(ids)):
            raise DuplicateAlternativeError(
                f"Alternative ids must be unique, got {ids}"
            )

        runtime_context: dict[str, Any] = dict(context or {})
        self._validate_values(parsed)

        eligible, excluded = _apply_constraints(
            parsed, self.constraints, runtime_context
        )
        if not eligible:
            raise ValidationError(
                "All alternatives were excluded by constraints; nothing to rank"
            )

        method_fn = METHODS[self.method]
        scored = method_fn(eligible, self.criteria)

        ranked: list[RankedAlternative] = []
        for index, row in enumerate(scored, start=1):
            (
                score,
                triggered_penalties,
                triggered_bonuses,
                penalty_total,
                bonus_total,
            ) = _apply_adjustments(
                row.score,
                row.values,
                self.penalties,
                self.bonuses,
                runtime_context,
            )
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
                    triggered_penalties=triggered_penalties,
                    triggered_bonuses=triggered_bonuses,
                )
            ranked.append(
                RankedAlternative(
                    id=row.alternative_id,
                    score=score,
                    rank=index,
                    values=row.values,
                    normalized_values=row.normalized_values,
                    contributions=row.contributions,
                    base_score=row.score,
                    triggered_penalties=triggered_penalties,
                    triggered_bonuses=triggered_bonuses,
                    penalty_total=penalty_total,
                    bonus_total=bonus_total,
                    explanation=explanation,
                )
            )

        if self.penalties or self.bonuses:
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
                        triggered_bonuses=item.triggered_bonuses,
                    )
                reranked.append(
                    RankedAlternative(
                        id=item.id,
                        score=item.score,
                        rank=new_rank,
                        values=item.values,
                        normalized_values=item.normalized_values,
                        contributions=item.contributions,
                        base_score=item.base_score,
                        triggered_penalties=item.triggered_penalties,
                        triggered_bonuses=item.triggered_bonuses,
                        penalty_total=item.penalty_total,
                        bonus_total=item.bonus_total,
                        explanation=explanation,
                    )
                )
            ranked = reranked

        return DecisionResult(
            ranking=tuple(ranked),
            method=self.method,
            excluded=tuple(excluded),
            model=self.to_dict(),
            input_ids=tuple(ids),
            context=runtime_context,
        )

    def _validate_values(self, alternatives: list[Alternative]) -> None:
        required = [c.name for c in self.criteria]
        for alt in alternatives:
            for name in required:
                if name not in alt.values:
                    raise MissingValueError(
                        f"Alternative '{alt.id}' is missing required "
                        f"criterion '{name}'"
                    )
                try:
                    number = _validate_finite_number(
                        alt.values[name],
                        context=(
                            f"Alternative '{alt.id}' value for '{name}'"
                        ),
                    )
                except InvalidValueError:
                    raise
                # Ensure scoring methods always see floats for criteria.
                alt.values[name] = number
