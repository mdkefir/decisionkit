"""Deterministic explanation text generation."""

from __future__ import annotations

from decisionkit.models import Criterion, Explanation
from decisionkit.typing import MethodName

# Benefit-normalized thresholds used for plain-language strength labels.
STRONG_NORMALIZED = 0.67
WEAK_NORMALIZED = 0.33


def _format_score(score: float) -> str:
    text = f"{score:.4f}".rstrip("0").rstrip(".")
    return text if text else "0"


def _normalized(normalized_values: dict[str, float], name: str) -> float:
    return float(normalized_values.get(name, 0.0))


def _describe_strengths(
    *,
    criteria: list[Criterion],
    normalized_values: dict[str, float],
    contributions: dict[str, float],
) -> str:
    """Build strength text from normalized values and contributions.

    ``strong`` / ``weak`` labels use benefit-normalized values only
    (higher is always better after min/max handling). Raw criterion values
    are never treated as inherently strong.
    """
    if not criteria:
        return "No criterion contributions were available."

    def sort_key(criterion: Criterion) -> tuple[float, float, str]:
        return (
            -contributions.get(criterion.name, 0.0),
            -criterion.weight,
            criterion.name,
        )

    strong = sorted(
        (
            criterion
            for criterion in criteria
            if _normalized(normalized_values, criterion.name) >= STRONG_NORMALIZED
        ),
        key=sort_key,
    )
    weak = sorted(
        (
            criterion
            for criterion in criteria
            if _normalized(normalized_values, criterion.name) <= WEAK_NORMALIZED
        ),
        key=lambda criterion: (-criterion.weight, criterion.name),
    )

    strong_max = [c for c in strong if c.direction == "max"]
    strong_min = [c for c in strong if c.direction == "min"]

    parts: list[str] = []

    if strong_max:
        top = strong_max[:2]
        if len(top) == 1:
            parts.append(f"It had a strong {top[0].name} value")
        else:
            parts.append(
                f"It had strong {top[0].name} and {top[1].name} values"
            )

    if strong_min:
        helpful = strong_min[:2]
        if len(helpful) == 1:
            name = helpful[0].name
            clause = (
                f"while its lower {name} improved its score because "
                f"{name} is minimized"
            )
        else:
            clause = (
                f"while its lower {helpful[0].name} and {helpful[1].name} "
                f"improved its score because those criteria are minimized"
            )
        if parts:
            parts.append(clause)
        else:
            parts.append(clause.replace("while its", "Its", 1))

    if weak:
        hurt = weak[0]
        if hurt.direction == "min":
            clause = f"while its {hurt.name} did not help much"
        else:
            clause = f"while its weak {hurt.name} limited the score"
        if parts:
            # Avoid stacking two "while" clauses awkwardly.
            if parts[-1].startswith("while "):
                parts.append(clause.replace("while its", "and its", 1))
            else:
                parts.append(clause)
        else:
            if hurt.direction == "min":
                parts.append(f"Its {hurt.name} did not help much")
            else:
                parts.append(f"Its weak {hurt.name} limited the score")

    if not parts:
        ranked = sorted(
            criteria,
            key=lambda criterion: (
                -contributions.get(criterion.name, 0.0),
                criterion.name,
            ),
        )
        top_name = ranked[0].name
        return (
            f"No criterion stood out as strong; the largest relative "
            f"contribution came from {top_name}."
        )

    if len(parts) == 1:
        return parts[0] + "."
    if len(parts) == 2:
        return parts[0] + ", " + parts[1] + "."
    # strong [, helpful_min], weak
    return parts[0] + ", " + parts[1] + ", " + parts[2] + "."


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
    strength = _describe_strengths(
        criteria=criteria,
        normalized_values=normalized_values,
        contributions=contributions,
    )
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
            " Score is the weighted sum of benefit-normalized criterion values "
            "relative to the evaluated alternatives."
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
