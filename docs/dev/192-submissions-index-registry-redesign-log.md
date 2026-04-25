# 192 Submissions Index Registry Redesign Log

## Context

The batch overview page used a wide nine-column table. Long ZIP filenames consumed too much horizontal space and made the surrounding layout feel unbalanced.

## Changes

- Rebuilt the batch registry row structure from 9 columns to 6 columns.
- Moved import mode and review strategy under the filename as compact metadata chips.
- Clamped long ZIP filenames to two lines with full filename preserved in the link title.
- Merged material, case, and report counts into one compact count group.
- Added a dedicated detail action column.
- Expanded the batch registry panel to full width.
- Moved status distribution below the registry as a full-width secondary panel.
- Removed the redundant "view method" explanation panel from the overview page.
- Added dedicated CSS for `.panel-batch-registry`, `.batch-file-cell`, `.batch-file-name`, `.batch-meta-row`, and `.batch-counts`.

## Verification

Passed:

- `D:\Soft\python310\python.exe -m py_compile app\web\page_submission.py app\web\view_helpers.py app\web\page_home.py app\web\page_case.py app\web\page_report.py app\web\page_ops.py app\web\page_review_rule.py app\web\review_profile_widgets.py app\web\prompt_views.py`
- `D:\Soft\python310\python.exe -m pytest tests\integration\test_web_mvp_contracts.py -q`

Result: `6 passed`.
