# Next Round Execution Todo

## Date

- 2026-04-20

## Execution Slice

- [x] Turn the final real-provider validation path into one repeatable command
- [x] Add a release-validation service that orchestrates probe, gate, sample smokes, and artifact writing
- [x] Add a release-validation CLI for operators and local verification
- [x] Add automated tests for blocked-state and sandbox-success validation flows
- [x] Run the new validation command against the current local config
- [x] Re-run full regression
- [x] Record the current blocked state, pass criteria, and next exact inputs needed

## Follow-Up Todo

- [ ] Fill real provider config and env vars locally
- [ ] Re-run the new release-validation command until it passes
- [ ] If the first real run fails, repair contract / auth / timeout mismatches and rerun
