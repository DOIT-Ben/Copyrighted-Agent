# 235 Evidence Location Hints Log

## Date
- 2026-04-26

## Goal
- Improve result explainability from file-level hints to field-level and section-level hints where possible.
- Keep the UI structure stable and avoid another large report-page expansion.

## Scope
- `app/web/page_report.py`
- `tests/integration/test_web_mvp_contracts.py`

## Changes
- Added rule-key-based precision hints for common audit issues.
- Precision hints now point operators toward likely fix locations such as:
  - information form name/version/applicant fields
  - document runtime-environment and install sections
  - agreement signing date, party order, approval sheet, signature page
  - source-code header, page range, sensitive values, and entry logic
  - online filing category, subject type, address, and date fields
- Wired the hints into the report evidence chain:
  - issue cards now include `定位：...`
  - issue trace rows now include a precise location hint before broader recheck guidance

## Testing
- `py -m py_compile app\web\page_report.py`
- `py -m pytest tests\integration\test_web_mvp_contracts.py tests\e2e\test_browser_workflows.py -q`

## Result
- The report now tells the operator not only which material is involved, but also which part of that material should be checked first.
- This closes part of the gap before true page/section anchors are added at the parser or reviewer payload layer.
