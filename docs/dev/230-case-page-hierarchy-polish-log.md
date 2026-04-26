# 230 Case Page Hierarchy Polish Log

Date: 2026-04-26

## Goal

- Reduce first-screen density on the case page.
- Put result reading and report entry ahead of AI, prompt, and configuration details.

## Changes

- Updated `app/web/page_case.py`.
  - Moved `报告查看` into the first row beside `审查结果`.
  - Kept `风险队列` and `审查维度` on the main canvas.
  - Moved `AI 辅助研判` and `在线填报` into `更多信息`.
  - Expanded the advanced fold stack to hold AI, online filing, dimension detail, config, material matrix, and prompt snapshot.

## Regression

- `py -m pytest tests\integration\test_web_mvp_contracts.py tests\integration\test_operator_console_and_exports.py tests\unit\test_web_source_contracts.py -q`

## Result

- The case page now reads as: current result, current risks, then report entry.
- Operational and model-debug details are still available, but no longer compete with the main outcome.
