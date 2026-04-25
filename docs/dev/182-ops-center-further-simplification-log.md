# 182 运维中心进一步简化记录

## 时间
- 2026-04-24

## 目标
- 继续降低运维中心的信息密度
- 让半宽面板先给结论，再按需展开表格
- 让命令区更短、更像入口而不是说明墙

## 本次调整
- 再次重写 `app/web/page_ops.py`，统一为干净 UTF-8 版本
- `发布闸门` 改为：
  - 顶部一句结论
  - 3 个摘要指标
  - 折叠后的明细表
- `模型通道` 改为：
  - 顶部一句结论
  - 3 个摘要指标
  - 折叠后的明细表
- `常用运维入口` 收敛为两组：
  - `常用命令`
  - `低频维护`
- 删掉不必要的命令项，只保留最常用入口
- `更多观测` 保持：
  - 启动自检
  - 探针观测
  - 质量趋势

## 结果
- 首屏更接近“结论页 + 入口页”
- 半宽卡片不再直接摆完整大表
- 页面风格与首页、批次页、结果页更一致

## 验证
- `D:\Soft\python310\python.exe -m py_compile app\web\page_ops.py app\web\view_helpers.py app\web\page_home.py app\web\page_submission.py app\web\page_case.py app\web\page_report.py app\web\page_review_rule.py app\web\review_profile_widgets.py app\web\prompt_views.py`
- `D:\Soft\python310\python.exe -m pytest tests\integration\test_web_mvp_contracts.py -q`
- 结果：`6/6 passed`
