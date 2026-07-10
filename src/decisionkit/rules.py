"""Deterministic rule evaluation for constraints, penalties, and bonuses."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from decisionkit.exceptions import ValidationError
from decisionkit.typing import ComparisonOp, ContextMapping

SUPPORTED_OPERATORS: frozenset[str] = frozenset(
    {
        "eq",
        "ne",
        "gt",
        "gte",
        "lt",
        "lte",
        "in",
        "not_in",
        "contains",
        "between",
    }
)


def _require_operator(operator: str, *, rule_name: str) -> ComparisonOp:
    if operator not in SUPPORTED_OPERATORS:
        supported = ", ".join(sorted(SUPPORTED_OPERATORS))
        raise ValidationError(
            f"Rule '{rule_name}' operator must be one of {supported}; "
            f"got {operator!r}"
        )
    return operator  # type: ignore[return-value]


def compare(operator: ComparisonOp, left: Any, right: Any) -> bool:
    """Evaluate ``left <op> right`` without using eval."""
    if operator == "eq":
        return left == right
    if operator == "ne":
        return left != right
    if operator == "gt":
        return left > right
    if operator == "gte":
        return left >= right
    if operator == "lt":
        return left < right
    if operator == "lte":
        return left <= right
    if operator == "in":
        if not isinstance(right, (list, tuple, set, frozenset)):
            raise ValidationError(
                f"'in' operator expects a sequence on the right, got "
                f"{type(right).__name__}"
            )
        return left in right
    if operator == "not_in":
        if not isinstance(right, (list, tuple, set, frozenset)):
            raise ValidationError(
                f"'not_in' operator expects a sequence on the right, got "
                f"{type(right).__name__}"
            )
        return left not in right
    if operator == "contains":
        if left is None:
            return False
        try:
            return right in left
        except TypeError as exc:
            raise ValidationError(
                f"'contains' operator requires a container on the left, got "
                f"{type(left).__name__}"
            ) from exc
    if operator == "between":
        if not isinstance(right, (list, tuple)) or len(right) != 2:
            raise ValidationError(
                "'between' operator expects a two-item sequence [low, high]"
            )
        low, high = right
        return low <= left <= high
    raise ValidationError(f"Unsupported operator: {operator!r}")


@dataclass(frozen=True, slots=True)
class RuleCondition:
    """Atomic comparison used by constraints, penalties, and bonuses.

    Parameters
    ----------
    field:
        Alternative field name to read.
    operator:
        Comparison operator.
    value:
        Literal right-hand value. Ignored when ``context`` is set.
    context:
        Context key whose value is used as the right-hand side.
    """

    field: str
    operator: ComparisonOp = "eq"
    value: Any = None
    context: str | None = None

    def __post_init__(self) -> None:
        if not self.field or not str(self.field).strip():
            raise ValidationError("Rule condition field must be a non-empty string")
        operator = _require_operator(self.operator, rule_name=self.field)
        if self.context is not None and (
            not self.context or not str(self.context).strip()
        ):
            raise ValidationError(
                f"Rule condition on '{self.field}' has an empty context key"
            )
        if self.context is None and self.value is None and operator not in {
            "eq",
            "ne",
        }:
            # Allow value=None only for equality checks (e.g. field is null).
            pass
        object.__setattr__(self, "field", str(self.field).strip())
        object.__setattr__(self, "operator", operator)
        if self.context is not None:
            object.__setattr__(self, "context", str(self.context).strip())

    def to_dict(self) -> dict[str, Any]:
        """Serialize this condition to a JSON-friendly dictionary."""
        payload: dict[str, Any] = {
            "field": self.field,
            "operator": self.operator,
        }
        if self.context is not None:
            payload["context"] = self.context
        else:
            payload["value"] = self.value
        return payload


def condition_from_mapping(
    raw: Mapping[str, Any],
    *,
    rule_name: str,
) -> RuleCondition:
    """Build a :class:`RuleCondition` from a config mapping."""
    if not isinstance(raw, Mapping):
        raise ValidationError(
            f"Rule '{rule_name}' condition must be a mapping, "
            f"got {type(raw).__name__}"
        )

    field = raw.get("field", raw.get("criterion"))
    if field is None:
        raise ValidationError(
            f"Rule '{rule_name}' condition requires 'field' (or legacy 'criterion')"
        )

    if "value" in raw and "threshold" in raw:
        raise ValidationError(
            f"Rule '{rule_name}' condition cannot set both 'value' and 'threshold'"
        )
    if "value" in raw:
        value: Any = raw["value"]
    elif "threshold" in raw:
        value = raw["threshold"]
    else:
        value = None

    context = raw.get("context")
    if context is not None and "value" in raw and raw.get("value") is not None:
        # Explicit context wins; value may still be present for documentation,
        # but we prefer a clear error if both are meaningfully set.
        if "threshold" in raw:
            raise ValidationError(
                f"Rule '{rule_name}' condition cannot mix context with threshold"
            )

    operator = raw.get("operator", "eq")
    return RuleCondition(
        field=str(field),
        operator=operator,
        value=value,
        context=str(context) if context is not None else None,
    )


def resolve_right_hand(
    condition: RuleCondition,
    context: ContextMapping,
    *,
    rule_name: str,
) -> Any:
    """Resolve the comparison target from a literal or context key."""
    if condition.context is None:
        return condition.value
    if condition.context not in context:
        raise ValidationError(
            f"Rule '{rule_name}' references missing context key "
            f"'{condition.context}'"
        )
    return context[condition.context]


def evaluate_condition(
    condition: RuleCondition,
    values: Mapping[str, Any],
    context: ContextMapping,
    *,
    rule_name: str,
    missing_as_false: bool = True,
) -> bool:
    """Evaluate one condition against alternative values and context."""
    if condition.field not in values:
        if missing_as_false:
            return False
        raise ValidationError(
            f"Rule '{rule_name}' requires field '{condition.field}'"
        )
    left = values[condition.field]
    right = resolve_right_hand(condition, context, rule_name=rule_name)
    try:
        return compare(condition.operator, left, right)
    except TypeError as exc:
        raise ValidationError(
            f"Rule '{rule_name}' cannot compare field '{condition.field}' "
            f"({type(left).__name__}) with {right!r} using "
            f"'{condition.operator}'"
        ) from exc


def evaluate_conditions(
    *,
    rule_name: str,
    values: Mapping[str, Any],
    context: ContextMapping,
    single: RuleCondition | None = None,
    all_of: Sequence[RuleCondition] | None = None,
    any_of: Sequence[RuleCondition] | None = None,
    missing_as_false: bool = True,
) -> bool:
    """Evaluate a simple or compound rule."""
    groups = sum(1 for item in (single, all_of, any_of) if item)
    if groups == 0:
        raise ValidationError(f"Rule '{rule_name}' has no conditions")
    if groups > 1:
        raise ValidationError(
            f"Rule '{rule_name}' must use exactly one of: single condition, "
            f"'all', or 'any'"
        )

    if single is not None:
        return evaluate_condition(
            single,
            values,
            context,
            rule_name=rule_name,
            missing_as_false=missing_as_false,
        )
    if all_of is not None:
        if not all_of:
            raise ValidationError(f"Rule '{rule_name}' 'all' list cannot be empty")
        return all(
            evaluate_condition(
                condition,
                values,
                context,
                rule_name=rule_name,
                missing_as_false=missing_as_false,
            )
            for condition in all_of
        )
    assert any_of is not None
    if not any_of:
        raise ValidationError(f"Rule '{rule_name}' 'any' list cannot be empty")
    return any(
        evaluate_condition(
            condition,
            values,
            context,
            rule_name=rule_name,
            missing_as_false=missing_as_false,
        )
        for condition in any_of
    )
