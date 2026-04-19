# Next Round Execution Todo

## Date

- 2026-04-20

## Execution Slice

- [x] Inspect the rebuilt `app/web/pages.py` and identify safe module boundaries
- [x] Extract shared rendering helpers into a reusable module
- [x] Extract page-scoped renderers for home, submission, case, report, and ops
- [x] Keep FastAPI imports stable by converting `app/web/pages.py` into a thin export layer
- [x] Re-run compile validation for the new module structure
- [x] Re-run page-focused and browser E2E regression
- [x] Re-run final full regression
- [x] Record the structure change and reusable lessons under `docs/dev`

## Follow-Up Todo

- [ ] Add a short renderer map for future contributors
- [ ] Decide whether to continue to smaller component-level extraction
- [ ] Resume real-provider onboarding once credentials exist locally
