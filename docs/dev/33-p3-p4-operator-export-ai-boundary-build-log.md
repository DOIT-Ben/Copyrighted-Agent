# P3-P4 构建记录

## 日期

- 2026-04-19

## 浏览器操作台与导出

- 新增 `app/core/services/app_logging.py`
- 新增 `app/core/services/exports.py`
- 在 `app/api/main.py` 增加 HTML operator routes：
  - `change-type`
  - `assign-case`
  - `create-case`
  - `merge-cases`
  - `rerun-review`
- 在 `app/api/main.py` 增加下载 routes：
  - `downloads/reports/{report_id}`
  - `downloads/materials/{material_id}/{artifact_kind}`
  - `downloads/submissions/{submission_id}/bundle`
  - `downloads/logs/app`
- 在导入、人工纠偏、下载动作中写入结构化日志
- 在 `app/web/pages.py` 补充：
  - `Operator Console`
  - `Export Center`
  - `Artifact Browser`
  - raw / clean / desensitized / privacy 预览与下载入口
- 在 `app/web/static/styles.css` 补充操作表单、下载 chips、预览块样式
- 新增集成测试 `tests/integration/test_operator_console_and_exports.py`

## AI 边界与配置

- 新增 `app/core/services/app_config.py`
- 新增配置项：
  - `SOFT_REVIEW_HOST`
  - `SOFT_REVIEW_PORT`
  - `SOFT_REVIEW_AI_ENABLED`
  - `SOFT_REVIEW_AI_PROVIDER`
  - `SOFT_REVIEW_AI_REQUIRE_DESENSITIZED`
  - `SOFT_REVIEW_AI_TIMEOUT_SECONDS`
- 在 `app/core/reviewers/ai/service.py` 增加：
  - `resolve_case_ai_provider`
  - `SUPPORTED_AI_PROVIDERS`
  - `safe_stub` provider
  - 非 mock provider 的脱敏校验
- 在 `app/core/privacy/desensitization.py` 增加：
  - `AI_SAFE_POLICY`
  - `is_ai_safe_case_payload`
  - `llm_safe` 标记
- 在 `submission_pipeline.py` 与 `corrections.py` 中改为配置驱动选择 provider
- 在 `app/api/main.py` 中改为从配置读取启动 host / port
- 新增单元测试：
  - `tests/unit/test_app_config_contracts.py`
  - `tests/unit/test_ai_provider_boundary_contracts.py`

## 阶段结论

- 浏览器操作台、导出、日志链路已形成最小闭环。
- AI 接入边界已经从“约定”升级为“代码强约束”。
- 当前系统仍默认本地 `mock`，但已经具备安全接入真实 provider 的预备结构。
