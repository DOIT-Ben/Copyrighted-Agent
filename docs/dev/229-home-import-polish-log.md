# 229 Home Import Polish Log

Date: 2026-04-26

## Goal

- Make the home page feel like a clean entry page instead of a dense dashboard.
- Keep import contracts unchanged while reducing visual noise around rule editing.

## Changes

- Updated `app/web/page_home.py`.
  - Rebuilt the import area into a clearer two-column layout.
  - Kept the upload path on the left and a concise `结果去向` guide on the right.
  - Reduced helper copy to one short explanation plus three compact cues.
  - Preserved existing upload controls, async progress attributes, and tested rule-edit fields.
- Updated `app/web/review_profile_widgets.py`.
  - Wrapped review controls in a single fold titled `调整本次审查要求`.
  - Kept `导入前编辑规则` available for every dimension.
  - Added a lightweight enabled-rule count in each inline rule editor summary.
- Updated `app/web/static/styles.css`.
  - Widened the left import column to reduce crowding at 100% browser zoom.
  - Simplified the rule-editor presentation into nested cards with lighter summaries.
  - Added compact route cards for the right-hand destination guide.

## Regression

- `py -m pytest tests\integration\test_web_mvp_contracts.py -q`

## Result

- The home page now behaves like a focused upload entry.
- Rule editing is still available before import, but it no longer dominates the first screen.
