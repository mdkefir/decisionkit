"""Tests for TOPSIS ranking."""

from __future__ import annotations

from decisionkit import Criterion, DecisionModel


def test_topsis_basic_ranking() -> None:
    model = DecisionModel(
        criteria=[
            Criterion("quality", weight=0.5, direction="max"),
            Criterion("price", weight=0.5, direction="min"),
        ],
        method="topsis",
    )
    result = model.rank(
        [
            {"id": "a", "quality": 9, "price": 8},
            {"id": "b", "quality": 7, "price": 3},
            {"id": "c", "quality": 5, "price": 5},
        ]
    )

    assert result.method == "topsis"
    assert len(result.ranking) == 3
    assert result.best.rank == 1
    assert all(0.0 <= item.score <= 1.0 for item in result.ranking)
    scores = [item.score for item in result.ranking]
    assert scores == sorted(scores, reverse=True)


def test_topsis_min_direction() -> None:
    model = DecisionModel(
        criteria=[
            Criterion("delay", weight=1.0, direction="min"),
        ],
        method="topsis",
    )
    result = model.rank(
        [
            {"id": "slow", "delay": 10},
            {"id": "fast", "delay": 1},
        ]
    )
    assert result.best.id == "fast"
    assert result.best.score > result.ranking[1].score


def test_topsis_prefers_dominant_alternative() -> None:
    model = DecisionModel(
        criteria=[
            Criterion("benefit", weight=0.7, direction="max"),
            Criterion("risk", weight=0.3, direction="min"),
        ],
        method="topsis",
    )
    result = model.rank(
        [
            {"id": "weak", "benefit": 2, "risk": 9},
            {"id": "strong", "benefit": 9, "risk": 2},
        ]
    )
    assert result.best.id == "strong"
    assert result.best.contributions
    assert result.best.normalized_values
