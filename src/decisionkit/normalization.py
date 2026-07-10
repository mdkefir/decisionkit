"""Normalization helpers for decision methods."""

from __future__ import annotations

from decisionkit.typing import Direction


def min_max_normalize(
    values: list[float],
    direction: Direction,
) -> list[float]:
    """Normalize values to ``[0, 1]`` with higher always better.

    For ``max`` criteria: ``(x - min) / (max - min)``.
    For ``min`` criteria: ``(max - x) / (max - min)``.

    When all values are equal, every entry becomes ``1.0`` (no discrimination).
    """
    if not values:
        return []

    lo = min(values)
    hi = max(values)
    if hi == lo:
        return [1.0] * len(values)

    span = hi - lo
    if direction == "max":
        return [(v - lo) / span for v in values]
    return [(hi - v) / span for v in values]


def vector_normalize(values: list[float]) -> list[float]:
    """Apply vector (Euclidean) normalization: ``x / ||x||``.

    Returns zeros when the vector norm is zero.
    """
    if not values:
        return []

    norm_sq = sum(v * v for v in values)
    if norm_sq == 0.0:
        return [0.0] * len(values)

    norm = norm_sq**0.5
    return [v / norm for v in values]
