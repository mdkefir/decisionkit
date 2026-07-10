"""Method result container shared by ranking algorithms."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ScoredRow:
    """Intermediate scoring output for one alternative."""

    alternative_id: str
    score: float
    values: dict[str, Any]
    normalized_values: dict[str, float]
    contributions: dict[str, float]
