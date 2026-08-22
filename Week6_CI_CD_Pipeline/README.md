# Week 6 — Continuous Integration for the Inventory Module

## What this is

A GitHub Actions CI pipeline (`.github/workflows/ci.yml`) wired to the
Week 3 project (`Week3_Automated_Testing/`), since that's the project
in this repo with an actual automated test suite — the thing CI exists
to run automatically. On every push or pull request to `main`, the
pipeline lints the code, runs all 31 tests across four Python versions
in parallel, enforces a minimum coverage threshold, and uploads a
coverage report as a build artifact.

## Why GitHub Actions

This repository already lives on GitHub, so Actions requires no
external account, no third-party service authorization, and no secrets
to wire up — the workflow file itself is the entire setup. Travis CI
and CircleCI would need a separate account linked to the repo; Actions
is the path of least friction here and is what a huge share of
public/open-source Python repos actually use today.

## Pipeline stages

```
push / PR to main
        |
        v
  checkout code
        |
        v
  set up Python (matrix: 3.9, 3.10, 3.11, 3.12 — all four in parallel)
        |
        v
  install dependencies (requirements.txt + flake8)
        |
        v
  lint with flake8            <-- fails fast, before spending time on tests
        |
        v
  run pytest + coverage        <-- fails the whole job if any test fails
        |                          or coverage drops below 95%
        v
  upload coverage.xml artifact (only from the 3.12 run, to avoid 4 duplicates)
```

If **any** step fails on **any** Python version, that matrix job is
marked failed and the overall workflow run shows as failed — exactly
the "pipeline fails if tests do not pass" requirement.

## The workflow file

```yaml
name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.9", "3.10", "3.11", "3.12"]
    defaults:
      run:
        working-directory: Week3_Automated_Testing
    steps:
      - name: Check out repository
        uses: actions/checkout@v4
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install flake8
      - name: Lint with flake8
        run: |
          flake8 inventory tests --max-line-length=100 --extend-ignore=E203
      - name: Run tests with coverage
        run: |
          pytest tests/ -v --cov=inventory --cov-report=term-missing \
            --cov-report=xml --cov-fail-under=95
      - name: Upload coverage report
        if: matrix.python-version == '3.12'
        uses: actions/upload-artifact@v4
        with:
          name: coverage-report
          path: Week3_Automated_Testing/coverage.xml
```

### Design decisions

- **`working-directory: Week3_Automated_Testing`** — this repo holds
  six separate weekly projects, not one Python package at the root, so
  every command needs to run from inside the specific project folder
  rather than the repo root.
- **Matrix build across 4 Python versions** — catches version-specific
  breakage a single-version run would miss, and `fail-fast: false`
  means one version failing doesn't cancel the others mid-run, so a
  single CI run always shows the full picture across all four.
- **Lint before test** — a cheap, fast check runs first and fails the
  job immediately if code style is broken, before spending time on the
  test suite.
- **`--cov-fail-under=95`** — coverage isn't just reported, it's
  enforced. A change that drops coverage below 95% fails CI even if
  every existing test still passes, catching untested new code
  automatically rather than relying on someone noticing a report.
- **Artifact upload gated to one Python version** — uploading the same
  coverage.xml four times (once per matrix entry) would just be
  redundant storage for no benefit.

## Local replication (what CI runs, run by hand)

This is exactly what was run locally to confirm the pipeline would
pass before ever pushing it:

```bash
cd Week3_Automated_Testing
pip install -r requirements.txt
pip install flake8

flake8 inventory tests --max-line-length=100 --extend-ignore=E203
# exit code 0 -- clean

pytest tests/ -v --cov=inventory --cov-report=term-missing --cov-report=xml --cov-fail-under=95
# 31 passed, 98.55% coverage, "Required test coverage of 95% reached"
```

## Triggering and viewing the pipeline

Once this workflow file is on `main`, any future push or pull request
automatically triggers a run. To view it:

1. Go to the repository on GitHub.
2. Click the **Actions** tab.
3. The most recent run is listed with a status icon (yellow = running,
   green check = passed, red X = failed).
4. Click into a run to see each matrix job (3.9/3.10/3.11/3.12)
   individually, and click into any job to see the full step-by-step
   log — identical output to what running the commands locally
   produces.
5. On a passed run for the 3.12 job, the `coverage-report` artifact is
   available for download at the bottom of that run's page.

## Challenges encountered

- **Working directory.** The default GitHub Actions checkout puts you
  at the repo root, but the project under test lives in a subfolder
  alongside five other unrelated weekly projects. Using `defaults.run.
  working-directory` at the job level (rather than prefixing every
  single `run:` step with `cd Week3_Automated_Testing &&`) keeps the
  workflow file readable and avoids repeating that path five times.
- **Choosing a coverage floor.** `--cov-fail-under=95` was set based on
  the actual coverage this suite already achieves (98.55%, see Week 3's
  `TESTING.md`), leaving a small margin rather than requiring exactly
  100% — which would make CI overly brittle against the one
  legitimately hard-to-test line (the `if __name__ == "__main__":`
  guard).
