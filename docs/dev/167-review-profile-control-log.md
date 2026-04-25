# 167 审查配置前端可控化日志

日期：2026-04-24

## 背景

用户希望前端不只展示审查结果，还能展示处理逻辑，并允许控制审查角度、维度和 LLM 补充研判的重点。

## 本次处理

1. 新增统一的审查配置模型：
   - 启用维度
   - 审查侧重
   - 严格程度
   - LLM 补充指令
2. 首页导入表单支持直接配置审查参数。
3. 人工干预台支持修改当前批次的审查配置，并“保存配置后重跑审查”。
4. 审查配置会随批次保存到 `submission.review_profile`。
5. 每次项目审查都会把当次配置快照写入 `review_result.review_profile_snapshot`。
6. 审查维度展示支持按启用维度过滤。
7. LLM 外部请求载荷新增 `review_profile`，用于控制补充研判角度。
8. MiniMax bridge prompt 已接入 `review_profile`，要求模型遵守：
   - enabled_dimensions
   - focus_mode
   - strictness
   - llm_instruction
9. 批次页、项目页、报告页均新增“审查配置”展示区。
10. 导出的项目 Markdown 报告会记录本次审查配置。

## 涉及文件

- `app/core/services/review_profile.py`
- `app/core/services/review_dimensions.py`
- `app/core/reviewers/ai/adapters.py`
- `app/core/reviewers/ai/service.py`
- `app/core/pipelines/submission_pipeline.py`
- `app/core/services/corrections.py`
- `app/api/main.py`
- `app/web/review_profile_widgets.py`
- `app/web/page_home.py`
- `app/web/page_submission.py`
- `app/web/page_case.py`
- `app/web/page_report.py`
- `app/web/static/styles.css`
- `tests/integration/test_web_mvp_contracts.py`

## 验证

- `python -m py_compile ...` 通过
- `python -m pytest tests\integration\test_web_mvp_contracts.py -q` 通过
- 新增覆盖：
  - 首页存在审查配置控件
  - 重跑审查后配置会持久化
  - 项目页和报告页显示审查配置

## 当前结果

用户现在可以在前端显式控制审查维度和 LLM 补充审查角度，并在结果页看到“这份结论是按什么配置审出来的”。

## 当前边界

本次开放的是“审查配置”和“LLM 补充视角”，不是让用户直接修改底层规则引擎。规则引擎仍保持稳定、可追溯。
