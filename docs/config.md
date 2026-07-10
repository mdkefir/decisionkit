# Config

DecisionKit models can be created from plain dictionaries, JSON, or optional YAML.

## Dict / JSON

```python
from decisionkit import DecisionModel

config = {
    "method": "weighted_sum",
    "explain": True,
    "criteria": [
        {"name": "relevance", "weight": 0.5, "direction": "max"},
        {"name": "workload", "weight": 0.5, "direction": "min"},
    ],
    "constraints": [],
    "penalties": [],
    "bonuses": [],
}

model = DecisionModel.from_dict(config)
assert DecisionModel.from_json(model.to_json()).to_dict() == model.to_dict()
```

## YAML (optional)

```bash
pip install "decisionkit[yaml]"
```

```python
model = DecisionModel.from_yaml(open("model.yaml", encoding="utf-8").read())
print(model.to_yaml())
```

If PyYAML is missing, YAML helpers raise `DependencyMissingError` with install guidance.

## Legacy keys

Rule configs accept both modern and legacy names:

- `field` / `criterion`
- `value` / `threshold`
- `reason` / `description`
