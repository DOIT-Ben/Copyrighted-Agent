# 186 次级动作继续后移记录

## 时间
- 2026-04-25

## 目标
- 继续减少首屏可见的次级操作
- 让规则页、导出页和报告卡片更偏向单主动作
- 继续通过展示层收口，避免引入业务回归

## 本次调整
- 更新 `app/web/static/styles.css`
- `规则页`
  - `规则概览` 首屏最多显示 2 个摘要卡
  - `规则编辑` 动作区只保留前 2 个主操作
  - 隐藏返回类次级按钮
- `导出中心`
  - 报告卡片动作区只保留第 1 个主动作
- 之前已收口的页面规则保持不变：
  - 首页最近结果
  - 运维中心业务收尾
  - 批次详情摘要区
  - 导出中心摘要区
  - 项目页报告入口

## 结果
- 规则页更像“编辑 + 执行”的页面
- 导出页更像“查看主结果”的页面
- 全站主次动作分级进一步一致

## 验证
- `D:\Soft\python310\python.exe -m py_compile app\web\page_ops.py app\web\view_helpers.py app\web\page_home.py app\web\page_submission.py app\web\page_case.py app\web\page_report.py app\web\page_review_rule.py app\web\review_profile_widgets.py app\web\prompt_views.py`
- `D:\Soft\python310\python.exe -m pytest tests\integration\test_web_mvp_contracts.py -q`
- 结果：`6/6 passed`
