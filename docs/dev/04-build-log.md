# Build Log

## 2026-04-20

### Latest Update Round 12

- Added `app/tools/minimax_bridge.py` to translate the project's `external_http` review contract into MiniMax OpenAI-compatible `chat/completions` calls
- Added bridge coverage:
  - `tests/unit/test_minimax_bridge_contracts.py`
  - `tests/integration/test_minimax_bridge_flow.py`
- Added `config/local.minimax_bridge.example.json` as the non-secret repeatable bridge config template
- Verified the MiniMax live path end to end with:
  - synthetic safe provider probe through the bridge
  - full `release_validation` through the bridge
- Reached the first true non-mock validated state in this workspace using:
  - local bridge endpoint `http://127.0.0.1:18011/review`
  - model `MiniMax-M2.7-highspeed`
  - env-based secret injection only
- Refreshed `docs/dev/real-provider-validation-latest.*` and timestamped history artifacts with a passing live-provider result

## 2026-04-20

### Latest Update Round 11

- Added `app/core/services/release_validation.py` to turn the final 10 percent into a single repeatable workflow:
  - provider probe
  - release gate
  - mode A real-sample smoke
  - mode B real-sample smoke
  - markdown / JSON artifact writing
- Added `app/tools/release_validation.py` as the operator-facing CLI entrypoint
- Added automated coverage for blocked-state and sandbox-success release-validation flows
- Fixed release-validation artifact write order so the latest JSON now includes non-empty `artifacts` metadata pointing to the latest files and timestamped history files
- Ran the new validation CLI against the current local config and wrote:
  - `docs/dev/real-provider-validation-latest.json`
  - `docs/dev/real-provider-validation-latest.md`
  - timestamped history artifacts under `docs/dev/history`
- Re-ran the one-command validation flow after the artifact fix and confirmed the remaining blocker is still local mock config, not code readiness
- Confirmed the current workspace remains environment-blocked only because local config is still mock-first

## 2026-04-20

### Latest Update Round 10

- Audited `config/local.json` plus `SOFT_REVIEW_*` environment variables before attempting to resume real-provider onboarding
- Confirmed the workspace is still in safe local mock mode and has no real provider credentials wired yet
- Added `app/web/README.md` as the contributor map for the modular renderer layer
- Documented the Windows-safe workflow for validating UTF-8 source with Python `unicode_escape` output before assuming a file is corrupted
- Added `tests/unit/test_web_source_contracts.py` to protect:
  - the stable `app.web.pages` export surface
  - the new `app/web` contributor guide presence
  - the absence of known mojibake markers in active web source
- Refined the new mojibake guardrail test to generate suspicious markers from canonical localized terms at runtime, keeping the test source itself ASCII-stable on Windows
- Re-ran targeted regression and final full regression after the new guardrails landed

## 2026-04-20

### Latest Update Round 9

- Added `app/web/view_helpers.py` to centralize layout, pills, tables, cards, nav, and stylesheet loading
- Split page renderers into:
  - `app/web/page_home.py`
  - `app/web/page_submission.py`
  - `app/web/page_case.py`
  - `app/web/page_report.py`
  - `app/web/page_ops.py`
- Replaced `app/web/pages.py` with a stable export layer so `app.api.main` keeps the same import surface
- Aligned the new layout output with the existing CSS structure such as `sidebar-brand`, `workspace`, and `workspace-header`
- Preserved all current route contracts and operator workflows while reducing the risk of future large single-file page edits
- Re-ran compile checks, targeted regression, and final full regression after the split

## 2026-04-20

### Latest Update Round 8

- Added `config/local.json` with mock-safe defaults so the workspace can boot consistently without ad hoc env setup
- Re-ran `py -m app.tools.provider_probe --config config\local.json` and confirmed mock-mode readiness plus persisted latest probe artifact
- Re-ran `py -m app.tools.release_gate --config config\local.json` and confirmed the environment is now config-ready but still warning in mock mode
- Tried a low-risk `/ops` command-text polish pass and hit a Windows encoding regression after a full-file PowerShell rewrite of `app/web/pages.py`
- Backed up the damaged page source into `docs/dev/history/pages_corrupted_source_backup_20260420_0104.py`
- Abandoned the risky patch-the-garbled-source path and rebuilt `app/web/pages.py` from the active FastAPI route contract instead
- Restored stable admin renderers for the home page, submissions index, submission detail, case detail, report reader, and `/ops`
- Updated `tests/unit/test_startup_self_check_contracts.py` to match the intentional new default of `config/local.json` existing locally
- Re-ran targeted regression, browser E2E, and final full regression until the workspace returned to green

## 2026-04-20

### Latest Update Round 7

- Reworked `app/core/services/provider_probe.py` into a phase-based readiness and probe-observability service
- Added readiness `phase`, `blocking_items`, `recommended_action`, and latest-artifact persistence to `data/runtime/ops/provider_probe_latest.json`
- Extended `app/tools/provider_probe.py` so the CLI writes the latest probe artifact by default and prints clearer readiness/probe summaries
- Updated `app/core/services/startup_checks.py` to expose `config_local` and `provider_probe_status`
- Upgraded `/ops` in `app/web/pages.py` with `Provider Readiness`, `Latest Probe`, `Probe Observatory`, and safer sandbox-first / real-provider smoke guidance
- Added / updated regression coverage in:
  - `tests/unit/test_provider_probe_contracts.py`
  - `tests/unit/test_startup_self_check_contracts.py`
  - `tests/integration/test_provider_probe_flow.py`
  - `tests/integration/test_operator_console_and_exports.py`
- Validated the live sandbox-first probe on 2026-04-20 after fixing the PowerShell job working-directory issue
- Re-ran rolling baseline archive generation and final full regression before documentation closeout

## 2026-04-19

### Latest Update Round 6

- Extended `app/core/services/ops_status.py` with baseline-history loading, signed delta formatting, and rolling-status aggregation
- Extended `app/tools/metrics_baseline.py` with latest-baseline auto-compare and archive output support
- Replaced the active `/ops` page implementation in `app/web/pages.py` with a trend-aware admin console view
- Added `Provider Checklist`, `Trend Watch`, and `Baseline History` panels plus a `Rolling Baseline` command block
- Updated `tests/unit/test_ops_status_contracts.py` to match the new warning semantics when review debt remains
- Updated `tests/integration/test_operator_console_and_exports.py` to assert the new ops modules
- Ran targeted regression, full regression, and rolling-baseline archive generation before writing docs

## 2026-04-19

### Latest Update Round 5

- Added `app/core/services/provider_probe.py` and `app/tools/provider_probe.py`
- Reused provider readiness inside `startup_checks`
- Expanded `config/local.example.json` with probe and env override examples
- Added `app/core/services/ops_status.py`
- Updated `app/web/pages.py` and `app/web/static/styles.css` for denser ops status cards
- Normalized control characters in `app/core/utils/text.py`
- Improved legacy `.doc` quality handling in `app/core/parsers/doc_binary.py`, `app/core/parsers/service.py`, and `app/core/parsers/quality.py`
- Reworked `app/core/parsers/pdf_parser.py` to decode `ToUnicode` streams without new dependencies
- Added regression tests for provider probe, ops status, text cleanup, parse quality, and PDF extraction
- Re-ran real sample metrics, baseline comparison, sandbox probe, and full regression before closeout

### Latest Update Round 4

- 增加 3 个新工具：
  - `provider_sandbox`
  - `runtime_backup`
  - `metrics_baseline`
- `input_runner` 提炼出可复用的 `collect_metrics_bundle(...)`
- `/ops` 页面补充 backup / sandbox / baseline 命令入口
- 在真实运行目录上生成首个 backup 归档并完成 restore dry-run 预演
- 在 `docs/dev` 中生成结构化 baseline Markdown / JSON
- 修复 `runtime_backup` 在 Windows/GBK 终端的大输出编码问题

### Latest Update Round 3

- 进入 P10-P13 收口：
  - 为 legacy `.doc` 增加真实最小回归语料
  - 为 parse quality 增加 `review_reason_code` / `legacy_doc_bucket`
  - 浏览器级 E2E 改为真实 HTTP 链路
  - 收紧 `external_http` provider 契约
  - 新增 `runtime_cleanup` 工具
- 修复两类回归脆弱点：
  - 轻量 pytest runner 与标准 pytest 语法不完全兼容
  - Windows 下 SQLite 清库可能命中文件占用
- `/ops` 页面补充运行时清理命令入口：
  - `py -m app.tools.runtime_cleanup`

### Step 1

- 建立 `docs/dev/` 目录
- 建立开发总览、计划、todo、架构决策文档
- 确认前端参考资料来源于本地 `ui-ux-pro-max-skill`
- 确认 MVP 技术路线为 FastAPI + Jinja2 + 设计令牌样式

### Pending

- 实现 `app/` 结构
- 实现核心服务
- 接入 Web
- 跑测试并修复

### Step 2

- 读取本地 `ui-ux-pro-max-skill` 相关说明
- 提炼本轮 UI 约束：强层次、可访问、移动端优先、设计令牌化
- 因环境中 `pip` 安装失败，决定采用“本地 FastAPI 兼容层 + 本地 pytest 兼容层”完成 MVP 和测试回归

### Step 3

- 建立 `app/core/domain`、`app/core/services`、`app/core/parsers`、`app/core/reviewers`、`app/core/reports`、`app/core/pipelines`
- 实现两种 ZIP 导入模式
- 实现材料分类、解析、规则审查、Mock AI、报告渲染

### Step 4

- 建立 `app/api/main.py`
- 建立首页、Submission 详情页、Case 详情页、报告页
- 建立自定义样式系统

### Step 5

- 执行全量测试
- 首轮失败：源码乱码检测不够敏感
- 修复后重新测试

### Step 6

- 执行手动冒烟验证
- 发现中文文件名 ZIP 在 Windows 落盘失败
- 修复文件名清洗逻辑
- 再次回归后触发 Zip Slip 安全回归
- 补回原始路径穿越检测
- 最终测试全绿，页面主链路可用

### Step 7

- 把 `ui-ux-pro-max-skill` 整理为本地技能目录：`C:\Users\DOIT\.codex\skills\ui-ux-pro-max`
- 补充 `SKILL.md` 与 `agents/openai.yaml`
- 新增 Web 主路径自动化测试
- 新增 Windows 非法文件名 ZIP 回归测试
- 更新 `README.md`、`requirements.txt`、`docs/dev/` 文档，使当前 MVP 状态与运行方式完全对齐

### Step 8

- 用户反馈前端质感不足，启动一轮 UI 重构
- 使用 `ui-ux-pro-max-skill` 重新生成设计基线
- 选定 `Trust & Authority` + `Accessible & Ethical` 的工作台方向
- 重构首页、Submission、Case、Report 的信息架构
- 重写样式系统，切换到 `Lexend + Source Sans 3` 与海军蓝 / 文档灰 / 扫描蓝方案
- 保留现有测试契约并完成回归

### Step 9

- 用户进一步明确：前端目标不是官网或展示页，而是“管理系统一样的分析系统”
- 再次使用 `ui-ux-pro-max-skill` 检索 `Data-Dense Dashboard` 方向
- 前端整体切换为后台工作台结构：
  - 左侧导航
  - 顶部状态栏
  - KPI 指标卡
  - 数据表格
  - 风险面板
  - 报告阅读器
- 首页、批次页、Submission、Case、Report 全部改为后台分析视图

### Step 10

- 进入 P0：真实样本解析质量与 unknown 收敛阶段
- 修复 ZIP 中文文件名乱码恢复逻辑，支持 `cp437 -> utf-8` 与 `cp437 -> gb18030`
- 新增 parse quality 评估模块，并把质量元数据写入 parse result 与 material metadata
- 在 pipeline 中加入 low quality content gate，阻断低质量文本的错误自动分类
- 为每个材料补充 `triage` 信息：
  - `needs_manual_review`
  - `unknown_reason`
  - `review_recommendation`
- 在 Submission 页面新增 `Needs Review` 队列
- 增强 material report 与 input runner，方便后续人工纠错与真实样本回归

### Step 11

- 进入 P1-P2：人工纠错与 SQLite 最小持久化阶段
- 新增 `Correction` 数据模型与 `RuntimeStore.corrections`
- 实现人工纠错动作：
  - 改材料类型
  - 新建 case
  - 分配材料到 case
  - 合并 case
  - 重跑 review
- 在 Submission 页面新增 `Correction Audit` 面板
- 新增 SQLite repository：
  - submission graph 落盘
  - 应用启动恢复
  - correction 一并持久化

### Step 12

- 进入 P3-P4：补齐浏览器端 `Operator Console`
- 新增导出与打包服务：
  - 报告下载
  - 材料 raw / clean / desensitized / privacy 下载
  - submission bundle 下载
  - app log 下载
- 新增结构化日志服务，覆盖上传、纠偏、下载关键动作
- 在 Submission 页面增加：
  - `Operator Console`
  - `Export Center`
  - `Artifact Browser`
- 新增集成测试 `tests/integration/test_operator_console_and_exports.py`
- 修复本地 FastAPI 兼容层在下载响应上的两个兼容性缺口：
  - `media_type`
  - `content`

### Step 13

- 进入下一轮硬化：AI provider 边界与配置化
- 新增 `app/core/services/app_config.py`
- 在 AI service 中增加：
  - `resolve_case_ai_provider`
  - `safe_stub`
  - 非 mock provider 脱敏强校验
- 在隐私模块中增加：
  - `AI_SAFE_POLICY`
  - `llm_safe`
  - `is_ai_safe_case_payload`
- 让 pipeline / correction 重建流程都走配置驱动 provider 解析
- 启动入口改为从配置读取 host / port
- 新增配置与 AI 边界单测，并通过真实样本 `safe_stub` 烟测

### Step 14

- 继续推进 P5-P8：
  - 把 legacy `.doc` 收敛结果正式落盘
  - 补齐浏览器端导入摘要、模式 B 指导、操作台预填
  - 增加 `Support / Ops` 页面
  - 增加真实 provider adapter skeleton
- 扩展 `AppConfig`，加入：
  - `sqlite_path`
  - `log_path`
  - `retention_days`
  - `ai_endpoint`
  - `ai_model`
  - `ai_api_key_env`
  - `ai_fallback_to_mock`
- 让 SQLite、日志、上传目录开始跟配置对齐

### Step 15

- 新增 `app/core/services/startup_checks.py`
- 启动时执行自检并记录结果
- 新增 `config/local.example.json`
- `Support / Ops` 页面集中展示：
  - 自检状态
  - 当前配置
  - 日志下载
  - 运行时保留策略
  - 常用验证命令

### Step 16

- AI review 层新增 `app/core/reviewers/ai/adapters.py`
- 新增 `external_http` adapter skeleton
- provider 调用增加：
  - started log
  - completed log
  - failed log
  - fallback to mock
- `ReviewResult` 扩展为规则结论和 AI 补充说明分层保存

### Step 17

- 首页新增运行摘要与模式 B 批量导入指导
- Submission 页新增：
  - `Import Digest`
  - review queue `quality_flags`
  - 操作台预填和提示文本
- Case 页新增 `AI Supplement`
- `input_runner` 新增聚合摘要
