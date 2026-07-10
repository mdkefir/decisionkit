# Quick start

## Install

```bash
pip install decisionkit
```

## Code API

```python
from decisionkit import DecisionModel, Criterion

model = DecisionModel(
    criteria=[
        Criterion("quality", weight=0.6, direction="max"),
        Criterion("cost", weight=0.4, direction="min"),
    ],
    method="weighted_sum",
)

result = model.rank([
    {"id": "a", "quality": 8, "cost": 120},
    {"id": "b", "quality": 7, "cost": 80},
])

print(result.best.id)
print(result.explain())
```

## Config API

```python
from decisionkit import DecisionModel

model = DecisionModel.from_dict({
    "method": "weighted_sum",
    "criteria": [
        {"name": "quality", "weight": 0.6, "direction": "max"},
        {"name": "cost", "weight": 0.4, "direction": "min"},
    ],
})

result = model.rank([
    {"id": "a", "quality": 8, "cost": 120},
    {"id": "b", "quality": 7, "cost": 80},
])
print(result.to_audit_dict(include_hash=True)["audit_hash"])
```
