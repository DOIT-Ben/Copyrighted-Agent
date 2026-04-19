# P14-P16 构建日志

## 日期

- 2026-04-19

## Step 1

- 新增本地 provider sandbox：`app/tools/provider_sandbox.py`
- 能力：
  - 标准 `external_http` request/response 契约联调
  - `success / missing_summary / invalid_json / http_error` 四种模式
  - 可选 bearer token 校验
  - 可选 JSONL 请求日志
  - 严格校验 `llm_safe` 与 desensitized payload

## Step 2

- 新增 provider sandbox 单元与集成测试：
  - `tests/unit/test_provider_sandbox_contracts.py`
  - `tests/integration/test_provider_sandbox_flow.py`
- 集成测试直接用真实本地 HTTP 服务调用 `generate_case_ai_review(...)`。

## Step 3

- 新增 runtime 备份/恢复工具：`app/tools/runtime_backup.py`
- 能力：
  - `create`
  - `inspect`
  - `restore`
  - SQLite 优先使用 `sqlite3.backup()` 做快照
  - restore 默认 dry-run，可显式 `--apply`
  - restore 目标路径强约束在给定 target root 内

## Step 4

- 新增 runtime backup 测试：
  - `tests/unit/test_runtime_backup_contracts.py`
- 覆盖：
  - 归档 manifest
  - SQLite 快照
  - restore 到新目录

## Step 5

- 新增趋势基线工具：`app/tools/metrics_baseline.py`
- 复用 `input_runner` 的聚合逻辑，提供：
  - 多目标基线快照
  - 与历史 snapshot 的 delta 对比
  - Markdown / JSON 双产物
- `input_runner` 提炼出 `collect_metrics_bundle(...)`，成为可复用的聚合入口。

## Step 6

- 新增基线测试：
  - `tests/unit/test_metrics_baseline_contracts.py`
  - `tests/integration/test_metrics_baseline_flow.py`

## Step 7

- `/ops` 页面加入 3 个新命令入口：
  - `py -m app.tools.runtime_backup create`
  - `py -m app.tools.provider_sandbox --port 8010`
  - `py -m app.tools.metrics_baseline ...`

## Step 8

- 在真实运行目录上生成首个 runtime 备份：
  - `data/backups/runtime_backup_20260419_2219.zip`
  - 大小约 `424308251` bytes
- 同时生成真实样本基线：
  - `docs/dev/54-real-sample-baseline.md`
  - `docs/dev/55-real-sample-baseline.json`

## Step 9

- 修复 `runtime_backup` 在 Windows/GBK 终端下的输出编码问题。
- 顺手把 `inspect` 和 `restore` 默认输出压缩为摘要，避免大归档直接刷屏。
