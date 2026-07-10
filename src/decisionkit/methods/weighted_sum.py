"""Weighted sum (SAW) decision method."""

from __future__ import annotations

from decisionkit.methods.base import ScoredRow
from decisionkit.models import Alternative, Criterion
from decisionkit.normalization import min_max_normalize


def rank_weighted_sum(
    alternatives: list[Alternative],
    criteria: list[Criterion],
) -> list[ScoredRow]:
    """Rank alternatives using a benefit-oriented weighted sum.

    Each criterion column is min-max normalized so that higher is always
    better (``min`` criteria are inverted). Weights are renormalized to
    sum to 1.0. The score is ``sum(w_i * n_i)``.
    """
    if not alternatives:
        return []

    total_weight = sum(c.weight for c in criteria)
    weights = {c.name: c.weight / total_weight for c in criteria}

    columns: dict[str, list[float]] = {
        c.name: [alt.values[c.name] for alt in alternatives] for c in criteria
    }
    normalized_columns: dict[str, list[float]] = {
        c.name: min_max_normalize(columns[c.name], c.direction) for c in criteria
    }

    rows: list[ScoredRow] = []
    for index, alt in enumerate(alternatives):
        normalized_values = {
            c.name: normalized_columns[c.name][index] for c in criteria
        }
        contributions = {
            c.name: weights[c.name] * normalized_values[c.name] for c in criteria
        }
        score = sum(contributions.values())
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
