# 232 Batch And Async Contract Hardening Log

Date: 2026-04-26

## Goal

- Strengthen real workflow coverage for batch uploads and async submission modes.
- Protect the current page split after the recent hierarchy simplification.

## Changes

- Updated `tests/integration/test_api_contracts.py`.
  - Added batch upload API coverage for `batch_same_material`.
  - Added async submission coverage for:
    - `single_case_package + manual_desensitized_review`
    - `batch_same_material + auto_review`
  - Added a small polling delay to avoid starving background worker completion in async tests.
- Updated `tests/integration/test_web_mvp_contracts.py`.
  - Added a batch upload HTML flow assertion.
  - Verified batch submission detail, export page, and batch report page stay reachable.
- Updated `tests/integration/test_manual_correction_api.py`.
  - Moved the correction-audit page assertion from the slimmed submission overview to the operator page, matching the new page responsibilities.

## Regression

- `py -m pytest tests\integration\test_api_contracts.py tests\integration\test_web_mvp_contracts.py tests\integration\test_manual_correction_api.py tests\integration\test_mode_b_pipeline_contracts.py tests\integration\test_operator_console_and_exports.py -q`
- `py -m pytest tests\e2e\test_browser_workflows.py -q`

## Result

- Batch mode, async mode, manual desensitized mode, and manual regroup flows now have stronger contract protection.
- The newer page hierarchy remains covered without forcing old page-layout expectations back into the product.
