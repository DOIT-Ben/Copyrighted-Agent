# 243 Report Submission Jobs Hierarchy Log

- Date: 2026-05-09
- Goal: continue the Jobs-style frontend tightening by improving the report and submission detail hierarchy without changing business behavior.

## Changes

- Updated [page_report.py](D:/Code/软著智能体/app/web/page_report.py):
  - added `report-metrics-strip` to the report metrics area
  - added `report-shell-grid` to the report body layout
- Updated [page_submission.py](D:/Code/软著智能体/app/web/page_submission.py):
  - added `submission-metrics-strip` to the submission status metrics
  - added `submission-detail-grid` to the submission detail layout
- Extended [styles.css](D:/Code/软著智能体/app/web/static/styles.css):
  - compresses report and submission metrics into calmer thin tiles
  - makes the review workflow panel the primary task region
  - makes import digest, pending review, and detail groups quieter
  - improves mobile collapse so panels stack before text gets squeezed

## Validation

- Focused frontend regression:
  - `py -m pytest tests\\integration\\test_web_mvp_contracts.py tests\\e2e\\test_browser_workflows.py tests\\unit\\test_web_source_contracts.py -q`
  - result: `17 passed`

## Notes

- This pass intentionally avoids changing review logic, routing, or persistence.
- Some legacy template text still contains historical encoding noise, so this round uses stable structural classes plus CSS constraints instead of broad template rewrites.
