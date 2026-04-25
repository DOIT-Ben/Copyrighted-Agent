# 171 审查重点规则页日志

## 目标

- 将不同审查重点拆成独立小页面。
- 支持查看每个重点的内部规则、编辑规则并保存。
- 保存后同步到当前批次审查配置，并支持基于新规则直接重跑审查。
- 让 LLM 调用显式接收这组更新后的规则。

## 本轮完成

- 新增规则册服务：
  - [review_rulebook.py](D:\Code\软著智能体\app\core\services\review_rulebook.py)
  - 内置七个审查重点的默认规则：
    - 基础信息完整性
    - 材料完整性
    - 跨材料一致性
    - 源码可审查性
    - 说明文档规范
    - 协议与权属规范
    - AI 补充研判
- 扩展审查配置：
  - [review_profile.py](D:\Code\软著智能体\app\core\services\review_profile.py)
  - `review_profile` 现在持久化 `dimension_rulebook`
  - 重跑审查表单不会再丢失自定义规则
- 新增规则编辑页：
  - [page_review_rule.py](D:\Code\软著智能体\app\web\page_review_rule.py)
  - 支持查看规则名称、目标、检查点、LLM 聚焦提示
  - 支持：
    - `保存规则`
    - `保存并重跑审查`
- 新增后端路由：
  - `GET /submissions/{submission_id}/review-rules/{dimension_key}`
  - `POST /submissions/{submission_id}/review-rules/{dimension_key}`
- 新增规则保存服务：
  - [corrections.py](D:\Code\软著智能体\app\core\services\corrections.py)
  - `update_submission_review_dimension_rule(...)`
  - 会写入更正留痕并保存图数据
- 新增页面入口：
  - 批次页审查配置区增加规则入口
  - 人工处理页当前配置区增加规则入口
  - 项目页维度明细可点击进入对应规则页
  - 报告页维度表和审查配置区可点击进入对应规则页
- LLM 调用接入新规则：
  - [adapters.py](D:\Code\软著智能体\app\core\reviewers\ai\adapters.py)
  - 外部 HTTP 请求体新增 `dimension_rulebook`
  - [minimax_bridge.py](D:\Code\软著智能体\app\tools\minimax_bridge.py)
  - Prompt 明确要求尊重 `dimension_rulebook`

## 测试

### 编译

```powershell
D:\Soft\python310\python.exe -m py_compile app\core\services\review_rulebook.py app\core\services\review_profile.py app\core\services\corrections.py app\core\reviewers\ai\adapters.py app\tools\minimax_bridge.py app\web\page_review_rule.py app\web\page_submission.py app\web\page_case.py app\web\page_report.py app\api\main.py tests\integration\test_web_mvp_contracts.py
```

- 结果：通过

### 集成测试

```powershell
D:\Soft\python310\python.exe -m pytest tests\integration\test_web_mvp_contracts.py -q
```

- 结果：`passed=6 failed=0`

新增覆盖：
- `test_review_rule_page_can_save_rule_and_persist_to_submission`

## 运行态验证

- 前端：`http://127.0.0.1:18080/`
- 使用样例：
  - `input\软著材料\2501_软著材料.zip`
- 实际验证通过：
  - 上传成功，返回批次：
    - `sub_7af8a53a1d`
  - 批次页存在规则入口：
    - `review-rules/source_code`
  - 规则页打开成功，页面包含：
    - `编辑规则`
    - `保存并重跑审查`
    - `检查规则`
    - `LLM 聚焦提示`
  - 真实保存后 API 返回的批次配置已更新：
    - `title = 源码核验规则`
    - `objective = 重点检查源码可读性和命名一致性。`
    - `llm_focus = 优先总结源码相关高风险问题。`
    - `checkpoints` 已写入并结构化保存

## 当前状态

- 审查重点已支持拆分为独立规则页。
- 用户可以查看、编辑、保存规则，并将其同步到当前批次审查配置。
- 规则更新后可直接基于新规则重跑审查，并随 LLM 请求一起发送。
