"""Reviewer selection example using DecisionKit."""

from __future__ import annotations

from decisionkit import Constraint, Criterion, DecisionModel, Penalty


def main() -> None:
    model = DecisionModel(
        criteria=[
            Criterion(
                "relevance",
                weight=0.5,
                direction="max",
                description="Topic match",
            ),
            Criterion(
                "rating",
                weight=0.3,
                direction="max",
                description="Historical quality",
            ),
            Criterion(
                "workload",
                weight=0.2,
                direction="min",
                description="Open assignments",
            ),
        ],
        method="weighted_sum",
        explain=True,
        constraints=[
            Constraint(
                name="min_rating",
                criterion="rating",
                operator="gte",
                threshold=4.0,
                description="Reviewer rating must be at least 4.0",
            )
        ],
        penalties=[
            Penalty(
                name="heavy_workload",
                criterion="workload",
                operator="gt",
                threshold=8,
                amount=0.05,
                description="Slight penalty when workload is very high",
            )
        ],
    )

    reviewers = [
        {"id": "reviewer_1", "relevance": 0.92, "rating": 4.8, "workload": 7},
        {"id": "reviewer_2", "relevance": 0.81, "rating": 4.5, "workload": 2},
        {"id": "reviewer_3", "relevance": 0.95, "rating": 3.2, "workload": 1},
        {"id": "reviewer_4", "relevance": 0.70, "rating": 4.9, "workload": 10},
    ]

    result = model.rank(reviewers)

    print(f"Best reviewer: {result.best.id} (score={result.best.score:.4f})")
    print("\nRanking:")
    for item in result.ranking:
        print(f"  #{item.rank} {item.id}: {item.score:.4f}")

    print("\nExplanation:")
    print(result.explain())


if __name__ == "__main__":
    main()
