# 151 Ops Noise Reduction Validation

- Date: 2026-04-21
- Validation scope: `ops` 页面结构、契约测试、运行实例验证

## Static Validation

- `py -m py_compile D:\Code\软著智能体\app\web\page_ops.py D:\Code\软著智能体\app\web\view_helpers.py D:\Code\软著智能体\app\api\main.py`
- Result: pass

## Regression Tests

- `py -m pytest tests\integration\test_web_mvp_contracts.py tests\integration\test_operator_console_and_exports.py tests\unit\test_web_source_contracts.py`
- Result: `passed=10 failed=0`

## Runtime Verification

- Bridge status:
  - `http://127.0.0.1:18011/review`
  - listening
- Existing managed web on 8000:
  - still returns old `ops` HTML structure
  - reason: old managed Python process holds pre-change module state
- Verified current repo build on 18080:
  - `http://127.0.0.1:18080/ops`
  - confirmed markers present in HTML:
    - `signal-ribbon`
    - `ops-workbench`
    - `probe-observatory-note`
    - `补齐缺失项`
    - `最新备份：`

## Outcome

- 新版 `ops` 页面已经通过代码级与运行级验证。
- 若需要让 8000 端口也切到新版页面，需要处理当前外部受管旧进程的接管关系。
