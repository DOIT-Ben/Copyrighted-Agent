# 首页导入台布局修正记录
## 日期

- 2026-04-21

## 问题

- `import-console` 与右侧并列卡片共用通用 `12` 列栅格。
- 左右两块被固定在同一行并强制等高，导致：
  - 左侧内容显得过长
  - 右侧卡片又瘦又高
  - 内部文字和表单区域被压缩

## 处理

- 将首页顶部这组面板从通用 `dashboard-grid` 中拆出，改为专用 `lead-grid`。
- 新规则：
  - 左侧导入台使用更宽主栏
  - 右侧可信信号保持自然高度，不再被强制拉长
  - 空间不足时允许整体下排
- 同时把内部 `compare-grid` 和 `control-grid` 改为最小宽度驱动的自适应布局，避免继续横向挤压。

## 代码落点

- `app/web/page_home.py`
- `app/web/static/styles.css`

## 验证

- `py_compile` 通过
- `pytest tests\\integration\\test_web_mvp_contracts.py tests\\integration\\test_operator_console_and_exports.py tests\\unit\\test_web_source_contracts.py` 通过
- Web 已重启，首页可直接刷新查看
