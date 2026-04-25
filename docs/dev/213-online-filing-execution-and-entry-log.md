# 213 Online Filing Execution And Entry Log

- Date: 2026-04-26
- Scope: online filing entry, persistence, rerun, report linkage

## Changes

- Added structured online filing normalization and review execution into the case rebuild path.
- Extended cross-material consistency checks to compare online filing values with info form and agreement signals.
- Added API and HTML actions to save online filing data per case and trigger case rebuild.
- Added operator-page forms for case-level online filing editing.
- Added case/report display so the saved online filing fields and resulting findings are visible without downloading markdown first.

## Verification Plan

- Compile touched Python modules.
- Run unit tests for review contracts and prompt/report contracts.
- Run integration tests for upload, rerun, review-rule editing, and online filing operator flow.

## Notes

- The operator flow is intentionally case-scoped so users can adjust rules and filing fields against the current material set.
- Findings remain rule-grounded first; online filing data only affects relevant dimensions and cross-material checks when fields are actually present.
