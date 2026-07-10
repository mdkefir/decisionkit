"""Config loading and serialization for DecisionModel."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from decisionkit.exceptions import DependencyMissingError, ValidationError
from decisionkit.models import Bonus, Constraint, Criterion, Penalty
from decisionkit.typing import MethodName

if TYPE_CHECKING:
    from decisionkit.engine import DecisionModel


def _require_mapping(data: Any, *, label: str) -> Mapping[str, Any]:
    if not isinstance(data, Mapping):
        raise ValidationError(f"{label} must be a mapping, got {type(data).__name__}")
    return data


def criterion_from_dict(raw: Mapping[str, Any]) -> Criterion:
    """Build a :class:`Criterion` from a config mapping."""
    raw = _require_mapping(raw, label="Criterion config")
    if "name" not in raw:
        raise ValidationError("Criterion config requires 'name'")
    return Criterion(
        str(raw["name"]),
        weight=float(raw.get("weight", 1.0)),
        direction=raw.get("direction", "max"),
        description=raw.get("description"),
    )


def constraint_from_dict(raw: Mapping[str, Any]) -> Constraint:
    """Build a :class:`Constraint` from a config mapping."""
    raw = _require_mapping(raw, label="Constraint config")
    if "name" not in raw:
        raise ValidationError("Constraint config requires 'name'")
    return Constraint(
        name=str(raw["name"]),
        field=raw.get("field"),
        operator=raw.get("operator", "eq"),
        value=raw.get("value"),
        criterion=raw.get("criterion"),
        threshold=raw.get("threshold"),
        description=raw.get("description"),
        reason=raw.get("reason"),
        context=raw.get("context"),
        all=raw.get("all"),
        any=raw.get("any"),
    )


def penalty_from_dict(raw: Mapping[str, Any]) -> Penalty:
    """Build a :class:`Penalty` from a config mapping."""
    raw = _require_mapping(raw, label="Penalty config")
    if "name" not in raw:
        raise ValidationError("Penalty config requires 'name'")
    if "amount" not in raw:
        raise ValidationError(f"Penalty '{raw['name']}' requires 'amount'")
    return Penalty(
        name=str(raw["name"]),
        field=raw.get("field"),
        operator=raw.get("operator", "eq"),
        value=raw.get("value"),
        amount=raw["amount"],
        criterion=raw.get("criterion"),
        threshold=raw.get("threshold"),
        description=raw.get("description"),
        reason=raw.get("reason"),
        context=raw.get("context"),
        all=raw.get("all"),
        any=raw.get("any"),
    )


def bonus_from_dict(raw: Mapping[str, Any]) -> Bonus:
    """Build a :class:`Bonus` from a config mapping."""
    raw = _require_mapping(raw, label="Bonus config")
    if "name" not in raw:
        raise ValidationError("Bonus config requires 'name'")
    if "amount" not in raw:
        raise ValidationError(f"Bonus '{raw['name']}' requires 'amount'")
    return Bonus(
        name=str(raw["name"]),
        field=raw.get("field"),
        operator=raw.get("operator", "eq"),
        value=raw.get("value"),
        amount=raw["amount"],
        reason=raw.get("reason"),
        description=raw.get("description"),
        context=raw.get("context"),
        all=raw.get("all"),
        any=raw.get("any"),
    )


def model_from_dict(data: Mapping[str, Any]) -> DecisionModel:
    """Build a :class:`DecisionModel` from a configuration mapping."""
    from decisionkit.engine import DecisionModel

    data = _require_mapping(data, label="DecisionModel config")
    if "criteria" not in data:
        raise ValidationError("DecisionModel config requires 'criteria'")
    criteria_raw = data["criteria"]
    if not isinstance(criteria_raw, list) or not criteria_raw:
        raise ValidationError("'criteria' must be a non-empty list")

    method: MethodName = data.get("method", "weighted_sum")
    explain = bool(data.get("explain", True))

    constraints_raw = data.get("constraints", [])
    penalties_raw = data.get("penalties", [])
    bonuses_raw = data.get("bonuses", [])
    if not isinstance(constraints_raw, list):
        raise ValidationError("'constraints' must be a list")
    if not isinstance(penalties_raw, list):
        raise ValidationError("'penalties' must be a list")
    if not isinstance(bonuses_raw, list):
        raise ValidationError("'bonuses' must be a list")

    return DecisionModel(
        criteria=[criterion_from_dict(item) for item in criteria_raw],
        method=method,
        explain=explain,
        constraints=[constraint_from_dict(item) for item in constraints_raw],
        penalties=[penalty_from_dict(item) for item in penalties_raw],
        bonuses=[bonus_from_dict(item) for item in bonuses_raw],
    )


def model_to_dict(model: DecisionModel) -> dict[str, Any]:
    """Serialize a :class:`DecisionModel` to a JSON-friendly dictionary."""
    return {
        "method": model.method,
        "explain": model.explain,
        "criteria": [item.to_dict() for item in model.criteria],
        "constraints": [item.to_dict() for item in model.constraints],
        "penalties": [item.to_dict() for item in model.penalties],
        "bonuses": [item.to_dict() for item in model.bonuses],
    }


def model_from_json(payload: str | bytes) -> DecisionModel:
    """Build a :class:`DecisionModel` from a JSON string."""
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Invalid JSON config: {exc}") from exc
    return model_from_dict(data)


def model_to_json(model: DecisionModel, *, indent: int | None = 2) -> str:
    """Serialize a :class:`DecisionModel` to a JSON string."""
    return json.dumps(model_to_dict(model), indent=indent, sort_keys=True)


def _load_yaml() -> Any:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - exercised in tests via mock
        raise DependencyMissingError(
            "YAML support requires PyYAML. Install it with: pip install "
            "'decisionkit[yaml]'"
        ) from exc
    return yaml


def model_from_yaml(payload: str | bytes) -> DecisionModel:
    """Build a :class:`DecisionModel` from a YAML string.

    Requires the optional ``decisionkit[yaml]`` extra (PyYAML).
    """
    yaml = _load_yaml()
    text = payload.decode("utf-8") if isinstance(payload, bytes) else payload
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValidationError(f"Invalid YAML config: {exc}") from exc
    if data is None:
        raise ValidationError("YAML config is empty")
    return model_from_dict(data)


def model_to_yaml(model: DecisionModel) -> str:
    """Serialize a :class:`DecisionModel` to a YAML string.

    Requires the optional ``decisionkit[yaml]`` extra (PyYAML).
    """
    yaml = _load_yaml()
    return yaml.safe_dump(
        model_to_dict(model),
        default_flow_style=False,
        sort_keys=True,
    )
