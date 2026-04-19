from __future__ import annotations

import zlib

import pytest

from tests.helpers.contracts import require_symbol


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.parser
def test_pdf_parser_can_decode_tounicode_streams_without_external_dependencies(tmp_path):
    PdfParser = require_symbol("app.core.parsers.pdf_parser", "PdfParser")

    cmap_stream = b"""
/CIDInit /ProcSet findresource begin
12 dict begin
begincmap
1 begincodespacerange
<0000> <FFFF>
endcodespacerange
4 beginbfchar
<0A38> <5408>
<058C> <4F5C>
<097F> <534F>
<1BE9> <8BAE>
endbfchar
endcmap
end
"""
    content_stream = b"BT <0A38>Tj <058C>Tj <097F>Tj <1BE9>Tj ET"
    pdf_bytes = (
        b"%PDF-1.4\n"
        + b"1 0 obj\n<< /Length 0 /Filter /FlateDecode >>\nstream\n"
        + zlib.compress(content_stream)
        + b"\nendstream\nendobj\n"
        + b"2 0 obj\n<< /Length 0 /Filter /FlateDecode >>\nstream\n"
        + zlib.compress(cmap_stream)
        + b"\nendstream\nendobj\n"
    )
    file_path = tmp_path / "agreement.pdf"
    file_path.write_bytes(pdf_bytes)

    text = PdfParser().parse(file_path)

    assert "合作协议" in text
