# Release checklist

Use this checklist before publishing a DecisionKit version to PyPI.

## 1. Pre-flight

- [ ] Version bumped in `pyproject.toml` and `src/decisionkit/__init__.py`
- [ ] `CHANGELOG.md` updated for the release
- [ ] README examples still match the public API
- [ ] No secrets or local paths committed

## 2. Quality gates

```bash
pip install -e ".[dev]"
python -m ruff check src tests examples
python -m mypy src
python -m pytest --cov=decisionkit --cov-report=term-missing
```

## 3. Build the package

```bash
python -m build
python -m twine check dist/*
```

Inspect the built artifacts:

```bash
tar -tzf dist/decisionkit-*.tar.gz | head
unzip -l dist/decisionkit-*.whl | head
```

Confirm `py.typed` and package modules are included.

## 4. TestPyPI (recommended)

```bash
python -m twine upload --repository testpypi dist/*
pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple decisionkit==X.Y.Z
python -c "from decisionkit import DecisionModel, Criterion; print('ok')"
```

## 5. PyPI

```bash
python -m twine upload dist/*
```

## 6. GitHub release

- [ ] Tag the commit: `git tag vX.Y.Z`
- [ ] Push the tag: `git push origin vX.Y.Z`
- [ ] Create a GitHub Release with changelog notes
- [ ] Confirm CI is green on the tagged commit

## Notes

- Core remains zero-dependency. Optional extras (`yaml`, `dev`) must stay optional.
- Do not include generated timestamps in audit digests unless callers opt in.
