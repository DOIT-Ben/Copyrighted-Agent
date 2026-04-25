# 181 运维中心极简化记录

## 时间
- 2026-04-24

## 目标
- 继续压缩运维中心的信息噪音
- 让页面更像结论页与入口页
- 把低频观测收进折叠区

## 本次调整
- 重写 `app/web/page_ops.py` 为干净 UTF-8 版本
- 维持统一的简约布局风格
- 去掉顶部横幅式提示
- KPI 从 4 个压到 3 个
- 运维命令区收敛为：
  - `常用命令`
  - `低频维护`
- 观测区收敛为：
  - `启动自检`
  - `探针观测`
  - `质量趋势`
- 移除首屏批次/项目/材料统计类辅助信息
- 保留必要的下载与日志入口

## 结果
- 首屏只保留：
  - 业务收尾
  - 常用运维入口
  - 发布闸门
  - 模型通道
  - 更多观测
- 页面层级更清晰，运维中心与其他页面的简约风格更一致

## 验证
- `D:\Soft\python310\python.exe -m py_compile app\web\page_ops.py app\web\view_helpers.py app\web\page_home.py app\web\page_submission.py app\web\page_case.py app\web\page_report.py app\web\page_review_rule.py app\web\review_profile_widgets.py app\web\prompt_views.py`
- `D:\Soft\python310\python.exe -m pytest tests\integration\test_web_mvp_contracts.py -q`
- 结果：`6/6 passed`
