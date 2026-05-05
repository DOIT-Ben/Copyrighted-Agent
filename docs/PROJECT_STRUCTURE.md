# Project Structure

This repository is now organized around the Web MVP in `app/`.

## Runtime Application

- `app/api/`: HTTP routes and local server entrypoint.
- `app/core/domain/`: dataclasses and enums shared across the system.
- `app/core/parsers/`: document parsing, text cleanup, page segmentation, and parse quality checks.
- `app/core/privacy/`: desensitization and AI-safe payload preparation.
- `app/core/reviewers/`: deterministic rule reviewers and AI adapter boundary.
- `app/core/services/`: orchestration services for corrections, exports, runtime storage, review profiles, global submission review, ops, and persistence.
- `app/core/pipelines/`: submission ingestion pipeline.
- `app/core/reports/`: markdown report renderers.
- `app/web/`: server-rendered admin UI pages and shared view helpers.
- `app/tools/`: operational CLIs for validation, provider probing, metrics, backup, and cleanup.

## Configuration And Runtime Data

- `config/local.example.json`: safe local configuration template.
- `config/local.json`: checked-in local default that uses environment-variable based secrets only.
- `data/runtime/`: local SQLite database, logs, parsed artifacts, and generated reports, ignored by Git.
- `input/` and `output/`: local sample materials and exports, ignored by Git.

## Tests

- `tests/unit/`: focused contracts for rules, services, UI source structure, and utility behavior.
- `tests/integration/`: upload flows, API contracts, persistence, provider bridge, and operational workflows.
- `tests/e2e/`: browser-style workflow coverage against the local app.
- `tests/non_functional/`: repository-level checks such as encoding guardrails.
- `docs/ENCODING.md`: UTF-8 and Chinese copywriting guardrails for Windows-safe editing.

## Legacy Area

- `cli.py` and `src/` are legacy CLI-era code kept for migration history and comparison.
- New product work should target `app/`, not the legacy CLI path.
- `_test_read.py` was removed because it was a one-off local material debugging script.

## Dependency Management

- `pyproject.toml` is the canonical project metadata for `uv`.
- `requirements.txt` is retained as a compatibility install list for older scripts and constrained environments.

Common commands:

```powershell
uv sync --dev
.venv\Scripts\python.exe -m app.api.main
.venv\Scripts\pytest.exe -q
```
