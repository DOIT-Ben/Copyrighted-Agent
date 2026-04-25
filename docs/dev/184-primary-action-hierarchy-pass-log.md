# 184 主次动作层级收口记录

## 时间
- 2026-04-24

## 目标
- 继续减少首屏按钮数量
- 让首页与运维页只保留主动作
- 把次级动作继续后移

## 本次调整
- 更新 `app/web/static/styles.css`
- 首页最近结果区：
  - 首屏只显示前两个动作
  - 额外次级动作隐藏
- 运维中心业务收尾区：
  - 首屏只显示第一个主下载动作
  - 次级下载动作继续后移

## 结果
- 首页最近结果更像“查看结果 + 继续处理”
- 运维中心收尾区更像“主结论 + 主导出”
- 主动作层级更清晰

## 验证
- `D:\Soft\python310\python.exe -m py_compile app\web\page_ops.py app\web\view_helpers.py app\web\page_home.py app\web\page_submission.py app\web\page_case.py app\web\page_report.py app\web\page_review_rule.py app\web\review_profile_widgets.py app\web\prompt_views.py`
- `D:\Soft\python310\python.exe -m pytest tests\integration\test_web_mvp_contracts.py -q`
- 结果：`6/6 passed`
