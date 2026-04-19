# Delivery Hardening Issues And Fixes

## Date

- 2026-04-20

## Issue 1

- Symptom: newly added PowerShell scripts failed immediately with `param`-related errors.
- Root cause: `param(...)` was placed after executable statements, which PowerShell does not accept.

### Fix

- Moved `param(...)` to the top of each script.
- Revalidated the scripts through real execution.

## Issue 2

- Symptom: the first script-based real validation failed because Chinese sample paths were rendered as mojibake and could not be found.
- Root cause: localized paths were hardcoded directly in the PowerShell script, and the Windows shell/output encoding path was fragile.

### Fix

- Forced UTF-8 console / Python output in the scripts.
- Reworked `scripts/run_real_validation.ps1` to auto-resolve the sample inputs under `input/` instead of hardcoding localized paths.

## Issue 3

- Symptom: documentation, `/ops`, and real-validation behavior disagreed about whether `config/local.json` was mock or external.
- Root cause: the workspace had accumulated historical docs from both the mock-safe phase and the real-provider phase.

### Fix

- Updated `config/local.json` to the validated bridge-backed `external_http` path.
- Updated `README.md`, `docs/dev/09-runbook.md`, and `docs/dev/106-real-provider-acceptance-checklist.md`.
- Added script entrypoints to `/ops`.

## Issue 4

- Symptom: real validation still blocked even after the bridge was up.
- Root cause: the validation shell itself did not have `MINIMAX_API_KEY` exported, even though a previously started bridge process did.

### Fix

- Exported the key only for the validation process.
- Kept the key out of repository files.
- Confirmed the real validation returned `pass`.
