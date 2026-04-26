# 226 Submission Detail Hierarchy Polish Log

Date: 2026-04-26

## Goal

- Make the submission detail page feel more like a directory page and less like a dense workbench.
- Keep only the import path and result destinations on the first screen.

## Changes

- Updated `app/web/page_submission.py`.
  - Reduced the import summary from 6 tiles to 4 tiles.
  - Removed duplicated material / case counts from the import summary because those already exist in the KPI row.
  - Renamed the main action panel from `业务流程` to `结果去向`.
  - Reframed the main action panel around destination pages:
    - `产物浏览`
    - `人工干预台`
    - `导出中心`
  - Replaced the old `更正审计` block in the first-screen extra area with a lighter `批次提醒` block.
  - Kept rule configuration entry points, but reduced extra explanatory density.
- Updated `tests/integration/test_web_mvp_contracts.py` to reflect the new section title.

## Regression

- `tests/integration/test_web_mvp_contracts.py`
- `tests/integration/test_operator_console_and_exports.py`

## Result

- Submission detail first screen is shorter and more navigational.
- Repeated count information is reduced.
- Existing actions, downloads, and detail routes remain unchanged.
