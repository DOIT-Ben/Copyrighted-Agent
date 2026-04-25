# 166 报告阅读页升级日志

日期：2026-04-24

## 背景

原有报告页虽然存在，但主体是把 Markdown 原文直接放进 `pre` 标签中展示。用户能够看到内容，但阅读体验仍然像在看源文件，而不是在看审查结果。

## 本次处理

1. 重做 `reports/{report_id}` 页面，改为结构化结果页。
2. 支持按报告类型展示不同结果：
   - 项目综合报告：审查结论、审查维度、发现的问题、审查材料、AI 补充说明
   - 材料审查报告：材料摘要、规则问题
   - 批次汇总报告：批次摘要、文件结果
3. 保留原始 Markdown，但折叠到“原始 Markdown”区域，避免抢占主阅读区。
4. 在报告页顶部加入两个导出动作：
   - `保存为 MD`
   - `保存为 PDF`
5. `保存为 PDF` 采用浏览器打印保存方案，避免额外引入 PDF 渲染依赖。
6. 补充打印样式，打印时隐藏侧边导航与无关控件，聚焦报告正文。

## 涉及文件

- `app/web/page_report.py`
- `app/web/static/styles.css`
- `tests/integration/test_web_mvp_contracts.py`

## 验证

- 集成测试通过：
  - `python -m pytest tests\integration\test_web_mvp_contracts.py -q`
- 在线页面校验通过：
  - 报告页存在 `window.print()`
  - 报告页存在 `report-overview`
  - 报告页存在 `report-dimensions`
  - 报告页存在 `report-source`

## 当前结果

用户现在可以直接在报告页阅读审查结果和分析内容，不需要先下载 Markdown 文件。若需要归档或外发，可继续点击保存为 MD，或通过打印保存为 PDF。
