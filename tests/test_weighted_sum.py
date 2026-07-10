"""Tests for weighted sum ranking."""

from __future__ import annotations

from decisionkit import Criterion, DecisionModel


def test_weighted_sum_basic_ranking() -> None:
    model = DecisionModel(
        criteria=[
            Criterion("quality", weight=0.6, direction="max"),
            Criterion("cost", weight=0.4, direction="min"),
        ],
        method="weighted_sum",
        explain=True,
    )
    result = model.rank(
        [
            {"id": "cheap_ok", "quality": 6, "cost": 10},
            {"id": "premium", "quality": 10, "cost": 50},
            {"id": "balanced", "quality": 8, "cost": 20},
        ]
    )

    assert result.method == "weighted_sum"
    assert len(result.ranking) == 3
    assert result.ranking[0].rank == 1
    assert result.best.id == result.ranking[0].id
    scores = [item.score for item in result.ranking]
    assert scores == sorted(scores, reverse=True)


def test_weighted_sum_prefers_higher_max_criterion() -> None:
    model = DecisionModel(
        criteria=[
            Criterion("score", weight=1.0, direction="max"),
        ],
        method="weighted_sum",
        explain=False,
    )
    result = model.rank(
        [
            {"id": "low", "score": 1},
            {"id": "high", "score": 9},
        ]
    )
    assert result.best.id == "high"
    assert result.ranking[0].score == 1.0
    assert result.ranking[1].score == 0.0


def test_min_direction_prefers_lower_raw_value() -> None:
    model = DecisionModel(
        criteria=[
            Criterion("workload", weight=1.0, direction="min"),
        ],
        method="weighted_sum",
    )
    result = model.rank(
        [
            {"id": "busy", "workload": 9},
            {"id": "free", "workload": 2},
        ]
    )
    assert result.best.id == "free"
    assert result.ranking[0].normalized_values["workload"] == 1.0
    assert result.ranking[1].normalized_values["workload"] == 0.0


def test_reviewer_selection_scenario() -> None:
    model = DecisionModel(
        criteria=[
            Criterion("relevance", weight=0.5, direction="max"),
            Criterion("rating", weight=0.3, direction="max"),
            Criterion("workload", weight=0.2, direction="min"),
        ],
        method="weighted_sum",
    )
    result = model.rank(
        [
            {"id": "reviewer_1", "relevance": 0.92, "rating": 4.8, "workload": 7},
            {"id": "reviewer_2", "relevance": 0.81, "rating": 4.5, "workload": 2},
        ]
    )
    assert {item.id for item in result.ranking} == {"reviewer_1", "reviewer_2"}
    assert result.best.score >= result.ranking[1].score
    assert "relevance" in result.best.contributions
    assert "workload" in result.best.normalized_values


def test_equal_values_produce_equal_normalized_scores() -> None:
    model = DecisionModel(
        criteria=[Criterion("x", weight=1.0, direction="max")],
        method="weighted_sum",
        explain=False,
    )
    result = model.rank(
        [
            {"id": "a", "x": 5},
            {"id": "b", "x": 5},
        ]
    )
    assert result.ranking[0].score == result.ranking[1].score == 1.0
