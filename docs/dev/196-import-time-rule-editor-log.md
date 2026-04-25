# 196 Import-Time Rule Editor Log

Time: 2026-04-25 15:14 +08:00

## Goal

Move review rule editing before upload, so users can adjust dimension rules while importing a software-copyright package.

## Changes

- Added inline rule editors under every review dimension on the import/review profile form.
- Each dimension can now edit:
  - rule title
  - review objective
  - checkpoints
  - LLM focus
- Extended `parse_review_profile_form()` so `rule_<dimension>_*` fields are saved into the submission `review_profile.dimension_rulebook`.
- Kept post-import rule pages available for later edits and reruns.

## Verification

- `py -m pytest tests.integration.test_web_mvp_contracts tests.unit.test_web_source_contracts -q` -> 10 passed.
- `py -m pytest tests.unit.test_ai_prompt_builder_contracts tests.unit.test_external_http_adapter_contracts -q` -> 8 passed.
- `py -m pytest tests.unit -q` -> 101 passed.
- `py -m pytest tests.integration -q` -> 41 passed.

## Notes

- The homepage now exposes `导入前编辑规则` under each review dimension.
- A new integration test verifies that import-time source-code rule edits persist into the created submission.
