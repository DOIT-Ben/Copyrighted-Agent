# 163 审查维度可视化日志

## 时间
- 2026-04-24

## 目标
- 让用户在项目详情页直接看懂“软著审查是从哪些维度完成的”。
- 不再只展示问题列表和 AI 摘要，而是补齐维度总览、维度明细和报告内的维度说明。

## 本轮改动
- 新增共享维度构建器：
  - `app/core/services/review_dimensions.py`
- 维度覆盖内容：
  - 基础信息完整性
  - 材料完整性
  - 跨材料一致性
  - 源码可审查性
  - 说明文档规范
  - 协议文本规范
  - AI 补充研判
- `Case` 详情页改为先展示：
  - 审查维度总览
  - 维度明细
  - 风险队列
  - AI 补充研判
  - 材料矩阵
  - 报告查看
- 项目报告 markdown 增加 `审查维度` 章节，下载报告时也能看到维度说明。
- 导入流程和人工重跑流程统一复用同一套维度构建逻辑，避免页面和报告口径不一致。

## 影响文件
- `app/core/services/review_dimensions.py`
- `app/core/reports/renderers.py`
- `app/core/pipelines/submission_pipeline.py`
- `app/core/services/corrections.py`
- `app/web/page_case.py`
- `tests/integration/test_web_mvp_contracts.py`

## 验证
- 编译：
  - `D:\Soft\python310\python.exe -m py_compile app\core\services\review_dimensions.py app\core\reports\renderers.py app\core\pipelines\submission_pipeline.py app\core\services\corrections.py app\web\page_case.py tests\integration\test_web_mvp_contracts.py`
- 集成回归：
  - `D:\Soft\python310\python.exe -m pytest tests\integration\test_web_mvp_contracts.py tests\integration\test_operator_console_and_exports.py tests\integration\test_manual_correction_api.py -q`
- 浏览器回归：
  - `D:\Soft\python310\python.exe -m pytest tests\e2e\test_browser_workflows.py -q`

## 结果
- 集成回归通过：`13/13`
- 浏览器回归通过：`3/3`

## 备注
- 这轮改动优先解决“看不懂系统怎么审查”的问题。
- 当前维度说明以规则引擎与材料信号为主，后续如果要继续增强，可以在每个维度下面补更细的证据跳转和材料片段预览。
