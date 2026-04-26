# 231 Report Advanced Info Polish Log

Date: 2026-04-26

## Goal

- Keep the report page friendly for business users first.
- Push evidence-chain and rule-trace detail below a single advanced section without losing transparency.

## Changes

- Updated `app/web/page_report.py`.
  - Kept the main visible sequence focused on:
    - `审查结果`
    - `先改这些地方`
    - `问题一眼看懂`
    - `重点问题说明`
    - `发现了什么不足`
  - Moved `问题级别归类`, `按材料来源看问题`, `怎么判定出来的`, `用了哪些审查规则`, `审查维度`, `发现的问题`, and `审查材料` into `更多信息`.
  - Kept `审查配置`, `LLM 审查提示词`, and `原始 Markdown` in the same advanced stack.
  - Reduced page-link navigation to the sections that matter most on first read.

## Regression

- `py -m pytest tests\integration\test_web_mvp_contracts.py tests\integration\test_operator_console_and_exports.py tests\unit\test_web_source_contracts.py -q`

## Result

- The report now shows a friendlier business-facing story on first load.
- Full rule traceability and raw output are still present, but clearly secondary.
