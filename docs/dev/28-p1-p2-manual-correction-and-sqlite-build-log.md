# P1-P2 构建记录

## 日期

- 2026-04-19

## 人工纠错

- 扩展 `Submission`，加入 `correction_ids`
- 新增 `Correction` 数据模型
- 扩展 `RuntimeStore`，加入 `corrections`
- 新增 `app/core/services/corrections.py`
- 实现动作：
  - `change_material_type`
  - `assign_material_to_case`
  - `create_case_from_materials`
  - `merge_cases`
  - `rerun_case_review`
- 为纠错动作自动记录 correction 审计信息
- 在 Submission 详情页加入 `Correction Audit` 面板

## SQLite 持久化

- 新增 `app/core/services/sqlite_repository.py`
- 首版持久化策略使用 JSON blob 落表，先保证恢复能力，再逐步细化 schema
- 当前落表对象：
  - submissions
  - cases
  - materials
  - parse_results
  - review_results
  - report_artifacts
  - jobs
  - corrections
- 在 ingestion 与 correction 动作结束后自动保存 submission graph
- 在应用启动时自动从 SQLite 恢复到 runtime store

## 本轮新增测试

- `tests/integration/test_manual_correction_api.py`
- `tests/integration/test_sqlite_persistence.py`

## 阶段结论

- P1 已具备“最小可用人工纠错后端”
- P2 已具备“最小可用持久化与恢复能力”
- 下一阶段重点应转向：
  - 前端纠错控件
  - correction 的浏览器端操作流
  - SQLite schema 细化与迁移
