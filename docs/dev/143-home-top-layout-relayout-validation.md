# 首页顶部布局重排验证记录

## 日期

- 2026-04-21

## 验证项

- Python 编译检查
- 首页/操作台/源码契约回归测试
- 首页顶部结构残留自检

## 执行命令

```powershell
py -m py_compile D:\Code\软著智能体\app\web\page_home.py D:\Code\软著智能体\app\api\main.py
py -m pytest tests\integration\test_web_mvp_contracts.py tests\integration\test_operator_console_and_exports.py tests\unit\test_web_source_contracts.py
```

## 结果

- `py_compile` 通过
- `pytest` 通过，汇总如下：

```text
passed=10 failed=0 skipped=0 xfailed=0
```

## 说明

- 首轮回归时有一个契约断言失败，原因是首页入口说明文案从“浏览器端导入说明”改成了别的标题。
- 已恢复该文案锚点后重跑测试，全部通过。

## 当前结论

- 本轮属于首页顶部信息架构重排，不是单纯 CSS 微调。
- 代码层面与页面契约层面均已通过当前回归范围验证。
