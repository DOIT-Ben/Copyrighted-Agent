# P5-P8 问题与修复

## Issue 1 规则结论和 AI 说明混在一起

- 现象：Case 页和报告里，综合结论只有一段文本，运营同学很难分辨“规则已经确定的结果”和“AI 补充解释”。
- 影响范围：结果可解释性、人工复核效率、未来真实 provider 接入后的审计可信度。
- 根因：`ReviewResult` 只保留了单一 `conclusion` 字段。

### Fix

- 修复策略：
  - 在 `ReviewResult` 中增加 `rule_conclusion / ai_summary / ai_provider / ai_resolution`
  - 页面与报告分开展示规则结论和 AI 补充说明
- 变更位置：
  - `app/core/domain/models.py`
  - `app/core/pipelines/submission_pipeline.py`
  - `app/core/services/corrections.py`
  - `app/core/reports/renderers.py`
  - `app/web/pages.py`
- 回归结果：Case 页和 markdown 报告均可独立看到规则结论与 AI 补充说明。

## Issue 2 运行路径虽可配置，但运行前缺少显式体检

- 现象：一旦目录权限、SQLite 目录或日志目录出现问题，之前只能靠运行失败后再排查。
- 影响范围：启动稳定性、运维可见性、问题追溯速度。
- 根因：系统没有统一的启动自检层。

### Fix

- 修复策略：
  - 增加 `run_startup_self_check`
  - 覆盖运行目录、上传目录、SQLite 目录、日志目录、配置模板和 AI 边界
  - 在 `Support / Ops` 页面集中呈现
- 变更位置：
  - `app/core/services/startup_checks.py`
  - `app/api/main.py`
  - `app/web/pages.py`
- 回归结果：`/ops` 可查看自检结果，且相关单测通过。

## Issue 3 provider 切到非 mock 时，接口层还不够像“可接真实服务”的形态

- 现象：此前只有 `safe_stub`，虽然安全边界有了，但“真实 provider 的调用入口、超时和失败回退”还没有单独成层。
- 影响范围：后续真实 provider 接入效率、失败时的可控性、日志审计。
- 根因：AI service 仍以单文件分支逻辑为主，没有明确 adapter 层。

### Fix

- 修复策略：
  - 抽出 `app/core/reviewers/ai/adapters.py`
  - 新增 `external_http` skeleton
  - 增加 provider started / completed / failed 结构化日志
  - 缺配置或调用失败时，可按配置回退到 `mock`
- 变更位置：
  - `app/core/reviewers/ai/adapters.py`
  - `app/core/reviewers/ai/service.py`
  - `app/core/services/app_config.py`
- 回归结果：`external_http` 未配置时可安全 fallback 到 `mock`，单测通过。

## Issue 4 模式 B 的浏览器体验缺少“先归档、后合并”的明确提示

- 现象：如果用户把模式 B 当成“立即生成完整综合报告”的入口，会对 Case 数量和散落材料感到困惑。
- 影响范围：浏览器端可理解性、人工操作效率。
- 根因：首页和 Submission 页虽然已经支持模式 B，但没有把其真实工作方式讲清楚。

### Fix

- 修复策略：
  - 首页增加模式 B 指导面板
  - Submission 页增加 `Import Digest`
  - 操作台增加预填与提示文本，明确“先归档，再人工合并”
- 变更位置：
  - `app/web/pages.py`
  - `app/web/static/styles.css`
- 回归结果：Web 集成测试通过，页面信息架构更贴近运营后台。
