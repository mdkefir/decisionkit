"""Task prioritization example for a product backlog."""

from __future__ import annotations

from decisionkit import DecisionModel


def main() -> None:
    model = DecisionModel.from_dict(
        {
            "method": "weighted_sum",
            "criteria": [
                {"name": "impact", "weight": 0.45, "direction": "max"},
                {"name": "urgency", "weight": 0.35, "direction": "max"},
                {"name": "effort", "weight": 0.20, "direction": "min"},
            ],
            "constraints": [
                {
                    "name": "ready",
                    "field": "status",
                    "operator": "in",
                    "value": ["ready", "groomed"],
                    "reason": "Only ready work can be scheduled",
                }
            ],
            "bonuses": [
                {
                    "name": "customer_request",
                    "field": "tags",
                    "operator": "contains",
                    "value": "customer",
                    "amount": 0.05,
                }
            ],
            "penalties": [
                {
                    "name": "blocked_deps",
                    "field": "blocked_deps",
                    "operator": "gt",
                    "value": 0,
                    "amount": 0.08,
                }
            ],
        }
    )

    tasks = [
        {
            "id": "TASK-12",
            "impact": 9,
            "urgency": 8,
            "effort": 5,
            "status": "ready",
            "tags": ["customer", "billing"],
            "blocked_deps": 0,
        },
        {
            "id": "TASK-18",
            "impact": 7,
            "urgency": 9,
            "effort": 2,
            "status": "groomed",
            "tags": ["infra"],
            "blocked_deps": 1,
        },
        {
            "id": "TASK-03",
            "impact": 10,
            "urgency": 10,
            "effort": 8,
            "status": "idea",
            "tags": ["customer"],
            "blocked_deps": 0,
        },
    ]

    result = model.rank(tasks)
    print("Priority order:")
    for item in result.ranking:
        print(f"  #{item.rank} {item.id}: {item.score:.4f}")
    print()
    print(result.explain())


if __name__ == "__main__":
    main()
