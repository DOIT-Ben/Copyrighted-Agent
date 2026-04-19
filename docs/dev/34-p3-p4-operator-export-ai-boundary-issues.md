# P3-P4 问题与修复

## Issue 1

- 现象：报告下载接口回归测试失败，下载路由返回 500。
- 影响范围：报告、材料、submission bundle、日志下载链路。
- 根因：本地 FastAPI 兼容层的 `Response` 构造器不支持 `media_type` 参数，而导出接口直接按真实 FastAPI 的写法创建响应。

## Fix 1

- 修复策略：改为先创建 `Response`，再显式设置 `response.media_type`。
- 变更位置：`app/api/main.py`
- 回归结果：下载相关集成测试恢复通过。

## Issue 2

- 现象：下载接口修好后，测试继续失败，原因是响应对象没有 `.content` 属性。
- 影响范围：本地测试客户端与真实 FastAPI 响应接口的兼容性。
- 根因：本地兼容层只有 `body`，没有补齐常见别名属性。

## Fix 2

- 修复策略：在 `fastapi/responses.py` 为 `Response` 增加 `content` 属性，映射到 `body`。
- 变更位置：`fastapi/responses.py`
- 回归结果：`test_operator_console_and_exports` 全部通过。

## Issue 3

- 现象：在当前代码结构里，AI 只靠调用约定避免泄露原始字段，一旦后续有人接入非 mock provider，存在把未脱敏 payload 直接送出去的风险。
- 影响范围：隐私边界、真实 provider 接入安全性、后续运维可控性。
- 根因：provider 选择、配置读取、payload 安全校验没有独立成层。

## Fix 3

- 修复策略：
  - 新增 `AppConfig` 统一读取配置
  - 新增 `resolve_case_ai_provider`
  - 新增 `safe_stub` 作为非 mock 的本地验证 provider
  - 新增 `is_ai_safe_case_payload`，强制非 mock provider 只能吃脱敏 payload
- 变更位置：
  - `app/core/services/app_config.py`
  - `app/core/reviewers/ai/service.py`
  - `app/core/privacy/desensitization.py`
  - `app/core/pipelines/submission_pipeline.py`
  - `app/core/services/corrections.py`
- 回归结果：新增 AI 边界单测通过，开启 `safe_stub` 后真实管线烟测通过。

## 当前残留风险

- 老 `.doc` 样本仍大量落入 `low_quality` / `needs_manual_review` 路径，后续仍需 parser hardening。
- 当前非 mock provider 只有 `safe_stub`，真实网络调用适配器尚未接入。
- `download_app_log` 仍是“先读后记日志”，因此导出的日志不会包含本次下载事件；现阶段属于可接受行为。
