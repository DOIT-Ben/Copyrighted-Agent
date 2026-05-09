from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from tests.helpers.contracts import require_symbol


def _write_docx(path: Path, document_xml: str) -> Path:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<?xml version='1.0' encoding='UTF-8'?><Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'></Types>")
        archive.writestr("word/document.xml", document_xml)
    return path


@pytest.mark.unit
@pytest.mark.contract
def test_docx_parser_parse_blocks_extracts_paragraph_structure(tmp_path: Path):
    DocxParser = require_symbol("app.core.parsers.docx_parser", "DocxParser")
    document_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
      <w:body>
        <w:p>
          <w:pPr><w:pStyle w:val="Heading1"/></w:pPr>
          <w:r><w:t>一、运行环境</w:t></w:r>
        </w:p>
        <w:p><w:r><w:t>硬件要求：8G 内存</w:t></w:r></w:p>
      </w:body>
    </w:document>"""
    file_path = _write_docx(tmp_path / "sample.docx", document_xml)
    blocks = DocxParser().parse_blocks(file_path)
    assert len(blocks) == 2
    assert blocks[0]["is_heading"] is True
    assert "运行环境" in blocks[0]["text"]


@pytest.mark.unit
@pytest.mark.contract
def test_build_segments_from_blocks_keeps_heading_excerpt():
    build_segments_from_blocks = require_symbol("app.core.parsers.structured_blocks", "build_segments_from_blocks")
    segments = build_segments_from_blocks(
        [
            {"page": 1, "text": "一、运行环境", "is_heading": True},
            {"page": 1, "text": "硬件要求：8G 内存", "is_heading": False},
            {"page": 2, "text": "二、安装说明", "is_heading": True},
        ]
    )
    assert len(segments) == 2
    assert "一、运行环境" in segments[0]["headings"][0]
    assert segments[0]["page"] == 1
    assert segments[1]["page"] == 2
