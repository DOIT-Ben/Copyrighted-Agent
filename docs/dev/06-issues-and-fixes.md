# Issues And Fixes

## Latest Update 2026-04-20 Round 12

### Issue 44

- Symptom: the project's `external_http` contract could not call MiniMax directly because the repo sends a custom review JSON shape while MiniMax expects OpenAI-compatible `chat/completions`.
- Root cause: the product-level provider boundary was intentionally narrowed around an internal contract, not vendor-native request formats.
- Fix: added a local `minimax_bridge` that accepts the existing `external_http` payload, calls MiniMax's OpenAI-compatible endpoint, and converts the model output back into the repo's response contract.

### Issue 45

- Symptom: even after the real MiniMax endpoint and model were known, there was still a risk of persisting the secret into tracked config or docs during live setup.
- Root cause: a successful live validation needs both repeatable config and strict secret handling, but only the non-secret part belongs in the repo.
- Fix: kept the API key env-only, added `config/local.minimax_bridge.example.json` for the non-secret bridge configuration, and validated the live path using temporary env overrides.

## Latest Update 2026-04-20 Round 11

### Issue 39

- Symptom: the project had all the underlying pieces for real-provider validation, but the last 10 percent still depended on a manual sequence of loosely connected commands.
- Root cause: provider probe, release gate, and sample smoke validation were implemented separately, without a single repeatable end-to-end entrypoint.
- Fix: added `app/core/services/release_validation.py` and `app/tools/release_validation.py` to orchestrate probe, release gate, sample smokes, and artifact output in one command.

### Issue 40

- Symptom: the first release-validation integration test failed even though the probe and smoke path were healthy.
- Root cause: the test forced `ai_fallback_to_mock=false`, which currently makes provider readiness report a warning and therefore keeps the release gate from reaching `pass`.
- Fix: aligned the integration test with the current gate contract by using the normal fallback-enabled configuration while still asserting the sample smoke actually used `external_http`.

### Issue 41

- Symptom: after the new validation command was added, the workspace still could not complete a true non-mock validation run.
- Root cause: `config/local.json` remains in mock mode and no real endpoint, model, or API-key env mapping is configured locally.
- Fix: ran the new validation command anyway, captured the blocked state as a durable artifact, and reduced the remaining work to explicit environment inputs instead of hidden code uncertainty.

### Issue 42

- Symptom: the first `real-provider-validation-latest.json` file did not describe its own latest/history artifact paths even though the writer knew them.
- Root cause: `write_release_validation_artifacts(...)` wrote the payload before injecting the resolved artifact metadata into it.
- Fix: built the artifact-path payload first, injected it before serializing the latest/history files, and reran validation so the latest JSON now self-describes its own artifact set.

### Issue 43

- Symptom: the repository still contains a legacy `config/settings.py` with historical provider values, which can make live-provider onboarding look more ready than it actually is.
- Root cause: the current MVP provider flow reads `AppConfig` from `config/local.json` plus `SOFT_REVIEW_*` env overrides, not from the older settings module.
- Fix: audited the active config path during the live start attempt and documented clearly that current real-provider validation must be configured through `config/local.json` or `SOFT_REVIEW_*`, not `config/settings.py`.

## Latest Update 2026-04-20 Round 10

### Issue 36

- Symptom: PowerShell preview can still make healthy UTF-8 Chinese page strings look corrupted, which creates a real risk of unnecessary "repair" edits.
- Root cause: shell display encoding and console rendering are not the same thing as source-file encoding.
- Fix: documented a Python `unicode_escape` verification workflow in `app/web/README.md` and added a source-safety contract test for known mojibake markers in active web files.

### Issue 37

- Symptom: the planned "continue" flow could easily drift back into blocked real-provider work even though local credentials are still absent.
- Root cause: the current workspace state still uses mock-first config and no `SOFT_REVIEW_*` provider variables are set, so real smoke is not actionable yet.
- Fix: re-audited config and env first, documented the blocking state explicitly, and advanced the highest-value non-blocked slice instead: contributor guardrails plus regression protection.

### Issue 38

- Symptom: even the new mojibake-guardrail test could become encoding-sensitive if suspicious markers were stored directly as non-ASCII literals.
- Root cause: a Windows-oriented source-safety test should not depend on fragile literal rendering to stay readable or editable.
- Fix: changed the test to derive suspicious markers from canonical localized terms at runtime, so the guardrail remains effective while the test source stays ASCII-stable.

## Latest Update 2026-04-20 Round 9

### Issue 34

- Symptom: the restored `app/web/pages.py` was stable again, but it remained a large mixed-responsibility file and kept the same future maintenance risk profile.
- Root cause: the emergency rebuild prioritized restoring behavior quickly, not reorganizing the renderer boundaries.
- Fix: split the page layer into shared helpers and page-scoped renderer modules, then reduced `app/web/pages.py` to a small export surface.

### Issue 35

- Symptom: the rebuilt page layout used some structural class names that did not line up well with the existing CSS naming scheme.
- Root cause: the emergency recovery focused on test contracts first and only secondarily on the established style skeleton.
- Fix: realigned the modular renderers to the current admin CSS structure such as `sidebar-brand`, `workspace`, `workspace-header`, and `workspace-content`.

## Latest Update 2026-04-20 Round 8

### Issue 30

- Symptom: the targeted regression failed even though the new provider probe and release-gate logic were sound.
- Root cause: `tests/integration/test_operator_console_and_exports.py` still depended on the `monkeypatch` fixture, but the local lightweight pytest runner does not provide it.
- Fix: rewrote the test to manage `SOFT_REVIEW_DATA_ROOT` and `SOFT_REVIEW_LOG_PATH` with explicit `os.environ` save / restore logic.

### Issue 31

- Symptom: after adding a default `config/local.json`, startup self-check contract tests still assumed `local_config.exists` must be `False`.
- Root cause: the product default changed intentionally, but the tests still encoded the earlier “no local config” assumption.
- Fix: updated the contract to assert local-config presence and normalized the Windows path assertion with `replace("\\", "/")`.

### Issue 32

- Symptom: a small `/ops` polish pass unexpectedly broke `app/web/pages.py` and caused widespread syntax errors during regression.
- Root cause: a full-file PowerShell rewrite used `Get-Content` / `Set-Content` without preserving the original UTF-8 source encoding, corrupting many Chinese literals in the page module.
- Fix: backed up the corrupted source to `docs/dev/history`, stopped patching the garbled file, and rebuilt `app/web/pages.py` from the active FastAPI route contract instead of trying to salvage corrupted strings in place.

### Issue 33

- Symptom: an emergency `.pyc` loader fallback was not a safe long-term recovery path.
- Root cause: compiling the wrapper would overwrite the same `pages.cpython-310.pyc` slot, so the compiled artifact could not be treated as a durable source of truth.
- Fix: discarded the `.pyc` recovery path and restored a source-based `pages.py` implementation before final validation.

## Latest Update 2026-04-20 Round 7

### Issue 26

- Symptom: the first live sandbox probe attempt still failed even though the sandbox command itself was correct.
- Root cause: PowerShell `Start-Job` did not start in the repository working directory, so the background job could not reliably launch the local module entrypoint.
- Fix: added an explicit `Set-Location` to the repository root inside the job script block before running `py -m app.tools.provider_sandbox`, then re-ran the probe successfully with HTTP `200`.

### Issue 27

- Symptom: provider readiness output was not granular enough to distinguish mock mode, incomplete external configuration, ready-for-probe state, and real probe result state.
- Root cause: the earlier readiness model mainly exposed a coarse health status and did not preserve the operator decision path.
- Fix: introduced explicit readiness `phase`, `blocking_items`, and `recommended_action`, then reused the structure in CLI output, startup checks, and `/ops`.

### Issue 28

- Symptom: the latest probe result was visible in terminal output but not durably available to operators after the command finished.
- Root cause: probe execution had no persisted latest-result artifact.
- Fix: persisted the latest probe payload to `data/runtime/ops/provider_probe_latest.json` and surfaced the summary on `/ops`.

### Issue 29

- Symptom: real non-sandbox provider smoke could still not be completed on 2026-04-20.
- Root cause: local `config/local.json` is still absent and no real endpoint / model / API-key environment mapping is configured in the current workspace.
- Fix: treated the gap as an environment dependency, documented it explicitly, and completed sandbox-first validation plus observability hardening instead of stalling the round.

## Latest Update 2026-04-19 Round 6

### Issue 23

- Symptom: `latest_metrics_baseline_status(...)` started classifying non-zero `needs_review / low_quality` as `warning`, but the old unit contract still expected `ok`.
- Root cause: status meaning shifted from “artifact exists” to “artifact exists and review debt is zero”.
- Fix: updated the unit contract to assert `warning` plus delta aggregation when review debt is present.

### Issue 24

- Symptom: rolling baseline data already existed in services and CLI output, but `/ops` still only showed the latest baseline card without trend history or checklist detail.
- Root cause: the UI stopped at “latest artifact visibility” and never exposed the comparison/archive workflow operators actually need.
- Fix: added `Trend Watch`, `Baseline History`, signed delta pills, `Provider Checklist`, and `Rolling Baseline` command guidance to the ops console.

### Issue 25

- Symptom: true live external-provider smoke could not be completed on 2026-04-19.
- Root cause: local `config/local.json` and real external provider credentials are still absent in the current workspace.
- Fix: treated this as a non-blocking environment dependency, surfaced the gap in `Provider Checklist`, and continued with the highest-value unblocked slice instead of stalling development.

## Usage

## Latest Update 2026-04-19 Round 5

### Issue 19

- Symptom: default mock mode would appear unhealthy after the first provider-readiness implementation.
- Root cause: disabled AI was treated as warning even when local/mock mode was expected.
- Fix: readiness now distinguishes mock/local validity from inactive external provider configuration.

### Issue 20

- Symptom: legacy `.doc` real samples were still flagged low quality after text extraction looked readable.
- Root cause: control separators from Word binary content leaked into quality scoring.
- Fix: added control-character stripping before cleanup and quality scoring.

### Issue 21

- Symptom: real PDFs still showed low signal despite containing readable Chinese agreement and document text.
- Root cause: the PDF parser ignored compressed content streams and `ToUnicode` CMaps.
- Fix: added lightweight stream decompression and `ToUnicode` decoding in `app/core/parsers/pdf_parser.py`.

### Issue 22

- Symptom: port `8010` was not available for one local sandbox probe attempt.
- Root cause: local Windows port availability and permission constraints.
- Fix: reran the live probe on configurable port `18010` and documented that probe port must remain configurable.

## Latest Update 2026-04-19 Round 4

### Issue 18

- 现象：provider 契约虽已固定，但缺少真实 HTTP 联调入口。
- 影响范围：接真实 provider 前的本地验证效率。
- 根因：此前只有 adapter/service 契约，没有可直接启动的本地 provider 端。

### Fix

- 修复策略：新增 `app.tools.provider_sandbox` 与集成测试。
- 回归结果：`external_http` 可以通过本地 sandbox 完整走通。

### Issue 19

- 现象：runtime cleanup 只解决清理，不解决留存与恢复。
- 影响范围：运维链路不闭环。
- 根因：缺少 backup / inspect / restore 工具。

### Fix

- 修复策略：新增 `app.tools.runtime_backup`。
- 回归结果：真实运行目录已生成首个 backup 归档，restore dry-run 成功。

### Issue 20

- 现象：`runtime_backup inspect` 和 `restore` 在 Windows/GBK 终端下打印大清单时触发编码异常。
- 影响范围：CLI 可用性。
- 根因：默认 `print()` 直接走控制台编码，且输出规模过大。

### Fix

- 修复策略：
  - 改为 UTF-8 buffer 输出
  - inspect 默认输出摘要
  - restore 默认只预览前 10 条
- 回归结果：真实 smoke 已恢复正常。

## Latest Update 2026-04-19 Round 3

### Issue 15

- 现象：自定义 pytest runner 不完全支持标准 `pytest.raises(match=...)` 与 `exc_info.value` 用法。
- 影响范围：新增测试的稳定性。
- 根因：项目当前使用的是轻量兼容 runner，而不是完整官方 pytest 行为。

### Fix

- 修复策略：把新增测试改写为最低兼容风格，使用显式 `try/except` 或基础 `pytest.raises(...)`。
- 变更位置：
  - `tests/unit/test_external_http_adapter_contracts.py`
  - `tests/unit/test_runtime_cleanup_contracts.py`
- 回归结果：全量回归恢复 `90 passed, 0 failed`。

### Issue 16

- 现象：Windows 下 `clear_database()` 直接删除 SQLite 文件时，可能因为另一个进程持有句柄而失败。
- 影响范围：持久化测试与本地联调稳定性。
- 根因：SQLite 文件级删除策略过于乐观。

### Fix

- 修复策略：`unlink()` 失败时回退到表级清空，而不是直接报错。
- 变更位置：`app/core/services/sqlite_repository.py`
- 回归结果：SQLite 持久化测试稳定通过。

### Issue 17

- 现象：runtime cleanup 如果默认就可执行删除，会在运维场景里引入新的误删风险。
- 影响范围：`data/runtime` 安全性与调查可追溯性。
- 根因：缺少“默认只观察、不直接执行”的保守策略。

### Fix

- 修复策略：
  - 默认 dry-run
  - 仅允许清理 `submissions / uploads / logs`
  - active log 跳过
  - SQLite 仅给出人工备份策略
  - apply 前校验 allowed roots
- 变更位置：
  - `app/tools/runtime_cleanup.py`
  - `tests/unit/test_runtime_cleanup_contracts.py`
  - `app/web/pages.py`
- 回归结果：清理工具可用且具备安全护栏。

记录开发和测试过程中发现的问题，以及最终修复方式。


## Template

### Issue

- 现象：
- 影响范围：
- 根因：

### Fix

- 修复策略：
- 变更位置：
- 回归结果：


## Issue 1

- 现象：全量测试时，源码乱码规则没有识别一段明显异常的中英夹杂乱码文本
- 影响范围：源码材料规则审查准确性
- 根因：规则只看整体乱码比例，没有识别长连续异常字符片段

### Fix

- 修复策略：在乱码比例之外，再增加异常非 ASCII 连续片段检测
- 变更位置：`app/core/reviewers/rules/source_code.py`
- 回归结果：相关测试通过


## Issue 2

- 现象：手动上传含中文文件名的 ZIP 时，`/api/submissions` 返回 500
- 影响范围：实际上传主路径不可用，尤其影响中文命名材料
- 根因：ZIP 成员文件名直接用于 Windows 落盘，遇到非法字符时触发路径错误

### Fix

- 修复策略：为 ZIP 成员路径增加文件名清洗逻辑
- 变更位置：`app/core/services/zip_ingestion.py`
- 回归结果：API 提交恢复成功


## Issue 3

- 现象：修复中文文件名后，Zip Slip 安全测试退化
- 影响范围：安全边界
- 根因：在检查路径穿越前就先做了文件名清洗，导致 `..` 被吞掉

### Fix

- 修复策略：先检测原始路径是否包含绝对路径或 `..`，再进行安全清洗
- 变更位置：`app/core/services/zip_ingestion.py`
- 回归结果：安全测试恢复通过

## Issue 4

- 现象：把 `ui-ux-pro-max` 接入本地技能库后，系统校验脚本无法运行
- 影响范围：技能目录无法做脚本级完整校验
- 根因：当前环境缺少 `yaml` 依赖，`quick_validate.py` 启动即报错

### Fix

- 修复策略：先完成人工结构校验与真实检索命令校验，并在文档中显式记录环境限制
- 变更位置：`docs/dev/02-todo.md`、`docs/dev/09-runbook.md`、`docs/dev/12-skill-integration.md`
- 回归结果：技能检索命令执行成功，后续待环境补齐后再补脚本校验

## Issue 5

- 现象：真实 ZIP 中的中文文件名被错误解码，导致分类器无法命中文件名信号，出现大量 `unknown`
- 影响范围：真实样本识别准确率、unknown 收敛、后续人工纠错成本
- 根因：ZIP 成员名在读取时存在默认解码与真实编码不一致的问题

### Fix

- 修复策略：对 ZIP 成员名执行 `cp437 -> utf-8` / `cp437 -> gb18030` 恢复，并按可读性评分选优
- 变更位置：`app/core/services/zip_ingestion.py`
- 回归结果：模式 A unknown 总数从 `5` 收敛到 `1`

## Issue 6

- 现象：低质量二进制 `.doc` 文本会误触发内容规则，存在错误自动分类风险
- 影响范围：分类可信度、结果解释性、后续人工纠错效率
- 根因：原有解析链路缺少质量判断，分类器不知道“文本是否可信”

### Fix

- 修复策略：新增 parse quality 评估、low quality content gate、unknown reason 与待复核队列
- 变更位置：`app/core/parsers/quality.py`、`app/core/parsers/service.py`、`app/core/pipelines/submission_pipeline.py`、`app/web/pages.py`
- 回归结果：低质量文本不再被无解释地自动归类，系统会显式标记 `needs_manual_review`

## Issue 7

- 现象：人工纠错如果只改材料或 case 状态，不同步 review/report，会导致页面结果与最终状态不一致
- 影响范围：人工纠错可信度、报告一致性、审计可追溯性
- 根因：纠错动作与 case rebuild 没有自动串联

### Fix

- 修复策略：把 correction 动作与 review rerun / report rewrite 绑定为同一条服务链
- 变更位置：`app/core/services/corrections.py`
- 回归结果：手动纠错后，case 结果和报告会同步刷新

## Issue 8

- 现象：SQLite 持久化测试在并行 pytest 下会出现 Windows 文件占用错误
- 影响范围：持久化测试稳定性
- 根因：多个测试进程同时访问同一个 SQLite 文件

### Fix

- 修复策略：SQLite 相关验证改为串行回归，并在测试前后清理数据库文件
- 变更位置：`app/core/services/sqlite_repository.py`、`tests/integration/test_sqlite_persistence.py`
- 回归结果：单次全量回归 `60 passed`

## Issue 9

- 现象：导出下载接口在本地回归环境下直接报 500。
- 影响范围：报告下载、材料产物下载、submission bundle、日志下载。
- 根因：本地 FastAPI 兼容层的 `Response` 构造器不支持 `media_type` 参数。

### Fix

- 修复策略：在 `app/api/main.py` 中改为先创建 `Response`，再设置 `response.media_type`。
- 变更位置：`app/api/main.py`
- 回归结果：下载相关接口恢复正常。

## Issue 10

- 现象：下载接口状态码已恢复，但测试继续失败，提示响应对象没有 `.content`。
- 影响范围：测试客户端兼容性与下载断言稳定性。
- 根因：本地兼容层只实现了 `body`，没有兼容常用的 `content` 属性。

### Fix

- 修复策略：为 `fastapi.responses.Response` 增加 `content` 属性别名。
- 变更位置：`fastapi/responses.py`
- 回归结果：`test_operator_console_and_exports` 完整通过。

## Issue 11

- 现象：当前 AI 隐私边界主要依赖调用约定，未来一旦切换到非 mock provider，存在把未脱敏字段送进 provider 的风险。
- 影响范围：隐私安全、真实 provider 接入可控性、审计能力。
- 根因：provider 解析、配置读取、payload 安全校验没有独立成层。

### Fix

- 修复策略：
  - 新增 `AppConfig`
  - 新增 `resolve_case_ai_provider`
  - 新增 `safe_stub`
  - 新增 `is_ai_safe_case_payload`
  - 在 pipeline 与 correction 重建链路中统一走配置驱动 provider 解析
- 变更位置：
  - `app/core/services/app_config.py`
  - `app/core/reviewers/ai/service.py`
  - `app/core/privacy/desensitization.py`
  - `app/core/pipelines/submission_pipeline.py`
  - `app/core/services/corrections.py`
- 回归结果：AI 边界单测通过，`safe_stub` 真实样本烟测通过。

## Issue 12

- 现象：Case 页和报告里，规则结论与 AI 说明混成一段，不利于审计和人工复核。
- 影响范围：结果解释性、后续真实 provider 接入可信度。
- 根因：`ReviewResult` 结构过于扁平，只保留了单一 `conclusion`。

### Fix

- 修复策略：拆分为 `rule_conclusion / ai_summary / ai_provider / ai_resolution`，并同步更新 Case 页面与 markdown 报告。
- 变更位置：
  - `app/core/domain/models.py`
  - `app/core/pipelines/submission_pipeline.py`
  - `app/core/services/corrections.py`
  - `app/core/reports/renderers.py`
  - `app/web/pages.py`
- 回归结果：页面和报告均能分开展示规则结论与 AI 补充说明。

## Issue 13

- 现象：系统已经开始依赖 runtime 目录、SQLite、日志和配置，但运行前没有统一体检入口。
- 影响范围：启动稳定性、排障速度、运维透明度。
- 根因：缺少单独的 startup self-check。

### Fix

- 修复策略：新增 `run_startup_self_check`，并在 `/ops` 页面呈现结果。
- 变更位置：
  - `app/core/services/startup_checks.py`
  - `app/api/main.py`
  - `app/web/pages.py`
- 回归结果：`/ops` 页面和自检单测通过。

## Issue 14

- 现象：模式 B 虽然已支持，但浏览器端没有讲清“先归档、后合并”的工作方式，容易被误解为一次上传就应该直接形成完整项目。
- 影响范围：浏览器端体验、人工操作效率。
- 根因：首页和 Submission 页缺少模式 B 的流程提示与结果摘要。

### Fix

- 修复策略：新增首页模式 B 指导、Submission `Import Digest`、操作台预填和提示文本。
- 变更位置：
  - `app/web/pages.py`
  - `app/web/static/styles.css`
- 回归结果：页面集成测试通过，管理台体验更贴近运营后台。
