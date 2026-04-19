from __future__ import annotations

import pytest

from tests.helpers.contracts import require_symbol


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.parser
def test_doc_binary_parser_can_extract_utf16le_lines_from_ole_like_content(tmp_path):
    DocBinaryParser = require_symbol("app.core.parsers.doc_binary", "DocBinaryParser")

    file_path = tmp_path / "legacy_agreement.doc"
    file_path.write_bytes(
        b"\xd0\xcf\x11\xe0"
        + "甲方：江西中医药大学\n乙方：杭州极光灵愈人工智能科技有限公司\n合作开发协议\n".encode("utf-16-le")
    )

    text = DocBinaryParser().parse(file_path)

    assert "甲方" in text
    assert "乙方" in text
    assert "协议" in text
