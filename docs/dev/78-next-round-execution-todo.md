# Next Round Execution Todo

## Date

- 2026-04-20

## Approved Execution Slice

- [x] Verify the new provider-probe history, release-gate, and `/ops` code compiles cleanly
- [x] Run targeted regression around provider probe, release gate, startup self-check, and `/ops`
- [x] Fix any failing contracts before touching the broader runtime
- [x] Add a safe default `config/local.json`
- [x] Re-run `provider_probe` and `release_gate` against the local config
- [x] Run full regression and keep the workspace green
- [x] Record implementation details, validation output, issues, and reusable lessons under `docs/dev`

## Unexpected Recovery Work Added During Execution

- [x] Back up the encoding-corrupted `app/web/pages.py`
- [x] Rebuild the page module from route contracts and regression expectations
- [x] Re-run browser E2E and manual-correction HTML flows after the page-module rebuild

## Follow-Up Todo

- [ ] Configure a real `external_http` endpoint and credential mapping in `config/local.json`
- [ ] Run a real non-sandbox provider smoke
- [ ] Decide whether to modularize `app/web/pages.py` into smaller renderer modules or templates
