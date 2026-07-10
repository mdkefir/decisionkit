"""DecisionKit: explainable decision support, scoring, and ranking."""

from __future__ import annotations

from decisionkit.engine import DecisionModel
from decisionkit.exceptions import (
    DecisionKitError,
    DuplicateAlternativeError,
    DuplicateCriterionError,
    EmptyAlternativesError,
    InvalidDirectionError,
    InvalidValueError,
    InvalidWeightError,
    MissingValueError,
    UnknownMethodError,
    ValidationError,
)
from decisionkit.models import (
    Alternative,
    Constraint,
    Criterion,
    DecisionResult,
    Explanation,
    Penalty,
    RankedAlternative,
)

__all__ = [
    "Alternative",
    "Constraint",
    "Criterion",
    "DecisionKitError",
    "DecisionModel",
    "DecisionResult",
    "DuplicateAlternativeError",
    "DuplicateCriterionError",
    "EmptyAlternativesError",
    "Explanation",
    "InvalidDirectionError",
    "InvalidValueError",
    "InvalidWeightError",
    "MissingValueError",
    "Penalty",
    "RankedAlternative",
    "UnknownMethodError",
    "ValidationError",
]

__version__ = "0.1.0"
