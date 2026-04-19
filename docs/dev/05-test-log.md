# Test Log

## Latest Update 2026-04-20 Round 12

### Compile Check 31

- Date: 2026-04-20
- Goal: validate the new MiniMax bridge implementation and its tests compile cleanly
- Command: `py -m py_compile app\tools\minimax_bridge.py tests\unit\test_minimax_bridge_contracts.py tests\integration\test_minimax_bridge_flow.py`
- Result: passed

### Test Run 35

- Date: 2026-04-20
- Goal: validate the MiniMax bridge contract layer and fake-upstream integration flow
- Command: `py -m pytest tests\unit\test_minimax_bridge_contracts.py tests\integration\test_minimax_bridge_flow.py`
- Result:
  - the local lightweight pytest runner executed the full suite instead of only the requested subset
  - `131 passed, 0 failed`

### Live Provider Probe 20

- Date: 2026-04-20
- Goal: validate MiniMax real-provider reachability through the local bridge before spending a full smoke run
- Command:
  - `py -m app.tools.minimax_bridge --port 18011 --upstream-base-url https://api.minimaxi.com/v1 --upstream-model MiniMax-M2.7-highspeed --upstream-api-key-env MINIMAX_API_KEY`
  - `py -m app.tools.provider_probe --config config\local.json --probe`
  - with env overrides:
    - `SOFT_REVIEW_AI_ENABLED=true`
    - `SOFT_REVIEW_AI_PROVIDER=external_http`
    - `SOFT_REVIEW_AI_ENDPOINT=http://127.0.0.1:18011/review`
    - `SOFT_REVIEW_AI_MODEL=MiniMax-M2.7-highspeed`
    - `SOFT_REVIEW_AI_API_KEY_ENV=MINIMAX_API_KEY`
- Result:
  - `provider_probe status=ok`
  - `phase=probe_passed`
  - HTTP `200`
  - real MiniMax request completed successfully through the bridge

### Real Provider Validation Status 20

- Date: 2026-04-20
- Goal: run the full release validation flow against the real MiniMax model through the local bridge
- Command:
  - `py -m app.tools.minimax_bridge --port 18011 --upstream-base-url https://api.minimaxi.com/v1 --upstream-model MiniMax-M2.7-highspeed --upstream-api-key-env MINIMAX_API_KEY`
  - `py -m app.tools.release_validation --config config\local.json --mode-a-path input\软著材料\2501_软著材料.zip --mode-b-path input\合作协议 --json`
  - with env overrides:
    - `SOFT_REVIEW_AI_ENABLED=true`
    - `SOFT_REVIEW_AI_PROVIDER=external_http`
    - `SOFT_REVIEW_AI_ENDPOINT=http://127.0.0.1:18011/review`
    - `SOFT_REVIEW_AI_MODEL=MiniMax-M2.7-highspeed`
    - `SOFT_REVIEW_AI_API_KEY_ENV=MINIMAX_API_KEY`
- Result:
  - overall `status=pass`
  - `provider_probe=ok`
  - `release_gate=pass`
  - `mode_a_smoke=pass`
  - `mode_b_smoke=pass`
  - `mode_a_smoke.review_provider=external_http`
  - `mode_a_smoke.review_resolution=minimax_bridge_success`
  - latest artifacts refreshed at:
    - `docs/dev/real-provider-validation-latest.json`
    - `docs/dev/real-provider-validation-latest.md`
    - timestamped history artifacts under `docs/dev/history`

## Latest Update 2026-04-20 Round 11

### Compile Check 29

- Date: 2026-04-20
- Goal: validate the new release-validation service, CLI, and tests compile cleanly
- Command: `py -m py_compile app\core\services\release_validation.py app\tools\release_validation.py tests\unit\test_release_validation_contracts.py tests\integration\test_release_validation_flow.py`
- Result: passed

### Test Run 32

- Date: 2026-04-20
- Goal: validate release-validation contracts, sandbox success flow, and adjacent provider gate coverage
- Command: `py -m pytest tests\unit\test_release_validation_contracts.py tests\integration\test_release_validation_flow.py tests\unit\test_release_gate_contracts.py tests\integration\test_provider_probe_flow.py`
- Result:
  - the local lightweight pytest runner executed the full suite instead of only the requested subset
  - `127 passed, 0 failed`

### Real Provider Validation Status 17

- Date: 2026-04-20
- Goal: run the new one-command release validation flow against the current local workspace
- Command: `py -m app.tools.release_validation --config config\local.json --mode-a-path input\软著材料\2501_软著材料.zip --mode-b-path input\合作协议 --json`
- Result:
  - overall `status=blocked`
  - `provider_probe=skipped`
  - `release_gate=warning`
  - current blocker is still local mock config, not code regression
  - artifacts written to:
    - `docs/dev/real-provider-validation-latest.json`
    - `docs/dev/real-provider-validation-latest.md`
    - timestamped history artifacts under `docs/dev/history`

### Test Run 33

- Date: 2026-04-20
- Goal: final full regression after adding the real-provider validation slice
- Command: `py -m pytest`
- Result: `127 passed, 0 failed`

### Compile Check 30

- Date: 2026-04-20
- Goal: validate the release-validation artifact self-description fix compiles cleanly
- Command: `py -m py_compile app\core\services\release_validation.py app\tools\release_validation.py tests\unit\test_release_validation_contracts.py tests\integration\test_release_validation_flow.py`
- Result: passed

### Real Provider Validation Status 18

- Date: 2026-04-20
- Goal: rerun the one-command release validation flow after the artifact self-description fix
- Command: `py -m app.tools.release_validation --config config\local.json --mode-a-path input\软著材料\2501_软著材料.zip --mode-b-path input\合作协议 --json`
- Result:
  - overall `status=blocked`
  - `provider_probe=skipped`
  - `release_gate=warning`
  - latest JSON now includes non-empty `artifacts` metadata pointing to the latest files and timestamped history artifacts under `docs/dev/history`
  - current blocker remains local mock config, not code regression

### Test Run 34

- Date: 2026-04-20
- Goal: final full regression after the artifact self-description fix and validation rerun
- Command: `py -m pytest`
- Result: `127 passed, 0 failed`

### Real Provider Validation Status 19

- Date: 2026-04-20
- Goal: confirm the current live start attempt still blocks only on real provider inputs
- Command: `py -m app.tools.release_validation --config config\local.json --mode-a-path input\软著材料\2501_软著材料.zip --mode-b-path input\合作协议 --json`
- Result:
  - overall `status=blocked`
  - `provider_probe=skipped`
  - `release_gate=warning`
  - `config/local.json` still uses `ai_enabled=false` and `ai_provider=mock`
  - no `SOFT_REVIEW_*` environment variables are present locally
  - latest artifacts refreshed at:
    - `docs/dev/real-provider-validation-latest.json`
    - `docs/dev/real-provider-validation-latest.md`
    - timestamped history artifacts under `docs/dev/history`
  - conclusion: the current blocker is still missing real endpoint, model, and credential mapping, not code readiness

## Latest Update 2026-04-20 Round 10

### Provider Readiness Audit 16

- Date: 2026-04-20
- Goal: determine whether real provider smoke can resume in this round
- Command:
  - `Get-Content -Raw config\local.json`
  - `Get-ChildItem Env:SOFT_REVIEW*`
- Result:
  - `config/local.json` still sets `ai_enabled=false`
  - `ai_provider=mock`
  - `ai_endpoint`, `ai_model`, and `ai_api_key_env` are empty
  - no `SOFT_REVIEW_*` environment variables are present locally
  - conclusion: real-provider smoke remains environment-blocked

### Compile Check 28

- Date: 2026-04-20
- Goal: validate the new web-source contract test compiles cleanly after the ASCII-safe mojibake-marker refactor
- Command: `py -m py_compile tests\unit\test_web_source_contracts.py`
- Result: passed

### Test Run 30

- Date: 2026-04-20
- Goal: validate new `app/web` contributor docs and web-source safety contracts alongside active HTML flows
- Command: `py -m pytest tests\unit\test_web_source_contracts.py tests\integration\test_web_mvp_contracts.py tests\integration\test_operator_console_and_exports.py tests\e2e\test_browser_workflows.py`
- Result:
  - the local lightweight pytest runner executed the full suite instead of only the requested subset
  - `124 passed, 0 failed`

### Test Run 31

- Date: 2026-04-20
- Goal: final full regression after adding page-layer contributor and encoding guardrails
- Command: `py -m pytest`
- Result: `124 passed, 0 failed`

## Latest Update 2026-04-20 Round 9

### Compile Check 27

- Date: 2026-04-20
- Goal: validate the new modular page-renderer structure
- Command: `py -m py_compile app\web\view_helpers.py app\web\page_home.py app\web\page_submission.py app\web\page_case.py app\web\page_report.py app\web\page_ops.py app\web\pages.py app\api\main.py`
- Result: passed

### Test Run 28

- Date: 2026-04-20
- Goal: validate modular page renderers against HTML flows, `/ops`, manual-correction actions, and browser E2E
- Command: `py -m pytest tests\integration\test_web_mvp_contracts.py tests\integration\test_operator_console_and_exports.py tests\integration\test_manual_correction_api.py tests\e2e\test_browser_workflows.py`
- Result: `121 passed, 0 failed`

### Test Run 29

- Date: 2026-04-20
- Goal: final full regression after page-layer modularization
- Command: `py -m pytest`
- Result: `121 passed, 0 failed`

## Latest Update 2026-04-20 Round 8

### Compile Check 24

- Date: 2026-04-20
- Goal: verify new provider-gate code and rebuilt page renderers compile cleanly
- Command: `py -m py_compile app\core\services\provider_probe.py app\core\services\release_gate.py app\tools\provider_probe.py app\tools\release_gate.py app\api\main.py app\web\pages.py`
- Result: passed

### Targeted Regression 25

- Date: 2026-04-20
- Goal: validate rebuilt page renderers, `/ops`, manual-correction flows, browser E2E, and updated startup self-check expectations
- Command: `py -m pytest tests\integration\test_web_mvp_contracts.py tests\integration\test_operator_console_and_exports.py tests\integration\test_manual_correction_api.py tests\e2e\test_browser_workflows.py tests\unit\test_startup_self_check_contracts.py`
- Result:
  - first pass exposed only the intentional old startup-self-check assumptions
  - after updating those contracts: `119 passed, 0 failed`

### Provider Probe Status 14

- Date: 2026-04-20
- Goal: capture the current mock-safe provider probe state after `config/local.json` bootstrap
- Command: `py -m app.tools.provider_probe --config config\local.json`
- Result:
  - `status=ok`
  - `phase=mock_mode`
  - latest artifact persisted to `data\runtime\ops\provider_probe_latest.json`

### Release Gate Status 15

- Date: 2026-04-20
- Goal: capture the current environment promotion status after local-config bootstrap
- Command: `py -m app.tools.release_gate --config config\local.json`
- Result:
  - `status=warning`
  - `mode=mock_local`
  - local config passes
  - remaining warnings are limited to expected mock-mode / no real smoke-yet items

### Test Run 26

- Date: 2026-04-20
- Goal: final full regression after page-module rebuild and startup-self-check contract update
- Command: `py -m pytest`
- Result: `121 passed, 0 failed`

## Latest Update 2026-04-20 Round 7

### Test Run 22

- Date: 2026-04-19
- Goal: validate provider readiness phases, startup self-check integration, probe artifact persistence, and `/ops` observability blocks
- Command: `py -m pytest tests\unit\test_provider_probe_contracts.py tests\unit\test_startup_self_check_contracts.py tests\integration\test_provider_probe_flow.py tests\integration\test_operator_console_and_exports.py`
- Result: `115 passed, 0 failed`

### Sandbox Probe Smoke 13

- Date: 2026-04-20
- Goal: validate a live sandbox-first provider probe with synthetic safe payload only
- Command:
  - `$repo = (Get-Location).Path`
  - `$job = Start-Job -ArgumentList $repo -ScriptBlock { param($repoPath) Set-Location $repoPath; py -m app.tools.provider_sandbox --port 18010 --request-log-path data/runtime/logs/provider_probe_sandbox_round6.jsonl --once }`
  - `Start-Sleep -Seconds 1`
  - `py -m app.tools.provider_probe --enable-ai --provider external_http --endpoint http://127.0.0.1:18010/review --model sandbox-model --probe`
- Result:
  - `status=ok`
  - `phase=probe_passed`
  - `http_status=200`
  - `provider_request_id=sandbox-054a95a3`
  - latest artifact written to `data/runtime/ops/provider_probe_latest.json`

### Real Sample Smoke 13

- Date: 2026-04-20
- Goal: refresh rolling baseline history after provider observability changes
- Command: `py -m app.tools.metrics_baseline --compare-latest-in-dir docs\dev --archive-dir docs\dev\history --archive-stem real-sample-baseline`
- Result:
  - generated_at `2026-04-20T00:16:31`
  - mode A `materials=24 cases=6 reports=6 unknown=0 needs_review=0 low_quality=0 redactions=252`
  - mode B `materials=11 cases=11 reports=1 unknown=0 needs_review=0 low_quality=0 redactions=152`
  - archive files written:
    - `docs/dev/history/real-sample-baseline_20260420_001631.json`
    - `docs/dev/history/real-sample-baseline_20260420_001631.md`

### Test Run 23

- Date: 2026-04-20
- Goal: final full regression after implementation closeout for the provider readiness and probe observability slice
- Command: `py -m pytest`
- Result: `115 passed, 0 failed`

## Latest Update 2026-04-19 Round 6

### Test Run 20

- Date: 2026-04-19
- Goal: validate rolling baseline helpers, ops status contracts, and updated `/ops` rendering assertions
- Command: `py -m pytest tests\unit\test_metrics_baseline_contracts.py tests\unit\test_ops_status_contracts.py tests\integration\test_operator_console_and_exports.py`
- Result: `113 passed, 0 failed`

### Test Run 21

- Date: 2026-04-19
- Goal: final full regression after trend-watch and rolling-baseline UI integration
- Command: `py -m pytest`
- Result: `113 passed, 0 failed`

### Real Sample Smoke 12

- Date: 2026-04-19
- Goal: validate rolling baseline auto-compare and timestamped archive generation
- Command: `py -m app.tools.metrics_baseline --compare-latest-in-dir docs\dev --archive-dir docs\dev\history --archive-stem real-sample-baseline`
- Result:
  - generated_at `2026-04-19T23:23:30`
  - mode A `materials=24 cases=6 reports=6 unknown=0 needs_review=0 low_quality=0 redactions=252`
  - mode B `materials=11 cases=11 reports=1 unknown=0 needs_review=0 low_quality=0 redactions=152`
  - archive files written:
    - `docs/dev/history/real-sample-baseline_20260419_232330.json`
    - `docs/dev/history/real-sample-baseline_20260419_232330.md`

## Policy

## Latest Update 2026-04-19 Round 5

### Test Run 16

- Date: 2026-04-19
- Goal: validate provider readiness service, CLI probe flow, and startup-check integration
- Command: `py -m pytest tests\unit\test_provider_probe_contracts.py tests\unit\test_startup_self_check_contracts.py tests\integration\test_provider_probe_flow.py`
- Result: passed

### Test Run 17

- Date: 2026-04-19
- Goal: validate ops status discovery and `/ops` dashboard additions
- Command: `py -m pytest tests\unit\test_ops_status_contracts.py tests\integration\test_operator_console_and_exports.py`
- Result: passed

### Test Run 18

- Date: 2026-04-19
- Goal: validate parser hardening for legacy `.doc` and PDF extraction
- Command: `py -m pytest tests\integration\test_legacy_doc_corpus_regression.py tests\unit\test_text_utils_contracts.py tests\unit\test_pdf_parser_regression.py tests\unit\test_parse_quality_contracts.py`
- Result: passed

### Real Sample Smoke 8

- Date: 2026-04-19
- Command: `py -m app.tools.input_runner --path input\软著材料 --mode single_case_package`
- Result: `packages=6 materials=24 cases=6 reports=6 unknown=0 needs_review=0 low_quality=0 redactions=252`

### Real Sample Smoke 9

- Date: 2026-04-19
- Command: `py -m app.tools.input_runner --path input\合作协议 --mode batch_same_material`
- Result: `materials=11 cases=11 reports=1 needs_review=0 low_quality=0 redactions=152`

### Real Sample Smoke 10

- Date: 2026-04-19
- Command: `py -m app.tools.metrics_baseline --compare docs\dev\55-real-sample-baseline.json --markdown-path docs\dev\56-real-sample-baseline-compare.md --json-path docs\dev\57-real-sample-baseline-compare.json`
- Result:
  - mode A `needs_review -10`
  - mode A `low_quality -10`
  - mode B `needs_review -2`
  - mode B `low_quality -2`

### Real Sample Smoke 11

- Date: 2026-04-19
- Goal: validate end-to-end CLI probe against live sandbox
- Command: `py -m app.tools.provider_probe --enable-ai --provider external_http --endpoint http://127.0.0.1:18010/review --model sandbox-model --probe`
- Result: readiness `ok`, probe `ok`, HTTP `200`

### Test Run 19

- Date: 2026-04-19
- Goal: final full regression for P17-P22 closeout
- Command: `py -m pytest`
- Result: `110 passed, 0 failed`

## Latest Update 2026-04-19 Round 4

### Test Run 15

- 目的：完成 P14-P16 的工具化与真实烟测
- 新增/更新测试：
  - `tests/unit/test_provider_sandbox_contracts.py`
  - `tests/integration/test_provider_sandbox_flow.py`
  - `tests/unit/test_runtime_backup_contracts.py`
  - `tests/unit/test_metrics_baseline_contracts.py`
  - `tests/integration/test_metrics_baseline_flow.py`
- 命令：`py -m pytest`
- 结果：`101 passed, 0 failed`

### Runtime Backup Smoke

- 命令：`py -m app.tools.runtime_backup create --output data\backups\runtime_backup_20260419_2219.zip`
- 结果：
  - 归档生成成功
  - `file_count=18011`
  - `size_bytes=424308251`

### Runtime Backup Inspect Smoke

- 命令：`py -m app.tools.runtime_backup inspect --archive data\backups\runtime_backup_20260419_2219.zip`
- 结果：
  - `format_version=soft_review.runtime_backup.v1`
  - `entry_count=18011`
  - `sqlite_snapshot_mode=sqlite_backup_api`

### Runtime Restore Dry Run Smoke

- 命令：`py -m app.tools.runtime_backup restore --archive data\backups\runtime_backup_20260419_2219.zip --target data\restore_preview\runtime_backup_20260419_2219`
- 结果：
  - dry-run 成功
  - 预览前 10 条恢复计划
  - 其余 `18001` 条省略

### Metrics Baseline Smoke

- 命令：`py -m app.tools.metrics_baseline --markdown-path docs\dev\54-real-sample-baseline.md --json-path docs\dev\55-real-sample-baseline.json`
- 结果：
  - `54-real-sample-baseline.md` 生成成功
  - `55-real-sample-baseline.json` 生成成功

## Latest Update 2026-04-19 Round 3

### Test Run 14

- 目的：完成 P10-P13 契约、运维工具与回归收口
- 新增/更新测试：
  - `tests/unit/test_external_http_adapter_contracts.py`
  - `tests/unit/test_runtime_cleanup_contracts.py`
  - `tests/unit/test_startup_self_check_contracts.py`
  - `tests/integration/test_operator_console_and_exports.py`
- 命令：`py -m pytest`
- 结果：`90 passed, 0 failed`

### Runtime Cleanup Smoke

- 命令：`py -m app.tools.runtime_cleanup`
- 结果：
  - `candidate_count=0`
  - `skipped_count=0`
  - `sqlite_action=skip_manual_backup`

### Runtime Cleanup JSON Smoke

- 命令：`py -m app.tools.runtime_cleanup --json`
- 结果：
  - JSON 输出包含 `plan` 与 `execution`
  - 当前无过期自动清理候选
  - SQLite 明确标记为 `manual_backup_only`

### Real Sample Smoke 8

- 命令：`py -m app.tools.input_runner --path input\软著材料 --mode single_case_package`
- 结果：
  - `packages=6 materials=24 cases=6 reports=6 unknown=0 needs_review=10 low_quality=10 redactions=239`
  - `review_reasons={'noise_too_high': 10, 'ole_readable_segments_insufficient': 1, 'clean_text_ready': 13}`
  - `legacy_doc_buckets={'binary_noise': 6, 'partial_fragments': 4, 'usable_text': 8}`

### Real Sample Smoke 9

- 命令：`py -m app.tools.input_runner --path input\合作协议 --mode batch_same_material`
- 结果：
  - `materials=11`
  - `cases=10`
  - `reports=1`
  - `types={'agreement': 11}`
  - `needs_review=2`
  - `low_quality=2`
  - `redactions=149`

所有测试执行结果、失败现象、修复前后变化，都记录在本文件。


## 2026-04-19

### Initial Status

- 已存在完整测试策略文档
- 已存在契约测试骨架
- 尚未进入完整 pytest 执行

### Test Run 1

- 命令：`py -m pytest`
- 结果：41 通过，1 失败
- 失败项：`test_source_code_rule_review_detects_garbled_ratio`
- 现象：源码乱码检测仅基于比例，未覆盖长异常字符片段

### Fix 1

- 调整源码规则：
  - 保留乱码比例阈值
  - 新增异常非 ASCII 连续片段检测

### Test Run 2

- 命令：`py -m pytest`
- 结果：42 通过，0 失败

### Manual Smoke 1

- 首页：200
- API 提交：500
- 根因：ZIP 中中文文件名在 Windows 解压时生成非法文件路径

### Fix 2

- 对 ZIP 成员路径做文件名清洗
- 保留原始 Zip Slip 安全校验

### Test Run 3

- 命令：`py -m pytest`
- 结果：41 通过，1 失败
- 失败项：`test_safe_extract_zip_blocks_zip_slip_entries`
- 根因：文件名清洗过早，吞掉了路径穿越检测

### Fix 3

- 先检查原始路径是否包含绝对路径或 `..`
- 再执行安全文件名清洗

### Test Run 4

- 命令：`py -m pytest`
- 结果：42 通过，0 失败

### Manual Smoke 2

- 首页：200
- API 提交：201
- Submission 页面：200
- Case 页面：200
- Report 页面：200

### Test Run 5

- 日期：2026-04-19
- 目的：补齐 Web 主路径和 Windows 非法文件名 ZIP 回归测试后做全量回归
- 新增覆盖：
  - 首页渲染
  - `/upload` 重定向链路
  - Submission / Case / Report / Index 页面可访问
  - Windows 非法文件名 ZIP 自动清洗
- 命令：`py -m pytest`
- 结果：46 通过，0 失败，0 跳过

### Skill Smoke

- 命令：`py C:\Users\DOIT\.codex\skills\ui-ux-pro-max\scripts\search.py "document review accessibility enterprise dashboard trust" --design-system -p "Soft Copyright Review Desk" -f markdown`
- 结果：执行成功，说明 skill 已可用于后续前端设计检索

### Validation Note

- `quick_validate.py` 未通过
- 原因：当前环境缺少 `yaml` 依赖
- 处理方式：保留结构校验待后续环境补齐，同时以真实命令执行成功作为当前手工验证依据

### Test Run 6

- 日期：2026-04-19
- 目的：前端重构后验证 Web 主链路未回归
- 变更范围：
  - `app/web/pages.py`
  - `app/web/static/styles.css`
- 命令：`py -m pytest`
- 结果：46 通过，0 失败，0 跳过
- 结论：UI 大改后，上传、页面渲染和主路径契约保持稳定

### Test Run 7

- 日期：2026-04-19
- 目的：将前端从展示型页面重构为管理系统 / 分析系统后回归验证
- 变更范围：
  - `app/web/pages.py`
  - `app/web/static/styles.css`
- 验证点：
  - 首页仍保留上传入口
  - 批次 / Submission / Case / Report 主链路可访问
  - 自动化测试契约不回归
- 命令：`py -m pytest`
- 结果：46 通过，0 失败，0 跳过

### Test Run 8

- 日期：2026-04-19
- 目的：验证 P0 解析质量、unknown 原因与待复核队列
- 变更范围：
  - `app/core/services/zip_ingestion.py`
  - `app/core/parsers/quality.py`
  - `app/core/parsers/service.py`
  - `app/core/services/material_classifier.py`
  - `app/core/pipelines/submission_pipeline.py`
  - `app/core/reports/renderers.py`
  - `app/tools/input_runner.py`
  - `app/web/pages.py`
- 新增测试：
  - `tests/unit/test_zip_filename_repair_contracts.py`
  - `tests/unit/test_parse_quality_contracts.py`
  - `tests/integration/test_parser_quality_regression.py`
- 命令：`py -m pytest`
- 结果：57 通过，0 失败，0 跳过
- 真实样本命令：
  - `D:\Soft\python310\python.exe -m app.tools.input_runner --path input\软著材料 --mode single_case_package`
  - `D:\Soft\python310\python.exe -m app.tools.input_runner --path input\合作协议 --mode batch_same_material`
- 核心结论：
  - 模式 A unknown 总数从 `5` 收敛到 `1`
  - `2505` 已收敛到 `0` unknown
  - 大量 `.doc` 仍为 low quality，但已被正确推入待复核队列

### Test Run 9

- 日期：2026-04-19
- 目的：验证 P1 人工纠错闭环与 P2 SQLite 恢复能力
- 变更范围：
  - `app/core/domain/models.py`
  - `app/core/services/runtime_store.py`
  - `app/core/services/corrections.py`
  - `app/core/services/sqlite_repository.py`
  - `app/api/main.py`
  - `app/web/pages.py`
- 新增测试：
  - `tests/integration/test_manual_correction_api.py`
  - `tests/integration/test_sqlite_persistence.py`
- 命令：`py -m pytest`
- 结果：60 通过，0 失败，0 跳过
- 验证结论：
  - correction record 可写入、可读取、可在页面显示
  - submission graph 可落盘到 SQLite 并恢复到 runtime store
  - 真实样本回归结果与 P0 一致，无新增导入回归

### Test Run 10

- 日期：2026-04-19
- 目的：验证 P3 浏览器操作台、导出与日志链路
- 命令：`py -m pytest`
- 首次结果：`61 passed, 1 failed`
- 失败点：`tests.integration.test_operator_console_and_exports.test_html_operator_actions_and_download_endpoints_work`
- 根因 1：本地 `Response` 不支持构造参数 `media_type`
- 修复 1：改为先创建响应再设置 `response.media_type`
- 二次结果：`61 passed, 1 failed`
- 根因 2：本地 `Response` 缺少 `.content`
- 修复 2：在 `fastapi/responses.py` 增加 `content` 属性
- 最终结果：`62 passed, 0 failed`

### Test Run 11

- 日期：2026-04-19
- 目的：验证 AI provider 边界与配置化改动
- 新增测试：
  - `tests/unit/test_app_config_contracts.py`
  - `tests/unit/test_ai_provider_boundary_contracts.py`
- 命令：`py -m pytest`
- 结果：`67 passed, 0 failed`
- 关键验证：
  - 默认配置保持 `mock`
  - 环境变量可切换 provider
  - 非 mock provider 会拒绝未脱敏 payload
  - `safe_stub` 可接受脱敏 payload

### Real Sample Smoke 3

- 日期：2026-04-19
- 命令：`py -m app.tools.input_runner --path input\软著材料 --mode single_case_package`
- 结果：
  - 模式 A 仍保持 unknown 总数 `1`
  - `2502` 仍有 `1` 个 `unknown`
  - 其余样本包分类结果稳定

### Real Sample Smoke 4

- 日期：2026-04-19
- 命令：`py -m app.tools.input_runner --path input\合作协议 --mode batch_same_material`
- 结果：
  - `11` 份材料全部识别为 `agreement`
  - 生成 `2` 个 case 与 `1` 个 report

### Real Sample Smoke 5

- 日期：2026-04-19
- 目的：验证非 mock provider 配置下的真实管线安全边界
- 命令：`$env:SOFT_REVIEW_AI_ENABLED='true'; $env:SOFT_REVIEW_AI_PROVIDER='safe_stub'; py -m app.tools.input_runner --path input\软著材料\2501_软著材料.zip --mode single_case_package`
- 结果：
  - 导入成功
  - case review 成功完成
  - 说明真实管线在非 mock 配置下仍只使用脱敏 payload

### Test Run 12

- 日期：2026-04-19
- 目的：验证 P5-P8 的后端骨架、页面增强和 provider skeleton
- 命令：
  - `py -m pytest tests\unit\test_ai_review_contracts.py tests\unit\test_ai_provider_boundary_contracts.py tests\unit\test_report_contracts.py tests\unit\test_startup_self_check_contracts.py tests\integration\test_web_mvp_contracts.py tests\integration\test_operator_console_and_exports.py`
- 结果：测试 runner 实际执行了全量回归，`73 passed, 0 failed`
- 关键验证：
  - `/ops` 页面可访问
  - `external_http` 未配置时可 fallback 到 `mock`
  - Case 页能分开展示规则结论与 AI 补充说明

### Test Run 13

- 日期：2026-04-19
- 目的：补入 `input_runner` 指标测试后做最终全量回归
- 命令：`py -m pytest`
- 结果：`74 passed, 0 failed`

### Real Sample Smoke 6

- 日期：2026-04-19
- 命令：`py -m app.tools.input_runner --path input\软著材料 --mode single_case_package`
- 结果：
  - 新增聚合摘要行
  - `packages=6 materials=24 cases=6 reports=6 unknown=0 needs_review=10 low_quality=10 redactions=239`
- 关键结论：模式 A `unknown` 总数已归零

### Real Sample Smoke 7

- 日期：2026-04-19
- 命令：`py -m app.tools.input_runner --path input\合作协议 --mode batch_same_material`
- 结果：
  - `materials=11`
  - `cases=10`
  - `reports=1`
  - `types={'agreement': 11}`
  - `needs_review=2`
  - `low_quality=2`
  - `redactions=149`
