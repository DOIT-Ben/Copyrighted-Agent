# P1-P2 验证报告

## 日期

- 2026-04-19

## 自动化回归

- 命令：`py -m pytest`
- 结果：`60 passed, 0 failed`

## 人工纠错验证

- 新增验证：
  - 改材料类型后会生成 correction record
  - Submission 页面可看到 correction history
  - 支持：
    - create case
    - assign case
    - merge case
    - rerun review

## SQLite 验证

- 新增验证：
  - submission graph 已落盘
  - runtime store reset 后可从 SQLite 恢复
  - correction 记录可恢复

## 真实样本回归

- 命令：
  - `D:\Soft\python310\python.exe -m app.tools.input_runner --path input\软著材料 --mode single_case_package`
  - `D:\Soft\python310\python.exe -m app.tools.input_runner --path input\合作协议 --mode batch_same_material`

## 真实样本结论

- 模式 A 结果与 P0 阶段一致，无新增回归
- 模式 B 结果与 P0 阶段一致，无新增回归
- 说明 SQLite 接入未破坏既有导入与分类链路

## 阶段结论

- P1 后端闭环可用
- P2 最小恢复能力可用
- 当前系统已经从“只会跑一次的 MVP”升级为“可纠错、可追溯、可恢复的内部分析系统基础版”
