# Reusable Playbook

## Latest Update 2026-04-20 Round 12

- If your repo uses a custom provider contract but the vendor exposes an OpenAI-compatible endpoint, add a local bridge first instead of widening the core review pipeline to every vendor shape.
- Keep secrets env-only during live onboarding; store only the repeatable non-secret bridge config in tracked example files.
- For first live spend, run a synthetic safe probe before full release validation. It catches auth and gateway issues at the lowest possible cost.
- Once a live path passes, preserve both the passing artifact and the exact bridge startup command in the runbook so reruns stay mechanical.

## Latest Update 2026-04-20 Round 11

- When the last mile depends on real credentials, turn the whole path into one command before asking anyone to fill secrets.
- A good final validation flow should emit both machine-readable JSON and human-readable Markdown, so operators and developers can share the same truth.
- Keep real-provider smoke low-cost by default: one safe probe, one mode A package smoke, and one mode B corpus smoke are enough for the first gate.
- If release-gate semantics and smoke semantics disagree, fix the test or contract alignment first; do not hand-wave the mismatch away.
- If an artifact is supposed to describe its own output paths, inject that metadata before serializing any file; post-write mutation leaves the first generated JSON stale.
- After fixing artifact serialization, rerun the operator command once so `latest.*` reflects the repaired payload and not just future history entries.
- Before editing provider config in an older repo, verify which config loader is actually live; legacy settings files can look authoritative while the real path is already `AppConfig` plus `config/local.json` / `SOFT_REVIEW_*`.

## Latest Update 2026-04-20 Round 10

- On Windows, do not trust a garbled PowerShell preview alone as proof that a UTF-8 source file is broken; verify the actual file with Python `unicode_escape` output first.
- When a page layer has just been modularized, add a short contributor map immediately. The structure is freshest right after extraction and easiest to keep correct.
- Protect thin export barrels with tests; if the API depends on a stable import surface, treat that surface as a contract.
- Prefer ASCII-stable test sources for encoding guardrails; derive suspicious localized mojibake markers at runtime instead of hardcoding brittle literals when possible.
- If real-provider smoke is still blocked, spend the round reducing future maintenance risk instead of waiting on credentials.

## Latest Update 2026-04-20 Round 9

- After an emergency UI recovery, follow with a structural cleanup pass; a stable monolith is safer than a broken one, but it should not become the new long-term architecture.
- Keep `pages.py` as a thin import barrel when the API layer depends on a stable renderer entry surface.
- Split admin UI code by page responsibility first, then by smaller subcomponents only when the page modules start growing again.
- Align renderer HTML class names with the existing stylesheet vocabulary before doing visual polish; this keeps refactors low-risk.
- When tests already cover core HTML contract strings, use them as the guardrail for page-module extraction.

## Latest Update 2026-04-20 Round 8

- On Windows, do not bulk-rewrite UTF-8 source files with `Get-Content` / `Set-Content` unless encoding is explicitly controlled end to end; prefer `apply_patch`.
- If a large UI source file becomes encoding-corrupted, do not keep patching broken strings blindly. Back it up first, then rebuild from route contracts and tests.
- A safe local `config/local.json` with mock defaults reduces boot friction and makes `/ops`, startup self-check, and release-gate output more repeatable.
- When bootstrap defaults change, update the test contract immediately; otherwise old assumptions will look like regressions even when the product behavior is intentional.
- `.pyc` files are a weak emergency fallback, not a durable recovery source. Treat source recovery as the real fix.

## Latest Update 2026-04-20 Round 7

- Real-provider onboarding should move in four steps: readiness audit, synthetic safe probe, operator observability, then real smoke.
- Persist the latest probe result even for CLI-only checks; otherwise the most recent truth disappears into terminal scrollback.
- In PowerShell background jobs, set the repository working directory explicitly before invoking local modules.
- Make readiness states operator-readable: `mock_mode`, `not_configured`, `partially_configured`, `ready_for_probe`, and probe pass/fail should not collapse into one status label.
- Keep provider probes synthetic and `llm_safe`; probe tooling should never require real user material to validate gateway wiring.

## Latest Update 2026-04-19 Round 6

- When provider configuration is missing locally, continue with non-blocked observability work instead of idling; capture the missing dependency explicitly in docs and UI.
- Treat baseline status as an operational quality signal, not merely an artifact-exists flag; keep service logic and tests aligned.
- For admin dashboards, surface “latest snapshot”, “history”, and “how to reproduce the snapshot” together in one place.
- Rolling baselines are more reusable when they auto-compare against the latest artifact and archive timestamped copies in a dedicated history folder.
- If legacy text or localized content makes large patch replacement brittle, preserve the old implementation as a named legacy backup and layer the new version cleanly on top.

## Purpose

## Latest Update 2026-04-19 Round 5

- Build provider onboarding as a reusable service plus CLI probe before coupling it to the UI.
- For ops tooling, a status panel is more reusable than a pure command list because operators need instant state, not just instructions.
- When parser quality is poor on real samples, first remove extraction artifacts, then adjust heuristics, then rerun baselines.
- PDF best-effort parsing should check `ToUnicode` maps before assuming the file is image-only or unrecoverable.
- Always regenerate a comparison baseline after parser fixes; otherwise quality wins remain anecdotal.

## Latest Update 2026-04-19 Round 4

- provider 真正接入前，先用本地 sandbox 演练 HTTP 契约，比直接对接真实网关更稳。
- backup/restore 能力应该在 cleanup 自动化之前成型，否则运维方案是不对称的。
- 大归档工具默认输出要做摘要，不然在 Windows 下既不易读，也容易命中编码问题。
- 趋势指标不要只写在验证文档里，还要固化为 JSON 基线文件。

## Latest Update 2026-04-19 Round 3

- 对 legacy `.doc`，把 `low_quality` 继续拆成“原因 + 分桶”，比单个状态值更适合运营和排障。
- 浏览器级 E2E 如果目标是校验真实页面工作流，优先走真实本地 HTTP 服务而不是只测 API。
- Provider 接入一定要先锁 JSON 契约，再接真实网关。
- 运维清理工具默认必须是 dry-run，并且要把 active log / SQLite 排除出自动删除范围。
- Windows 下 SQLite 清理不要只依赖删文件，保留表级清空的兜底路径。

把这次从脚本工具演进到 Web MVP 的经验，沉淀成后续可复用的操作手册。


## Principles

- 先锁测试契约，再写实现
- 先做领域建模，再做页面
- 先打通主路径，再做增强能力
- 规则引擎必须可脱离 AI 独立运行
- 所有问题都要形成可追溯修复记录


## Expected Sections To Fill

- 架构收敛方法
- ZIP 导入模式设计方法
- 审查系统的规则分层方法
- MVP 网站的最小实现路径
- 测试优先开发经验
- 常见坑与规避手法


## Architecture Convergence

- 先从测试里锁 `Submission / Case / Material`
- 再从这些核心实体反推服务边界
- 不要先写页面，也不要先做数据库


## ZIP Design Method

- Mode A 直接形成单 Case
- Mode B 先形成 Material，再尝试归档
- ZIP 安全要优先考虑：
  - 原始路径穿越
  - 可执行文件
  - Windows 非法文件名


## Review Layering

- 规则负责确定性问题
- Mock / AI 负责解释与综合结论
- 先让规则测试稳定，再接 AI


## MVP Web Path

最短闭环是：

1. 首页上传 ZIP
2. API 接收入库
3. Pipeline 解压、分类、解析、审查
4. 生成 Submission / Case / Report
5. 页面展示结果


## Test-First Lessons

- 契约测试能快速收敛模块接口
- 仅靠测试状态码不够，必须补手动冒烟
- “测试通过但真实上传失败”是常见情况
- 每发现一个真实问题，最好都补成自动化回归测试
- Web 项目不能只测 API，页面主链路也要锁住


## Common Pitfalls

- Windows 文件名规则和 ZIP 编码问题
- 为修一个问题而破坏安全测试
- 只验证 API，不验证页面链路
- 受限环境下包安装失败，导致文档与真实运行方式脱节
- 有本地 skill 资源但没有整理进可复用技能目录，后续难以复用

## Reuse Checklist

下一次做类似项目时，优先沿用这个顺序：

1. 先写测试策略和最低契约
2. 再建领域模型和流水线
3. 再做 Web MVP
4. 发现真实问题后立即补回归测试
5. 把运行说明、问题、经验同步写入 `docs/dev/`

## Operator And Export Lessons

- 本地兼容层项目里，下载类回归优先检查响应接口兼容性，不要先怀疑业务数据。
- 对导出链路，最小有效断言至少要覆盖：
  - 状态码
  - `Content-Disposition`
  - 非空内容
  - ZIP 是否可打开
- 浏览器端操作台能力一旦增加，就要同步补集成测试，而不是只补单元测试。

## AI Boundary Lessons

- 隐私边界必须拆分成独立层：
  - 本地脱敏
  - AI safe payload
  - provider 解析
  - provider adapter
- 默认 provider 应长期保持 `mock`，把外部依赖隔离在配置开关之后。
- 真正接外部 provider 之前，先用本地 `safe_stub` 验证“非 mock 只能吃脱敏 payload”。

## Ops And Self-Check Lessons

- 一旦系统有 SQLite、日志、runtime 文件夹和下载链路，就应该尽早补一个 `Support / Ops` 页面。
- 启动自检至少要覆盖：
  - runtime 根目录
  - uploads 目录
  - SQLite 目录
  - 日志目录
  - 配置模板存在性
  - AI 脱敏边界状态
- 自检结果不应该只打印到终端，最好也能在页面中回看。

## Admin UX Lessons

- 管理台不只要“能用”，还要让用户第一眼知道：
  - 这次导入的摘要是什么
  - 是否可继续下游
  - 如果不可继续，下一步该去哪修
- 模式 B 一定要显式提醒“先归档、后合并”，否则用户会误以为系统分组错了。
- 操作台表单尽量预填系统已推断出的名称、版本、公司名和材料 ID，减少复制粘贴错误。

## Real Sample Regression Lessons

- 对真实样本回归，不要只输出逐包结果，还要输出聚合摘要。
- 最小可比指标建议固定为：
  - `unknown`
  - `needs_review`
  - `low_quality`
  - `redactions`
- 这样每轮收敛都能直接比较趋势，而不是人工重新统计。
