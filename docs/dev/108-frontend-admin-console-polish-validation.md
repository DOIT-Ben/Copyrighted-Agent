# Frontend Admin Console Polish Validation

## Date

- 2026-04-20

## Compile Validation

- Command:

```powershell
py -m py_compile app\web\view_helpers.py app\web\page_home.py app\web\page_submission.py app\web\page_case.py app\web\page_report.py app\web\page_ops.py app\web\pages.py app\api\main.py
```

- Result:
  - passed

## Regression Validation

- Command:

```powershell
py -m pytest tests\integration\test_web_mvp_contracts.py tests\integration\test_operator_console_and_exports.py tests\e2e\test_browser_workflows.py tests\unit\test_web_source_contracts.py
```

- Result:
  - `passed=131 failed=0 skipped=0`

## Coverage Confirmed In This Round

- 首页仍然保留关键契约：
  - `Control Center`
  - `Import Console`
  - `action="/upload"`
- Submission 页仍然保留关键契约：
  - `Import Digest`
  - `Operator Console`
  - `Export Center`
  - `Artifact Browser`
- Case 页仍然保留关键契约：
  - `Risk Queue`
  - `AI Supplement`
- Report 页仍然保留关键契约：
  - `Report Reader`
- Ops 页仍然保留关键契约：
  - `Support / Ops`
  - `Release Gate`
  - `Startup Self Check`
  - `Provider Readiness`
  - `Provider Checklist`
  - `Probe Observatory`
  - `Probe History`
  - `Trend Watch`
- 源码契约仍然通过：
  - 未引入已知 mojibake marker
  - 页面 barrel export 未被破坏

## Runtime Note

- 当前 `config/local.json` 默认仍为：
  - host=`127.0.0.1`
  - port=`8000`
  - provider=`mock`
- 因此直接执行：

```powershell
py -m app.api.main
```

会启动本地 mock 版后台界面。

- 如果要单独拉起一个不影响默认实例的测试端口，可使用：

```powershell
$env:SOFT_REVIEW_PORT='18080'
py -m app.api.main
```

- 本轮已额外确认 `http://127.0.0.1:18080/` 与 `http://127.0.0.1:18080/ops` 可访问。

## Conclusion

- 这轮前端美化不是“只改样式”，而是在保持页面契约和回归通过的前提下，完成了后台分析台语义对齐。
