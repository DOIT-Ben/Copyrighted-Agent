# 185 摘要卡压缩与次级动作后移记录

## 时间
- 2026-04-24

## 目标
- 继续压缩详情页首屏摘要卡数量
- 继续减少首屏次级动作按钮
- 保持功能不变，只做展示层收口

## 本次调整
- 更新 `app/web/static/styles.css`
- `批次详情`
  - `导入摘要` 首屏最多显示 3 个摘要卡
  - `下一步` 首屏最多显示 3 个摘要卡
  - `少量提醒` 首屏最多显示 3 个摘要卡
  - `下一步` 动作区只显示前 2 个动作
- `导出中心`
  - 首屏最多显示 2 个摘要卡
  - 动作区只显示第 1 个主动作
- `项目页报告入口`
  - 报告入口动作区只显示第 1 个主动作

## 结果
- 批次详情首屏更像概览入口页
- 导出中心更像单主动作交付页
- 项目页报告入口更克制

## 验证
- `D:\Soft\python310\python.exe -m py_compile app\web\page_ops.py app\web\view_helpers.py app\web\page_home.py app\web\page_submission.py app\web\page_case.py app\web\page_report.py app\web\page_review_rule.py app\web\review_profile_widgets.py app\web\prompt_views.py`
- `D:\Soft\python310\python.exe -m pytest tests\integration\test_web_mvp_contracts.py -q`
- 结果：`6/6 passed`
