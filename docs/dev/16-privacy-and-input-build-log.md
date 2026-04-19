# Privacy And Input Round Build Log

## Date

- 2026-04-19

## Step 1

- Audited the current MVP pipeline, existing parse artifacts, and UI delivery path.
- Confirmed that a basic desensitized text output already existed, but it was not isolated enough as a privacy subsystem and was not surfaced to the user.
- Confirmed that Mode B did not yet support directory intake.

## Step 2

- Added a dedicated privacy module at `app/core/privacy/desensitization.py`.
- Implemented deterministic local redaction rules for labeled fields, contact data, identity-like values, organization identifiers, URLs, and explicit extracted values.
- Added an AI-safe case payload builder for future non-mock providers.

## Step 3

- Integrated privacy output into parsing.
- Added structured privacy summaries to parse metadata.
- Persisted `desensitized.txt` and `privacy.json` alongside `raw.txt` and `clean.txt`.
- Switched `Material.content` to the desensitized text so API defaults are safer.

## Step 4

- Added directory intake support for Mode B through `app/core/services/input_intake.py`.
- Unified submission ingestion so the same pipeline can accept:
  - a zip file
  - a directory of files
- Added ignore rules for noisy archive members such as `__MACOSX`, `.DS_Store`, and `._*`.

## Step 5

- Improved classification resilience by rewriting `app/core/services/material_classifier.py` with clean keyword rules and content fallbacks.
- Added a second classification pass after parsing for low-confidence or unknown materials.

## Step 6

- Updated the web experience to make privacy processing visible:
  - upload form privacy notice
  - submission detail privacy audit panel
  - report page privacy pill

## Step 7

- Added local validation runner:
  - `py -m app.tools.input_runner --path <path> --mode <mode>`
- This supports:
  - Mode A directories that contain multiple zip packages
  - single zip inputs
  - Mode B directories of same-type materials

## Step 8

- Added regression tests for:
  - local desensitization behavior
  - directory intake for Mode B
  - privacy manifest persistence
  - macOS archive noise filtering
