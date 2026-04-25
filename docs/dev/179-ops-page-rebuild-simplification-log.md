# 179 Ops Page Rebuild Simplification Log

## 日期
- 2026-04-24

## 目标
- 继续简化运维中心。
- 解决旧版 `page_ops.py` 中历史编码混乱导致的结构改造困难。

## 本次改动
- 重建 [`app/web/page_ops.py`](D:\Code\软著智能体\app\web\page_ops.py)
  - 将运维页核心中文文案统一改为干净 UTF-8。
  - 保留原有业务数据来源与状态计算逻辑。
  - 首屏结构改为：
    - `业务收尾`
    - `常用运维入口`
    - `发布闸门`
    - `模型通道就绪度`
    - `更多观测`
  - 将 `启动自检 / 探针观测 / 质量趋势 / 探针历史` 收敛到一个 `更多观测` 面板内，通过折叠块按需展开。
  - 去掉运维页中重复的次级摘要区块，避免首屏像监控墙。
- 保持共享布局与样式体系不变，尽量把变化控制在页面结构本身。

## 设计结果
- 运维页现在更像“决策页”，而不是“堆信息页”。
- 首屏先回答 3 个问题：
  - 当前能不能交付
  - 当前能不能放行
  - 模型通道是否就绪
- 观测、自检、趋势和历史仍保留，但退到第二层。

## 验证
- `D:\Soft\python310\python.exe -m py_compile app\web\page_ops.py app\web\view_helpers.py app\web\page_home.py app\web\page_submission.py app\web\page_case.py app\web\page_report.py`
- `D:\Soft\python310\python.exe -m pytest tests\integration\test_web_mvp_contracts.py -q`

## 结果
- `py_compile` 通过。
- 集成测试 `6/6` 通过。

## 后续建议
- 现在运维页结构已经干净了，下一轮可以继续削减文案长度，把部分 KPI 的说明再压一档。
- 也可以把 `更多观测` 中的折叠块默认全部关闭，只保留一个最常用的默认展开项。
