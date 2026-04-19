# P17-P22 Issues And Fixes

## Issue 1

- Symptom: provider readiness was initially treated as warning under default `mock + ai_enabled=false`, which would have made the ops dashboard look unhealthy even in valid local mode.
- Root cause: readiness logic treated `ai_enabled=false` as universally suspicious instead of distinguishing local/mock mode from external provider mode.
- Fix: provider readiness now marks disabled AI as `ok` for local/mock mode and only warns when `external_http` is configured but inactive.

## Issue 2

- Symptom: many real legacy `.doc` inputs were marked `low_quality` even though the extracted text was already readable.
- Root cause: Word control separators leaked into extracted text and depressed quality scoring.
- Fix: added control-character stripping before cleanup and quality scoring, then added regression coverage for cleaned structured text.

## Issue 3

- Symptom: one real legacy info form still stayed in manual review after control-character cleanup.
- Root cause: the legacy OLE quality heuristic was still too strict for structured form text with many labels and separators.
- Fix: added a structured-legacy-text path in parse quality so low-garble, sufficiently long, field-heavy forms can be treated as usable.

## Issue 4

- Symptom: PDF agreements and software docs were classified as low-signal noise even though the original PDF clearly contained readable Chinese text.
- Root cause: the previous PDF parser only scraped raw parentheses strings and ignored compressed content streams plus `ToUnicode` CMaps.
- Fix: implemented lightweight stream decompression plus `ToUnicode` decoding in `app/core/parsers/pdf_parser.py`, with a synthetic regression test.

## Issue 5

- Symptom: sandbox probe failed when trying to bind to port `8010` on the local Windows environment.
- Root cause: the port was not available in the current environment.
- Fix: reran the live CLI probe on port `18010` and documented that the probe is fully configurable and should not depend on a fixed port.

## Outcome

- All issues above were fixed inside this round.
- No failing automated tests remained after the fixes.
