# DecisionKit

Explainable decision support, scoring, and ranking for Python backends.

DecisionKit lets you describe criteria, weights, constraints, penalties, and bonuses in code or config, then get ranked alternatives with scores, explanations, and audit-ready output. No machine learning, no database, no web framework required.

## Installation

```bash
pip install decisionkit
```

Optional YAML support:

```bash
pip install "decisionkit[yaml]"
```

Until the package is published on PyPI, install from source:

```bash
pip install -e ".[dev]"
```

## Quick start

```python
from decisionkit import DecisionModel, Criterion

model = DecisionModel(
    criteria=[
        Criterion("relevance", weight=0.5, direction="max"),
        Criterion("rating", weight=0.3, direction="max"),
        Criterion("workload", weight=0.2, direction="min"),
    ],
    method="weighted_sum",
    explain=True,
)

result = model.rank([
    {"id": "reviewer_1", "relevance": 0.92, "rating": 4.8, "workload": 7},
    {"id": "reviewer_2", "relevance": 0.81, "rating": 4.5, "workload": 2},
])

print(result.best.id)
print(result.explain())
```

## Config-driven quick start

```python
from decisionkit import DecisionModel

config = {
    "method": "weighted_sum",
    "explain": True,
    "criteria": [
        {"name": "relevance", "weight": 0.5, "direction": "max"},
        {"name": "rating", "weight": 0.3, "direction": "max"},
        {"name": "workload", "weight": 0.2, "direction": "min"},
    ],
    "constraints": [
        {
            "name": "available_only",
            "field": "available",
            "operator": "eq",
            "value": True,
            "reason": "Reviewer must be available",
        }
    ],
    "penalties": [
        {
            "name": "high_workload_penalty",
            "field": "workload",
            "operator": "gt",
            "value": 5,
            "amount": 0.1,
            "reason": "High workload reduces recommendation score",
        }
    ],
    "bonuses": [
        {
            "name": "exact_topic_bonus",
            "field": "topic_match",
            "operator": "gte",
            "value": 0.9,
            "amount": 0.05,
            "reason": "Very strong topic match",
        }
    ],
}

model = DecisionModel.from_dict(config)

result = model.rank(
    [
        {
            "id": "reviewer_1",
            "relevance": 0.92,
            "rating": 4.8,
            "workload": 7,
            "available": True,
            "topic_match": 0.95,
        },
        {
            "id": "reviewer_2",
            "relevance": 0.81,
            "rating": 4.5,
            "workload": 2,
            "available": True,
            "topic_match": 0.8,
        },
    ],
    context={"max_workload": 5},
)

print(result.best.id)
print(result.explain())
print(result.to_audit_dict(decision_id="demo-1"))
```

### JSON config

```python
model = DecisionModel.from_json(open("model.json", encoding="utf-8").read())
print(model.to_json())
```

### YAML config

Requires `pip install "decisionkit[yaml]"`.

```python
model = DecisionModel.from_yaml(open("model.yaml", encoding="utf-8").read())
print(model.to_yaml())
```

## Rules: constraints, penalties, bonuses

Supported operators: `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `in`, `not_in`, `contains`, `between`.

Rules can compare an alternative field to a literal value or to a context key:

```python
{
    "name": "within_capacity",
    "field": "workload",
    "operator": "lte",
    "context": "max_workload",
    "reason": "Workload must stay within capacity",
}
```

Compound rules use `all` (AND) or `any` (OR):

```python
{
    "name": "eligible",
    "all": [
        {"field": "available", "operator": "eq", "value": True},
        {"field": "workload", "operator": "lte", "context": "max_workload"},
    ],
    "reason": "Available and within capacity",
}
```

## Audit export

```python
audit = result.to_audit_dict(
    decision_id="req-123",
    metadata={"tenant": "acme"},
    timestamp="2026-07-10T10:00:00Z",  # optional; not auto-generated
)
```

The audit payload includes model config, context, input ids, exclusions, score breakdowns, triggered penalties/bonuses, and the selected best alternative. It is JSON-serializable.

## Why DecisionKit exists

Most teams eventually hard-code scoring logic inside views, services, or spreadsheets. That logic is hard to test, hard to explain, and hard to reuse.

Academic MCDA packages are powerful, but often awkward for day-to-day backend work.

DecisionKit is a backend-friendly decision engine:

- clean, typed Python API
- config-driven models (dict / JSON / optional YAML)
- explainable ranking output
- constraints, penalties, bonuses
- audit-friendly results for APIs and logs
- no ML, no ORM, no framework lock-in

## Supported methods

| Method | Key | Notes |
| --- | --- | --- |
| Weighted sum (SAW) | `weighted_sum` | Min-max normalization; `min` criteria are inverted so higher is always better |
| TOPSIS | `topsis` | Vector normalization and closeness to the ideal solution |

## FastAPI example

```python
from fastapi import FastAPI, HTTPException
from decisionkit import DecisionModel, ValidationError

app = FastAPI()

@app.post("/rank")
def rank(payload: dict):
    try:
        model = DecisionModel.from_dict(payload["model"])
        result = model.rank(
            payload["alternatives"],
            context=payload.get("context", {}),
        )
        return result.to_audit_dict(decision_id=payload.get("decision_id"))
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
```

See `examples/fastapi_example.py` for a complete request model.

## Django service-layer example

Store the DecisionKit config in admin/settings/DB, then rank in a service module:

```python
from decisionkit import DecisionModel

def rank_reviewers(candidates: list[dict], model_config: dict) -> dict:
    model = DecisionModel.from_dict(model_config)
    result = model.rank(candidates, context={"max_workload": 5})
    return result.to_audit_dict(decision_id="editorial-assign")
```

See `examples/django_service_example.py` for a DTO-based service pattern.

## Examples

```bash
python examples/reviewer_selection.py
python examples/django_service_example.py
```

## Development

```bash
pip install -e ".[dev]"
python -m pytest
python -m ruff check src tests examples
```

## Roadmap

### v0.3.0

- AHP method
- richer audit hashing / signed decision records
- FastAPI dependency helpers
- first-class Django integration package sketch

### Later

- ELECTRE / PROMETHEE
- optional CLI for batch ranking

## License

MIT
