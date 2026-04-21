# 162 脱敏包回传与审查阶段闭环日志

## 时间
- 2026-04-22

## 本轮目标
- 打通“先脱敏、再人工回传、再继续审查”的业务闭环。
- 为提交、项目补充更细粒度的 `review_stage`，让前后端都能感知当前处于哪一阶段。
- 把脱敏包上传能力接入 API 与 HTML 操作台。
- 补齐浏览器级回归，覆盖完整人工脱敏链路。

## 已完成实现
- 在 `Submission` 和 `Case` 模型上新增 `review_stage` 字段。
- 在导入流水线中区分以下阶段：
  - `intake_processing`
  - `desensitized_ready`
  - `desensitized_uploaded`
  - `review_processing`
  - `review_completed`
- 在人工脱敏模式下，初次导入后停在 `awaiting_manual_review + desensitized_ready`。
- 新增脱敏包上传服务 `upload_desensitized_package(...)`，支持 ZIP 回传并匹配脱敏件。
- 上传脱敏包后会：
  - 覆盖材料内容
  - 覆盖脱敏产物路径
  - 写入上传元信息
  - 将阶段推进到 `desensitized_uploaded`
  - 保持状态为 `awaiting_manual_review`
- 继续审查后会推进到 `review_processing`，完成后落到 `review_completed`。
- API 新增脱敏包上传入口。
- HTML 操作台新增脱敏包上传入口，并补充阶段提示。
- 首页与批次详情页补充审查策略、审查阶段展示。
- 下载响应头改为 ASCII fallback + `filename*`，修复带中文文件名时在 `wsgiref` 下的 `Content-Disposition` 编码异常。

## 主要影响文件
- `app/core/domain/models.py`
- `app/core/pipelines/submission_pipeline.py`
- `app/core/services/corrections.py`
- `app/api/main.py`
- `app/web/view_helpers.py`
- `app/web/page_home.py`
- `app/web/page_submission.py`
- `tests/integration/test_manual_correction_api.py`
- `tests/integration/test_operator_console_and_exports.py`
- `tests/e2e/test_browser_workflows.py`

## 回归结果
- 编译检查通过：
  - `D:\Soft\python310\python.exe -m py_compile ...`
- 业务回归通过：
  - `D:\Soft\python310\python.exe -m pytest tests/integration/test_api_contracts.py tests/integration/test_manual_correction_api.py tests/integration/test_operator_console_and_exports.py tests/integration/test_web_mvp_contracts.py tests/e2e/test_browser_workflows.py -q`
- 结果：
  - `passed=19 failed=0 skipped=0 xfailed=0`

## 备注
- 本次提交刻意不包含无关前端样式文件与历史未纳管日志，避免污染业务闭环提交范围。
