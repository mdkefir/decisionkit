"""Shared type aliases for DecisionKit."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal

Direction = Literal["max", "min"]
MethodName = Literal["weighted_sum", "topsis"]
ComparisonOp = Literal["gt", "gte", "lt", "lte", "eq"]

AlternativeInput = Mapping[str, Any]
AlternativeList = Sequence[AlternativeInput]
