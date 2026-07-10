"""Backward-compatibility checks for the v0.1.0 public API."""

from __future__ import annotations

from decisionkit import Constraint, Criterion, DecisionModel, Penalty


def test_v010_constructor_and_rank_still_work() -> None:
    model = DecisionModel(
        criteria=[
            Criterion("relevance", weight=0.5, direction="max"),
            Criterion("rating", weight=0.3, direction="max"),
            Criterion("workload", weight=0.2, direction="min"),
        ],
        method="weighted_sum",
        explain=True,
    )
    result = model.rank(
        [
            {"id": "reviewer_1", "relevance": 0.92, "rating": 4.8, "workload": 7},
            {"id": "reviewer_2", "relevance": 0.81, "rating": 4.5, "workload": 2},
        ]
    )
    assert result.best.id == "reviewer_1"
    assert result.explain()
    assert result.to_dict()["best"] == "reviewer_1"


def test_v010_constraint_and_penalty_kwargs_still_work() -> None:
    model = DecisionModel(
        criteria=[Criterion("rating", weight=1.0)],
        constraints=[
            Constraint(
                name="min_rating",
                criterion="rating",
                operator="gte",
                threshold=4.0,
                description="legacy description",
            )
        ],
        penalties=[
            Penalty(
                name="too_high",
                criterion="rating",
                operator="gt",
                threshold=4.8,
                amount=0.05,
                description="legacy penalty",
            )
        ],
    )
    result = model.rank(
        [
            {"id": "ok", "rating": 4.5},
            {"id": "star", "rating": 5.0},
            {"id": "low", "rating": 3.0},
        ]
    )
    assert {item.id for item in result.ranking} == {"ok", "star"}
    assert result.excluded[0][0] == "low"
    star = next(item for item in result.ranking if item.id == "star")
    assert "too_high" in star.triggered_penalties
