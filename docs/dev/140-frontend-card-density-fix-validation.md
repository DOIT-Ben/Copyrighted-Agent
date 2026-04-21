# 前端卡片密度修正验证记录
## 日期

- 2026-04-21

## 语法检查

```powershell
C:\Users\DOIT\miniconda3\python.exe -m py_compile app\api\main.py app\web\page_ops.py
```

- 结果：通过

## 回归测试

```powershell
C:\Users\DOIT\miniconda3\python.exe -m pytest tests\integration\test_operator_console_and_exports.py tests\integration\test_web_mvp_contracts.py tests\unit\test_web_source_contracts.py
```

- 结果：`10 passed`

## 运行确认

- `http://127.0.0.1:8000` 已重启
- `http://127.0.0.1:8000/ops` 可访问
- 当前监听端口：
  - `8000`
  - `18011`

## 说明

- `show_stack_status.ps1` 显示 `MINIMAX_API_KEY present: False` 是因为它读取的是当前 shell 进程环境。
- 已运行中的 bridge 不受影响，当前端口 `18011` 仍处于监听状态。
