"""Decision method registry."""

from __future__ import annotations

from collections.abc import Callable

from decisionkit.methods.base import ScoredRow
from decisionkit.methods.topsis import rank_topsis
from decisionkit.methods.weighted_sum import rank_weighted_sum
from decisionkit.models import Alternative, Criterion
from decisionkit.typing import MethodName

MethodFn = Callable[[list[Alternative], list[Criterion]], list[ScoredRow]]

METHODS: dict[MethodName, MethodFn] = {
    "weighted_sum": rank_weighted_sum,
    "topsis": rank_topsis,
}

__all__ = ["METHODS", "MethodFn", "rank_topsis", "rank_weighted_sum"]
