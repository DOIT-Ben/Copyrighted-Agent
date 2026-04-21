# 161 Manual Desensitized Review Workflow Log

## Date
- 2026-04-21

## Goal
- 补齐“双模式审查”业务闭环。
- 支持两条路径：
  - 直接审查
  - 先脱敏后继续审查

## Delivered
- 在 `Submission` 增加 `review_strategy` 字段，默认值为 `auto_review`。
- 在提交流水线中新增 `manual_desensitized_review` 分支：
  - 继续完成导入、解析、分类、脱敏、材料级产物生成。
  - 单项目模式下先不生成项目级审查结果和报告。
  - 批次状态和项目状态标记为 `awaiting_manual_review`。
- 复用既有重建逻辑，新增 `continue_case_review_from_desensitized()`：
  - 从脱敏优先状态继续进入正式项目审查。
  - 生成项目级审查结果和报告。
  - 写入 correction 留痕。
- API 与 HTML 动作新增继续审查入口：
  - `POST /api/cases/{case_id}/continue-review`
  - `POST /submissions/{submission_id}/actions/continue-review`
- 首页重构为清晰导入入口：
  - 导入模式
  - 审查策略
  - ZIP 上传
- 批次相关页面重构为更清晰的业务视图：
  - 批次总览
  - 批次详情
  - 产物浏览
  - 人工干预台
  - 导出中心
- 在材料页增加“脱敏工作台”。
- 在人工干预台增加“脱敏后继续审查”表单入口。

## Main Files
- `app/core/domain/models.py`
- `app/core/domain/enums.py`
- `app/core/pipelines/submission_pipeline.py`
- `app/core/services/corrections.py`
- `app/api/main.py`
- `app/web/page_home.py`
- `app/web/page_submission.py`
- `app/web/view_helpers.py`

## Tests
- `py -3 -m py_compile app\core\domain\models.py app\core\domain\enums.py app\core\pipelines\submission_pipeline.py app\core\services\corrections.py app\api\main.py app\web\view_helpers.py app\web\page_home.py app\web\page_submission.py tests\integration\test_api_contracts.py tests\integration\test_manual_correction_api.py tests\integration\test_web_mvp_contracts.py tests\integration\test_operator_console_and_exports.py`
- `py -3 -m pytest tests\integration\test_api_contracts.py tests\integration\test_manual_correction_api.py tests\integration\test_web_mvp_contracts.py tests\integration\test_operator_console_and_exports.py tests\integration\test_mode_a_pipeline_contracts.py tests\integration\test_mode_b_pipeline_contracts.py tests\integration\test_sqlite_persistence.py tests\integration\test_privacy_and_directory_intake.py -q`
- `py -3 -m pytest tests\unit\test_web_source_contracts.py tests\unit\test_domain_contracts.py tests\unit\test_ops_status_contracts.py -q`

## Result
- 双模式审查已经形成可执行闭环。
- 用户现在可以：
  - 上传时直接选择审查策略。
  - 下载脱敏文件查看。
  - 在人工干预台手动继续项目审查。
  - 在继续审查后查看报告与导出结果。
