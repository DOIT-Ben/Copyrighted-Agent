# app/web Contributor Guide

## Purpose

`app/web/` contains the HTML renderer layer for the admin-style analysis console.
The goal is to keep page responsibilities clear, keep FastAPI imports stable, and reduce the risk of another large Windows encoding regression during UI edits.

## Module Map

- `view_helpers.py`
  Shared layout, cards, tables, pills, nav links, labels, and stylesheet loading.
- `page_home.py`
  Home dashboard and ZIP intake console.
- `page_submission.py`
  Submission index, submission detail, material matrix, exports, and operator actions.
- `page_case.py`
  Case risk queue, AI supplement, and report entry.
- `page_report.py`
  Report reader page.
- `page_ops.py`
  Support and operations console.
- `pages.py`
  Thin export barrel used by `app.api.main`. Keep this file small and stable.
- `static/styles.css`
  Admin UI stylesheet.

## Safe Editing Rules

1. Use `apply_patch` for source edits instead of full-file shell rewrites.
2. Do not use `Get-Content` plus `Set-Content` to rewrite Python page files unless UTF-8 encoding is controlled end to end.
3. Keep `pages.py` as an import barrel. Put real page logic in page-scoped modules.
4. Reuse `view_helpers.py` before introducing another one-off HTML helper.
5. Preserve the current product shape: this UI is an admin analysis system, not a landing page.

## Windows Encoding Guardrail

PowerShell text preview can make valid UTF-8 Chinese strings look corrupted even when the source file is still correct.
Before editing a file because it "looks garbled", verify the real source text with Python:

```powershell
@'
from pathlib import Path
path = Path(r"app\web\page_home.py")
for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
    if any(ord(ch) > 127 for ch in line):
        print(f"{idx}: {line.encode('unicode_escape').decode('ascii')}")
'@ | py -
```

If the output shows normal `\uXXXX` Chinese text, the file is fine and the terminal preview is the problem.

## Change Workflow

1. Edit the page-scoped module or `view_helpers.py`.
2. Keep `pages.py` exports unchanged unless a route contract intentionally changes.
3. Run targeted regression:
   `py -m pytest tests\unit\test_web_source_contracts.py tests\integration\test_web_mvp_contracts.py tests\integration\test_operator_console_and_exports.py tests\e2e\test_browser_workflows.py`
4. Run full regression:
   `py -m pytest`
5. Record the change and any issue in `docs/dev`.

## Visual Smoke Checklist

- Home page keeps the admin dashboard structure.
- Sidebar, KPI cards, tables, and operator panels still render.
- `/static/styles.css` is served as `text/css`.
- The page does not degrade into raw text or a single oversized clickable block.
- Submission detail still exposes material matrix, exports, and correction actions.
- `/ops` still exposes provider readiness, release gate, and probe history.
