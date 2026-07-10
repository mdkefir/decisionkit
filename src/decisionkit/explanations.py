"""Deterministic explanation text generation."""

from __future__ import annotations

from decisionkit.models import Criterion, Explanation
from decisionkit.typing import MethodName


def _format_score(score: float) -> str:
    text = f"{score:.4f}".rstrip("0").rstrip(".")
    return text if text else "0"


def _describe_strengths(
    contributions: dict[str, float],
    criteria: list[Criterion],
) -> str:
    if not contributions:
        return "No criterion contributions were available."

    by_name = {c.name: c for c in criteria}
    ranked = sorted(contributions.items(), key=lambda item: item[1], reverse=True)

    max_names = [
        name
        for name, _ in ranked
        if by_name.get(name) is not None and by_name[name].direction == "max"
    ]
    min_names = [
        name
        for name, value in ranked
        if by_name.get(name) is not None
        and by_name[name].direction == "min"
        and value > 0
    ]

    strong_max = max_names[:2]
    helpful_min = [
        name
        for name in min_names
        if contributions[name] >= max(contributions.values()) * 0.45
    ][:2]

    parts: list[str] = []
    if strong_max:
        if len(strong_max) == 1:
            parts.append(f"It had a strong {strong_max[0]} value")
        else:
            parts.append(
                f"It had strong {strong_max[0]} and {strong_max[1]} values"
            )

    if helpful_min:
        if len(helpful_min) == 1:
            parts.append(
                f"while its lower {helpful_min[0]} improved its score because "
                f"{helpful_min[0]} is minimized"
            )
        else:
            parts.append(
                f"while its lower {helpful_min[0]} and {helpful_min[1]} improved "
                f"its score because those criteria are minimized"
            )

    if not parts:
        top_name = ranked[0][0]
        return f"Its strongest relative contribution came from {top_name}."

    if len(parts) == 1:
        return parts[0] + "."
    return parts[0] + ", " + parts[1] + "."


def build_explanation(
    *,
    alternative_id: str,
    rank: int,
    score: float,
    method: MethodName,
    criteria: list[Criterion],
    normalized_values: dict[str, float],
    contributions: dict[str, float],
    triggered_penalties: tuple[str, ...] = (),
    triggered_bonuses: tuple[str, ...] = (),
) -> Explanation:
    """Build a structured explanation with deterministic plain text."""
    score_text = _format_score(score)
    strength = _describe_strengths(contributions, criteria)
    text = f"{alternative_id} ranked #{rank} with score {score_text}. {strength}"

    if triggered_penalties:
        names = ", ".join(triggered_penalties)
        text += f" Penalties applied: {names}."
    if triggered_bonuses:
        names = ", ".join(triggered_bonuses)
        text += f" Bonuses applied: {names}."

    if method == "topsis":
        text += (
            " Score is the TOPSIS closeness coefficient "
            "(higher is closer to the ideal)."
        )
    else:
        text += (
            " Score is the weighted sum of benefit-normalized criterion values."
        )

    return Explanation(
        alternative_id=alternative_id,
        rank=rank,
        score=score,
        method=method,
        normalized_values=dict(normalized_values),
        contributions=dict(contributions),
        triggered_penalties=triggered_penalties,
        triggered_bonuses=triggered_bonuses,
        text=text,
    )
