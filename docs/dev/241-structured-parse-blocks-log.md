# 241 Structured Parse Blocks Log

- Date: 2026-05-09
- Goal: improve report evidence positioning by upgrading parser output from flat text scans to lightweight structured blocks.

## Changes

- Added [structured_blocks.py](D:/Code/软著智能体/app/core/parsers/structured_blocks.py) to convert parser blocks into stable `page_segments`.
- Extended [docx_parser.py](D:/Code/软著智能体/app/core/parsers/docx_parser.py) with `parse_blocks()`:
  - extracts paragraph-level blocks from `word/document.xml`
  - marks `Heading*` styles as headings
- Extended [pdf_parser.py](D:/Code/软著智能体/app/core/parsers/pdf_parser.py) with `parse_blocks()`:
  - emits block records from decoded text streams
  - falls back to line-based blocks when structured extraction is unavailable
- Updated [service.py](D:/Code/软著智能体/app/core/parsers/service.py):
  - preserves existing `parse()` contract
  - stores `parse_blocks` in metadata
  - prefers structured blocks to build `page_segments`
  - falls back to legacy page-marker splitting when needed

## Fixes During This Round

- Fixed a cross-page merge bug in `build_segments_from_blocks()`.
- The original implementation incorrectly merged a heading from page 2 into the page 1 segment.
- The segment builder now flushes on page transitions and starts a fresh segment for the new page.

## Tests

- Added [test_structured_block_contracts.py](D:/Code/软著智能体/tests/unit/test_structured_block_contracts.py)
- Updated [test_parser_contracts.py](D:/Code/软著智能体/tests/unit/test_parser_contracts.py)
- Targeted regression:
  - `py -m pytest tests\\unit\\test_structured_block_contracts.py -q`
  - result: `2 passed`
- Parser and evidence regression:
  - `py -m pytest tests\\unit\\test_structured_block_contracts.py tests\\unit\\test_parser_contracts.py tests\\unit\\test_pdf_parser_regression.py tests\\unit\\test_page_segments_contracts.py tests\\unit\\test_evidence_anchor_service.py tests\\integration\\test_doc_binary_pipeline_regression.py tests\\integration\\test_web_mvp_contracts.py tests\\e2e\\test_browser_workflows.py -q`
  - result: `26 passed`

## Outcome

- Evidence anchors now have a cleaner path toward real document structure instead of only relying on plain text rescans.
- Report-side evidence display can evolve toward more precise section/page explanations without breaking the current parse pipeline.
- The main upload, review, report, and operator workflows remain compatible.
