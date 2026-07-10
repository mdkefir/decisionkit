"""Tests for explanation output."""

from __future__ import annotations

from decisionkit import Criterion, DecisionModel, DecisionResult


def test_explanation_contains_rank_score_and_criteria() -> None:
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

    text = result.explain()
    assert "ranked #1" in text
    assert "score" in text
    assert result.best.explanation is not None
    assert result.best.explanation.normalized_values
    assert result.best.explanation.contributions
    assert result.best.id in text


def test_explain_false_skips_structured_explanation() -> None:
    model = DecisionModel(
        criteria=[Criterion("x", weight=1.0)],
        explain=False,
    )
    result = model.rank([{"id": "a", "x": 1}, {"id": "b", "x": 2}])
    assert result.best.explanation is None
    assert "ranked #1" in result.explain()


def test_result_to_dict_is_json_friendly() -> None:
    model = DecisionModel(
        criteria=[
            Criterion("quality", weight=1.0, direction="max"),
        ],
        explain=True,
    )
    result = model.rank([{"id": "a", "quality": 3}, {"id": "b", "quality": 9}])
    payload = result.to_dict()
    assert payload["best"] == result.best.id
    assert payload["method"] == "weighted_sum"
    assert isinstance(payload["ranking"], list)
    assert payload["ranking"][0]["id"] == result.best.id
    assert "explanation" in payload["ranking"][0]


def test_decision_result_best_requires_ranking() -> None:
    empty = DecisionResult(ranking=(), method="weighted_sum")
    try:
        _ = empty.best
        raised = False
    except Exception:
        raised = True
    assert raised
