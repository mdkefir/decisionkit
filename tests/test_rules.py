"""Tests for the rule engine, bonuses, penalties, and context."""

from __future__ import annotations

from decisionkit import Bonus, Constraint, Criterion, DecisionModel, Penalty


def test_bonus_increases_score() -> None:
    model = DecisionModel(
        criteria=[Criterion("score", weight=1.0, direction="max")],
        bonuses=[
            Bonus(
                name="boost",
                field="score",
                operator="gte",
                value=8,
                amount=0.25,
            )
        ],
    )
    result = model.rank(
        [
            {"id": "high", "score": 10},
            {"id": "low", "score": 1},
        ]
    )
    high = next(item for item in result.ranking if item.id == "high")
    assert high.base_score == 1.0
    assert high.bonus_total == 0.25
    assert high.score == 1.25
    assert "boost" in high.triggered_bonuses


def test_penalty_still_works_with_legacy_kwargs() -> None:
    model = DecisionModel(
        criteria=[Criterion("score", weight=1.0, direction="max")],
        penalties=[
            Penalty(
                name="overload",
                criterion="score",
                operator="gt",
                threshold=8,
                amount=0.5,
            )
        ],
    )
    result = model.rank(
        [
            {"id": "high", "score": 10},
            {"id": "mid", "score": 7},
        ]
    )
    high = next(item for item in result.ranking if item.id == "high")
    assert high.penalty_total == 0.5
    assert high.score == 0.5


def test_hard_constraint_exclusion_with_bool_field() -> None:
    model = DecisionModel(
        criteria=[Criterion("rating", weight=1.0)],
        constraints=[
            Constraint(
                name="available_only",
                field="available",
                operator="eq",
                value=True,
                reason="Must be available",
            )
        ],
    )
    result = model.rank(
        [
            {"id": "ok", "rating": 4.0, "available": True},
            {"id": "busy", "rating": 5.0, "available": False},
        ]
    )
    assert result.best.id == "ok"
    assert result.excluded[0] == (
        "busy",
        "available_only (Must be available)",
    )


def test_context_based_constraint() -> None:
    model = DecisionModel(
        criteria=[Criterion("quality", weight=1.0)],
        constraints=[
            Constraint(
                name="within_capacity",
                field="workload",
                operator="lte",
                context="max_workload",
                reason="Workload must be within capacity",
            )
        ],
    )
    result = model.rank(
        [
            {"id": "fit", "quality": 7, "workload": 4},
            {"id": "over", "quality": 9, "workload": 8},
        ],
        context={"max_workload": 5},
    )
    assert [item.id for item in result.ranking] == ["fit"]
    assert result.excluded[0][0] == "over"


def test_compound_all_constraint() -> None:
    model = DecisionModel(
        criteria=[Criterion("rating", weight=1.0)],
        constraints=[
            Constraint(
                name="eligible",
                all=[
                    {"field": "available", "operator": "eq", "value": True},
                    {
                        "field": "workload",
                        "operator": "lte",
                        "context": "max_workload",
                    },
                ],
                reason="Available and within capacity",
            )
        ],
    )
    result = model.rank(
        [
            {"id": "a", "rating": 4.5, "available": True, "workload": 3},
            {"id": "b", "rating": 4.9, "available": True, "workload": 9},
            {"id": "c", "rating": 5.0, "available": False, "workload": 1},
        ],
        context={"max_workload": 5},
    )
    assert [item.id for item in result.ranking] == ["a"]
    assert {item[0] for item in result.excluded} == {"b", "c"}


def test_in_and_contains_operators() -> None:
    model = DecisionModel(
        criteria=[Criterion("score", weight=1.0)],
        constraints=[
            Constraint(
                name="specialization_ok",
                field="specialization",
                operator="in",
                value=["NLP", "Django"],
            )
        ],
        bonuses=[
            Bonus(
                name="keyword_hit",
                field="keywords",
                operator="contains",
                value="django",
                amount=0.1,
            )
        ],
    )
    result = model.rank(
        [
            {
                "id": "a",
                "score": 5,
                "specialization": "Django",
                "keywords": ["django", "api"],
            },
            {
                "id": "b",
                "score": 9,
                "specialization": "Rust",
                "keywords": ["systems"],
            },
        ],
        context={"article_keywords": ["django", "nlp"]},
    )
    assert result.best.id == "a"
    assert "keyword_hit" in result.best.triggered_bonuses
    assert result.excluded[0][0] == "b"


def test_between_and_not_in_operators() -> None:
    model = DecisionModel(
        criteria=[Criterion("score", weight=1.0)],
        constraints=[
            Constraint(
                name="score_band",
                field="score",
                operator="between",
                value=[0.7, 1.0],
            ),
            Constraint(
                name="not_blocked",
                field="id_tag",
                operator="not_in",
                value=["blocked", "banned"],
            ),
        ],
    )
    # score is also a criterion, so values must be numeric for scoring.
    # Use a separate band field for between on non-criterion? 
    # Here we constrain the criterion itself before ranking.
    result = model.rank(
        [
            {"id": "ok", "score": 0.8, "id_tag": "active"},
            {"id": "low", "score": 0.2, "id_tag": "active"},
            {"id": "blocked", "score": 0.9, "id_tag": "blocked"},
        ]
    )
    assert [item.id for item in result.ranking] == ["ok"]
    assert {item[0] for item in result.excluded} == {"low", "blocked"}


def test_compound_any_bonus() -> None:
    model = DecisionModel(
        criteria=[Criterion("score", weight=1.0)],
        bonuses=[
            Bonus(
                name="vip_or_hot",
                amount=0.2,
                any=[
                    {"field": "vip", "operator": "eq", "value": True},
                    {"field": "score", "operator": "gte", "value": 9},
                ],
            )
        ],
    )
    result = model.rank(
        [
            {"id": "vip", "score": 1, "vip": True},
            {"id": "hot", "score": 10, "vip": False},
            {"id": "plain", "score": 5, "vip": False},
        ]
    )
    by_id = {item.id: item for item in result.ranking}
    assert by_id["vip"].bonus_total == 0.2
    assert by_id["hot"].bonus_total == 0.2
    assert by_id["plain"].bonus_total == 0.0
