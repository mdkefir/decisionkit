"""Reviewer selection example using DecisionKit v0.2 config + rules."""

from __future__ import annotations

from decisionkit import DecisionModel


def main() -> None:
    model = DecisionModel.from_dict(
        {
            "method": "weighted_sum",
            "explain": True,
            "criteria": [
                {
                    "name": "relevance",
                    "weight": 0.5,
                    "direction": "max",
                    "description": "Topic match",
                },
                {
                    "name": "rating",
                    "weight": 0.3,
                    "direction": "max",
                    "description": "Historical quality",
                },
                {
                    "name": "workload",
                    "weight": 0.2,
                    "direction": "min",
                    "description": "Open assignments",
                },
            ],
            "constraints": [
                {
                    "name": "available_only",
                    "field": "available",
                    "operator": "eq",
                    "value": True,
                    "reason": "Reviewer must be available",
                },
                {
                    "name": "within_capacity",
                    "field": "workload",
                    "operator": "lte",
                    "context": "max_workload",
                    "reason": "Workload must stay within capacity",
                },
            ],
            "penalties": [
                {
                    "name": "heavy_workload",
                    "field": "workload",
                    "operator": "gt",
                    "value": 8,
                    "amount": 0.05,
                    "reason": "Slight penalty when workload is very high",
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
    )

    reviewers = [
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
            "relevance": 0.95,
            "rating": 3.2,
            "workload": 1,
            "available": False,
            "topic_match": 1.0,
        },
        {
            "id": "reviewer_4",
            "relevance": 0.70,
            "rating": 4.9,
            "workload": 10,
            "available": True,
            "topic_match": 0.7,
        },
    ]

    result = model.rank(reviewers, context={"max_workload": 9})

    print(f"Best reviewer: {result.best.id} (score={result.best.score:.4f})")
    print("\nRanking:")
    for item in result.ranking:
        print(f"  #{item.rank} {item.id}: {item.score:.4f}")

    print("\nExplanation:")
    print(result.explain())

    print("\nAudit:")
    audit = result.to_audit_dict(
        decision_id="reviewer-selection-demo",
        metadata={"workflow": "editorial"},
        timestamp="2026-07-10T10:00:00Z",
    )
    print(f"  decision_id={audit['decision_id']} best={audit['best']['id']}")


if __name__ == "__main__":
    main()
