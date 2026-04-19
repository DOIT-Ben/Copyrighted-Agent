# P23-P25 Issues

## Date

- 2026-04-19

## Issue 23

- Symptom: the baseline service semantics changed, but the old unit test still expected `status == "ok"` whenever a baseline artifact existed.
- Impact: regression would fail even though the service behavior was intentionally improved.
- Root cause: the previous contract treated baseline status as “artifact presence”, while the new operator-facing meaning is “artifact presence plus current review debt health”.

## Fix

- Updated the contract to expect `warning` when `needs_review` or `low_quality` is non-zero.
- Added a delta-total assertion so the test now covers the new behavior instead of only the old one.

## Issue 24

- Symptom: operators could generate baseline comparison artifacts from CLI, but the web console still did not expose history, deltas, or the recommended rolling command.
- Impact: observability existed only for developers who already knew which docs and commands to inspect.
- Root cause: the UI stopped at “show latest card” and did not complete the last-mile operator workflow.

## Fix

- Added `Trend Watch`, `Baseline History`, delta pills, and `Rolling Baseline` command guidance to `/ops`.
- Added `Provider Checklist` so ops users can see why real-provider smoke is still gated.

## Issue 25

- Symptom: a real non-sandbox provider smoke still cannot be executed in the current local environment.
- Impact: release validation for a real gateway remains incomplete even though the code path is ready for it.
- Root cause: `config/local.json` and real provider secrets are not present locally as of 2026-04-19.

## Fix

- Treated the gap as an environment dependency rather than a code blocker.
- Surfaced the dependency on `/ops` and in the runbook instead of stalling the rest of the round.
