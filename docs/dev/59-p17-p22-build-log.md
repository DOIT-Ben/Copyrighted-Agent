# P17-P22 Build Log

## Date

- 2026-04-19

## Summary

- Added a reusable provider readiness service and CLI probe tool so real provider onboarding is no longer coupled to the web page.
- Upgraded `/ops` from a command list into an operator dashboard with visible status for provider readiness, latest backup, and latest baseline.
- Reduced real-sample parser friction by normalizing control characters in legacy `.doc` extraction, promoting structured low-noise legacy forms, and decoding PDF `ToUnicode` streams.
- Re-ran real baselines and full regression after each major slice instead of waiting until the end.

## Change Log

### Provider Readiness

- Added `app/core/services/provider_probe.py`.
- Added `app/tools/provider_probe.py`.
- Updated `app/core/services/startup_checks.py` to reuse provider readiness evaluation.
- Updated `config/local.example.json` with sandbox and environment override examples.
- Added unit and integration coverage for readiness and live sandbox probe.

### Ops Visibility

- Added `app/core/services/ops_status.py`.
- Updated `app/web/pages.py` to show provider readiness, latest backup, and latest baseline cards.
- Updated `app/web/static/styles.css` to support a denser admin status layout.
- Expanded `/ops` command blocks to include provider probe and baseline compare commands.

### Parser Hardening

- Added `strip_control_chars(...)` and normalized extraction flow before quality scoring.
- Updated `app/core/parsers/doc_binary.py` so decoded candidates and readable lines no longer carry Word control separators into quality scoring.
- Updated `app/core/parsers/quality.py` so structured legacy forms with low garble and enough content are treated as usable instead of false low-quality.
- Reworked `app/core/parsers/pdf_parser.py` to decode compressed PDF streams and `ToUnicode` maps without external libraries.
- Added focused regression tests for PDF `ToUnicode`, text cleanup, and improved legacy quality decisions.

## Result

- Mode A real sample aggregate moved from `needs_review=10 / low_quality=10` to `0 / 0`.
- Mode B real sample aggregate moved from `needs_review=2 / low_quality=2` to `0 / 0`.
- Provider sandbox probe now succeeds through the CLI flow.
- Full regression ended at `110 passed, 0 failed`.
