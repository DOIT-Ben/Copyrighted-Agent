# P23-P25 Validation

## Automated Regression

- Command: `py -m pytest`
- Result: `113 passed, 0 failed`

## Focused Regression

- Command: `py -m pytest tests\unit\test_metrics_baseline_contracts.py tests\unit\test_ops_status_contracts.py tests\integration\test_operator_console_and_exports.py`
- Result: `113 passed, 0 failed`
- Note: the local project runner executed a broad compatible regression set, so the pass count remained the full suite count.

## Rolling Baseline Validation

- Command:

```bash
py -m app.tools.metrics_baseline --compare-latest-in-dir docs\dev --archive-dir docs\dev\history --archive-stem real-sample-baseline
```

- Result:
  - generated_at `2026-04-19T23:23:30`
  - mode A `materials=24 cases=6 reports=6 unknown=0 needs_review=0 low_quality=0 redactions=252`
  - mode B `materials=11 cases=11 reports=1 unknown=0 needs_review=0 low_quality=0 redactions=152`
  - all recorded deltas were `0` against the latest previous baseline

## Generated Archive Artifacts

- `docs/dev/history/real-sample-baseline_20260419_232330.json`
- `docs/dev/history/real-sample-baseline_20260419_232330.md`

## Ops Validation

- `/ops` now exposes:
  - `Provider Readiness`
  - `Latest Backup`
  - `Latest Baseline`
  - `Provider Checklist`
  - `Trend Watch`
  - `Baseline History`
  - `Rolling Baseline`

## Deferred Validation

- Real external-provider non-sandbox smoke remains deferred on 2026-04-19 because local `config/local.json` and real credentials are still absent.
