# P26-P29 Issues

## Date

- 2026-04-20

## Issue 26

- Symptom: the first live sandbox probe attempt still failed even with a valid sandbox command.
- Impact: it looked like the probe path was broken, which could have sent the team chasing the wrong code area.
- Root cause: PowerShell `Start-Job` did not start inside the repository root, so the background process did not reliably launch the local module entrypoint.

## Fix

- Added an explicit `Set-Location` to the repository root inside the job script block before running `py -m app.tools.provider_sandbox`.
- Re-ran the probe and confirmed HTTP `200` plus persisted latest-probe artifact output.

## Issue 27

- Symptom: provider readiness output was too coarse for operators to tell whether the system was simply in mock mode, incompletely configured, ready for probe, or failed after a probe.
- Impact: `/ops`, startup checks, and CLI output did not yet form a clear operational decision tree.
- Root cause: the earlier readiness structure focused on broad health labels instead of explicit phase transitions and blocking reasons.

## Fix

- Introduced explicit readiness phases, `blocking_items`, and `recommended_action`.
- Reused the same structure across the provider service, startup checks, CLI output, and `/ops`.

## Issue 28

- Symptom: the latest probe result was visible only in terminal output after a manual probe run.
- Impact: operators had no durable latest-known probe record once the command scrollback was gone.
- Root cause: probe execution did not persist a latest-result artifact under runtime data.

## Fix

- Persisted the latest result to `data/runtime/ops/provider_probe_latest.json`.
- Surfaced the latest artifact summary and probe outcome on `/ops`.

## Issue 29

- Symptom: real non-sandbox provider smoke still could not be completed on 2026-04-20.
- Impact: the real gateway path remains environment-blocked even though the readiness / observability code is now in place.
- Root cause: local `config/local.json` is absent and no real endpoint / model / API-key environment mapping is configured in the current workspace.

## Fix

- Treated the gap as an explicit environment dependency rather than a code blocker.
- Completed sandbox-first validation, documented the blocker in `/ops` and `docs/dev`, and left the next real-smoke step ready for local credentials.
