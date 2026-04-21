# 响应式密度优化验证记录

## 日期

- 2026-04-21

## 验证范围

- 批次详情布局重排
- 项目详情布局重排
- 报告页布局重排
- 全局断点与表格响应式调整

## 执行命令

```powershell
py -m py_compile D:\Code\软著智能体\app\web\page_submission.py D:\Code\软著智能体\app\web\page_case.py D:\Code\软著智能体\app\web\page_report.py D:\Code\软著智能体\app\api\main.py
py -m pytest tests\integration\test_web_mvp_contracts.py tests\integration\test_operator_console_and_exports.py tests\unit\test_web_source_contracts.py
```

## 结果

- `py_compile` 通过
- `pytest` 通过

```text
passed=10 failed=0 skipped=0 xfailed=0
```

## 备注

- 首次编译检查时误将 `styles.css` 作为 Python 文件传入 `py_compile`，已修正命令后重新执行并通过。
- 当前回归范围覆盖首页、批次详情、操作台、源码契约；未包含视觉截图型自动化检查。
