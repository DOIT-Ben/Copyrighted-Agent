# 234 Fix Entry And Material Fix Plan Log

## Date
- 2026-04-26

## Goal
- Make the review result easier to act on after the evidence-chain upgrade.
- Reduce the gap between "I see the problem" and "I know where to fix it".

## Scope
- `app/web/page_report.py`
- `app/web/page_case.py`
- `tests/integration/test_web_mvp_contracts.py`

## Changes
- Added a new report panel: `按材料怎么改`
  - groups issues by source material
  - keeps the top actionable fixes per material
  - exposes direct actions to inspect materials and adjust rules
- Added a compact `修复入口` card on the case page
  - shows the top few current issues
  - links operators directly into materials, rule editing, and the report
- Kept the existing simplified page hierarchy intact instead of adding another heavy dashboard section.

## Testing
- `py -m py_compile app\web\page_report.py app\web\page_case.py`
- `py -m pytest tests\integration\test_web_mvp_contracts.py tests\e2e\test_browser_workflows.py -q`

## Result
- Operators now have one clear entry on the case page and one material-oriented execution list on the report page.
- The result flow is more task-oriented without increasing overall page noise.
