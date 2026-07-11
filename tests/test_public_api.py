"""Tests for public API import stability across releases."""

from __future__ import annotations

import decisionkit


def test_public_exports_available() -> None:
    assert hasattr(decisionkit, "DecisionModel")
    assert hasattr(decisionkit, "Criterion")
    assert hasattr(decisionkit, "Constraint")
    assert hasattr(decisionkit, "Penalty")
    assert hasattr(decisionkit, "Bonus")
    assert hasattr(decisionkit, "DecisionResult")
    assert hasattr(decisionkit, "ValidationError")
    assert decisionkit.__version__ == "0.3.1"


def test_star_imports_from_package_root() -> None:
    from decisionkit import (  # noqa: F401
        Bonus,
        Constraint,
        Criterion,
        DecisionModel,
        Penalty,
    )

    model = DecisionModel(
        criteria=[Criterion("score", weight=1.0)],
        constraints=[
            Constraint(name="positive", field="score", operator="gt", value=0)
        ],
        penalties=[
            Penalty(
                name="cap",
                field="score",
                operator="gt",
                value=100,
                amount=0.1,
            )
        ],
        bonuses=[
            Bonus(
                name="boost",
                field="score",
                operator="gte",
                value=90,
                amount=0.05,
            )
        ],
    )
    result = model.rank([{"id": "a", "score": 95}])
    assert result.best.id == "a"
