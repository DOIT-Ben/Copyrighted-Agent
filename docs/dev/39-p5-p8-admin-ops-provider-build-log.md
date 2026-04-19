# P5-P8 构建日志

## 日期

- 2026-04-19

## Step 1 基线确认

- 重新执行真实样本：
  - `input\软著材料`
  - `input\合作协议`
- 确认 legacy `.doc` 收敛后，模式 A 六个真实 ZIP 均不再出现 `unknown`。
- 确认模式 B 的合作协议批量导入仍稳定。

## Step 2 配置与运维骨架

- 扩展 `AppConfig`：
  - `sqlite_path`
  - `log_path`
  - `retention_days`
  - `ai_endpoint`
  - `ai_model`
  - `ai_api_key_env`
  - `ai_fallback_to_mock`
- 让日志与 SQLite 读取配置路径，而不是只写死默认位置。
- 新增 `startup_checks.py`，提供统一启动自检报告。
- 新增 `config/local.example.json` 作为配置模板。

## Step 3 Provider Skeleton

- 新增 `app/core/reviewers/ai/adapters.py`
- 保留当前 `mock` 与 `safe_stub`
- 新增 `external_http` adapter skeleton：
  - 只接受脱敏 payload
  - 支持 endpoint / model / timeout / api key env 配置
  - 网络失败时可按配置 fallback 到 `mock`
- 在 AI service 增加：
  - provider call started log
  - provider call completed log
  - provider call failed log

## Step 4 Review 结果分层

- 扩展 `ReviewResult`：
  - `rule_conclusion`
  - `ai_summary`
  - `ai_provider`
  - `ai_resolution`
- Case 页不再把规则结论和 AI 补充说明混在一起。
- Case markdown 报告新增：
  - `规则结论`
  - `AI 补充说明`

## Step 5 管理台页面增强

- 首页新增：
  - 运行摘要
  - 模式 B 批量导入指导
  - 更明确的模式说明和 ZIP 优先提示
- Submission 页新增：
  - `Import Digest`
  - review queue 的 `quality_flags`
  - 操作台预填 Case 名称 / 版本 / 公司名 / 建议材料 ID
  - 更具体的操作提示文案
- 新增 `Support / Ops` 页面：
  - 启动自检
  - 当前配置
  - 日志下载
  - 运行时保留策略
  - 常用验证命令

## Step 6 命令行验证体验

- `app.tools.input_runner` 增加聚合摘要：
  - `packages`
  - `unknown`
  - `needs_review`
  - `low_quality`
  - `redactions`

## Step 7 测试补齐

- 新增：
  - `tests/unit/test_startup_self_check_contracts.py`
  - `tests/unit/test_input_runner_contracts.py`
- 扩展：
  - `tests/unit/test_ai_provider_boundary_contracts.py`
  - `tests/unit/test_report_contracts.py`
  - `tests/integration/test_operator_console_and_exports.py`
  - `tests/integration/test_web_mvp_contracts.py`
