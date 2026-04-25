# 172 审查规则对照与恢复日志

## 目标

- 在规则页增加“当前规则 vs 默认规则”的对照视图。
- 增加“恢复默认规则”动作，避免规则越改越偏。

## 本轮完成

- [review_rulebook.py](D:\Code\软著智能体\app\core\services\review_rulebook.py)
  - 新增：
    - `default_dimension_rule(...)`
    - `reset_profile_dimension_rule(...)`
- [corrections.py](D:\Code\软著智能体\app\core\services\corrections.py)
  - 新增：
    - `reset_submission_review_dimension_rule(...)`
  - 会写入更正留痕并保存批次图数据
- [page_review_rule.py](D:\Code\软著智能体\app\web\page_review_rule.py)
  - 新增“默认对照”面板
  - 新增“恢复默认规则”按钮
  - 显示：
    - 默认规则名称 / 当前规则名称
    - 默认目标 / 当前目标
    - 默认 LLM 聚焦 / 当前 LLM 聚焦
    - 默认规则数 / 当前规则数
    - 默认检查规则列表
    - 当前检查规则列表
- [main.py](D:\Code\软著智能体\app\api\main.py)
  - 规则保存路由新增 `restore_default` 分支
- [page_submission.py](D:\Code\软著智能体\app\web\page_submission.py)
  - 更正留痕标签新增：
    - `恢复默认规则`

## 修复

- 规则页渲染时遗漏引入 `table`，导致页面返回 `500`
- 已修复并重新验证通过

## 测试

```powershell
D:\Soft\python310\python.exe -m py_compile app\web\page_review_rule.py tests\integration\test_web_mvp_contracts.py
D:\Soft\python310\python.exe -m pytest tests\integration\test_web_mvp_contracts.py -q
```

- 结果：`passed=6 failed=0`

## 运行态验证

- 前端：`http://127.0.0.1:18080/`
- 规则页已确认显示：
  - `默认对照`
  - `恢复默认规则`
  - `默认检查规则`
  - `当前检查规则`

## 当前状态

- 规则页已具备：
  - 查看
  - 编辑
  - 保存
  - 保存并重跑
  - 与默认规则对照
  - 恢复默认
