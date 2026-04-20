# 中文运维台重构验证记录

## 日期

- 2026-04-20

## 语法检查

```powershell
py -m py_compile app\web\view_helpers.py app\web\page_home.py app\web\page_submission.py app\web\page_case.py app\web\page_report.py app\web\page_ops.py app\api\main.py
```

- 结果：通过

## 页面与契约回归

```powershell
py -m pytest tests\integration\test_web_mvp_contracts.py tests\integration\test_operator_console_and_exports.py tests\integration\test_manual_correction_api.py tests\e2e\test_browser_workflows.py tests\unit\test_web_source_contracts.py
```

- 结果：`14 passed`

## 本轮可确认结论

- 首页、批次页、项目页、报告页、运维页已统一为中文主界面。
- `/ops` 中的命令区和 `#trend-watch` 已重构为更清晰的管理台布局。
- 没有发现新的源码乱码标记。
- 当前改动不影响 Web 主链路、人工更正链路和浏览器级 E2E。
