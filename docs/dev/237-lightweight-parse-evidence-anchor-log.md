# 237 Lightweight Parse Evidence Anchor Log

- 日期：2026-04-26
- 目标：基于现有 `clean_text / desensitized_text` 能力，补一层轻量解析锚点，让报告页展示更接近真实命中的页码、行号和摘录。

## 本轮改动

- 新增服务：[evidence_anchors.py](D:/Code/软著智能体/app/core/services/evidence_anchors.py)
  - 从材料文本中抽取页码标记
  - 按规则关键词定位章节/字段
  - 为问题补充 `page` / `line` / `excerpt`
- 在提交流水线中接入问题锚点增强：
  - [submission_pipeline.py](D:/Code/软著智能体/app/core/pipelines/submission_pipeline.py)
- 结果页补充展示：
  - `定位：约第 N 页`
  - `摘录：...`
  - 修改文件：[page_report.py](D:/Code/软著智能体/app/web/page_report.py)

## 回归

- `py -m py_compile app/core/services/evidence_anchors.py app/core/pipelines/submission_pipeline.py app/web/page_report.py tests/unit/test_evidence_anchor_service.py`
- `py -m pytest tests/unit/test_evidence_anchor_service.py tests/integration/test_web_mvp_contracts.py tests/e2e/test_browser_workflows.py -q`
- 结果：13 passed

## 下一步

- 把 PDF / DOCX 解析进一步升级成真正的“页对象”或“区块对象”
- 将规则命中与真实页块关联，而不是仅靠关键词回扫
- 在报告页支持更明确的“第几页 / 哪一段 / 命中哪条规则”
