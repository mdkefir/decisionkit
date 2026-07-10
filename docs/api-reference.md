# API reference

Public imports:

```python
from decisionkit import (
    DecisionModel,
    Criterion,
    Constraint,
    Penalty,
    Bonus,
    DecisionResult,
    RuleCondition,
    ValidationError,
    DependencyMissingError,
)
```

## DecisionModel

- `DecisionModel(criteria, method="weighted_sum", explain=True, constraints=[], penalties=[], bonuses=[])`
- `DecisionModel.from_dict(config)`
- `DecisionModel.from_json(text)`
- `DecisionModel.from_yaml(text)`  (optional extra)
- `model.to_dict()` / `to_json()` / `to_yaml()`
- `model.rank(alternatives, context=None) -> DecisionResult`

## DecisionResult

- `result.best`
- `result.ranking`
- `result.excluded`
- `result.explain()`
- `result.to_dict()`
- `result.to_audit_dict(..., include_hash=False)`
- `result.audit_hash(algorithm="sha256")`

## Rule models

- `Constraint(name, field=..., operator=..., value=..., context=..., all=..., any=..., reason=...)`
- `Penalty(..., amount=...)`
- `Bonus(..., amount=...)`

Legacy aliases `criterion`, `threshold`, and `description` remain supported.
