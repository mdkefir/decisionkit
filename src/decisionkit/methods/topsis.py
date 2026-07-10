"""TOPSIS decision method."""

from __future__ import annotations

from decisionkit.methods.base import ScoredRow
from decisionkit.models import Alternative, Criterion
from decisionkit.normalization import vector_normalize


def rank_topsis(
    alternatives: list[Alternative],
    criteria: list[Criterion],
) -> list[ScoredRow]:
    """Rank alternatives with TOPSIS (Technique for Order Preference).

    Steps:
    1. Vector-normalize each criterion column.
    2. Multiply by renormalized weights.
    3. Determine ideal best / ideal worst per criterion direction.
    4. Compute separation distances and closeness coefficient.
    """
    if not alternatives:
        return []

    total_weight = sum(c.weight for c in criteria)
    weights = {c.name: c.weight / total_weight for c in criteria}

    columns: dict[str, list[float]] = {
        c.name: [alt.values[c.name] for alt in alternatives] for c in criteria
    }
    vector_columns: dict[str, list[float]] = {
        c.name: vector_normalize(columns[c.name]) for c in criteria
    }
    weighted_columns: dict[str, list[float]] = {
        c.name: [weights[c.name] * value for value in vector_columns[c.name]]
        for c in criteria
    }

    ideal_best: dict[str, float] = {}
    ideal_worst: dict[str, float] = {}
    for criterion in criteria:
        col = weighted_columns[criterion.name]
        if criterion.direction == "max":
            ideal_best[criterion.name] = max(col)
            ideal_worst[criterion.name] = min(col)
        else:
            ideal_best[criterion.name] = min(col)
            ideal_worst[criterion.name] = max(col)

    rows: list[ScoredRow] = []
    for index, alt in enumerate(alternatives):
        weighted = {c.name: weighted_columns[c.name][index] for c in criteria}
        # Benefit-oriented view of vector-normalized values for explanations.
        normalized_values = {
            c.name: (
                vector_columns[c.name][index]
                if c.direction == "max"
                else (1.0 - vector_columns[c.name][index])
            )
            for c in criteria
        }
        # Contribution approximates weighted proximity toward the ideal on each axis.
        contributions: dict[str, float] = {}
        for criterion in criteria:
            name = criterion.name
            span = abs(ideal_best[name] - ideal_worst[name])
            if span == 0.0:
                contributions[name] = weights[name]
            else:
                distance_from_worst = abs(weighted[name] - ideal_worst[name])
                contributions[name] = weights[name] * (distance_from_worst / span)

        dist_best = sum(
            (weighted[c.name] - ideal_best[c.name]) ** 2 for c in criteria
        ) ** 0.5
        dist_worst = sum(
            (weighted[c.name] - ideal_worst[c.name]) ** 2 for c in criteria
        ) ** 0.5
        denom = dist_best + dist_worst
        score = 0.0 if denom == 0.0 else dist_worst / denom

        rows.append(
            ScoredRow(
                alternative_id=alt.id,
                score=score,
                values=dict(alt.values),
                normalized_values=normalized_values,
                contributions=contributions,
            )
        )

    rows.sort(key=lambda row: (-row.score, row.alternative_id))
    return rows
