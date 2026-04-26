# 233 Rule Template And Report Evidence Polish Log

## Date
- 2026-04-26

## Goal
- Refine review-rule templates so each dimension carries business-readable guidance.
- Improve the report page so operators can see what failed, which rule matched, where the evidence came from, and where to go fix it.

## Scope
- `app/core/services/review_rulebook.py`
- `app/core/reviewers/ai/prompt_builder.py`
- `app/core/services/review_profile.py`
- `app/core/services/corrections.py`
- `app/api/main.py`
- `app/web/page_review_rule.py`
- `app/web/page_report.py`
- `tests/unit/test_ai_prompt_builder_contracts.py`
- `tests/integration/test_web_mvp_contracts.py`

## Changes
- Added per-dimension guidance metadata to the rulebook:
  - `evidence_targets`
  - `common_failures`
  - `operator_notes`
- Normalized the new metadata from both list and multiline textarea input.
- Exposed the new metadata in the rule-detail editor and default comparison page.
- Persisted the new fields through the review-rule save flow.
- Extended the AI prompt snapshot so the LLM sees:
  - evidence targets
  - common failure patterns
  - operator notes
- Upgraded report explainability:
  - issue cards now show source material labels
  - issue snapshot cards now show where to inspect
  - issue explainer cards now show rule focus plus direct fix actions
  - issue trace table now includes evidence hints and quick actions
  - dimension evidence cards now surface target materials and common failure patterns
- Added contract coverage for the new metadata and updated report-page expectations.

## Testing
- `py -m py_compile app\web\page_report.py app\web\page_review_rule.py app\core\services\review_rulebook.py app\core\reviewers\ai\prompt_builder.py app\core\services\corrections.py app\api\main.py app\core\services\review_profile.py`
- `py -m pytest tests\integration\test_web_mvp_contracts.py tests\unit\test_ai_prompt_builder_contracts.py -q`
- `py -m pytest tests\unit\test_ai_prompt_builder_contracts.py tests\unit\test_report_contracts.py tests\integration\test_web_mvp_contracts.py tests\e2e\test_browser_workflows.py -q`

## Result
- Rule templates are now more explicit and operator-friendly.
- Report output is more actionable without expanding the page into another dense dashboard.
- Regression stayed green across unit, integration, and browser workflow coverage.

## Notes
- `page_report.py` required extra care because of mixed historical encoding in surrounding content. The final file was revalidated with `py_compile` and downstream tests.
