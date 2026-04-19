# Next Round Execution Todo

## Execution Status 2026-04-20

- Current slice completed; implementation, validation, and closeout are recorded in `docs/dev/72-77`
- Remaining blocked item: real non-sandbox provider smoke still depends on local `config/local.json` and real credentials

## Date

- 2026-04-19

## Goal

- Continue the project from the current stable MVP state.
- Prioritize real provider readiness, provider observability, and operator-facing history/ops polish.
- Keep every step traceable in `docs/dev`.

## Execution Order Proposal

### Phase 0: Round Setup And Traceability

- [ ] Create this round's document set in `docs/dev`
- [ ] Write round plan with scope, dependencies, risks, and exit criteria
- [ ] Write initial build-log entry with current project baseline
- [ ] Write initial validation checklist for this round
- [ ] Snapshot current blockers:
  - [ ] `config/local.json` missing
  - [ ] no real provider endpoint/model/key configured locally
- [ ] Record the current stable baseline:
  - [ ] full regression currently passing
  - [ ] latest rolling baseline archive exists
  - [ ] `/ops` trend watch is already online

### Phase 1: Real Provider Readiness Audit

- [ ] Audit `app/core/services/app_config.py`
- [ ] Audit `app/core/services/provider_probe.py`
- [ ] Audit `app/core/services/startup_checks.py`
- [ ] Audit `/ops` provider checklist rendering
- [ ] Identify all fields required for real provider smoke:
  - [ ] provider name
  - [ ] endpoint
  - [ ] model
  - [ ] API key env name
  - [ ] desensitized-only boundary switch
  - [ ] fallback strategy
- [ ] Tighten readiness messages so every missing field is explicit
- [ ] Ensure readiness status distinguishes:
  - [ ] not configured
  - [ ] partially configured
  - [ ] configured but probe not run
  - [ ] configured and probe passed
  - [ ] configured and probe failed

### Phase 2: Real Provider Smoke Flow Hardening

- [ ] Decide whether current `provider_probe` flow is sufficient or needs a dedicated persisted smoke result
- [ ] If needed, add a lightweight persisted probe-result artifact under runtime data
- [ ] Ensure the probe request path uses desensitized synthetic payload only
- [ ] Ensure the probe never sends raw user material
- [ ] Normalize probe success/failure output into a stable structure
- [ ] Add or tighten structured logs for:
  - [ ] probe started
  - [ ] readiness failed before request
  - [ ] probe HTTP success
  - [ ] probe HTTP failure
  - [ ] response normalization failure
- [ ] Add clear operator-facing remediation text for common failures:
  - [ ] missing endpoint
  - [ ] missing model
  - [ ] missing API key env
  - [ ] connection refused
  - [ ] timeout
  - [ ] invalid JSON response

### Phase 3: Ops Console Provider Observability

- [ ] Add latest probe summary service if not already present
- [ ] Show latest probe time on `/ops`
- [ ] Show latest probe result on `/ops`
- [ ] Show latest probe error code/detail on `/ops` when failed
- [ ] Show whether the current environment is still mock-only
- [ ] Add a command block for the recommended real provider smoke command
- [ ] Add a command block for the recommended sandbox-first sequence
- [ ] Make sure the UI stays in admin/management style, not landing-page style

### Phase 4: Baseline History And Operator UX Follow-Up

- [ ] Review whether `/ops` baseline history needs filter/sort controls
- [ ] Add clearer labels for archive artifacts if current naming is too low-context
- [ ] Consider adding direct download links for recent baseline archives
- [ ] Consider surfacing a "latest healthy baseline" signal
- [ ] Consider surfacing a "latest degraded baseline" warning if review debt rises again
- [ ] Keep any UI changes consistent with the existing dashboard system

### Phase 5: Contract And Regression Coverage

- [ ] Add unit coverage for any new provider status/probe summary helpers
- [ ] Add integration coverage for new `/ops` provider observability blocks
- [ ] Add regression coverage for any new persisted probe artifact behavior
- [ ] Run targeted regression after Phase 2 and Phase 3
- [ ] Run targeted regression after Phase 4
- [ ] Run full `py -m pytest` after all implementation work

### Phase 6: Real Environment Validation

- [ ] If local real-provider config is available, run real non-sandbox probe validation
- [ ] If local real-provider config is not available, explicitly mark this phase blocked
- [ ] In either case, run rolling baseline again after the ops changes
- [ ] Verify no privacy boundary regression is introduced
- [ ] Verify `/ops` reflects the actual latest status after validation

### Phase 7: Documentation And Reuse Closure

- [ ] Update shared `docs/dev/02-todo.md`
- [ ] Update shared `docs/dev/04-build-log.md`
- [ ] Update shared `docs/dev/05-test-log.md`
- [ ] Update shared `docs/dev/06-issues-and-fixes.md`
- [ ] Update shared `docs/dev/07-playbook.md`
- [ ] Update shared `docs/dev/09-runbook.md`
- [ ] Write this round's plan/build-log/issues/validation/playbook/closeout docs
- [ ] Record all blocked items and environmental dependencies clearly
- [ ] Record reusable operator steps and future follow-ups

## Suggested Regression Cadence

1. Complete Phase 1 + Phase 2, then run targeted regression.
2. Complete Phase 3 + Phase 4, then run targeted regression.
3. Complete Phase 5 + Phase 6, then run full regression.
4. Complete Phase 7 only after validation data is final.

## Suggested Priority

1. Phase 0
2. Phase 1
3. Phase 2
4. Phase 3
5. Phase 5
6. Phase 6
7. Phase 4
8. Phase 7

## Why This Order

- Real provider readiness and smoke hardening are the highest-value next step.
- Provider observability should follow immediately, so operators can see what happened.
- Regression should happen before extra UX polish to reduce debugging surface.
- Baseline-history polish is valuable, but not as urgent as real-provider readiness.
- Documentation closes the loop after the implementation and validation data are final.
