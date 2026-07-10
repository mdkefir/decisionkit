"""Domain models for DecisionKit."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from decisionkit.exceptions import (
    InvalidDirectionError,
    InvalidValueError,
    InvalidWeightError,
    ValidationError,
)
from decisionkit.rules import (
    RuleCondition,
    condition_from_mapping,
    evaluate_conditions,
)
from decisionkit.typing import ComparisonOp, ContextMapping, Direction, MethodName


def _validate_finite_number(value: Any, *, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidValueError(
            f"{context} must be a number, got {type(value).__name__}"
        )
    number = float(value)
    if number != number or number in (float("inf"), float("-inf")):  # NaN / inf
        raise InvalidValueError(f"{context} must be a finite number, got {value!r}")
    return number


def _normalize_conditions(
    *,
    rule_name: str,
    field: str | None,
    operator: ComparisonOp,
    value: Any,
    context: str | None,
    all_of: Sequence[RuleCondition | Mapping[str, Any]] | None,
    any_of: Sequence[RuleCondition | Mapping[str, Any]] | None,
) -> tuple[
    RuleCondition | None,
    tuple[RuleCondition, ...] | None,
    tuple[RuleCondition, ...] | None,
]:
    def _coerce(
        items: Sequence[RuleCondition | Mapping[str, Any]],
    ) -> tuple[RuleCondition, ...]:
        out: list[RuleCondition] = []
        for item in items:
            if isinstance(item, RuleCondition):
                out.append(item)
            else:
                out.append(condition_from_mapping(item, rule_name=rule_name))
        return tuple(out)

    parsed_all = _coerce(all_of) if all_of is not None else None
    parsed_any = _coerce(any_of) if any_of is not None else None
    single: RuleCondition | None = None
    if field:
        single = RuleCondition(
            field=field,
            operator=operator,
            value=value,
            context=context,
        )

    groups = sum(1 for item in (single, parsed_all, parsed_any) if item is not None)
    if groups == 0:
        raise ValidationError(
            f"Rule '{rule_name}' requires a field/condition or compound all/any"
        )
    if groups > 1:
        raise ValidationError(
            f"Rule '{rule_name}' must use exactly one of: field, all, or any"
        )
    return single, parsed_all, parsed_any


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

    def to_dict(self) -> dict[str, Any]:
        """Serialize this criterion to a JSON-friendly dictionary."""
        return {
            "name": self.name,
            "weight": self.weight,
            "direction": self.direction,
            "description": self.description,
        }


@dataclass(frozen=True, slots=True)
class Constraint:
    """Hard filter: alternatives failing the rule are excluded from ranking.

    Accepts modern ``field`` / ``value`` / ``reason`` names and legacy
    ``criterion`` / ``threshold`` / ``description`` aliases.
    """

    name: str
    field: str = ""
    operator: ComparisonOp = "eq"
    value: Any = None
    context: str | None = None
    reason: str | None = None
    all: tuple[RuleCondition, ...] | None = None
    any: tuple[RuleCondition, ...] | None = None

    def __init__(
        self,
        name: str,
        field: str | None = None,
        operator: ComparisonOp = "eq",
        value: Any = None,
        *,
        criterion: str | None = None,
        threshold: Any = None,
        description: str | None = None,
        reason: str | None = None,
        context: str | None = None,
        all: Sequence[RuleCondition | Mapping[str, Any]] | None = None,
        any: Sequence[RuleCondition | Mapping[str, Any]] | None = None,
    ) -> None:
        if not name or not str(name).strip():
            raise ValidationError("Constraint name must be a non-empty string")
        if field is not None and criterion is not None and field != criterion:
            raise ValidationError(
                f"Constraint '{name}' cannot set both 'field' and 'criterion'"
            )
        if value is not None and threshold is not None and value != threshold:
            raise ValidationError(
                f"Constraint '{name}' cannot set both 'value' and 'threshold'"
            )
        if reason is not None and description is not None and reason != description:
            raise ValidationError(
                f"Constraint '{name}' cannot set both 'reason' and 'description'"
            )

        resolved_field = field if field is not None else criterion
        resolved_value = value if value is not None else threshold
        resolved_reason = reason if reason is not None else description
        single, all_of, any_of = _normalize_conditions(
            rule_name=str(name),
            field=resolved_field,
            operator=operator,
            value=resolved_value,
            context=context,
            all_of=all,
            any_of=any,
        )

        object.__setattr__(self, "name", str(name).strip())
        object.__setattr__(self, "field", single.field if single else "")
        object.__setattr__(
            self, "operator", single.operator if single else operator
        )
        object.__setattr__(self, "value", single.value if single else resolved_value)
        object.__setattr__(
            self, "context", single.context if single else context
        )
        object.__setattr__(self, "reason", resolved_reason)
        object.__setattr__(self, "all", all_of)
        object.__setattr__(self, "any", any_of)

    @property
    def criterion(self) -> str:
        """Legacy alias for :attr:`field`."""
        return self.field

    @property
    def threshold(self) -> Any:
        """Legacy alias for :attr:`value`."""
        return self.value

    @property
    def description(self) -> str | None:
        """Legacy alias for :attr:`reason`."""
        return self.reason

    def matches(
        self,
        values: Mapping[str, Any],
        context: ContextMapping | None = None,
    ) -> bool:
        """Return whether alternative ``values`` satisfy this constraint."""
        return evaluate_conditions(
            rule_name=self.name,
            values=values,
            context=context or {},
            single=self._single_condition(),
            all_of=self.all,
            any_of=self.any,
            missing_as_false=True,
        )

    def is_satisfied(self, value: float) -> bool:
        """Legacy helper for simple numeric constraints."""
        if self.all is not None or self.any is not None or not self.field:
            raise ValidationError(
                f"Constraint '{self.name}' is compound; use matches() instead"
            )
        return self.matches({self.field: value})

    def _single_condition(self) -> RuleCondition | None:
        if not self.field:
            return None
        return RuleCondition(
            field=self.field,
            operator=self.operator,
            value=self.value,
            context=self.context,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize this constraint to a JSON-friendly dictionary."""
        payload: dict[str, Any] = {"name": self.name}
        if self.reason is not None:
            payload["reason"] = self.reason
        if self.all is not None:
            payload["all"] = [item.to_dict() for item in self.all]
        elif self.any is not None:
            payload["any"] = [item.to_dict() for item in self.any]
        else:
            payload["field"] = self.field
            payload["operator"] = self.operator
            if self.context is not None:
                payload["context"] = self.context
            else:
                payload["value"] = self.value
        return payload


@dataclass(frozen=True, slots=True)
class Penalty:
    """Soft rule: subtracts ``amount`` from the score when triggered."""

    name: str
    field: str = ""
    operator: ComparisonOp = "eq"
    value: Any = None
    amount: float = 0.0
    context: str | None = None
    reason: str | None = None
    all: tuple[RuleCondition, ...] | None = None
    any: tuple[RuleCondition, ...] | None = None

    def __init__(
        self,
        name: str,
        field: str | None = None,
        operator: ComparisonOp = "eq",
        value: Any = None,
        amount: float = 0.0,
        *,
        criterion: str | None = None,
        threshold: Any = None,
        description: str | None = None,
        reason: str | None = None,
        context: str | None = None,
        all: Sequence[RuleCondition | Mapping[str, Any]] | None = None,
        any: Sequence[RuleCondition | Mapping[str, Any]] | None = None,
    ) -> None:
        if not name or not str(name).strip():
            raise ValidationError("Penalty name must be a non-empty string")
        if field is not None and criterion is not None and field != criterion:
            raise ValidationError(
                f"Penalty '{name}' cannot set both 'field' and 'criterion'"
            )
        if value is not None and threshold is not None and value != threshold:
            raise ValidationError(
                f"Penalty '{name}' cannot set both 'value' and 'threshold'"
            )
        if reason is not None and description is not None and reason != description:
            raise ValidationError(
                f"Penalty '{name}' cannot set both 'reason' and 'description'"
            )

        resolved_field = field if field is not None else criterion
        resolved_value = value if value is not None else threshold
        resolved_reason = reason if reason is not None else description
        amount_value = _validate_finite_number(
            amount, context=f"Penalty '{name}' amount"
        )
        if amount_value <= 0:
            raise ValidationError(
                f"Penalty '{name}' amount must be positive, got {amount_value}"
            )

        single, all_of, any_of = _normalize_conditions(
            rule_name=str(name),
            field=resolved_field,
            operator=operator,
            value=resolved_value,
            context=context,
            all_of=all,
            any_of=any,
        )

        object.__setattr__(self, "name", str(name).strip())
        object.__setattr__(self, "field", single.field if single else "")
        object.__setattr__(
            self, "operator", single.operator if single else operator
        )
        object.__setattr__(self, "value", single.value if single else resolved_value)
        object.__setattr__(self, "amount", amount_value)
        object.__setattr__(
            self, "context", single.context if single else context
        )
        object.__setattr__(self, "reason", resolved_reason)
        object.__setattr__(self, "all", all_of)
        object.__setattr__(self, "any", any_of)

    @property
    def criterion(self) -> str:
        """Legacy alias for :attr:`field`."""
        return self.field

    @property
    def threshold(self) -> Any:
        """Legacy alias for :attr:`value`."""
        return self.value

    @property
    def description(self) -> str | None:
        """Legacy alias for :attr:`reason`."""
        return self.reason

    def matches(
        self,
        values: Mapping[str, Any],
        context: ContextMapping | None = None,
    ) -> bool:
        """Return whether this penalty is triggered."""
        return evaluate_conditions(
            rule_name=self.name,
            values=values,
            context=context or {},
            single=self._single_condition(),
            all_of=self.all,
            any_of=self.any,
            missing_as_false=True,
        )

    def is_triggered(self, value: float) -> bool:
        """Legacy helper for simple numeric penalties."""
        if self.all is not None or self.any is not None or not self.field:
            raise ValidationError(
                f"Penalty '{self.name}' is compound; use matches() instead"
            )
        return self.matches({self.field: value})

    def _single_condition(self) -> RuleCondition | None:
        if not self.field:
            return None
        return RuleCondition(
            field=self.field,
            operator=self.operator,
            value=self.value,
            context=self.context,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize this penalty to a JSON-friendly dictionary."""
        payload: dict[str, Any] = {
            "name": self.name,
            "amount": self.amount,
        }
        if self.reason is not None:
            payload["reason"] = self.reason
        if self.all is not None:
            payload["all"] = [item.to_dict() for item in self.all]
        elif self.any is not None:
            payload["any"] = [item.to_dict() for item in self.any]
        else:
            payload["field"] = self.field
            payload["operator"] = self.operator
            if self.context is not None:
                payload["context"] = self.context
            else:
                payload["value"] = self.value
        return payload


@dataclass(frozen=True, slots=True)
class Bonus:
    """Soft rule: adds ``amount`` to the score when triggered."""

    name: str
    field: str = ""
    operator: ComparisonOp = "eq"
    value: Any = None
    amount: float = 0.0
    context: str | None = None
    reason: str | None = None
    all: tuple[RuleCondition, ...] | None = None
    any: tuple[RuleCondition, ...] | None = None

    def __init__(
        self,
        name: str,
        field: str | None = None,
        operator: ComparisonOp = "eq",
        value: Any = None,
        amount: float = 0.0,
        *,
        reason: str | None = None,
        description: str | None = None,
        context: str | None = None,
        all: Sequence[RuleCondition | Mapping[str, Any]] | None = None,
        any: Sequence[RuleCondition | Mapping[str, Any]] | None = None,
    ) -> None:
        if not name or not str(name).strip():
            raise ValidationError("Bonus name must be a non-empty string")
        if reason is not None and description is not None and reason != description:
            raise ValidationError(
                f"Bonus '{name}' cannot set both 'reason' and 'description'"
            )

        resolved_reason = reason if reason is not None else description
        amount_value = _validate_finite_number(
            amount, context=f"Bonus '{name}' amount"
        )
        if amount_value <= 0:
            raise ValidationError(
                f"Bonus '{name}' amount must be positive, got {amount_value}"
            )

        single, all_of, any_of = _normalize_conditions(
            rule_name=str(name),
            field=field,
            operator=operator,
            value=value,
            context=context,
            all_of=all,
            any_of=any,
        )

        object.__setattr__(self, "name", str(name).strip())
        object.__setattr__(self, "field", single.field if single else "")
        object.__setattr__(
            self, "operator", single.operator if single else operator
        )
        object.__setattr__(self, "value", single.value if single else value)
        object.__setattr__(self, "amount", amount_value)
        object.__setattr__(
            self, "context", single.context if single else context
        )
        object.__setattr__(self, "reason", resolved_reason)
        object.__setattr__(self, "all", all_of)
        object.__setattr__(self, "any", any_of)

    @property
    def description(self) -> str | None:
        """Alias for :attr:`reason`."""
        return self.reason

    def matches(
        self,
        values: Mapping[str, Any],
        context: ContextMapping | None = None,
    ) -> bool:
        """Return whether this bonus is triggered."""
        return evaluate_conditions(
            rule_name=self.name,
            values=values,
            context=context or {},
            single=self._single_condition(),
            all_of=self.all,
            any_of=self.any,
            missing_as_false=True,
        )

    def _single_condition(self) -> RuleCondition | None:
        if not self.field:
            return None
        return RuleCondition(
            field=self.field,
            operator=self.operator,
            value=self.value,
            context=self.context,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize this bonus to a JSON-friendly dictionary."""
        payload: dict[str, Any] = {
            "name": self.name,
            "amount": self.amount,
        }
        if self.reason is not None:
            payload["reason"] = self.reason
        if self.all is not None:
            payload["all"] = [item.to_dict() for item in self.all]
        elif self.any is not None:
            payload["any"] = [item.to_dict() for item in self.any]
        else:
            payload["field"] = self.field
            payload["operator"] = self.operator
            if self.context is not None:
                payload["context"] = self.context
            else:
                payload["value"] = self.value
        return payload


@dataclass(frozen=True, slots=True)
class Alternative:
    """A scored option identified by ``id`` with arbitrary field values."""

    id: str
    values: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id or not str(self.id).strip():
            raise ValidationError("Alternative id must be a non-empty string")
        cleaned = {str(key): value for key, value in self.values.items()}
        object.__setattr__(self, "id", str(self.id).strip())
        object.__setattr__(self, "values", cleaned)

    def get(self, key: str) -> Any:
        """Return the value for ``key``."""
        return self.values[key]


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
    triggered_bonuses: tuple[str, ...] = ()
    text: str = ""


@dataclass(frozen=True, slots=True)
class RankedAlternative:
    """One alternative after scoring and ranking."""

    id: str
    score: float
    rank: int
    values: dict[str, Any]
    normalized_values: dict[str, float]
    contributions: dict[str, float]
    base_score: float | None = None
    triggered_penalties: tuple[str, ...] = ()
    triggered_bonuses: tuple[str, ...] = ()
    penalty_total: float = 0.0
    bonus_total: float = 0.0
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
    model:
        Snapshot of the model configuration used for this decision.
    input_ids:
        Alternative ids in input order.
    context:
        Context mapping supplied to :meth:`DecisionModel.rank`.
    """

    ranking: tuple[RankedAlternative, ...]
    method: MethodName
    excluded: tuple[tuple[str, str], ...] = ()
    model: dict[str, Any] = field(default_factory=dict)
    input_ids: tuple[str, ...] = ()
    context: dict[str, Any] = field(default_factory=dict)

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
                    "base_score": item.base_score,
                    "values": dict(item.values),
                    "normalized_values": dict(item.normalized_values),
                    "contributions": dict(item.contributions),
                    "triggered_penalties": list(item.triggered_penalties),
                    "triggered_bonuses": list(item.triggered_bonuses),
                    "penalty_total": item.penalty_total,
                    "bonus_total": item.bonus_total,
                    "explanation": (
                        item.explanation.text if item.explanation else None
                    ),
                }
                for item in self.ranking
            ],
            "excluded": [
                {"id": alt_id, "reason": reason}
                for alt_id, reason in self.excluded
            ],
        }

    def to_audit_dict(
        self,
        *,
        decision_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        """Return a stable, JSON-serializable audit record.

        Parameters
        ----------
        decision_id:
            Optional caller-supplied decision identifier.
        metadata:
            Optional caller-supplied metadata (must be JSON-serializable).
        timestamp:
            Optional caller-supplied timestamp string. DecisionKit does not
            invent timestamps, so audits stay deterministic unless you inject
            one.
        """
        from decisionkit.audit import build_audit_dict

        return build_audit_dict(
            self,
            decision_id=decision_id,
            metadata=metadata,
            timestamp=timestamp,
        )
