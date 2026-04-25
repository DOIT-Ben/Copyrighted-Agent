# 169 首页导入区重排日志

## 目标

- 解决首页导入组件被左侧说明内容挤压的问题。
- 将上传与审查配置表单提升为首页主操作区。
- 将说明性内容收敛到右侧辅助区域，减少主路径干扰。

## 实施

- 在 [page_home.py](D:\Code\软著智能体\app\web\page_home.py) 中新增 `_import_form_rebalanced()`。
- 通过后定义覆盖 `_import_form()`，让首页渲染切换到新布局而不触碰旧实现。
- 新布局调整为：
  - 左侧主列：导入模式、审查策略、ZIP 上传、审查配置、开始分析
  - 右侧辅列：导入路径说明、两种处理路径摘要、结果去向说明
- 在 [styles.css](D:\Code\软著智能体\app\web\static\styles.css) 中补充并调整：
  - `import-console-grid-wide`
  - `import-console-form-primary`
  - `import-console-side-compact`
  - `import-console-copy-compact`
  - `helper-chip-row-tight`
- 调整首页导入区两栏比例，主表单列明显加宽，并将导入区堆叠断点从 `1520px` 下调到 `1280px`。

## 验证

- `D:\Soft\python310\python.exe -m py_compile app\web\page_home.py`
  - 通过
- `D:\Soft\python310\python.exe -m pytest tests\integration\test_web_mvp_contracts.py -q`
  - `5/5 passed`
- 运行态验证：
  - 前端：`http://127.0.0.1:18080/`
  - Bridge：`http://127.0.0.1:18011/review`
  - 首页返回 `200`
  - 样式返回 `200`
  - 页面已包含：
    - `import-console-grid-wide`
    - `import-console-form-primary`
    - `import-console-side-compact`

## 结果

- 首页导入区不再被说明内容压缩。
- 上传表单现在是首页主视觉和主操作区。
- 说明内容仍然保留，但被收纳为次级信息，不再抢占主流程宽度。
