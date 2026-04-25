# 173 Prompt Snapshot Log

## Goal

Make the LLM review prompt explicit, persistent, and visible in the web UI so operators can understand what the system actually sent to the model for a given software copyright review case.

## Changes

- Added `app/core/reviewers/ai/prompt_builder.py`
  - Builds a readable prompt snapshot from:
    - desensitized case payload
    - rule engine findings
    - current review profile
    - per-dimension rulebook
  - Produces:
    - `system_prompt`
    - `user_prompt`
    - active dimension summary
    - review profile summary

- Updated `app/core/reviewers/ai/adapters.py`
  - External HTTP request payload now includes `prompt_snapshot`.
  - Normalized external result now returns the same snapshot for persistence/UI use.

- Updated `app/tools/minimax_bridge.py`
  - Bridge now prefers `prompt_snapshot.system_prompt` and `prompt_snapshot.user_prompt`.
  - Removed dependence on the old generic payload-dump prompt shape for runtime calls.

- Updated `app/core/reviewers/ai/service.py`
  - All provider paths now attach a prompt snapshot, including `mock` fallback paths.

- Updated persistence models
  - `app/core/domain/models.py`
  - `ReviewResult` now stores `prompt_snapshot_json`.

- Updated review result assembly
  - `app/core/pipelines/submission_pipeline.py`
  - `app/core/services/corrections.py`
  - Prompt snapshot is saved into review results during initial run and rerun.

- Added frontend prompt viewer
  - `app/web/prompt_views.py`
  - `app/web/page_case.py`
  - `app/web/page_report.py`
  - `app/web/static/styles.css`
  - New panel: `LLM 审查提示词`
  - Shows:
    - active dimensions
    - focus mode / strictness / custom instruction
    - per-dimension objective and LLM focus
    - collapsible full prompt text

## Result

Operators can now inspect the actual LLM review prompt used for each case/report directly in the UI, without downloading source files or guessing how rules were translated into instructions.

## Validation

- `D:\Soft\python310\python.exe -m py_compile app\core\reviewers\ai\prompt_builder.py app\core\reviewers\ai\adapters.py app\core\reviewers\ai\service.py app\core\domain\models.py app\core\services\corrections.py app\core\pipelines\submission_pipeline.py app\tools\minimax_bridge.py app\web\prompt_views.py app\web\page_case.py app\web\page_report.py`
- `D:\Soft\python310\python.exe -m pytest tests\unit\test_ai_prompt_builder_contracts.py tests\unit\test_external_http_adapter_contracts.py tests\integration\test_web_mvp_contracts.py -q`

## Notes

- This exposes prompt content for operator transparency, but does not expose secrets.
- Prompt content is based on already desensitized payloads and current per-submission rule configuration.
