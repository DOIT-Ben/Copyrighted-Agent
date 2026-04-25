# 199 Live Review Payload Hardening Log

Date: 2026-04-25

## Scope

- Ran a live upload/review smoke flow with an existing real soft-copyright sample package.
- Found that the external AI prompt only received basic case fields, so the AI could incorrectly infer that source code, documentation, or agreement materials were missing.
- Added a privacy-safe material inventory to the AI case payload.
- Fixed duplicated agreement counting in the AI prompt and review dimension payload.

## Changes

- AI-safe payload now includes:
  - `material_count`
  - `material_type_counts`
  - `material_inventory`
- The material inventory intentionally excludes original filenames and material text.
- Mode A pipeline now passes the actual case material list once, instead of appending agreement materials a second time.

## Live Validation

- Sample package: `data/runtime/submissions/sub_006fd5a371/2504_软著材料.zip`
- New validation submission: `sub_727d71988d`
- Result:
  - status: `completed`
  - materials: `4`
  - prompt `material_count`: `4`
  - prompt material type counts: `info_form:1`, `agreement:1`, `source_code:1`, `software_doc:1`
  - generated report no longer contains the misleading missing-material wording.

## Regression

- `py -m pytest tests.unit -q`
  - Result: `103 passed`
- `py -m pytest tests.integration -q`
  - Result: `41 passed`

