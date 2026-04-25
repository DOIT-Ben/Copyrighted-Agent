# 195 Review Rule Editor Layout Log

Time: 2026-04-25 14:56 +08:00

## Goal

Make the internal review-dimension rules easier to understand and edit during a submission workflow.

## Changes

- Added per-dimension descriptions to the checkbox cards.
- Added direct `编辑规则` links beside each dimension when editing a concrete submission review profile.
- Rebuilt the review-rule detail page into a compact admin layout:
  - summary strip
  - left-side rule editor
  - right-side prompt/rule preview
  - default comparison section
- Kept all rule actions visible: save, save and rerun, restore default, and return to operator console.

## Verification

- `py -m pytest tests.integration.test_web_mvp_contracts tests.unit.test_web_source_contracts -q` -> 9 passed.
- `py -m pytest tests.integration.test_operator_console_and_exports tests.e2e.test_browser_workflows -q` -> 9 passed.
- `py -m pytest tests.unit -q` -> 101 passed.
- `py -m pytest tests.integration -q` -> 40 passed.

## Notes

- Import page still shows dimension checkboxes without edit links because no submission exists yet.
- Submission/operator pages now expose rule editing in-context because a submission id is available.
