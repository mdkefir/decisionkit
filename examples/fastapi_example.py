"""FastAPI integration example (adapter only; FastAPI is not a core dependency).

Install extras to run this file:

    pip install fastapi uvicorn decisionkit

Then:

    uvicorn examples.fastapi_example:app --reload
"""

from __future__ import annotations

from typing import Any, Literal

from decisionkit import Criterion, DecisionModel, ValidationError

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel, Field
except ImportError as exc:  # pragma: no cover - example-only dependency
    raise SystemExit(
        "Install FastAPI to run this example: pip install fastapi uvicorn"
    ) from exc


class CriterionIn(BaseModel):
    name: str
    weight: float = Field(gt=0)
    direction: Literal["max", "min"] = "max"
    description: str | None = None


class RankRequest(BaseModel):
    criteria: list[CriterionIn]
    alternatives: list[dict[str, Any]]
    method: Literal["weighted_sum", "topsis"] = "weighted_sum"
    explain: bool = True


app = FastAPI(title="DecisionKit FastAPI Example", version="0.1.0")


@app.post("/rank")
def rank_alternatives(payload: RankRequest) -> dict[str, Any]:
    """Rank alternatives using DecisionKit and return an audit-friendly payload."""
    try:
        model = DecisionModel(
            criteria=[
                Criterion(
                    item.name,
                    weight=item.weight,
                    direction=item.direction,
                    description=item.description,
                )
                for item in payload.criteria
            ],
            method=payload.method,
            explain=payload.explain,
        )
        result = model.rank(payload.alternatives)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return result.to_dict()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
