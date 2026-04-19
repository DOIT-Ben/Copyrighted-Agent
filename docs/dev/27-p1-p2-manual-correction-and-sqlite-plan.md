# P1-P2 人工纠错与 SQLite 计划

## 日期

- 2026-04-19

## 本轮目标

- 先把人工纠错最小闭环做通：
  - 改材料类型
  - 新建 case
  - 分配材料到 case
  - 合并 case
  - 重跑 review
- 再把 submission 图谱最小化落到 SQLite，解决“重启即丢失”的核心风险。

## 本轮范围

- correction 数据模型
- correction API
- correction audit 展示
- SQLite JSON-blob 持久化
- SQLite 恢复到 runtime store

## 不在本轮处理

- 完整的前端纠错操作面板
- 数据库完全规范化建模
- 迁移脚本版本化
- 多用户权限模型

## Done 标准

- 纠错动作可通过 API 完成并留痕
- Submission 页面可看到 correction history
- submission/case/material/parse/review/report/correction 可落盘到 SQLite
- runtime store 清空后可从 SQLite 恢复
- 全量测试通过
