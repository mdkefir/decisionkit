"""Extra edge-case tests to harden validation and coverage."""

from __future__ import annotations

import pytest

from decisionkit import (
    Bonus,
    Constraint,
    Criterion,
    DecisionModel,
    ValidationError,
)
from decisionkit.audit import canonical_json_bytes
from decisionkit.normalization import min_max_normalize, vector_normalize
from decisionkit.rules import RuleCondition, compare


def test_empty_normalization_helpers() -> None:
    assert min_max_normalize([], "max") == []
    assert vector_normalize([]) == []
    assert vector_normalize([0.0, 0.0]) == [0.0, 0.0]


def test_compare_operator_error_paths() -> None:
    with pytest.raises(ValidationError, match="sequence"):
        compare("in", "x", 123)  # type: ignore[arg-type]
    with pytest.raises(ValidationError, match="sequence"):
        compare("not_in", "x", "abc")  # type: ignore[arg-type]
    with pytest.raises(ValidationError, match="two-item"):
        compare("between", 5, [1])
    with pytest.raises(ValidationError, match="container"):
        compare("contains", 5, "x")


def test_rule_condition_rejects_empty_field() -> None:
    with pytest.raises(ValidationError, match="field"):
        RuleCondition(field="", operator="eq", value=1)


def test_compound_rule_rejects_mixed_shapes() -> None:
    with pytest.raises(ValidationError, match="exactly one"):
        Constraint(
            name="bad",
            field="available",
            operator="eq",
            value=True,
            all=[{"field": "x", "operator": "eq", "value": 1}],
        )


def test_bonus_rejects_non_positive_amount() -> None:
    with pytest.raises(ValidationError, match="positive"):
        Bonus(name="b", field="x", operator="eq", value=1, amount=0)


def test_config_rejects_non_mapping() -> None:
    with pytest.raises(ValidationError, match="mapping"):
        DecisionModel.from_dict([])  # type: ignore[arg-type]


def test_canonical_json_rejects_nan() -> None:
    with pytest.raises(ValidationError, match="JSON-serializable"):
        canonical_json_bytes({"x": float("nan")})


def test_empty_criteria_rejected() -> None:
    with pytest.raises(ValidationError, match="at least one criterion"):
        DecisionModel(criteria=[])


def test_criterion_empty_name_rejected() -> None:
    with pytest.raises(ValidationError, match="non-empty"):
        Criterion("", weight=1.0)
