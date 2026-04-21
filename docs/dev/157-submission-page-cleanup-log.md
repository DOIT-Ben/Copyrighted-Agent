# 157 Submission Page Cleanup Log

## Date
- 2026-04-21

## Goal
- Continue the frontend simplification pass.
- Split high-density submission content into clearer task pages.
- Remove the duplicated renderer overrides that had accumulated in `app/web/page_submission.py`.

## Changes
- Rewrote `app/web/page_submission.py` into a single clean implementation.
- Kept the submission overview page focused on:
  - 导入摘要
  - 待复核队列
  - 子页面导航
  - 更正审计
- Preserved dedicated child pages for:
  - `/submissions/{id}/materials`
  - `/submissions/{id}/operator`
  - `/submissions/{id}/exports`
- Preserved contract-critical strings on the overview page:
  - `人工干预台`
  - `导出中心`
  - `产物浏览`
  - `导入摘要`
- Tightened the export boundary in `app/web/pages.py` so it only exposes the canonical public renderers expected by tests.
- Updated `app/api/main.py` to import submission child-page renderers directly from `app.web.page_submission`.

## Why
- The previous file had multiple same-name renderer definitions appended at the end of the file.
- That made the frontend hard to reason about and risky to iterate on.
- The cleanup reduces maintenance cost and makes later UI refinement safer.

## Validation
- `py -3 -m py_compile app\web\page_submission.py app\web\pages.py app\api\main.py`
- `py -3 -m pytest tests\integration\test_operator_console_and_exports.py tests\integration\test_web_mvp_contracts.py`
- `py -3 -m pytest tests\unit\test_web_source_contracts.py`
- `py -3 -m pytest`
- `powershell -ExecutionPolicy Bypass -File scripts\restart_real_stack.ps1`

## Result
- Full regression passed: `136/136`
- Real stack restarted successfully.
- Active URLs:
  - Frontend: `http://127.0.0.1:18080/`
  - Ops: `http://127.0.0.1:18080/ops`
  - Bridge: `http://127.0.0.1:18011/review`
