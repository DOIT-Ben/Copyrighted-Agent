from __future__ import annotations

import pytest

from tests.helpers.contracts import get_signature, require_symbol


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.parser
@pytest.mark.parametrize(
    ("module_name", "symbol_name"),
    [
        ("app.core.parsers.doc_binary", "DocBinaryParser"),
        ("app.core.parsers.docx_parser", "DocxParser"),
        ("app.core.parsers.pdf_parser", "PdfParser"),
        ("app.core.parsers.code_material", "CodeMaterialParser"),
    ],
)
def test_parser_classes_exist(module_name, symbol_name):
    parser_cls = require_symbol(module_name, symbol_name)
    assert parser_cls is not None


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.parser
def test_each_parser_class_exposes_parse_method():
    for module_name, symbol_name in [
        ("app.core.parsers.doc_binary", "DocBinaryParser"),
        ("app.core.parsers.docx_parser", "DocxParser"),
        ("app.core.parsers.pdf_parser", "PdfParser"),
        ("app.core.parsers.code_material", "CodeMaterialParser"),
    ]:
        parser_cls = require_symbol(module_name, symbol_name)
        assert hasattr(parser_cls, "parse")


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.parser
def test_structured_parsers_can_optionally_expose_parse_blocks():
    for module_name, symbol_name in [
        ("app.core.parsers.docx_parser", "DocxParser"),
        ("app.core.parsers.pdf_parser", "PdfParser"),
    ]:
        parser_cls = require_symbol(module_name, symbol_name)
        assert hasattr(parser_cls, "parse_blocks")


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.parser
def test_unified_parse_material_entry_exists_and_accepts_core_arguments():
    parse_material = require_symbol("app.core.parsers.service", "parse_material")
    signature = get_signature(parse_material)
    assert "file_path" in signature.parameters
    assert "material_type" in signature.parameters
