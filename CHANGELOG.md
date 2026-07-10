# Changelog

All notable changes to DecisionKit are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0.post1] - 2026-07-10

### Fixed

- Packaging hotfix release aligned to `0.3.0.post1`

## [0.3.0] - 2026-07-10

### Added

- Deterministic audit hashing via `DecisionResult.audit_hash()` and
  `to_audit_dict(include_hash=True)`
- Markdown docs under `docs/`
- GitHub Actions CI for Python 3.11 and 3.12
- mypy configuration and typed package checks
- pytest-cov coverage configuration (`fail_under = 85`)
- Examples: vendor ranking, task prioritization, risk scoring
- `CHANGELOG.md` and `RELEASE.md`
- Public API stability tests

### Changed

- Packaging metadata and keywords for PyPI readiness
- README rewritten for public release
- Development status classifier set to Beta

## [0.2.0] - 2026-07-10

### Added

- Config loading: `from_dict` / `to_dict` / `from_json` / `to_json`
- Optional YAML support via `decisionkit[yaml]`
- `Bonus` rules and expanded operators
- Flat compound `all` / `any` rules
- Context-aware rule evaluation in `rank(..., context=...)`
- `DecisionResult.to_audit_dict(...)`

### Changed

- Constraints/penalties accept modern `field` / `value` / `reason` keys
- Alternatives may include non-numeric rule fields

### Fixed

- Legacy `criterion` / `threshold` / `description` aliases remain supported

## [0.1.0] - 2026-07-10

### Added

- Initial DecisionKit core library
- `DecisionModel`, `Criterion`, weighted sum and TOPSIS
- Min-max and vector normalization
- Hard constraints and simple penalties
- Deterministic explanations
- Reviewer, FastAPI, and Django service-layer examples

[0.3.0]: https://github.com/decisionkit/decisionkit/releases/tag/v0.3.0
[0.2.0]: https://github.com/decisionkit/decisionkit/releases/tag/v0.2.0
[0.1.0]: https://github.com/decisionkit/decisionkit/releases/tag/v0.1.0
