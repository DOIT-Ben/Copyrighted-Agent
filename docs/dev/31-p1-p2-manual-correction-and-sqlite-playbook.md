# P1-P2 经验手册

## 人工纠错阶段的经验

- 不要把 correction 当成对原对象的简单覆盖。
- correction 必须是独立记录，否则后续无法审计。
- 改材料类型之后，不能只改 `material.material_type`，还要同步：
  - case review
  - case report
  - correction history

## SQLite 阶段的经验

- 首版持久化优先保证“能保存、能恢复”，不要一开始就追求完美 schema。
- 先用 JSON blob 把 submission graph 保存下来，开发速度更高，回滚成本更低。
- 真正的难点不是建表，而是定义“什么时候保存”和“恢复后怎么重新装回 runtime store”。

## 测试经验

- 共享 SQLite 文件的测试不要并行跑。
- 持久化测试要显式清理数据库，避免跨测试污染。
- 只要引入 correction，就要同时测：
  - 数据变更
  - 审计记录
  - 页面可见性
  - 持久化恢复

## 对下一阶段的建议

- P3 优先补浏览器端纠错控件，而不是继续堆后端动作
- P2 下一步优先细化 SQLite schema，而不是继续扩大 JSON blob 使用范围
- 完成浏览器端纠错后，再考虑导出 correction audit 和 privacy manifest
