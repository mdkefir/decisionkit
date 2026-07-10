"""FastAPI integration example using config-driven DecisionKit models.

Install extras to run this file:

    pip install fastapi uvicorn decisionkit

Then:

    uvicorn examples.fastapi_example:app --reload
"""

from __future__ import annotations

from typing import Any

from decisionkit import DecisionModel, ValidationError

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel, Field
except ImportError as exc:  # pragma: no cover - example-only dependency
    raise SystemExit(
        "Install FastAPI to run this example: pip install fastapi uvicorn"
    ) from exc


class RankRequest(BaseModel):
    """Request body: model config + alternatives (+ optional context)."""

    model: dict[str, Any] = Field(
        description="DecisionKit model config (criteria, rules, method)"
    )
    alternatives: list[dict[str, Any]]
    context: dict[str, Any] = Field(default_factory=dict)
    decision_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


app = FastAPI(title="DecisionKit FastAPI Example", version="0.2.0")


@app.post("/rank")
def rank_alternatives(payload: RankRequest) -> dict[str, Any]:
    """Rank alternatives and return an audit-friendly payload."""
    try:
        model = DecisionModel.from_dict(payload.model)
        result = model.rank(payload.alternatives, context=payload.context)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return result.to_audit_dict(
        decision_id=payload.decision_id,
        metadata=payload.metadata,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
