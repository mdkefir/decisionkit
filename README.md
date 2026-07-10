# DecisionKit

[![CI](https://github.com/mdkefir/decisionkit/actions/workflows/ci.yml/badge.svg)](https://github.com/mdkefir/decisionkit/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/decisionkit.svg?cacheSeconds=3600)](https://pypi.org/project/decisionkit/)
[![Python versions](https://img.shields.io/pypi/pyversions/decisionkit.svg?cacheSeconds=3600)](https://pypi.org/project/decisionkit/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**DecisionKit** is a lightweight explainable scoring and ranking engine for Python backends.

Describe criteria, weights, constraints, penalties, and bonuses — in code or config — then get ranked alternatives with scores, human-readable explanations, and audit-ready output.

No machine learning. No database. No web UI. Core has **zero runtime dependencies**.

## Project status

**Beta (v0.3.0)** — useful for real backend workflows; API aims to stay stable across minor releases. See [CHANGELOG.md](CHANGELOG.md).

## Installation

```bash
pip install decisionkit
```

Optional YAML support:

```bash
pip install "decisionkit[yaml]"
```

From source:

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

## Config-driven usage

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
        }
    ],
    "bonuses": [
        {
            "name": "exact_topic_bonus",
            "field": "topic_match",
            "operator": "gte",
            "value": 0.9,
            "amount": 0.05,
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
print(result.to_audit_dict(include_hash=True)["audit_hash"])
```

JSON and optional YAML helpers:

```python
model = DecisionModel.from_json(model.to_json())
# pip install "decisionkit[yaml]"
# model = DecisionModel.from_yaml(model.to_yaml())
```

## Rules: constraints, penalties, bonuses

Operators: `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `in`, `not_in`, `contains`, `between`.

Context-aware rule:

```python
{
    "name": "within_capacity",
    "field": "workload",
    "operator": "lte",
    "context": "max_workload",
}
```

Compound rule (`all` = AND, `any` = OR):

```python
{
    "name": "eligible",
    "all": [
        {"field": "available", "operator": "eq", "value": True},
        {"field": "workload", "operator": "lte", "context": "max_workload"},
    ],
}
```

## Audit export and hash

```python
audit = result.to_audit_dict(
    decision_id="req-123",
    metadata={"tenant": "acme"},
    timestamp="2026-07-10T10:00:00Z",
    include_hash=True,
)
digest = result.audit_hash()  # sha256 of canonical decision payload
```

The digest covers method, model, context, inputs, exclusions, ranking, and best alternative. It excludes `decision_id`, `metadata`, and `timestamp` by default. Details: [docs/audit.md](docs/audit.md).

## FastAPI integration

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
        return result.to_audit_dict(
            decision_id=payload.get("decision_id"),
            include_hash=True,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
```

See `examples/fastapi_example.py`.

## Django service-layer integration

Keep DecisionKit in a service module; store config in settings/admin/DB:

```python
from decisionkit import DecisionModel

def rank_reviewers(candidates: list[dict], model_config: dict) -> dict:
    model = DecisionModel.from_dict(model_config)
    result = model.rank(candidates, context={"max_workload": 5})
    return result.to_audit_dict(decision_id="editorial-assign", include_hash=True)
```

See `examples/django_service_example.py`.

## How DecisionKit compares

| Approach | Fit |
| --- | --- |
| Ad-hoc `if` / spreadsheet scoring | Fast to start, hard to explain, test, or reuse |
| Generic rule engines | Great for branching logic; weaker at weighted ranking + score breakdowns |
| Academic MCDA toolkits | Broad method coverage; often awkward for backend APIs and audits |
| **DecisionKit** | Backend-friendly weighted ranking with rules, explanations, and audit hashes |

DecisionKit is not trying to replace every MCDA method. It focuses on explainable scoring you can ship in Django/FastAPI services.

## Supported methods

| Method | Key | Notes |
| --- | --- | --- |
| Weighted sum | `weighted_sum` | Min-max normalization; `min` criteria inverted |
| TOPSIS | `topsis` | Vector normalization + closeness to ideal |

## Examples

```bash
python examples/reviewer_selection.py
python examples/vendor_ranking.py
python examples/task_prioritization.py
python examples/risk_scoring.py
python examples/django_service_example.py
```

More: [docs/examples.md](docs/examples.md)

## Documentation

- [docs/index.md](docs/index.md) — docs home
- [docs/quickstart.md](docs/quickstart.md)
- [docs/rules.md](docs/rules.md)
- [docs/audit.md](docs/audit.md)
- [docs/api-reference.md](docs/api-reference.md)

## Development

```bash
pip install -e ".[dev]"
python -m ruff check src tests examples
python -m mypy src
python -m pytest --cov=decisionkit --cov-report=term-missing
```

CI runs on Python 3.11 and 3.12 (see `.github/workflows/ci.yml`).

Release steps: [RELEASE.md](RELEASE.md)

## Roadmap

### v0.4.0

- AHP method (optional, still backend-friendly)
- Nested boolean rule trees (beyond flat `all`/`any`)
- Signed / hashed decision record helpers for long-term storage

### Later

- ELECTRE / PROMETHEE (only if API stays simple)
- `decisionkit-django` integration package
- Optional CLI for batch ranking

## License

MIT — see [LICENSE](LICENSE).
