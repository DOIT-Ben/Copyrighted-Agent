# 214 Report Export And Provider Validation Log

- Date: 2026-04-26
- Scope: delivery-grade report export and live provider validation

## Export Changes

- Added structured report JSON download for case/material/submission reports.
- Kept markdown download.
- Clarified PDF behavior in the report toolbar as `打印 / 另存 PDF` to match the browser-print flow.

## Validation Changes

- Planned a live `external_http -> minimax_bridge -> MiniMax` probe using a synthetic llm-safe payload.
- Validation artifacts are intended to remain under runtime ops output, while this log stays in `docs/dev`.

## Why

- Markdown alone is not enough for downstream operators and secondary processing.
- JSON export gives us a stable structured handoff artifact for audit, automation, and future PDF/report pipelines.
- Live provider validation closes the gap between mocked review flow and real model readiness.
