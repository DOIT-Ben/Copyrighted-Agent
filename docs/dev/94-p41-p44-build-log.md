# P41-P44 Build Log

## Date

- 2026-04-20

## Work Completed

- Audited the local provider configuration before doing more work.
- Confirmed `config/local.json` still points to mock mode and no `SOFT_REVIEW_*` environment variables are present.
- Added `app/web/README.md` with:
  - page-layer module map
  - thin-barrel rule for `pages.py`
  - Windows-safe UTF-8 verification guidance
  - targeted regression commands
  - visual smoke checklist
- Added `tests/unit/test_web_source_contracts.py` for:
  - `app.web.pages` export stability
  - contributor-guide presence
  - active-source mojibake marker detection
- Refined the mojibake detection test to build suspicious marker variants at runtime from canonical localized terms, which keeps the test source itself safer on Windows.
- Re-ran targeted regression and full regression after the new guardrails landed.

## Files Added

- `app/web/README.md`
- `tests/unit/test_web_source_contracts.py`

## Outcome

- Real-provider onboarding remains blocked by environment state, but the web layer is safer to maintain and easier for future contributors to extend without repeating the earlier encoding incident.
