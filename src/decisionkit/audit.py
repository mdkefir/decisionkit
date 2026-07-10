"""Audit export and deterministic hashing for DecisionResult."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from decisionkit.exceptions import ValidationError
from decisionkit.models import DecisionResult

SUPPORTED_HASH_ALGORITHMS = frozenset({"sha256", "sha384", "sha512"})


def build_audit_dict(
    result: DecisionResult,
    *,
    decision_id: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    timestamp: str | None = None,
    include_hash: bool = False,
    hash_algorithm: str = "sha256",
    include_timestamp_in_hash: bool = False,
) -> dict[str, Any]:
    """Build a stable, JSON-serializable audit record.

    Timestamps are never auto-generated. Pass ``timestamp`` explicitly when
    you want one recorded.

    When ``include_hash`` is true, an ``audit_hash`` object is added. The digest
    is computed from the canonical decision payload and does **not** include
    ``decision_id``, ``metadata``, or ``timestamp`` unless
    ``include_timestamp_in_hash`` is true (timestamp only).
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
    if include_hash:
        audit["audit_hash"] = {
            "algorithm": hash_algorithm,
            "digest": compute_audit_hash(
                audit,
                algorithm=hash_algorithm,
                include_timestamp=include_timestamp_in_hash,
            ),
        }
    return audit


def digest_payload(
    audit: Mapping[str, Any],
    *,
    include_timestamp: bool = False,
) -> dict[str, Any]:
    """Return the subset of an audit record used for hashing.

    Included by default:
    ``schema_version``, ``method``, ``model``, ``context``,
    ``input_alternative_ids``, ``excluded``, ``ranking``, ``best``.

    Excluded by default:
    ``decision_id``, ``metadata``, ``timestamp``, ``audit_hash``.
    """
    payload: dict[str, Any] = {
        "schema_version": audit.get("schema_version"),
        "method": audit.get("method"),
        "model": audit.get("model"),
        "context": audit.get("context"),
        "input_alternative_ids": audit.get("input_alternative_ids"),
        "excluded": audit.get("excluded"),
        "ranking": audit.get("ranking"),
        "best": audit.get("best"),
    }
    if include_timestamp:
        payload["timestamp"] = audit.get("timestamp")
    return payload


def canonical_json_bytes(data: Any) -> bytes:
    """Serialize ``data`` to canonical UTF-8 JSON bytes."""
    try:
        return json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            f"Audit payload is not JSON-serializable: {exc}"
        ) from exc


def compute_audit_hash(
    audit: Mapping[str, Any],
    *,
    algorithm: str = "sha256",
    include_timestamp: bool = False,
) -> str:
    """Compute a hex digest for an audit dictionary."""
    if algorithm not in SUPPORTED_HASH_ALGORITHMS:
        supported = ", ".join(sorted(SUPPORTED_HASH_ALGORITHMS))
        raise ValidationError(
            f"Unsupported hash algorithm {algorithm!r}. "
            f"Supported: {supported}"
        )
    payload = digest_payload(audit, include_timestamp=include_timestamp)
    digest = hashlib.new(algorithm)
    digest.update(canonical_json_bytes(payload))
    return digest.hexdigest()


def audit_hash_for_result(
    result: DecisionResult,
    *,
    algorithm: str = "sha256",
    include_timestamp: bool = False,
    timestamp: str | None = None,
) -> str:
    """Compute an audit hash directly from a :class:`DecisionResult`."""
    audit = build_audit_dict(result, timestamp=timestamp)
    return compute_audit_hash(
        audit,
        algorithm=algorithm,
        include_timestamp=include_timestamp,
    )
