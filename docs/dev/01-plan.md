# Development Plan

## Goal

把“软著材料审查脚本”收敛为一个可网站化演进的 MVP，并把开发、测试、修复、经验沉淀全部写入 `docs/dev/`。

## Delivery Order

### Phase 0: Requirement Alignment

目标：

- 明确最终产品是网站，而不是 CLI 包装
- 明确 ZIP 的两种核心模式
- 明确 MVP 不做数据库、权限、真实 AI

交付：

- `docs/dev/00-overview.md`
- `docs/web-roadmap.md`

### Phase 1: Test Baseline First

目标：

- 先把系统边界写成可执行测试和测试策略
- 锁住领域模型、主路径与安全底线

交付：

- `docs/test-strategy.md`
- `tests/unit/`
- `tests/integration/`
- `tests/non_functional/`

### Phase 2: Core Domain And Services

目标：

- 建立 `Submission / Case / Material / ReviewResult / ReportArtifact / Job`
- 建立统一解析、分类、审查、报告接口

交付：

- `app/core/domain`
- `app/core/parsers`
- `app/core/services`
- `app/core/reviewers`
- `app/core/reports`

### Phase 3: Submission Pipeline

目标：

- 支持 ZIP 安全解压
- 支持模式 A / B
- 支持材料分类、Case 聚合、报告生成

交付：

- `safe_extract_zip`
- `ingest_submission`
- `SubmissionMode` 驱动的流水线

### Phase 4: Web MVP

目标：

- 打通用户可见的主路径
- 可上传、可浏览、可查看报告

交付：

- `app/api/main.py`
- `app/web/pages.py`
- `app/web/static/styles.css`

### Phase 5: Validation And Fix Loop

目标：

- 运行自动化测试
- 做手工主链路验证
- 把发现的问题立刻转成回归测试

交付：

- `docs/dev/05-test-log.md`
- `docs/dev/06-issues-and-fixes.md`
- 新增回归测试

### Phase 6: Documentation And Reuse

目标：

- 把开发顺序、运行方式、测试矩阵、经验手册都沉淀下来
- 把前端设计 skill 接入可复用技能目录

交付：

- `docs/dev/07-playbook.md`
- `docs/dev/09-runbook.md`
- `docs/dev/10-test-matrix.md`
- `docs/dev/12-skill-integration.md`

## Current Status

- Phase 0-6 已完成 MVP 闭环
- 当前进入“回归测试补强 + 为下一轮网站增强做准备”阶段
