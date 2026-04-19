# Todo

## Latest Update 2026-04-20 Round 11

### Newly Completed

- [x] Added end-to-end real-provider validation service at `app/core/services/release_validation.py`
- [x] Added one-command validation CLI at `app/tools/release_validation.py`
- [x] Added release-validation unit and integration coverage
- [x] Validated the new release-validation flow against the live sandbox success path
- [x] Ran the new release-validation CLI against current local config and wrote the blocked-state artifacts to `docs/dev/real-provider-validation-latest.*`
- [x] Re-ran final full regression to `127 passed, 0 failed`
- [x] Wrote round-specific docs in `docs/dev/99-106`

### Next Backlog Snapshot

- [ ] Fill real `external_http` endpoint, model, and API-key env mapping into `config/local.json`
- [ ] Export the real API key into the configured local environment variable
- [ ] Re-run `py -m app.tools.release_validation --config config\\local.json --mode-a-path input\\软著材料\\2501_软著材料.zip --mode-b-path input\\合作协议`
- [ ] If the first real run fails, fix gateway contract / timeout / auth issues and rerun until `provider_probe=ok` and `release_gate=pass`

## Latest Update 2026-04-20 Round 10

### Newly Completed

- [x] Audited `config/local.json` and local `SOFT_REVIEW_*` environment state before resuming work
- [x] Confirmed the workspace is still intentionally blocked on real-provider smoke because local config remains mock-first and no provider env vars exist
- [x] Added `app/web/README.md` with the page-layer module map, edit workflow, and Windows encoding guardrails
- [x] Added `tests/unit/test_web_source_contracts.py` to protect the `app/web` export surface and catch known mojibake markers early
- [x] Re-ran targeted web regression for the new contributor and source-safety guardrails
- [x] Re-ran final full regression to `124 passed, 0 failed`
- [x] Wrote round-specific docs in `docs/dev/92-98`

### Next Backlog Snapshot

- [ ] Connect a real `external_http` endpoint, model, and API-key env mapping into `config/local.json`
- [ ] Run the first non-mock provider smoke and capture the first non-mock release-gate result
- [ ] Decide whether to extract repeated submission action forms into smaller HTML blocks now that the page layer is documented and protected
- [ ] Consider expanding mojibake-guardrail coverage to other localized docs or operator-facing text modules if Windows editing continues

## Latest Update 2026-04-20 Round 9

### Newly Completed

- [x] Split the rebuilt page layer into shared helpers plus per-page renderer modules
- [x] Added `app/web/view_helpers.py` as the shared rendering toolkit
- [x] Added modular renderers for home, submission, case, report, and ops views
- [x] Reduced `app/web/pages.py` to a stable export barrel for FastAPI imports
- [x] Realigned the renderer layout output with the existing admin CSS structure
- [x] Re-ran compile validation for all new page modules
- [x] Re-ran page, ops, manual-correction, and browser E2E regression
- [x] Re-ran final full regression to `121 passed, 0 failed`
- [x] Wrote round-specific docs in `docs/dev/85-91`

### Next Backlog Snapshot

- [ ] Connect a real `external_http` endpoint and credentials into `config/local.json`
- [ ] Run a real non-sandbox provider smoke and record the first non-mock release-gate result
- [ ] If needed, continue refining the admin UX visually now that the renderer structure is safer to iterate on
- [ ] Consider extracting repeated HTML sections into even smaller reusable blocks if the page layer grows again
- [ ] Add a lightweight contributor note for `app/web/` so future UI edits follow the new module map

## Latest Update 2026-04-20 Round 8

### Newly Completed

- [x] Added `config/local.json` with safe mock-first defaults for repeatable local startup
- [x] Re-ran `provider_probe` and `release_gate` against the new local config and recorded the current mock-mode gate state
- [x] Rebuilt `app/web/pages.py` from active route contracts after a Windows encoding write corrupted the page source
- [x] Backed up the corrupted page source to `docs/dev/history/pages_corrupted_source_backup_20260420_0104.py`
- [x] Preserved the admin-style management console contract for home, submission, case, report, and `/ops`
- [x] Updated startup self-check tests to align with the new default local config presence
- [x] Re-ran targeted UI / ops / manual-correction / browser E2E regression
- [x] Re-ran final full regression to `121 passed, 0 failed`
- [x] Wrote round-specific docs in `docs/dev/78-84`

### Next Backlog Snapshot

- [ ] Wire a real `external_http` endpoint, model, and API-key env mapping into `config/local.json`
- [ ] Run a real non-sandbox provider smoke after local credentials are available
- [ ] Consider splitting `app/web/pages.py` into smaller renderer modules or templates now that the contract-first rebuild is stable
- [ ] Decide whether to restore additional high-fidelity visual polish on top of the rebuilt stable admin renderer
- [ ] Add a guardrail or tooling note that blocks unsafe full-file rewrites of UTF-8 source on Windows without explicit encoding

## Latest Update 2026-04-20 Round 7

### Newly Completed

- [x] Audited real-provider readiness gates across config loading, startup checks, probe flow, and `/ops`
- [x] Added phase-based provider readiness states with `blocking_items` and `recommended_action`
- [x] Persisted the latest provider probe artifact to `data/runtime/ops/provider_probe_latest.json`
- [x] Upgraded `/ops` with `Provider Readiness`, `Latest Probe`, `Probe Observatory`, and richer smoke-command guidance
- [x] Validated sandbox-first `external_http` probe flow with synthetic `llm_safe` payload only
- [x] Re-ran rolling baseline archival on 2026-04-20 and captured fresh history artifacts under `docs/dev/history`
- [x] Re-ran final full regression to `115 passed, 0 failed`
- [x] Wrote round-specific docs in `docs/dev/72-77`

### Next Backlog Snapshot

- [ ] Add local `config/local.json` with real provider endpoint, model, and API-key env name
- [ ] Run a real non-sandbox provider smoke after local credentials are available
- [ ] Decide whether provider probe should remain manual or also run on startup / release gates
- [ ] Consider exposing probe-artifact history or download links in `/ops`
- [ ] Review and safely remove the legacy ops renderer backup in `app/web/pages.py` after a dedicated cleanup pass

## Latest Update 2026-04-19 Round 6

### Newly Completed

- [x] Added rolling baseline archive support to `app.tools.metrics_baseline`
- [x] Added baseline history discovery and signed delta formatting in `app.core.services.ops_status`
- [x] Upgraded `/ops` to expose `Trend Watch`, `Baseline History`, and `Provider Checklist`
- [x] Added `Rolling Baseline` command guidance to the ops console
- [x] Updated ops integration coverage and aligned baseline-status unit expectations
- [x] Ran full regression to `113 passed, 0 failed`
- [x] Generated rolling baseline archives in `docs/dev/history`
- [x] Wrote round-specific docs in `docs/dev/64-70`

### Next Backlog Snapshot

- [ ] Add real non-sandbox provider smoke after `config/local.json` and real credentials exist locally
- [ ] Decide whether rolling baseline should run nightly, pre-release, or both
- [ ] Add searchable baseline-history filters or exported ops summaries for operators
- [ ] Consider surfacing baseline archive downloads directly in the web console

## Latest Update 2026-04-19 Round 5

### Newly Completed

- [x] Added `app.tools.provider_probe` plus reusable provider readiness service
- [x] Upgraded `/ops` to show provider readiness, latest backup, and latest baseline
- [x] Added ops status helpers for backup and baseline discovery
- [x] Hardened legacy `.doc` parsing by stripping control characters before quality scoring
- [x] Hardened PDF parsing by decoding compressed streams and `ToUnicode` maps
- [x] Reduced real sample mode A `needs_review / low_quality` from `10 / 10` to `0 / 0`
- [x] Reduced real sample mode B `needs_review / low_quality` from `2 / 2` to `0 / 0`
- [x] Generated final comparison artifacts in `docs/dev/56-57`
- [x] Wrote round-specific docs in `docs/dev/58-63`

### Next Backlog Snapshot

- [ ] Connect a real external provider endpoint, model, and credential for non-sandbox smoke
- [ ] Decide baseline capture cadence for ongoing regression tracking
- [ ] Review backup retention and cleanup automation thresholds with real runtime growth data

## Latest Update 2026-04-19 Round 4

### Newly Completed

- [x] 增加 `app.tools.provider_sandbox`，打通 `external_http` 本地联调沙箱
- [x] 增加 `app.tools.runtime_backup`，补齐 backup / inspect / restore 预演能力
- [x] 增加 `app.tools.metrics_baseline`，沉淀真实样本趋势基线
- [x] 在 `/ops` 页面补充 sandbox / backup / baseline 命令入口
- [x] 生成首个 runtime 备份归档
- [x] 生成首个真实样本基线 Markdown / JSON
- [x] 修复 `runtime_backup` 在 Windows 终端下的编码与大输出问题
- [x] 把本轮计划、构建、问题、验证、经验写入 `docs/dev/49-53`

### Next Backlog Snapshot

- [ ] 把 provider sandbox 的联调流程拓展到真实网关配置模板
- [ ] 设计基于 baseline JSON 的持续趋势看板或周期任务
- [ ] 继续降低真实样本中的 `needs_review / low_quality`
- [ ] 评估是否清理 `data/runtime` 中历史诊断产物以控制备份体积

## Latest Update 2026-04-19 Round 3

### Newly Completed

- [x] 建立 legacy `.doc` 最小真实回归语料目录
- [x] 细化 `review_reason_code` / `legacy_doc_bucket` 并贯通到页面、报告、`input_runner`
- [x] 增加浏览器级 E2E 主链路
- [x] 把 `external_http` adapter 收敛为正式 request/response 契约
- [x] 增加 `ai_provider_readiness` 启动自检
- [x] 增加 `app.tools.runtime_cleanup` 与运行时保留策略
- [x] 修复 Windows 下 SQLite 清库文件锁回归
- [x] 把本轮计划、构建、问题、验证、经验写入 `docs/dev/44-48`

### Next Backlog Snapshot

- [ ] 为真实 provider 接入准备端到端联调沙箱
- [ ] 为 runtime cleanup 增加备份前置 SOP 与值班手册
- [ ] 持续降低 `needs_review / low_quality` 占比
- [ ] 补一轮真实样本趋势对比报表

## MVP Closed

- [x] 建立开发总览、计划、架构、运行说明
- [x] 建立测试策略与基础测试骨架
- [x] 建立领域模型与核心服务
- [x] 实现 ZIP 安全解压与两种导入模式
- [x] 实现材料分类、解析、规则审查、Mock AI、报告渲染
- [x] 建立 Web MVP 页面与接口
- [x] 跑通自动化测试与手工主链路验证
- [x] 记录问题、修复和经验手册

## This Round Completed

- [x] 更新 `requirements.txt`，对齐当前 MVP 的目标依赖说明
- [x] 更新 `README.md`，对齐当前网站化形态
- [x] 新增 Web 主路径自动化测试
- [x] 新增 Windows 非法文件名 ZIP 回归测试
- [x] 把 `ui-ux-pro-max-skill` 整理到本地技能库目录
- [x] 补齐 `docs/dev/10-test-matrix.md`
- [x] 补齐 `docs/dev/12-skill-integration.md`

## Next Backlog

- [ ] 接入 SQLite / PostgreSQL 持久化
- [ ] 增加人工纠正分类和 Case 归并页面
- [ ] 增加更完整的 `.doc` / `.pdf` 解析回归样本
- [ ] 接入真实 AI provider
- [ ] 增加批次筛选、重审、误报标记功能
- [ ] 增加更完整的浏览器级 E2E

## Notes

- 当前环境下 `skill-creator` 的 `quick_validate.py` 因缺少 `yaml` 依赖未能运行，但技能目录结构与检索脚本已完成手工验证。

## Latest Update 2026-04-19

### Newly Completed

- [x] 增加浏览器端 `Operator Console`
- [x] 增加 `Export Center` 与 `Artifact Browser`
- [x] 增加报告、材料产物、submission bundle、app log 下载
- [x] 增加上传 / 纠偏 / 下载结构化日志
- [x] 增加配置驱动 AI provider 解析
- [x] 增加非 mock provider 的脱敏强校验
- [x] 用 `safe_stub` 完成非 mock 边界真实烟测
- [x] 把本轮计划、构建、问题、验证、经验手册写入 `docs/dev/32-36`

### Next Backlog Snapshot

- [ ] 继续降低老 `.doc` 样本的 `low_quality` / `needs_review` 占比
- [ ] 细化模式 B 的浏览器端批量导入体验
- [ ] 在 `safe_stub` 之后接入真实 provider adapter
- [ ] 增加 `Support / Ops` 页面或等效运维入口
- [ ] 增加浏览器级 E2E 与真实样本趋势基线

## Latest Update 2026-04-19 Round 2

### Newly Completed

- [x] 模式 A 真实样本 `unknown` 总数收敛到 `0`
- [x] `input_runner` 增加聚合摘要
- [x] 增加 `Support / Ops` 页面
- [x] 增加启动自检与配置模板
- [x] 增加 `external_http` provider adapter skeleton
- [x] 页面与报告分离展示规则结论和 AI 补充说明
- [x] Submission 页面增加 `Import Digest` 与操作台预填
- [x] 把本轮计划、构建、问题、验证、经验手册写入 `docs/dev/38-42`
- [x] 新增下一阶段细颗粒 todo：`docs/dev/43-next-granular-todo.md`

### Current Backlog Snapshot

- [ ] 建立 legacy `.doc` 最小真实回归语料目录
- [ ] 增加浏览器级 E2E 主链路
- [ ] 把 `external_http` skeleton 收敛为正式 provider 契约
- [ ] 增加 runtime 清理策略 / 脚本 / runbook
