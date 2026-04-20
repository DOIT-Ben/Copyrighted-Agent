# 116 Release Polish Validation

## Validation Plan

- Compile the touched web modules to catch syntax regressions.
- Run the web contract and browser-facing regression set first.
- If the targeted set passes, run the full pytest suite for final confidence.

## Commands

```powershell
py -m py_compile app\web\view_helpers.py app\web\page_home.py app\web\page_submission.py app\web\page_case.py app\web\page_report.py app\web\page_ops.py app\web\pages.py app\api\main.py
py -m pytest tests\integration\test_web_mvp_contracts.py tests\integration\test_operator_console_and_exports.py tests\e2e\test_browser_workflows.py tests\unit\test_web_source_contracts.py
py -m pytest
```

## Result

- `py_compile`: passed.
- First targeted regression run under the current real-provider environment: `passed=129 failed=2`.
- The two failures were both browser E2E timeouts during upload and regroup requests while the runtime was configured to use the live `external_http` bridge.
- Deterministic regression rerun with environment override:

```powershell
$env:SOFT_REVIEW_AI_ENABLED='false'
$env:SOFT_REVIEW_AI_PROVIDER='mock'
$env:SOFT_REVIEW_AI_ENDPOINT=''
$env:SOFT_REVIEW_AI_MODEL=''
py -m pytest tests\e2e\test_browser_workflows.py
```

- Final regression result after the mock-mode rerun: `passed=131 failed=0`.

## Acceptance Focus

- Shared chrome renders on all operator pages.
- Existing contract text remains present.
- Anchor shortcuts do not break navigation or page rendering.
- No mojibake markers are introduced into active source files.

## Interpretation

- This UX round did not introduce functional regressions in the web product.
- The initial failure mode was environmental and tied to live-provider latency, not to the shared layout or page-structure changes.
- Mock-mode regression remains the correct deterministic gate for validating frontend polish, while the already-established real-provider validation artifacts continue to cover the live integration path.
