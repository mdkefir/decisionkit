"""Django service-layer example with config stored like admin/DB settings.

This module shows how to keep DecisionKit in the service layer of a Django app
without turning DecisionKit into a Django package.

Typical usage:

    from myapp.services.reviewer_ranking import rank_reviewers_from_settings
    result = rank_reviewers_from_settings(candidates, settings_json)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from decisionkit import DecisionModel, DecisionResult


@dataclass(frozen=True)
class ReviewerCandidate:
    """Plain DTO you might build from Django ORM objects."""

    id: str
    relevance: float
    rating: float
    workload: int
    available: bool = True
    topic_match: float = 0.0


DEFAULT_MODEL_CONFIG: dict[str, Any] = {
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
            "name": "heavy_workload",
            "field": "workload",
            "operator": "gt",
            "value": 8,
            "amount": 0.05,
        }
    ],
    "bonuses": [
        {
            "name": "exact_topic_bonus",
            "field": "topic_match",
            "operator": "gte",
            "value": 0.9,
            "amount": 0.05,
        }
    ],
}


def rank_reviewers_from_settings(
    candidates: list[ReviewerCandidate],
    model_config: dict[str, Any] | None = None,
    *,
    context: dict[str, Any] | None = None,
) -> DecisionResult:
    """Rank reviewers using a config dict (e.g. loaded from DB/admin)."""
    model = DecisionModel.from_dict(model_config or DEFAULT_MODEL_CONFIG)
    payload = [
        {
            "id": candidate.id,
            "relevance": candidate.relevance,
            "rating": candidate.rating,
            "workload": candidate.workload,
            "available": candidate.available,
            "topic_match": candidate.topic_match,
        }
        for candidate in candidates
    ]
    return model.rank(payload, context=context or {})


def rank_reviewers_as_audit(
    candidates: list[ReviewerCandidate],
    model_config: dict[str, Any] | None = None,
    *,
    context: dict[str, Any] | None = None,
    decision_id: str | None = None,
) -> dict[str, Any]:
    """Convenience helper for JSON responses / audit logs."""
    result = rank_reviewers_from_settings(
        candidates, model_config, context=context
    )
    return result.to_audit_dict(
        decision_id=decision_id,
        metadata={"layer": "django-service"},
    )


def main() -> None:
    """Runnable demo without Django installed."""
    candidates = [
        ReviewerCandidate(
            "reviewer_1",
            relevance=0.92,
            rating=4.8,
            workload=7,
            topic_match=0.95,
        ),
        ReviewerCandidate(
            "reviewer_2",
            relevance=0.81,
            rating=4.5,
            workload=2,
            topic_match=0.8,
        ),
        ReviewerCandidate(
            "reviewer_3",
            relevance=0.88,
            rating=4.1,
            workload=9,
            available=False,
            topic_match=0.99,
        ),
    ]
    result = rank_reviewers_from_settings(
        candidates, context={"max_workload": 10}
    )
    print(f"Selected reviewer: {result.best.id}")
    print(result.explain())
    print(result.to_audit_dict(decision_id="django-demo")["best"])


if __name__ == "__main__":
    main()
