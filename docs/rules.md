# Rules

Rules evaluate alternative fields (and optional context values) without `eval`.

## Operators

`eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `in`, `not_in`, `contains`, `between`

## Constraint / penalty / bonus

```python
{
    "name": "available_only",
    "field": "available",
    "operator": "eq",
    "value": True,
    "reason": "Must be available",
}
```

Penalties and bonuses also require a positive `amount`.

## Context comparisons

```python
result = model.rank(
    alternatives,
    context={"max_workload": 5},
)
```

```python
{
    "name": "within_capacity",
    "field": "workload",
    "operator": "lte",
    "context": "max_workload",
}
```

## Compound rules

Use flat `all` (AND) or `any` (OR):

```python
{
    "name": "eligible",
    "all": [
        {"field": "available", "operator": "eq", "value": True},
        {"field": "workload", "operator": "lte", "context": "max_workload"},
    ],
}
```
