# 238 Page Segment Index Log

- 日期：2026-04-26
- 目标：在解析阶段生成可复用的页块索引，减少后续证据定位对纯关键词回扫的依赖。

## 本轮改动

- 新增页块切分器：
  - [page_segments.py](D:/Code/软著智能体/app/core/parsers/page_segments.py)
- 解析服务现在会把页块索引放入 `metadata_json.page_segments`：
  - [service.py](D:/Code/软著智能体/app/core/parsers/service.py)
- 证据锚点服务优先使用 `page_segments` 做定位：
  - [evidence_anchors.py](D:/Code/软著智能体/app/core/services/evidence_anchors.py)
- 提交流水线继续透传这部分结构到问题锚点：
  - [submission_pipeline.py](D:/Code/软著智能体/app/core/pipelines/submission_pipeline.py)

## 结果

- 解析结果里现在已经有一层轻量结构：
  - `page`
  - `line_start`
  - `line_end`
  - `text`
  - `headings`
  - `excerpt`
- 报告页里的“定位 / 摘录”会优先消费这层结构，再回退到文本回扫。

## 回归

- `py -m pytest tests/unit/test_page_segments_contracts.py tests/unit/test_evidence_anchor_service.py tests/integration/test_doc_binary_pipeline_regression.py tests/integration/test_web_mvp_contracts.py tests/e2e/test_browser_workflows.py -q`
- 结果：16 passed

## 下一步

- 把 PDF / DOCX 解析进一步升级成更真实的页对象与区块对象
- 给问题锚点增加“命中片段原文 + 所在页块标题”
- 在结果页增加更清晰的“证据路径”展示
