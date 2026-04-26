# 217 Report Layout Stability Pass Log

- Date: 2026-04-26
- Scope: final report page stability pass for desktop 100 percent zoom and dense review content

## Changes

- Scoped layout tweaks to the report page instead of changing global card behavior.
- Widened report toolbar actions so export buttons do not get squeezed.
- Increased report section spacing slightly to improve scan rhythm.
- Switched report tables into a fixed-layout reading mode with stronger wrapping.
- Marked the old report toolbar helper as legacy to avoid future confusion from duplicate definitions.

## Why

- The report page now carries more explanation blocks, rule traces, and evidence rows than earlier iterations.
- At desktop 100 percent zoom, the risk is not missing content but having long cells and action buttons compress the layout.
- This pass keeps the page compact while preventing the report-specific areas from collapsing or stretching unevenly.

## Validation

- `py -m py_compile app\\web\\page_report.py app\\web\\view_helpers.py`
- `py -m pytest tests\\integration\\test_web_mvp_contracts.py tests\\integration\\test_operator_console_and_exports.py -q`
