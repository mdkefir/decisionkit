"""DecisionKit: explainable decision support, scoring, and ranking."""

from __future__ import annotations

from decisionkit.engine import DecisionModel
from decisionkit.exceptions import (
    DecisionKitError,
    DependencyMissingError,
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
    Bonus,
    Constraint,
    Criterion,
    DecisionResult,
    Explanation,
    Penalty,
    RankedAlternative,
)
from decisionkit.rules import RuleCondition

__all__ = [
    "Alternative",
    "Bonus",
    "Constraint",
    "Criterion",
    "DecisionKitError",
    "DecisionModel",
    "DecisionResult",
    "DependencyMissingError",
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
    "RuleCondition",
    "UnknownMethodError",
    "ValidationError",
    "__version__",
]

__version__ = "0.3.1"
