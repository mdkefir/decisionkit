"""Public exceptions raised by DecisionKit."""

from __future__ import annotations


class DecisionKitError(Exception):
    """Base exception for all DecisionKit errors."""


class ValidationError(DecisionKitError):
    """Raised when model configuration or input data is invalid."""


class InvalidWeightError(ValidationError):
    """Raised when a criterion weight is not strictly positive."""


class InvalidDirectionError(ValidationError):
    """Raised when a criterion direction is not ``max`` or ``min``."""


class MissingValueError(ValidationError):
    """Raised when an alternative is missing a required criterion value."""


class InvalidValueError(ValidationError):
    """Raised when a criterion value is not a finite number."""


class EmptyAlternativesError(ValidationError):
    """Raised when ranking is requested with no alternatives."""


class UnknownMethodError(ValidationError):
    """Raised when an unsupported decision method is requested."""


class DuplicateCriterionError(ValidationError):
    """Raised when criterion names are not unique."""


class DuplicateAlternativeError(ValidationError):
    """Raised when alternative ids are not unique."""


class DependencyMissingError(DecisionKitError):
    """Raised when an optional dependency is required but not installed."""
