# Automated Quality Gates

## Purpose

TASK-0006 establishes one reproducible quality contract for local development and protected
Pull Requests. The same commands apply to Python 3.11 and Python 3.12.

## Local commands

Install the project and quality tools:

```bash
python -m pip install --upgrade pip setuptools wheel
python -m pip install --editable ".[dev]"
```

Run the complete gate set from the repository root:

```bash
python -m compileall -q src scripts tests
ruff check src tests scripts
ruff format --check src tests scripts
mypy src/ai_os
pytest --cov=ai_os --cov-report=term-missing --cov-report=xml
python -m build
aios bootstrap --root .
aios control-plane check --root .
```

The coverage threshold is defined once in `pyproject.toml` and is currently 80%.

## CI strategy

`.github/workflows/control-plane-check.yml` runs on every Pull Request, relevant pushes to
`main`, and manual dispatch. Its matrix executes the same gates on Python 3.11 and 3.12.
The stable job names remain `Python 3.11` and `Python 3.12` so the active
`main-governance` ruleset can require them.

The workflow validates, in order:

1. installation and byte-code compilation;
2. Ruff lint and formatting;
3. strict mypy type checking;
4. the full pytest suite with branch coverage;
5. source/wheel distribution build;
6. Control Plane bootstrap and consistency;
7. machine-readable Control Plane and coverage evidence upload.

## Failure behavior

Each command is a blocking gate. A non-zero exit code fails that matrix job. Because matrix
`fail-fast` is disabled, both supported Python versions finish and provide independent
evidence. Pending or failed required checks prevent merge to `main`.

Warnings from the Control Plane checker remain subject to its existing severity contract:
a checker exit code of zero is non-blocking; a failure exit code blocks the Pull Request.
Quality evidence is uploaded with `if: always()` where available, even after an earlier
failure. Missing diagnostic artifacts produce a warning instead of hiding the original
failed gate.

Do not bypass a failed gate. Correct the cause on the feature branch, rerun the complete
gate set, obtain Reviewer approval, and merge only after both required checks succeed.
