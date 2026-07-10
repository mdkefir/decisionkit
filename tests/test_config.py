"""Tests for config loading and serialization."""

from __future__ import annotations

import json
from typing import Any

import pytest

from decisionkit import (
    Criterion,
    DecisionModel,
    DependencyMissingError,
    ValidationError,
)

SAMPLE_CONFIG: dict[str, Any] = {
    "method": "weighted_sum",
    "explain": True,
    "criteria": [
        {"name": "relevance", "weight": 0.5, "direction": "max"},
        {"name": "rating", "weight": 0.3, "direction": "max"},
        {"name": "workload", "weight": 0.2, "direction": "min"},
    ],
    "constraints": [
        {
            "name": "available_only",
            "field": "available",
            "operator": "eq",
            "value": True,
            "reason": "Reviewer must be available",
        }
    ],
    "penalties": [
        {
            "name": "high_workload_penalty",
            "field": "workload",
            "operator": "gt",
            "value": 5,
            "amount": 0.1,
            "reason": "High workload reduces recommendation score",
        }
    ],
    "bonuses": [
        {
            "name": "exact_topic_bonus",
            "field": "topic_match",
            "operator": "gte",
            "value": 0.9,
            "amount": 0.05,
            "reason": "Very strong topic match",
        }
    ],
}


def test_from_dict_and_to_dict_roundtrip() -> None:
    model = DecisionModel.from_dict(SAMPLE_CONFIG)
    payload = model.to_dict()
    assert payload["method"] == "weighted_sum"
    assert len(payload["criteria"]) == 3
    assert payload["constraints"][0]["field"] == "available"
    assert payload["penalties"][0]["amount"] == 0.1
    assert payload["bonuses"][0]["name"] == "exact_topic_bonus"

    again = DecisionModel.from_dict(payload)
    assert again.to_dict() == payload


def test_from_json_and_to_json() -> None:
    model = DecisionModel.from_json(json.dumps(SAMPLE_CONFIG))
    text = model.to_json()
    restored = DecisionModel.from_json(text)
    assert restored.to_dict() == model.to_dict()


def test_from_dict_accepts_legacy_criterion_threshold_keys() -> None:
    model = DecisionModel.from_dict(
        {
            "criteria": [{"name": "rating", "weight": 1.0}],
            "constraints": [
                {
                    "name": "min_rating",
                    "criterion": "rating",
                    "operator": "gte",
                    "threshold": 4.0,
                    "description": "legacy",
                }
            ],
            "penalties": [
                {
                    "name": "busy",
                    "criterion": "rating",
                    "operator": "gt",
                    "threshold": 4.9,
                    "amount": 0.01,
                }
            ],
        }
    )
    assert model.constraints[0].field == "rating"
    assert model.constraints[0].value == 4.0
    assert model.constraints[0].reason == "legacy"
    assert model.penalties[0].criterion == "rating"


def test_invalid_json_raises() -> None:
    with pytest.raises(ValidationError, match="Invalid JSON"):
        DecisionModel.from_json("{not-json")


def test_yaml_roundtrip_when_available() -> None:
    pytest.importorskip("yaml")
    model = DecisionModel.from_dict(SAMPLE_CONFIG)
    yaml_text = model.to_yaml()
    restored = DecisionModel.from_yaml(yaml_text)
    assert restored.to_dict() == model.to_dict()


def test_yaml_missing_dependency_message(monkeypatch: pytest.MonkeyPatch) -> None:
    def _missing() -> None:
        raise DependencyMissingError(
            "YAML support requires PyYAML. Install it with: pip install "
            "'decisionkit[yaml]'"
        )

    monkeypatch.setattr("decisionkit.config._load_yaml", _missing)
    model = DecisionModel(criteria=[Criterion("x", weight=1.0)])
    with pytest.raises(DependencyMissingError, match="decisionkit\\[yaml\\]"):
        model.to_yaml()
    with pytest.raises(DependencyMissingError, match="decisionkit\\[yaml\\]"):
        DecisionModel.from_yaml("method: weighted_sum\ncriteria: []\n")


def test_config_driven_rank_matches_api_goal() -> None:
    model = DecisionModel.from_dict(SAMPLE_CONFIG)
    result = model.rank(
        [
            {
                "id": "reviewer_1",
                "relevance": 0.92,
                "rating": 4.8,
                "workload": 7,
                "available": True,
                "topic_match": 0.95,
            },
            {
                "id": "reviewer_2",
                "relevance": 0.81,
                "rating": 4.5,
                "workload": 2,
                "available": True,
                "topic_match": 0.8,
            },
            {
                "id": "reviewer_3",
                "relevance": 0.99,
                "rating": 5.0,
                "workload": 1,
                "available": False,
                "topic_match": 1.0,
            },
        ]
    )
    assert result.excluded[0][0] == "reviewer_3"
    reviewer_1 = next(item for item in result.ranking if item.id == "reviewer_1")
    assert "exact_topic_bonus" in reviewer_1.triggered_bonuses
    assert "high_workload_penalty" in reviewer_1.triggered_penalties
    assert result.best.id in {"reviewer_1", "reviewer_2"}
