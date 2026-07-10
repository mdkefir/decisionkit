"""Tests for input and configuration validation."""

from __future__ import annotations

import pytest

from decisionkit import (
    Constraint,
    Criterion,
    DecisionModel,
    DuplicateAlternativeError,
    DuplicateCriterionError,
    EmptyAlternativesError,
    InvalidDirectionError,
    InvalidValueError,
    InvalidWeightError,
    MissingValueError,
    Penalty,
    UnknownMethodError,
    ValidationError,
)


def test_invalid_weight_rejected() -> None:
    with pytest.raises(InvalidWeightError):
        Criterion("x", weight=0)
    with pytest.raises(InvalidWeightError):
        Criterion("x", weight=-1)


def test_invalid_direction_rejected() -> None:
    with pytest.raises(InvalidDirectionError):
        Criterion("x", weight=1, direction="sideways")  # type: ignore[arg-type]


def test_duplicate_criteria_rejected() -> None:
    with pytest.raises(DuplicateCriterionError):
        DecisionModel(
            criteria=[
                Criterion("a", weight=1),
                Criterion("a", weight=2),
            ]
        )


def test_unknown_method_rejected() -> None:
    with pytest.raises(UnknownMethodError):
        DecisionModel(
            criteria=[Criterion("a", weight=1)],
            method="ahp",  # type: ignore[arg-type]
        )


def test_missing_criterion_value() -> None:
    model = DecisionModel(criteria=[Criterion("score", weight=1)])
    with pytest.raises(MissingValueError, match="missing required criterion"):
        model.rank([{"id": "a", "other": 1}])


def test_non_numeric_value_rejected() -> None:
    model = DecisionModel(criteria=[Criterion("score", weight=1)])
    with pytest.raises(InvalidValueError):
        model.rank([{"id": "a", "score": "good"}])


def test_nan_and_inf_rejected() -> None:
    model = DecisionModel(criteria=[Criterion("score", weight=1)])
    with pytest.raises(InvalidValueError):
        model.rank([{"id": "a", "score": float("nan")}])
    with pytest.raises(InvalidValueError):
        model.rank([{"id": "a", "score": float("inf")}])


def test_empty_alternatives_rejected() -> None:
    model = DecisionModel(criteria=[Criterion("score", weight=1)])
    with pytest.raises(EmptyAlternativesError):
        model.rank([])


def test_duplicate_alternative_ids_rejected() -> None:
    model = DecisionModel(criteria=[Criterion("score", weight=1)])
    with pytest.raises(DuplicateAlternativeError):
        model.rank(
            [
                {"id": "a", "score": 1},
                {"id": "a", "score": 2},
            ]
        )


def test_missing_alternative_id_rejected() -> None:
    model = DecisionModel(criteria=[Criterion("score", weight=1)])
    with pytest.raises(ValidationError, match="id"):
        model.rank([{"score": 1}])


def test_constraint_excludes_alternatives() -> None:
    model = DecisionModel(
        criteria=[
            Criterion("rating", weight=1.0, direction="max"),
        ],
        constraints=[
            Constraint(
                name="min_rating",
                criterion="rating",
                operator="gte",
                threshold=4.0,
            )
        ],
    )
    result = model.rank(
        [
            {"id": "ok", "rating": 4.5},
            {"id": "low", "rating": 3.0},
        ]
    )
    assert result.best.id == "ok"
    assert len(result.ranking) == 1
    assert result.excluded[0][0] == "low"


def test_penalty_reduces_score_and_can_change_order() -> None:
    model = DecisionModel(
        criteria=[Criterion("score", weight=1.0, direction="max")],
        penalties=[
            Penalty(
                name="overload",
                criterion="score",
                operator="gt",
                threshold=8,
                amount=0.9,
            )
        ],
        explain=True,
    )
    result = model.rank(
        [
            {"id": "high_penalized", "score": 10},
            {"id": "mid", "score": 7},
        ]
    )
    # Without penalty: high=1.0, mid=0.0. With 0.9 penalty: high=0.1, mid=0.0.
    # Larger penalty flips the winner.
    model_flip = DecisionModel(
        criteria=[Criterion("score", weight=1.0, direction="max")],
        penalties=[
            Penalty(
                name="overload",
                criterion="score",
                operator="gt",
                threshold=8,
                amount=1.1,
            )
        ],
    )
    flipped = model_flip.rank(
        [
            {"id": "high_penalized", "score": 10},
            {"id": "mid", "score": 7},
        ]
    )
    assert result.best.id == "high_penalized"
    assert "overload" in result.best.triggered_penalties
    assert flipped.best.id == "mid"
    assert "Penalties applied: overload" in result.explain()


def test_all_excluded_raises() -> None:
    model = DecisionModel(
        criteria=[Criterion("rating", weight=1.0)],
        constraints=[
            Constraint(
                name="impossible",
                criterion="rating",
                operator="gt",
                threshold=100,
            )
        ],
    )
    with pytest.raises(ValidationError, match="excluded"):
        model.rank([{"id": "a", "rating": 1}])
