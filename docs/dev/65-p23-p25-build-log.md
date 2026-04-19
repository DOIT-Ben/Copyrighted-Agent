# P23-P25 Build Log

## Date

- 2026-04-19

## Summary

- Continued autonomously into the next non-blocked slice because local real-provider configuration is still absent.
- Added reusable rolling-baseline behavior so baseline capture can keep generating time-series artifacts instead of one-off snapshots.
- Upgraded `/ops` from “latest status only” into an operations console that exposes trends, history, and provider gate detail.

## Change Log

### Baseline Services

- Added `format_signed_delta(...)` to `app/core/services/ops_status.py`.
- Added `list_metrics_baseline_history(...)` to scan recent baseline artifacts under `docs/dev`.
- Updated baseline status loading so delta totals are aggregated from comparison data.
- Marked baseline status `warning` whenever `needs_review` or `low_quality` is still non-zero.

### Rolling Baseline CLI

- Added `load_snapshot_from_path(...)`, `find_latest_baseline_json(...)`, and archive path helpers to `app/tools/metrics_baseline.py`.
- Added `--compare-latest-in-dir`, `--archive-dir`, and `--archive-stem`.
- Enabled timestamped archive output for both JSON and Markdown.

### Ops Console UI

- Added `Provider Checklist`, `Trend Watch`, and `Baseline History` modules to `/ops`.
- Added signed delta pills for latest baseline review debt and redaction changes.
- Added `Rolling Baseline` command guidance to the operator command panel.
- Kept the page in an admin/dashboard style instead of drifting into marketing or landing-page structure.

### Contract Alignment

- Updated `tests/unit/test_ops_status_contracts.py` for the new baseline warning semantics.
- Updated `tests/integration/test_operator_console_and_exports.py` to assert the new ops modules.

## Result

- rolling baseline archives now land in `docs/dev/history`
- `/ops` shows both current state and recent baseline history
- full regression now ends at `113 passed, 0 failed`
