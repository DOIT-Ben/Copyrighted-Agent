# 183 运维中心首屏瘦身记录

## 时间
- 2026-04-24

## 目标
- 对运维中心再做一轮首屏减法
- 删除重复摘要与次要动作
- 让首屏更偏向结论与主动作

## 本次调整
- `业务收尾`
  - 摘要卡从 3 个压到 2 个
  - 动作区只保留主下载与探针下载
  - 去掉 `Closeout JSON` 与 `应用日志` 的首屏入口
- `发布闸门`
  - 去掉 `基线` 摘要卡
- `模型通道`
  - 去掉 `接口` 摘要卡
- 页头状态区
  - 去掉 `本地脱敏` 状态 pill

## 结果
- 运维中心首屏更薄
- 视觉焦点更集中在：
  - 业务收尾
  - 发布闸门
  - 模型通道
  - 常用命令
- 次要下载和补充信息继续后移

## 验证
- `D:\Soft\python310\python.exe -m py_compile app\web\page_ops.py app\web\view_helpers.py app\web\page_home.py app\web\page_submission.py app\web\page_case.py app\web\page_report.py app\web\page_review_rule.py app\web\review_profile_widgets.py app\web\prompt_views.py`
- `D:\Soft\python310\python.exe -m pytest tests\integration\test_web_mvp_contracts.py -q`
- 结果：`6/6 passed`
