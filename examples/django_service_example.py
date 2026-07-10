"""Django service-layer example (adapter only; Django is not a core dependency).

This module shows how to keep DecisionKit in the service layer of a Django app
without turning DecisionKit into a Django package.

Typical usage inside a view or management command:

    from myapp.services.reviewer_ranking import rank_reviewers
    result = rank_reviewers(candidates)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from decisionkit import Constraint, Criterion, DecisionModel, DecisionResult, Penalty


@dataclass(frozen=True)
class ReviewerCandidate:
    """Plain DTO you might build from Django ORM objects."""

    id: str
    relevance: float
    rating: float
    workload: int


def build_reviewer_model() -> DecisionModel:
    """Create the shared ranking model used by the editorial workflow."""
    return DecisionModel(
        criteria=[
            Criterion("relevance", weight=0.5, direction="max"),
            Criterion("rating", weight=0.3, direction="max"),
            Criterion("workload", weight=0.2, direction="min"),
        ],
        method="weighted_sum",
        explain=True,
        constraints=[
            Constraint(
                name="min_rating",
                criterion="rating",
                operator="gte",
                threshold=4.0,
            )
        ],
        penalties=[
            Penalty(
                name="heavy_workload",
                criterion="workload",
                operator="gt",
                threshold=8,
                amount=0.05,
            )
        ],
    )


def rank_reviewers(candidates: list[ReviewerCandidate]) -> DecisionResult:
    """Rank reviewer candidates and return an explainable DecisionResult."""
    model = build_reviewer_model()
    payload = [
        {
            "id": candidate.id,
            "relevance": candidate.relevance,
            "rating": candidate.rating,
            "workload": candidate.workload,
        }
        for candidate in candidates
    ]
    return model.rank(payload)


def rank_reviewers_as_dict(candidates: list[ReviewerCandidate]) -> dict[str, Any]:
    """Convenience helper for JSON responses / audit logs."""
    return rank_reviewers(candidates).to_dict()


def main() -> None:
    """Runnable demo without Django installed."""
    candidates = [
        ReviewerCandidate("reviewer_1", relevance=0.92, rating=4.8, workload=7),
        ReviewerCandidate("reviewer_2", relevance=0.81, rating=4.5, workload=2),
        ReviewerCandidate("reviewer_3", relevance=0.88, rating=4.1, workload=9),
    ]
    result = rank_reviewers(candidates)
    print(f"Selected reviewer: {result.best.id}")
    print(result.explain())


if __name__ == "__main__":
    main()
