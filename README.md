# DecisionKit

Explainable decision support, scoring, and ranking for Python backends.

DecisionKit lets you describe criteria, weights, constraints, and a decision method in a few lines of code, then get ranked alternatives with scores and human-readable explanations. No machine learning, no database, no web framework required.

## Installation

```bash
pip install decisionkit
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
print(result.ranking)
print(result.explain())
```

Example explanation:

```text
reviewer_1 ranked #1 with score 0.8. It had strong relevance and rating values. Score is the weighted sum of benefit-normalized criterion values.
reviewer_2 ranked #2 with score 0.2. It had strong relevance and rating values, while its lower workload improved its score because workload is minimized. Score is the weighted sum of benefit-normalized criterion values.
```

## Why DecisionKit exists

Most teams eventually hard-code scoring logic inside views, services, or spreadsheets. That logic is hard to test, hard to explain, and hard to reuse.

Academic MCDA packages are powerful, but often awkward for day-to-day backend work.

DecisionKit is a backend-friendly decision engine:

- clean, typed Python API
- explainable ranking output
- JSON-friendly results for APIs and audit logs
- no ML, no ORM, no framework lock-in

Useful for reviewer selection, vendor ranking, task prioritization, candidate scoring, risk scoring, and similar weighted decisions.

## Supported methods

| Method | Key | Notes |
| --- | --- | --- |
| Weighted sum (SAW) | `weighted_sum` | Min-max normalization; `min` criteria are inverted so higher is always better |
| TOPSIS | `topsis` | Vector normalization and closeness to the ideal solution |

Also included in the MVP:

- criterion directions: `max` / `min`
- hard `Constraint` filters
- soft `Penalty` adjustments
- structured + plain-text explanations

## FastAPI example

```python
from fastapi import FastAPI, HTTPException
from decisionkit import Criterion, DecisionModel, ValidationError

app = FastAPI()

@app.post("/rank")
def rank(payload: dict):
    try:
        model = DecisionModel(
            criteria=[Criterion(**c) for c in payload["criteria"]],
            method=payload.get("method", "weighted_sum"),
        )
        return model.rank(payload["alternatives"]).to_dict()
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
```

See `examples/fastapi_example.py` for a complete request model.

## Django service-layer example

Keep DecisionKit in a service module, not in views:

```python
from decisionkit import Criterion, DecisionModel

def rank_reviewers(candidates: list[dict]) -> dict:
    model = DecisionModel(
        criteria=[
            Criterion("relevance", weight=0.5, direction="max"),
            Criterion("rating", weight=0.3, direction="max"),
            Criterion("workload", weight=0.2, direction="min"),
        ],
        method="weighted_sum",
    )
    return model.rank(candidates).to_dict()
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
```

## Roadmap

### v0.2.0

- JSON/YAML config loading
- AHP method
- richer rule engine (bonuses, compound conditions)
- audit log export helpers

### Later

- ELECTRE / PROMETHEE
- `decisionkit-django` integration package
- FastAPI dependency helpers
- optional CLI for batch ranking

## License

MIT
