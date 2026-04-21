# Runbook

## Latest Update 2026-04-20 Round 13

## Delivery Scripts

Use the script wrappers when you want repeatable local startup without manually retyping env overrides:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_mock_web.ps1
powershell -ExecutionPolicy Bypass -File scripts\start_real_bridge.ps1
powershell -ExecutionPolicy Bypass -File scripts\start_real_web.ps1 -Port 18080
powershell -ExecutionPolicy Bypass -File scripts\restart_real_stack.ps1
powershell -ExecutionPolicy Bypass -File scripts\run_real_validation.ps1
powershell -ExecutionPolicy Bypass -File scripts\show_stack_status.ps1
```

If you want the fastest clean restart without stale processes on `8000`, `18011`, or `18080`, use:

```powershell
$env:MINIMAX_API_KEY='your-key'
powershell -ExecutionPolicy Bypass -File scripts\restart_real_stack.ps1
```

Or pass the key inline for the current shell only:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\restart_real_stack.ps1 -ApiKey 'your-key'
```

Recommended execution order for a real run:

1. Export `MINIMAX_API_KEY`
2. Start `scripts\start_real_bridge.ps1`
3. Start `scripts\start_real_web.ps1 -Port 18080`
4. Run `scripts\run_real_validation.ps1`

`scripts\run_real_validation.ps1` now auto-resolves the default Mode A ZIP and Mode B sample directory under `input\` when explicit paths are not provided.

These wrappers are now the preferred operator-facing entrypoints. The raw module commands remain valid and are still documented below.

## Latest Update 2026-04-20 Round 12

## Validated MiniMax Bridge Path

Validated on 2026-04-20 with:

- upstream base URL: `https://api.minimaxi.com/v1`
- upstream model: `MiniMax-M2.7-highspeed`
- local bridge endpoint: `http://127.0.0.1:18011/review`
- API key source: `MINIMAX_API_KEY`

Bridge startup:

```bash
py -m app.tools.minimax_bridge --port 18011 --upstream-base-url https://api.minimaxi.com/v1 --upstream-model MiniMax-M2.7-highspeed --upstream-api-key-env MINIMAX_API_KEY
```

Live validation env overrides:

```powershell
$env:SOFT_REVIEW_AI_ENABLED='true'
$env:SOFT_REVIEW_AI_PROVIDER='external_http'
$env:SOFT_REVIEW_AI_ENDPOINT='http://127.0.0.1:18011/review'
$env:SOFT_REVIEW_AI_MODEL='MiniMax-M2.7-highspeed'
$env:SOFT_REVIEW_AI_API_KEY_ENV='MINIMAX_API_KEY'
```

Validated release command:

```bash
py -m app.tools.release_validation --config config\local.json --mode-a-path input\软著材料\2501_软著材料.zip --mode-b-path input\合作协议 --json
```

Expected validated state:

- `release_validation status=pass`
- `provider_probe=ok`
- `release_gate=pass`
- `mode_a_smoke=pass`
- `mode_b_smoke=pass`

## Latest Update 2026-04-20 Round 11

## One-Command Real Provider Validation

After real provider config is ready, run:

```bash
py -m app.tools.release_validation --config config\local.json --mode-a-path input\软著材料\2501_软著材料.zip --mode-b-path input\合作协议
```

Expected pass state:

- `release_validation status=pass`
- `provider_probe=ok`
- `release_gate=pass`
- `mode_a_smoke=pass`
- `mode_b_smoke=pass`

Verified command text for current workspace:

```bash
py -m app.tools.release_validation --config config\local.json --mode-a-path input\软著材料\2501_软著材料.zip --mode-b-path input\合作协议
```

Latest artifacts:

```text
docs/dev/real-provider-validation-latest.json
docs/dev/real-provider-validation-latest.md
docs/dev/history/real_provider_validation_YYYYMMDD_HHMMSS.json
docs/dev/history/real_provider_validation_YYYYMMDD_HHMMSS.md
```

## Current Local Default Snapshot

As of 2026-04-20, this workspace now has a validated real-provider-ready local config:

- `config/local.json` uses `ai_provider=external_http`
- `ai_enabled=true`
- `ai_endpoint=http://127.0.0.1:18011/review`
- `ai_model=MiniMax-M2.7-highspeed`
- `ai_api_key_env=MINIMAX_API_KEY`

Normal local work can still use `scripts\start_mock_web.ps1`, while real validation can use the bridge-backed script flow above.

## Active Config Path

The current MVP live-provider flow reads from:

- `config/local.json`
- `SOFT_REVIEW_*` environment overrides

Do not treat `config/settings.py` as the active provider config source for this flow. That file is legacy and is not what `provider_probe`, `release_gate`, or `release_validation` read.

## Latest Update 2026-04-20 Round 8

## Default Local Startup

For the least-friction local boot, use the script wrappers instead of manually juggling env overrides:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_mock_web.ps1
```

Or, if you want to rely on the current `config/local.json` directly:

```bash
py -m app.api.main
```

Expected default local address:

```text
http://127.0.0.1:8000
```

## Current Provider Status

Check the current probe and release-gate state against the local config:

```bash
py -m app.tools.provider_probe --config config\local.json
py -m app.tools.release_gate --config config\local.json
```

Expected status on 2026-04-20:

- `provider_probe status=ok`
- `phase=mock_mode`
- `release_gate status=warning`
- warnings remain only because real external-provider smoke has not been configured yet

## Windows Source-Safety Note

If you must edit a UTF-8 Python source file on Windows, avoid full-file `Get-Content` / `Set-Content` rewrites unless you control encoding explicitly. The preferred recovery-safe path in this repo is:

1. back up the current file
2. use `apply_patch` for code edits
3. run `py -m py_compile`
4. run targeted regression before full regression

## Latest Update 2026-04-20 Round 7

## Sandbox-First Provider Probe

Use a local sandbox before any real gateway smoke, and force the PowerShell job to enter the repository root:

```powershell
$repo = (Get-Location).Path
$job = Start-Job -ArgumentList $repo -ScriptBlock { param($repoPath) Set-Location $repoPath; py -m app.tools.provider_sandbox --port 18010 --request-log-path data/runtime/logs/provider_probe_sandbox_round6.jsonl --once }
Start-Sleep -Seconds 1
py -m app.tools.provider_probe --enable-ai --provider external_http --endpoint http://127.0.0.1:18010/review --model sandbox-model --probe
Receive-Job $job -Wait -AutoRemoveJob
```

Expected successful outcome on 2026-04-20:

- CLI prints `provider_probe status=ok`
- phase becomes `probe_passed`
- HTTP status is `200`
- latest result is persisted to `data/runtime/ops/provider_probe_latest.json`

## Latest Probe Artifact

Inspect the most recent persisted probe summary:

```bash
type data\runtime\ops\provider_probe_latest.json
```

Use this artifact to confirm the latest:

- readiness phase
- probe phase
- endpoint / model used for the safe smoke
- remediation text when the probe fails or is blocked

## Real Provider Environment Gate

A real non-sandbox probe remains blocked until all of the following exist locally:

- `config/local.json`
- `ai_provider=external_http`
- a real `ai_endpoint`
- a real `ai_model`
- an API-key environment mapping when authentication is required
- desensitized-only boundary still enabled

If these are missing, stop at the sandbox-first probe and keep the validation classified as environment-blocked rather than code-blocked.

## Latest Update 2026-04-19 Round 6

## Rolling Baseline

Capture a new baseline, auto-compare it with the latest baseline found under `docs/dev`, and archive timestamped copies:

```bash
py -m app.tools.metrics_baseline --compare-latest-in-dir docs\dev --archive-dir docs\dev\history --archive-stem real-sample-baseline
```

Expected outcome on 2026-04-19:

- archive files created under `docs/dev/history`
- mode A remains `needs_review=0 / low_quality=0`
- mode B remains `needs_review=0 / low_quality=0`
- deltas are shown in `/ops` under `Trend Watch` and `Latest Baseline`

## Real Provider Smoke Gate

Before attempting a real non-sandbox provider smoke, verify all of the following:

- `config/local.json` exists locally
- `ai_provider`, `ai_endpoint`, and `ai_model` are set
- the configured API-key environment variable is present
- `ai_require_desensitized` remains enabled
- `Provider Checklist` on `/ops` shows no blocking warnings

## Provider Probe

Validate external provider readiness without sending raw user data:

```bash
py -m app.tools.provider_probe
```

Probe a local sandbox with a safe synthetic payload:

```powershell
$job = Start-Job -ScriptBlock { py -m app.tools.provider_sandbox --port 18010 --request-log-path data/runtime/logs/provider_probe_sandbox.jsonl --once }
Start-Sleep -Seconds 1
py -m app.tools.provider_probe --enable-ai --provider external_http --endpoint http://127.0.0.1:18010/review --model sandbox-model --probe
```

Notes:

- `provider_probe` only sends a synthetic `llm_safe` payload.
- If a fixed port is unavailable locally, switch to any open port.
- Real gateway smoke should only happen after sandbox probe passes.

## Runtime Cleanup

默认仅做检查，不做删除：

```bash
py -m app.tools.runtime_cleanup
```

如需机器可读输出：

```bash
py -m app.tools.runtime_cleanup --json
```

如需执行删除：

```bash
py -m app.tools.runtime_cleanup --apply
```

说明：

- 自动清理范围仅限 `data/runtime/submissions`、`data/runtime/uploads`、`data/runtime/logs`
- 当前 active log 不会被自动删除
- `soft_review.db` 不会被自动删除，只会给出人工备份建议

## Runtime Backup

创建 runtime 归档：

```bash
py -m app.tools.runtime_backup create --output data\backups\runtime_backup_latest.zip
```

查看归档摘要：

```bash
py -m app.tools.runtime_backup inspect --archive data\backups\runtime_backup_latest.zip
```

恢复预演到新目录：

```bash
py -m app.tools.runtime_backup restore --archive data\backups\runtime_backup_latest.zip --target data\restore_preview\runtime_backup_latest
```

说明：

- `restore` 默认 dry-run，不会直接写入
- 若要实际恢复，再加 `--apply`
- 建议不要直接对活跃 `data/runtime` 做 restore，优先恢复到新目录做检查

## Provider Sandbox

启动本地联调沙箱：

```bash
py -m app.tools.provider_sandbox --port 8010 --request-log-path data\runtime\logs\provider_sandbox.jsonl
```

常用模式：

- `--mode success`
- `--mode http_error`
- `--mode missing_summary`
- `--mode invalid_json`

## Metrics Baseline

生成真实样本基线：

```bash
py -m app.tools.metrics_baseline --markdown-path docs\dev\54-real-sample-baseline.md --json-path docs\dev\55-real-sample-baseline.json
```

如需比较上一份基线：

```bash
py -m app.tools.metrics_baseline --compare docs\dev\55-real-sample-baseline.json
```

Final comparison artifact for this round:

```bash
py -m app.tools.metrics_baseline --compare docs\dev\55-real-sample-baseline.json --markdown-path docs\dev\56-real-sample-baseline-compare.md --json-path docs\dev\57-real-sample-baseline-compare.json
```

## Start The MVP Site

在项目根目录执行：

```bash
py -m app.api.main
```

默认地址：

```text
http://127.0.0.1:8000
```


## Run Tests

在项目根目录执行：

```bash
py -m pytest
```

说明：

- 当前环境中无法通过 `pip` 正常安装官方 pytest
- 本项目为当前阶段提供了一个本地轻量兼容运行器
- 因此 `py -m pytest` 仍可执行现有测试契约

## Use The UI Skill

前端设计检索命令：

```bash
py C:\Users\DOIT\.codex\skills\ui-ux-pro-max\scripts\search.py "document review accessibility enterprise dashboard trust" --design-system -p "Soft Copyright Review Desk" -f markdown
```

适用场景：

- 新页面设计
- 组件重构
- 配色 / 字体 / 版式选择
- UI 审查与体验优化


## Recommended Smoke Test

1. 打开首页
2. 选择导入模式
3. 上传一个 ZIP
4. 查看 Submission 页面
5. 点击进入 Case 页面
6. 打开报告页面


## Current Limitations

- 运行时数据主要保存在内存与 `data/runtime/`
- 暂无用户体系
- 暂无真实数据库
- 暂无真实 AI 供应商接入
- `.doc` / `.pdf` 解析仍是 MVP 级 best-effort 实现
- 技能目录已接入，但 `quick_validate.py` 因环境缺少 `yaml` 未完成脚本级校验

## AI Boundary Config

默认不需要任何额外配置，系统会继续使用本地 `mock`。

可选环境变量：

```bash
SOFT_REVIEW_HOST=127.0.0.1
SOFT_REVIEW_PORT=8000
SOFT_REVIEW_AI_ENABLED=false
SOFT_REVIEW_AI_PROVIDER=mock
SOFT_REVIEW_AI_REQUIRE_DESENSITIZED=true
SOFT_REVIEW_AI_TIMEOUT_SECONDS=30
```

本地验证非 mock 边界：

```powershell
$env:SOFT_REVIEW_AI_ENABLED='true'
$env:SOFT_REVIEW_AI_PROVIDER='safe_stub'
py -m app.tools.input_runner --path input\软著材料\2501_软著材料.zip --mode single_case_package
```

## Operator Smoke Test

1. 打开首页并上传一个 ZIP。
2. 进入 Submission 详情页，确认能看到 `Operator Console`。
3. 执行一次 `change type` 或 `rerun review`。
4. 在 `Export Center` 下载报告或 submission bundle。
5. 在 `Artifact Browser` 预览 desensitized / privacy 产物。
6. 下载 `/downloads/logs/app`，确认本轮操作已有结构化日志。

## Real Sample Validation

```bash
py -m app.tools.input_runner --path input\软著材料 --mode single_case_package
py -m app.tools.input_runner --path input\合作协议 --mode batch_same_material
```
