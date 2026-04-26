# 225 Report Snapshot Polish Log

Date: 2026-04-26

## Goal

- Make the report page easier to scan on first open.
- Put the most important issues, evidence, and rules into a short summary area before the longer trace tables.

## Changes

- Updated `app/web/page_report.py`.
  - Added `_issue_snapshot_board(...)`.
  - Added a new report panel: `问题一眼看懂`.
  - Each snapshot card now shows:
    - `哪里不对`
    - `怎么发现的`
    - `对应规则`
    - `建议动作`
    - `命中维度`
- Updated `tests/integration/test_web_mvp_contracts.py` to assert the new section and key phrases.

## Regression

- `tests/integration/test_web_mvp_contracts.py`
- `tests/integration/test_operator_console_and_exports.py`

## Result

- Report first screen now has a shorter decision layer before the detailed trace and evidence sections.
- Existing report navigation, downloads, and operator pages remain green.
