# 224 Ops Pass-State Copy Polish Log

Date: 2026-04-26

## Goal

- Make the operations page read correctly when release and closeout are already green.
- Remove misleading blocker-oriented fallback copy from pass-state cards.
- Fix one remaining mojibake string in `app/api/main.py`.

## Changes

- Updated `app/web/page_ops.py`.
  - Added `_ops_callout_text(...)` to choose summary vs action text by status.
  - Added `_closeout_action_list(...)` so empty action lists render positive handoff copy.
  - Applied the new helpers to both the current ops renderer and the legacy renderer.
- Updated `app/api/main.py`.
  - Replaced one residual mojibake HTTP error message with `缺少 case_id`.
- Added `tests/unit/test_page_ops_contracts.py`.

## Regression

- `tests/unit/test_page_ops_contracts.py`
- `tests/unit/test_web_source_contracts.py`
- `tests/integration/test_operator_console_and_exports.py`

## Result

- Ops pass-state cards no longer imply there are blockers when the environment is already green.
- Empty closeout action lists now render positive next-step guidance.
- Web source mojibake guard passes again.
