# 218 Page Hierarchy Reduction Pass Log

- Date: 2026-04-26
- Scope: reduce first-screen density on submission detail and ops pages without removing capability

## Changes

- Submission detail page:
  - kept only import summary, workflow, and priority queue on the first screen
  - moved review configuration and correction audit into a collapsed `更多信息` section
  - reduced summary-tile count so the top block reads faster
- Ops page:
  - merged `发布闸门` and `模型通道就绪度` into one `放行判断` panel
  - kept command entry and observability, but preserved them as expandable groups
  - kept all existing key strings and routes so current tests and user flows remain stable

## Why

- The pages were already functionally complete, but the first screen still asked users to read too many peer sections at once.
- This pass keeps the same data and actions while making the decision path clearer:
  - submission detail: first understand the batch, then enter a sub-page
  - ops: first decide whether the stack is ready, then inspect commands and observability

## Validation

- `py -m py_compile app\\web\\page_submission.py app\\web\\page_ops.py`
- `py -m pytest tests\\integration\\test_operator_console_and_exports.py tests\\integration\\test_web_mvp_contracts.py tests\\integration\\test_manual_correction_api.py -q`
