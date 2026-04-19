# P10-P13 构建日志

## 日期

- 2026-04-19

## Step 1

- 细化 `parse_quality` 输出：
  - `review_reason_code`
  - `review_reason_label`
  - `legacy_doc_bucket`
  - `legacy_doc_bucket_label`
- 把这些字段贯通到：
  - pipeline triage
  - material report
  - Submission review queue
  - `input_runner` 聚合摘要

## Step 2

- 从真实材料抽出最小 legacy `.doc` 回归语料：
  - `usable_text/agreement_2505.doc`
  - `partial_fragments/info_form.doc`
  - `partial_fragments/agreement_2502.doc`
  - `binary_noise/source_code_2502.doc`
- 为真实语料补 `README.md`，明确每个样本的预期桶位与用途。

## Step 3

- 新增/更新解析质量相关测试：
  - `tests/integration/test_legacy_doc_corpus_regression.py`
  - `tests/unit/test_parse_quality_contracts.py`
  - `tests/unit/test_input_runner_contracts.py`
  - `tests/unit/test_report_contracts.py`

## Step 4

- 新增浏览器级 E2E：`tests/e2e/test_browser_workflows.py`
- 覆盖：
  - Mode A 上传
  - Submission 页面
  - HTML 更正动作
  - rerun review
  - report page
  - app log download
  - `/ops`
  - Mode B create case / merge case / rerun review
- 实现方式改为真实本地 HTTP 服务，不依赖 `TestClient`。

## Step 5

- 收紧 `external_http` provider 契约：
  - `EXTERNAL_HTTP_REQUEST_VERSION`
  - `EXTERNAL_HTTP_RESPONSE_VERSION`
  - `build_external_http_request_payload(...)`
  - `normalize_external_http_response(...)`
  - `external_http_error_code(...)`
- Service 层补 provider 失败日志的错误码归一化。

## Step 6

- 启动自检增加 `ai_provider_readiness`：
  - `external_http` 开启但 `ai_endpoint` 为空时给 warning
  - `external_http` 开启但 `ai_model` 为空时给 warning

## Step 7

- 新增运行时清理工具：`app/tools/runtime_cleanup.py`
- 设计原则：
  - 默认 dry-run
  - 仅清理 `submissions / uploads / logs`
  - active log 永远跳过
  - SQLite 只输出 `manual_backup_only` 策略，不自动删除
  - apply 前校验所有候选路径必须位于允许根目录内

## Step 8

- 修复 Windows 下 SQLite 清理脆弱点：
  - `clear_database()` 先尝试 `unlink()`
  - 若命中文件占用，则退化为按表清空
- 这让全量回归不再依赖“当前没有其他进程打开 DB 文件”。

## Step 9

- `/ops` 页面增加运行时清理命令入口：
  - `py -m app.tools.runtime_cleanup`
- 同步补页面断言测试。

## Step 10

- 完成全量回归、真实样本验证、runtime cleanup dry-run 验证。
- 把计划、构建、问题、验证、手册全部落入 `docs/dev`。
