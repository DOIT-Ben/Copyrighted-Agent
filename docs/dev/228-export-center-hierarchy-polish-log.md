# 228 Export Center Hierarchy Polish Log

Date: 2026-04-26

## Goal

- Make the export page read like a delivery page first, and a support page second.
- Separate handoff assets from troubleshooting artifacts.

## Changes

- Updated `app/web/page_submission.py`.
  - Split the old single export panel into:
    - `导出中心`
    - `排障附件`
  - Kept reports and batch bundle in the handoff area.
  - Moved app log download into the support area.
  - Reframed the top summary around `先下报告和批次包`.
- Added an integration assertion in `tests/integration/test_operator_console_and_exports.py`.

## Regression

- `tests/integration/test_operator_console_and_exports.py`
- `tests/integration/test_web_mvp_contracts.py`

## Result

- The export page now separates business delivery assets from engineering support logs.
- Download behavior and routes remain unchanged.
