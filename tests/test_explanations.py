"""Tests for explanation output."""

from __future__ import annotations

from decisionkit import Criterion, DecisionModel, DecisionResult


def _reviewer_model() -> DecisionModel:
    return DecisionModel(
        criteria=[
            Criterion("relevance", weight=0.5, direction="max"),
            Criterion("rating", weight=0.3, direction="max"),
            Criterion("workload", weight=0.2, direction="min"),
        ],
        method="weighted_sum",
        explain=True,
    )


def test_explanation_contains_rank_score_and_criteria() -> None:
    model = _reviewer_model()
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


def test_explanations_use_normalized_strength_not_raw_labels() -> None:
    model = _reviewer_model()
    result = model.rank(
        [
            {"id": "alice", "relevance": 0.92, "rating": 4.8, "workload": 7},
            {"id": "bob", "relevance": 0.92, "rating": 3.8, "workload": 3},
            {"id": "james", "relevance": 0.32, "rating": 4.8, "workload": 2},
            {"id": "john", "relevance": 0.52, "rating": 4.0, "workload": 8},
        ]
    )
    by_id = {item.id: item for item in result.ranking}

    alice = by_id["alice"].explanation
    bob = by_id["bob"].explanation
    james = by_id["james"].explanation
    john = by_id["john"].explanation
    assert alice is not None and bob is not None
    assert james is not None and john is not None

    assert alice.normalized_values["relevance"] >= 0.67
    assert alice.normalized_values["rating"] >= 0.67
    assert alice.normalized_values["workload"] <= 0.33
    assert "strong relevance" in alice.text
    assert "rating" in alice.text
    assert "workload did not help much" in alice.text

    assert bob.normalized_values["rating"] == 0.0
    assert "strong rating" not in bob.text
    assert "strong relevance" in bob.text
    assert "weak rating" in bob.text
    assert "lower workload improved" in bob.text

    assert james.normalized_values["relevance"] == 0.0
    assert "strong relevance" not in james.text
    assert "strong rating" in james.text
    assert "weak relevance" in james.text
    assert "lower workload improved" in james.text

    assert john.normalized_values["relevance"] < 0.67
    assert john.normalized_values["rating"] < 0.67
    assert "strong relevance" not in john.text
    assert "strong rating" not in john.text
    assert "weak rating" in john.text or "did not help much" in john.text


def test_input_alternative_ids_preserves_caller_order() -> None:
    model = _reviewer_model()
    ordered = [
        {"id": "john", "relevance": 0.52, "rating": 4.0, "workload": 8},
        {"id": "james", "relevance": 0.32, "rating": 4.8, "workload": 2},
        {"id": "bob", "relevance": 0.92, "rating": 3.8, "workload": 3},
        {"id": "alice", "relevance": 0.92, "rating": 4.8, "workload": 7},
    ]
    result = model.rank(ordered)
    assert result.input_ids == ("john", "james", "bob", "alice")
    audit = result.to_audit_dict()
    assert audit["input_alternative_ids"] == [
        "john",
        "james",
        "bob",
        "alice",
    ]
    # Ranking order is by score, not input order.
    assert [item.id for item in result.ranking] != list(result.input_ids)
