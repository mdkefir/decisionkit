"""Audit export helpers for DecisionResult."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from decisionkit.models import DecisionResult


def build_audit_dict(
    result: DecisionResult,
    *,
    decision_id: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Build a stable, JSON-serializable audit record.

    Timestamps are never auto-generated. Pass ``timestamp`` explicitly when
    you want one recorded.
    """
    best = result.best if result.ranking else None
    audit: dict[str, Any] = {
        "schema_version": "1.0",
        "decision_id": decision_id,
        "timestamp": timestamp,
        "metadata": dict(metadata) if metadata is not None else {},
        "method": result.method,
        "model": dict(result.model),
        "context": dict(result.context),
        "input_alternative_ids": list(result.input_ids),
        "excluded": [
            {"id": alt_id, "reason": reason} for alt_id, reason in result.excluded
        ],
        "ranking": [
            {
                "id": item.id,
                "rank": item.rank,
                "score": item.score,
                "base_score": (
                    item.base_score if item.base_score is not None else item.score
                ),
                "penalty_total": item.penalty_total,
                "bonus_total": item.bonus_total,
                "triggered_penalties": list(item.triggered_penalties),
                "triggered_bonuses": list(item.triggered_bonuses),
                "values": dict(item.values),
                "normalized_values": dict(item.normalized_values),
                "contributions": dict(item.contributions),
                "explanation": (
                    item.explanation.text if item.explanation else None
                ),
            }
            for item in result.ranking
        ],
        "best": (
            {
                "id": best.id,
                "score": best.score,
                "rank": best.rank,
                "explanation": (
                    best.explanation.text if best.explanation else None
                ),
            }
            if best is not None
            else None
        ),
    }
    return audit
