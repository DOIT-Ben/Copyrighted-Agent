# 175 Submission Detail Simplification Log

## Goal

Make the batch detail page lighter and more operational:

- keep only summary and next-step entry points on first screen
- remove dense descriptive content from the main view
- push secondary content into expandable sections

## Changes

- Simplified `app/web/page_submission.py`
  - Batch detail page now prioritizes:
    - `导入摘要`
    - `下一步`
    - `少量提醒`
    - `更多信息`
  - Main screen no longer leads with long review/configuration blocks.
  - Review configuration and correction audit are still available, but moved into collapsed sections.

- Updated integration contract expectations
  - Rewrote `tests/integration/test_web_mvp_contracts.py` as clean UTF-8
  - Updated submission page assertions to match the new simplified UI contract

## UX Outcome

- The batch detail page now behaves like a routing page instead of a dense dashboard.
- Operators can decide quickly whether to:
  - inspect materials/desensitized files
  - enter operator actions
  - export results

## Validation

- `D:\Soft\python310\python.exe -m py_compile app\web\page_submission.py tests\integration\test_web_mvp_contracts.py`
- `D:\Soft\python310\python.exe -m pytest tests\integration\test_web_mvp_contracts.py -q`
