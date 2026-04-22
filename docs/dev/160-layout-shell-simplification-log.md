# 160 Layout Shell Simplification Log

## Date
- 2026-04-21

## Goal
- Continue frontend polish by simplifying the shared page shell.
- Reduce repeated visual chrome that appeared on every page and made the product feel heavier than necessary.

## Changes
- Rewrote `app/web/view_helpers.py` into a clean, readable shared layout module.
- Kept all existing renderer exports and helper contracts intact.
- Simplified the global page shell:
  - removed the repeated top shortcut strip in the workspace rail
  - removed the repeated trust/release card band that appeared before page content
  - kept breadcrumb + one-line page note as the only shared top context layer
  - standardized the page-link strip label to `本页导航`
- Updated `app/web/static/styles.css` to match the leaner shell:
  - compacted the workspace rail
  - softened the page-link strip
  - reduced header visual weight
  - removed dependence on unused workspace shortcut/trust-grid behavior

## Why
- Page-level content had already been simplified, but the shared shell still repeated too much framing.
- The result was that every page felt like it had one extra layer before users could reach the real work area.
- This pass makes the application feel more direct and consistent.

## Validation
- `py -3 -m py_compile app\web\view_helpers.py app\web\page_home.py app\web\page_submission.py app\web\page_ops.py app\api\main.py`
- `py -3 -m pytest tests\unit\test_web_source_contracts.py tests\integration\test_web_mvp_contracts.py tests\integration\test_operator_console_and_exports.py`
- `Invoke-WebRequest http://127.0.0.1:18080/`

## Result
- Focused regression passed: `10/10`
- Frontend remained online at `http://127.0.0.1:18080/`
