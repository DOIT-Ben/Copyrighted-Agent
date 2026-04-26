# 219 Legacy Render Entry Cleanup Log

- Date: 2026-04-26
- Scope: remove ambiguous same-name page render fallbacks after the final UI hierarchy passes

## Changes

- Renamed the older submission detail renderer to `render_submission_detail_legacy`.
- Renamed the older ops renderer to `render_ops_page_legacy`.
- Kept the newer implementations as the only active public render entry points.
- Left the legacy code in place for now because the source files still contain mixed encoding noise, and a full hard-delete pass is higher risk than value at this stage.

## Why

- During the previous rounds, tail-appended overrides were the safest way to keep momentum while avoiding fragile in-place edits.
- Once behavior stabilized, the bigger maintenance risk became ambiguous duplicate function names.
- This pass removes that ambiguity without changing runtime behavior.

## Validation

- `py -m py_compile app\\web\\page_submission.py app\\web\\page_ops.py app\\web\\page_report.py`
- `py -m pytest tests\\integration\\test_operator_console_and_exports.py tests\\integration\\test_web_mvp_contracts.py tests\\integration\\test_manual_correction_api.py -q`
