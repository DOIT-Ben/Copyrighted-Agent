# Next Round Execution Todo

## Date

- 2026-04-20

## Execution Slice

- [x] Audit `config/local.json` and local `SOFT_REVIEW_*` environment variables before resuming work
- [x] Decide whether real-provider smoke is actionable or still blocked
- [x] Add a lightweight contributor map for `app/web`
- [x] Document Windows-safe UTF-8 verification for active page source
- [x] Add automated contracts for the `app.web.pages` export barrel and mojibake guardrails
- [x] Re-run targeted web regression
- [x] Re-run final full regression
- [x] Record the round in shared logs and round-specific docs under `docs/dev`

## Follow-Up Todo

- [ ] Wire real provider config into `config/local.json`
- [ ] Export `SOFT_REVIEW_*` credentials locally and run the first non-mock probe
- [ ] Decide whether the next UI-maintenance round should extract repeated submission action forms into smaller blocks
