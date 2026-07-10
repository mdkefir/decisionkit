"""Shared type aliases for DecisionKit."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal

Direction = Literal["max", "min"]
MethodName = Literal["weighted_sum", "topsis"]
ComparisonOp = Literal[
    "eq",
    "ne",
    "gt",
    "gte",
    "lt",
    "lte",
    "in",
    "not_in",
    "contains",
    "between",
]

AlternativeInput = Mapping[str, Any]
AlternativeList = Sequence[AlternativeInput]
ContextMapping = Mapping[str, Any]
