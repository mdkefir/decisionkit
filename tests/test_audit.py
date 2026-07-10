"""Tests for audit export."""

from __future__ import annotations

import json

import pytest

from decisionkit import Criterion, DecisionModel, ValidationError
from decisionkit.audit import compute_audit_hash


def test_to_audit_dict_schema_and_json_serializable() -> None:
    model = DecisionModel.from_dict(
        {
            "method": "weighted_sum",
            "criteria": [
                {"name": "relevance", "weight": 0.5, "direction": "max"},
                {"name": "workload", "weight": 0.5, "direction": "min"},
            ],
            "constraints": [
                {
                    "name": "available_only",
                    "field": "available",
                    "operator": "eq",
                    "value": True,
                    "reason": "Must be available",
                }
            ],
            "penalties": [
                {
                    "name": "busy",
                    "field": "workload",
                    "operator": "gt",
                    "value": 5,
                    "amount": 0.1,
                }
            ],
            "bonuses": [
                {
                    "name": "topic",
                    "field": "topic_match",
                    "operator": "gte",
                    "value": 0.9,
                    "amount": 0.05,
                }
            ],
        }
    )
    result = model.rank(
        [
            {
                "id": "a",
                "relevance": 0.9,
                "workload": 7,
                "available": True,
                "topic_match": 0.95,
            },
            {
                "id": "b",
                "relevance": 0.8,
                "workload": 2,
                "available": False,
                "topic_match": 0.5,
            },
        ],
        context={"max_workload": 5},
    )

    audit = result.to_audit_dict(
        decision_id="dec-123",
        metadata={"source": "test"},
        timestamp="2026-07-10T10:00:00Z",
    )

    assert audit["schema_version"] == "1.0"
    assert audit["decision_id"] == "dec-123"
    assert audit["timestamp"] == "2026-07-10T10:00:00Z"
    assert audit["metadata"] == {"source": "test"}
    assert audit["method"] == "weighted_sum"
    assert audit["model"]["criteria"][0]["name"] == "relevance"
    assert audit["context"] == {"max_workload": 5}
    assert audit["input_alternative_ids"] == ["a", "b"]
    assert audit["excluded"][0]["id"] == "b"
    assert audit["best"]["id"] == result.best.id
    assert "base_score" in audit["ranking"][0]
    assert "contributions" in audit["ranking"][0]

    encoded = json.dumps(audit)
    assert "dec-123" in encoded


def test_audit_without_timestamp_stays_deterministic() -> None:
    model = DecisionModel(criteria=[Criterion("x", weight=1.0)])
    result = model.rank([{"id": "a", "x": 1}, {"id": "b", "x": 2}])
    first = result.to_audit_dict(decision_id="same")
    second = result.to_audit_dict(decision_id="same")
    assert first == second
    assert first["timestamp"] is None


def test_audit_hash_is_deterministic_and_ignores_envelope() -> None:
    model = DecisionModel(criteria=[Criterion("x", weight=1.0)])
    result = model.rank([{"id": "a", "x": 1}, {"id": "b", "x": 2}])

    h1 = result.audit_hash()
    h2 = result.audit_hash()
    assert h1 == h2
    assert len(h1) == 64

    audit_a = result.to_audit_dict(decision_id="one", metadata={"a": 1})
    audit_b = result.to_audit_dict(
        decision_id="two",
        metadata={"b": 2},
        timestamp="2026-07-10T10:00:00Z",
    )
    assert compute_audit_hash(audit_a) == compute_audit_hash(audit_b) == h1


def test_to_audit_dict_include_hash() -> None:
    model = DecisionModel(criteria=[Criterion("x", weight=1.0)])
    result = model.rank([{"id": "a", "x": 3}, {"id": "b", "x": 1}])
    audit = result.to_audit_dict(include_hash=True)
    assert audit["audit_hash"]["algorithm"] == "sha256"
    assert audit["audit_hash"]["digest"] == result.audit_hash()


def test_audit_hash_can_include_timestamp() -> None:
    model = DecisionModel(criteria=[Criterion("x", weight=1.0)])
    result = model.rank([{"id": "a", "x": 1}, {"id": "b", "x": 2}])
    plain = result.audit_hash()
    stamped = result.audit_hash(
        include_timestamp=True,
        timestamp="2026-07-10T10:00:00Z",
    )
    assert plain != stamped


def test_unsupported_hash_algorithm_raises() -> None:
    model = DecisionModel(criteria=[Criterion("x", weight=1.0)])
    result = model.rank([{"id": "a", "x": 1}, {"id": "b", "x": 2}])
    with pytest.raises(ValidationError, match="Unsupported hash algorithm"):
        result.audit_hash(algorithm="md5")
