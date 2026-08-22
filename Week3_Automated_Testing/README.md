# Week 3 — Automated Tests for a Python Module

## What this is

This deliverable contains a small, well-structured Python module
(`inventory/`) and a comprehensive `pytest` test suite (`tests/`) for it.

The module itself is the corrected inventory-reporting tool from the
Week 2 debugging exercise, lightly refactored (see
`inventory/core.py` docstring) to make it straightforward to unit test —
specifically, `main()` was split into a parameterized `run_report()`
function so the full pipeline can be tested against temporary files
instead of hardcoded filenames.

## Project structure

```
inventory/
  __init__.py       - package exports
  core.py           - all module logic (read, compute, write, CLI)
tests/
  __init__.py
  test_core.py       - 31 automated tests (unit + integration)
TESTING.md            - test methodology and a table explaining every test case
requirements.txt       - pytest + pytest-cov
```

## How to run it

```bash
pip install -r requirements.txt

# Run the module directly (requires an inventory.csv in the cwd):
python3 -m inventory.core

# Run the test suite:
pytest tests/ -v

# Run with coverage:
pytest tests/ --cov=inventory --cov-report=term-missing
```

Current result: **31 tests passing, 99% line coverage.**

## Test methodology, in brief

- Every function in `inventory/core.py` is either pure (no I/O — tested
  with direct input/output assertions) or isolated I/O (tested against
  pytest's `tmp_path` fixture, never touching real files).
- Boundary conditions are tested explicitly wherever the code has a
  comparison operator that could be off by one (e.g. quantity exactly
  equal to a discount threshold or low-stock cutoff).
- Every bug fixed during the Week 2 debugging exercise has a dedicated
  regression test, so it can never silently reappear.
- An integration test (`TestRunReportIntegration`) exercises the full
  read -> compute -> write pipeline against real (temporary) files, to
  catch any issue that only shows up when the pieces run together.

See `TESTING.md` for the full case-by-case breakdown of what each test
covers and why it was chosen.
