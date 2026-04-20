# 中文运维台重构构建日志

## 日期

- 2026-04-20

## 本轮目标

- 把 Web 管理台从中英混杂状态统一为中文界面。
- 重点重构 `/ops`，尤其是 `#trend-watch` 的信息层级和可读性。
- 保持后端业务逻辑不变，只调整页面表达、交互文案和样式结构。

## 本轮完成

- 重写以下页面的可见文案与管理台表达：
  - `app/web/page_home.py`
  - `app/web/page_submission.py`
  - `app/web/page_case.py`
  - `app/web/page_report.py`
  - `app/web/page_ops.py`
- 统一共享标签与导入模式文案：
  - `app/web/view_helpers.py`
- 增补运维页样式：
  - 命令分组卡片
  - 趋势观察提示区
  - 趋势摘要卡
  - 中文内容更适合的排版密度
- 同步把 HTML 通知提示改为中文：
  - `app/api/main.py`
- 同步更新页面契约测试：
  - `tests/integration/test_web_mvp_contracts.py`
  - `tests/integration/test_operator_console_and_exports.py`
  - `tests/integration/test_manual_correction_api.py`
  - `tests/e2e/test_browser_workflows.py`

## 设计取舍

- 没有继续堆更多炫技视觉，而是优先把中文管理系统最需要的三件事做好：
  - 层级清楚
  - 一屏能扫完重点
  - 关键动作有明确分组
- `/ops` 命令区从“同层级大平铺”改为三组：
  - 环境启动
  - 校验与联调
  - 回溯与维护
- `#trend-watch` 从单纯表格改为：
  - 趋势提示
  - 趋势摘要卡
  - 基线表格

## 影响范围

- 只改 Web 表达层、提示文案和前端样式。
- 未修改导入、审查、脱敏、导出等核心业务逻辑。
