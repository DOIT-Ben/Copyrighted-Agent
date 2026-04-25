# 174 Report And Case Simplification Log

## Goal

Reduce visual noise on the case page and report page so operators see the primary path first:

- result
- issues
- dimensions
- export

Secondary information should remain available, but only on demand.

## Changes

- Rebuilt `app/web/page_case.py`
  - Reduced top-level information density.
  - Kept only:
    - overview
    - AI summary
    - issue queue
    - dimension summary
    - report entry
  - Moved these into collapsed advanced sections:
    - dimension details
    - review profile
    - material matrix
    - LLM prompt snapshot

- Rebuilt `app/web/page_report.py`
  - Simplified the default report reading path.
  - Primary visible sections now focus on:
    - review result
    - dimensions
    - issues
    - materials
  - Moved secondary information behind fold:
    - review profile
    - prompt snapshot
    - raw markdown

## UX Intent

- Default view should answer:
  - What is the conclusion?
  - What is wrong?
  - What should I open next?
- Deep debugging content remains available without crowding the main screen.

## Validation

- `D:\Soft\python310\python.exe -m py_compile app\web\page_case.py app\web\page_report.py`
- `D:\Soft\python310\python.exe -m pytest tests\integration\test_web_mvp_contracts.py -q`
