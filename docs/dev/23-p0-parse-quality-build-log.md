# P0 构建记录

## 日期

- 2026-04-19

## 本轮变更摘要

- 修复 ZIP 中文文件名乱码恢复逻辑：
  - 新增 `cp437 -> utf-8`
  - 新增 `cp437 -> gb18030`
  - 新增成员名可读性评分，自动选择更可信的解码结果
- 新增解析质量模块 `app/core/parsers/quality.py`
- 在 `parse_material` 中注入 parse quality 元数据
- 在 submission pipeline 中加入：
  - first pass / second pass 分类调试字段
  - low quality content gate
  - unknown reason
  - needs manual review triage
- 增强 material report，补充 parse quality 与 triage 信息
- 增强本地 `input_runner`，输出 `needs_review` 和 `low_quality`
- 在 Submission 详情页新增待复核队列

## 关键代码位置

- `app/core/services/zip_ingestion.py`
- `app/core/parsers/quality.py`
- `app/core/parsers/service.py`
- `app/core/services/material_classifier.py`
- `app/core/pipelines/submission_pipeline.py`
- `app/core/reports/renderers.py`
- `app/tools/input_runner.py`
- `app/web/pages.py`

## 新增测试

- `tests/unit/test_zip_filename_repair_contracts.py`
- `tests/unit/test_parse_quality_contracts.py`
- `tests/integration/test_parser_quality_regression.py`

## 直接结果

- `2502`：
  - 由 3 个 unknown 收敛到 1 个 unknown
  - 其余 3 份材料可根据修复后的文件名正确归类
- `2505`：
  - 由 2 个 unknown 收敛到 0 个 unknown
  - `合作协议.doc`、`信息采集表.doc`、`软著文档.docx`、`源代码.docx` 均可正确归类

## 阶段结论

- P0 已经解决“真实样本无法解释地失败”的核心问题。
- 当前剩余问题不再是“为什么失败不知道”，而是“`.doc` 文本质量低，需要人工复核或更强解析器”。
- 这为下一阶段人工纠错工作流提供了稳定输入。
