# 176 Home Page Simplification Log

## Goal

Further simplify the home page so it behaves as a clean intake screen:

- upload
- choose mode
- choose review strategy
- go to latest result

## Changes

- Rebuilt `app/web/page_home.py`
  - Reduced explanatory copy inside the import area.
  - Removed the extra process panel from the home page.
  - Kept only:
    - import entry
    - latest result
    - recent imports
  - Shortened the side explanation block to only explain result destination and the two main processing paths.

## UX Outcome

- The home page now reads as a single-purpose intake screen.
- The user no longer has to scan workflow teaching blocks before uploading.
- More detailed handling remains in batch, materials, operator, and export pages.

## Validation

- `D:\Soft\python310\python.exe -m py_compile app\web\page_home.py`
- `D:\Soft\python310\python.exe -m pytest tests\integration\test_web_mvp_contracts.py -q`
