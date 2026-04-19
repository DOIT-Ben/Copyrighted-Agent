# Next Granular Todo Round 6

## Date

- 2026-04-19

## Completed This Round

- [x] Added baseline history service support
- [x] Added rolling baseline archive support
- [x] Added `/ops` trend-watch and provider-checklist modules
- [x] Added regression coverage for the new ops view
- [x] Generated a new rolling baseline archive under `docs/dev/history`

## Next Recommended Slice

- [ ] Create `config/local.json` with a real provider endpoint, model, and local key-env mapping
- [ ] Run a real non-sandbox provider smoke with desensitized payload only
- [ ] Capture provider result observability in logs and `/ops`
- [ ] Add archive download/filter controls for baseline history
- [ ] Decide whether rolling baseline capture should be nightly, pre-release, or manual-only
