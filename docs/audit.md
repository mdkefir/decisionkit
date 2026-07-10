# Audit

DecisionKit can export JSON-serializable audit records and deterministic digests.

## Export

```python
audit = result.to_audit_dict(
    decision_id="req-123",
    metadata={"tenant": "acme"},
    timestamp="2026-07-10T10:00:00Z",  # optional; never auto-generated
    include_hash=True,
)
```

## Hash API

```python
digest = result.audit_hash()  # sha256 hex digest
```

### What the digest includes

- `schema_version`
- `method`
- `model` (criteria, constraints, penalties, bonuses, explain flag)
- `context`
- `input_alternative_ids`
- `excluded`
- `ranking` (scores, contributions, triggered rules, explanations)
- `best`

### What the digest excludes by default

- `decision_id`
- `metadata`
- `timestamp`
- `audit_hash` itself

To include a caller-supplied timestamp in the digest:

```python
result.audit_hash(include_timestamp=True, timestamp="2026-07-10T10:00:00Z")
```

### Canonicalization

The digest is `hashlib.<algorithm>` over UTF-8 JSON with:

- `sort_keys=True`
- compact separators `(",", ":")`
- `ensure_ascii=False`
- `allow_nan=False`

Supported algorithms: `sha256` (default), `sha384`, `sha512`.
