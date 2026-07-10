"""Domain models for DecisionKit."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from decisionkit.exceptions import (
    InvalidDirectionError,
    InvalidValueError,
    InvalidWeightError,
    ValidationError,
)
from decisionkit.typing import ComparisonOp, Direction, MethodName


def _validate_finite_number(value: Any, *, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidValueError(
            f"{context} must be a number, got {type(value).__name__}"
        )
    number = float(value)
    if number != number or number in (float("inf"), float("-inf")):  # NaN / inf
        raise InvalidValueError(f"{context} must be a finite number, got {value!r}")
    return number


@dataclass(frozen=True, slots=True)
class Criterion:
    """A scored decision criterion.

    Parameters
    ----------
    name:
        Unique criterion key used in alternative value maps.
    weight:
        Positive relative importance. Weights are normalized internally
        so they need not sum to 1.0.
    direction:
        ``"max"`` if higher values are better, ``"min"`` if lower is better.
    description:
        Optional human-readable description for explanations and audits.
    """

    name: str
    weight: float = 1.0
    direction: Direction = "max"
    description: str | None = None

    def __post_init__(self) -> None:
        if not self.name or not str(self.name).strip():
            raise ValidationError("Criterion name must be a non-empty string")
        if self.direction not in ("max", "min"):
            raise InvalidDirectionError(
                f"Criterion '{self.name}' direction must be 'max' or 'min', "
                f"got {self.direction!r}"
            )
        weight = _validate_finite_number(
            self.weight, context=f"Criterion '{self.name}' weight"
        )
        if weight <= 0:
            raise InvalidWeightError(
                f"Criterion '{self.name}' weight must be positive, got {weight}"
            )
        object.__setattr__(self, "name", str(self.name).strip())
        object.__setattr__(self, "weight", weight)


@dataclass(frozen=True, slots=True)
class Constraint:
    """Hard filter: alternatives failing the rule are excluded from ranking."""

    name: str
    criterion: str
    operator: ComparisonOp
    threshold: float
    description: str | None = None

    def __post_init__(self) -> None:
        if not self.name or not str(self.name).strip():
            raise ValidationError("Constraint name must be a non-empty string")
        if not self.criterion or not str(self.criterion).strip():
            raise ValidationError(
                f"Constraint '{self.name}' criterion must be non-empty"
            )
        if self.operator not in ("gt", "gte", "lt", "lte", "eq"):
            raise ValidationError(
                f"Constraint '{self.name}' operator must be one of "
                f"gt, gte, lt, lte, eq; got {self.operator!r}"
            )
        threshold = _validate_finite_number(
            self.threshold, context=f"Constraint '{self.name}' threshold"
        )
        object.__setattr__(self, "name", str(self.name).strip())
        object.__setattr__(self, "criterion", str(self.criterion).strip())
        object.__setattr__(self, "threshold", threshold)

    def is_satisfied(self, value: float) -> bool:
        """Return whether ``value`` satisfies this constraint."""
        ops = {
            "gt": value > self.threshold,
            "gte": value >= self.threshold,
            "lt": value < self.threshold,
            "lte": value <= self.threshold,
            "eq": value == self.threshold,
        }
        return ops[self.operator]


@dataclass(frozen=True, slots=True)
class Penalty:
    """Soft rule: subtracts ``amount`` from the score when triggered."""

    name: str
    criterion: str
    operator: ComparisonOp
    threshold: float
    amount: float
    description: str | None = None

    def __post_init__(self) -> None:
        if not self.name or not str(self.name).strip():
            raise ValidationError("Penalty name must be a non-empty string")
        if not self.criterion or not str(self.criterion).strip():
            raise ValidationError(f"Penalty '{self.name}' criterion must be non-empty")
        if self.operator not in ("gt", "gte", "lt", "lte", "eq"):
            raise ValidationError(
                f"Penalty '{self.name}' operator must be one of "
                f"gt, gte, lt, lte, eq; got {self.operator!r}"
            )
        threshold = _validate_finite_number(
            self.threshold, context=f"Penalty '{self.name}' threshold"
        )
        amount = _validate_finite_number(
            self.amount, context=f"Penalty '{self.name}' amount"
        )
        if amount <= 0:
            raise ValidationError(
                f"Penalty '{self.name}' amount must be positive, got {amount}"
            )
        object.__setattr__(self, "name", str(self.name).strip())
        object.__setattr__(self, "criterion", str(self.criterion).strip())
        object.__setattr__(self, "threshold", threshold)
        object.__setattr__(self, "amount", amount)

    def is_triggered(self, value: float) -> bool:
        """Return whether ``value`` triggers this penalty."""
        ops = {
            "gt": value > self.threshold,
            "gte": value >= self.threshold,
            "lt": value < self.threshold,
            "lte": value <= self.threshold,
            "eq": value == self.threshold,
        }
        return ops[self.operator]


@dataclass(frozen=True, slots=True)
class Alternative:
    """A scored option identified by ``id`` with criterion values."""

    id: str
    values: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id or not str(self.id).strip():
            raise ValidationError("Alternative id must be a non-empty string")
        cleaned: dict[str, float] = {}
        for key, raw in self.values.items():
            cleaned[str(key)] = _validate_finite_number(
                raw, context=f"Alternative '{self.id}' value for '{key}'"
            )
        object.__setattr__(self, "id", str(self.id).strip())
        object.__setattr__(self, "values", cleaned)

    def get(self, criterion: str) -> float:
        """Return the numeric value for ``criterion``."""
        return self.values[criterion]


@dataclass(frozen=True, slots=True)
class Explanation:
    """Structured, audit-friendly explanation for one ranked alternative."""

    alternative_id: str
    rank: int
    score: float
    method: MethodName
    normalized_values: dict[str, float]
    contributions: dict[str, float]
    triggered_penalties: tuple[str, ...] = ()
    text: str = ""


@dataclass(frozen=True, slots=True)
class RankedAlternative:
    """One alternative after scoring and ranking."""

    id: str
    score: float
    rank: int
    values: dict[str, float]
    normalized_values: dict[str, float]
    contributions: dict[str, float]
    triggered_penalties: tuple[str, ...] = ()
    explanation: Explanation | None = None


@dataclass(frozen=True, slots=True)
class DecisionResult:
    """Outcome of a ranking run.

    Attributes
    ----------
    ranking:
        Alternatives ordered best-first (rank 1 first).
    method:
        Method used to produce the ranking.
    excluded:
        Alternatives removed by hard constraints, with reasons.
    """

    ranking: tuple[RankedAlternative, ...]
    method: MethodName
    excluded: tuple[tuple[str, str], ...] = ()

    @property
    def best(self) -> RankedAlternative:
        """Return the top-ranked alternative."""
        if not self.ranking:
            raise ValidationError("No ranked alternatives available")
        return self.ranking[0]

    def explain(self, *, limit: int | None = None) -> str:
        """Return a plain-text multi-alternative explanation.

        Parameters
        ----------
        limit:
            Optional max number of ranked alternatives to include.
        """
        lines: list[str] = []
        items = self.ranking if limit is None else self.ranking[:limit]
        for item in items:
            if item.explanation is not None and item.explanation.text:
                lines.append(item.explanation.text)
            else:
                lines.append(
                    f"{item.id} ranked #{item.rank} with score {item.score:.4f}."
                )
        if self.excluded:
            lines.append("")
            lines.append("Excluded by constraints:")
            for alt_id, reason in self.excluded:
                lines.append(f"- {alt_id}: {reason}")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the result to a JSON-friendly dictionary."""
        return {
            "method": self.method,
            "best": self.best.id if self.ranking else None,
            "ranking": [
                {
                    "id": item.id,
                    "score": item.score,
                    "rank": item.rank,
                    "values": dict(item.values),
                    "normalized_values": dict(item.normalized_values),
                    "contributions": dict(item.contributions),
                    "triggered_penalties": list(item.triggered_penalties),
                    "explanation": item.explanation.text if item.explanation else None,
                }
                for item in self.ranking
            ],
            "excluded": [
                {"id": alt_id, "reason": reason}
                for alt_id, reason in self.excluded
            ],
        }
