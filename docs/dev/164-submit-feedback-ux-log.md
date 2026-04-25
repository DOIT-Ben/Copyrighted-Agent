# 164 提交反馈体验补强日志

日期：2026-04-24

## 背景

首页点击“开始分析”后，用户缺少即时反馈，容易误判为按钮无响应。

## 本次处理

1. 在首页导入表单补齐即时反馈信息。
2. 保留表单内联提示，提交后立即展示“分析已开始”状态。
3. 在全局提交浮层中加入阶段文案轮播：
   - 文件已提交
   - 正在解析材料
   - 正在执行脱敏与审查
   - 正在整理结果页
4. 为提交浮层补充进度条与阶段文本样式。
5. 调整首页表单的 `onsubmit` 行为，避免与全局提交监听重复占用同一提交标记。
6. 扩展集成测试，覆盖提交反馈浮层节点。

## 涉及文件

- `app/web/page_home.py`
- `app/web/view_helpers.py`
- `app/web/static/styles.css`
- `tests/integration/test_web_mvp_contracts.py`

## 验证

- `python -m py_compile app\web\page_home.py app\web\view_helpers.py tests\integration\test_web_mvp_contracts.py`
- `python -m pytest tests\integration\test_web_mvp_contracts.py -q`
- 重启运行栈后检查首页 HTML，确认存在：
  - `data-inline-pending`
  - `data-pending-steps`
  - `submit-feedback-progress-fill`
  - `submit-feedback-step`

## 当前结果

点击“开始分析”后，用户可以立即看到按钮 loading、表单内联提示，以及右下角阶段式提交反馈浮层。主观“无反应”问题已收敛。

## 后续建议

- 如果后续要提供真实进度条，应把上传改成先创建 job，再由前端轮询 `job_id` 状态，而不是继续依赖同步表单提交。
