# 168 审查配置模板联动日志

## 本轮目标

- 为审查配置增加可直接点击的模板入口，降低导入前配置成本。
- 保留模板选择在提交结果、案例页、报告页中的可追溯性。
- 完成前端联动、语法修复、测试验证和运行态确认。

## 本轮完成

- 在 `app/core/services/review_profile.py` 中补齐模板定义与归一化逻辑：
  - `REVIEW_PROFILE_PRESETS`
  - `PRESET_MAP`
  - `apply_review_profile_preset(...)`
  - `preset_title(...)`
- 在 `app/web/review_profile_widgets.py` 中新增模板按钮行和隐藏字段 `review_profile_preset`。
- 在 `app/web/view_helpers.py` 中补齐模板点击联动脚本，支持一键回填：
  - 审查侧重
  - 严格程度
  - LLM 补充指令
  - 审查维度勾选项
- 修复 `app/web/view_helpers.py` 中因 HTML f-string 内嵌 JS 字面量 `{}` 导致的语法错误。
- 在 `app/web/static/styles.css` 中补齐模板按钮行与激活态样式。
- 更新 `tests/integration/test_web_mvp_contracts.py`，覆盖模板入口渲染与模板驱动的重跑审查持久化。

## 验证记录

### 编译

```powershell
D:\Soft\python310\python.exe -m py_compile app\core\services\review_profile.py app\web\review_profile_widgets.py app\web\view_helpers.py tests\integration\test_web_mvp_contracts.py
```

- 结果：通过

### 集成测试

```powershell
D:\Soft\python310\python.exe -m pytest tests\integration\test_web_mvp_contracts.py -q
```

- 结果：`passed=5 failed=0`

### 运行态确认

- 干净重启后确认：
  - Frontend: `http://127.0.0.1:18080/`
  - Bridge: `http://127.0.0.1:18011/review`
- 首页返回 `200`
- 样式表返回 `200`
- 首页已确认包含：
  - `data-review-preset="source_code_strict"`
  - `review_profile_preset`
  - `review-profile-preset-row`
  - `审查配置`
  - `data-async-upload-url="/api/submissions/async"`

## 设计取舍

- 模板入口采用轻量按钮而不是额外分步页，避免打断现有导入流程。
- 用户仍然可以在模板基础上继续微调维度和补充说明。
- 结果页继续展示当前审查配置，保证“用了什么模板/角度”可回溯。

## 当前状态

- 审查配置模板功能已打通。
- 当前最新前端实例已运行在 `18080`，可直接访问验证。
