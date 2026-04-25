# 170 前端文案去说明化日志

## 目标

- 清理页面中暴露给用户的“布局解释型”“开发者口吻型”文案。
- 保持页面简约、可用，只保留必要操作提示。

## 本轮调整

- 首页导入区文案收短：
  - `上传一个软著包，然后按你的处理路径继续` -> `上传软著包`
  - `导入区前置并加宽` -> `选择处理方式`
  - `左侧负责上传，右侧负责说明` -> `处理方式`
  - `浏览器端导入说明` -> `使用提示`
- 首页头部与面板副标题收短：
  - `上传即进入批次工作台` -> `上传后自动进入批次`
  - `首页只保留导入、模式选择和结果入口...` -> `上传 ZIP，选择模式并开始处理。`
  - `如果想先看脱敏件...` -> `可直接审查，也可先脱敏再继续。`
  - 首页多个 panel description 改为更短的操作型表述。
- 全局头部辅助说明标题：
  - [view_helpers.py](D:\Code\软著智能体\app\web\view_helpers.py) 中 `当前说明` -> `提示`
- 审查配置区域提示收短：
  - [review_profile_widgets.py](D:\Code\软著智能体\app\web\review_profile_widgets.py) 中
    `用于控制 LLM 的补充审查视角，不会直接篡改规则引擎。`
    -> `用于补充审查重点。`

## 验证

- `D:\Soft\python310\python.exe -m py_compile app\web\page_home.py app\web\review_profile_widgets.py app\web\view_helpers.py`
  - 通过
- `D:\Soft\python310\python.exe -m pytest tests\integration\test_web_mvp_contracts.py -q`
  - `5/5 passed`
- 运行态验证：
  - 前端：`http://127.0.0.1:18080/`
  - 旧文案已确认从实际页面消失
  - 新的简化文案已确认生效

## 当前结论

- 页面更接近“简约可用”的目标。
- 这轮主要清理了首页和全局头部中最显眼的说明型文案。
