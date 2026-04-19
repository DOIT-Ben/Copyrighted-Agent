from __future__ import annotations

import pytest

from tests.helpers.contracts import require_symbol


@pytest.mark.unit
@pytest.mark.contract
def test_parse_quality_marks_ole_binary_text_as_low_quality():
    assess_parse_quality = require_symbol("app.core.parsers.quality", "assess_parse_quality")
    result = assess_parse_quality(
        raw_text="\xd0\xcf\x11\xe0def hello():\n    return 1\n",
        clean_text="def hello():\n    return 1\n",
        parser_name="DocBinaryParser",
    )
    assert result["quality_level"] == "low"
    assert result["is_text_usable"] is False
    assert "ole_binary_header" in result["quality_flags"]
    assert result["review_reason_code"] == "text_too_short"
    assert result["legacy_doc_bucket"] == "binary_noise"


@pytest.mark.unit
@pytest.mark.contract
def test_parse_quality_marks_clean_docx_text_as_usable():
    assess_parse_quality = require_symbol("app.core.parsers.quality", "assess_parse_quality")
    result = assess_parse_quality(
        raw_text="\u76ee\u5f55\n\u8fd0\u884c\u73af\u5883\n\u64cd\u4f5c\u6b65\u9aa4\n",
        clean_text="\u76ee\u5f55\n\u8fd0\u884c\u73af\u5883\n\u64cd\u4f5c\u6b65\u9aa4\n",
        parser_name="DocxParser",
    )
    assert result["quality_level"] in {"high", "medium"}
    assert result["is_text_usable"] is True


@pytest.mark.unit
@pytest.mark.contract
def test_parse_quality_allows_extracted_legacy_doc_text_when_signal_is_good():
    assess_parse_quality = require_symbol("app.core.parsers.quality", "assess_parse_quality")
    extracted_text = (
        "\u7532\u65b9\uff1a\u6c5f\u897f\u4e2d\u533b\u836f\u5927\u5b66\n"
        "\u4e59\u65b9\uff1a\u676d\u5dde\u6781\u5149\u7075\u6108\u4eba\u5de5\u667a\u80fd\u79d1\u6280\u6709\u9650\u516c\u53f8\n"
        "\u7ecf\u53cc\u65b9\u53cb\u597d\u534f\u5546\uff0c\u5c31\u5408\u4f5c\u5f00\u53d1\u201c\u5c45\u5bb6\u5eb7\u590d\u966a\u4f34\u673a\u5668\u4eba\u201dV1.0\u8fbe\u6210\u4ee5\u4e0b\u534f\u8bae\u3002\n"
    )
    result = assess_parse_quality(
        raw_text=extracted_text,
        clean_text=extracted_text,
        parser_name="DocBinaryParser",
        file_header_bytes=b"\xd0\xcf\x11\xe0",
    )
    assert result["quality_level"] in {"high", "medium"}
    assert result["is_text_usable"] is True
    assert "binary_doc_text_extracted" in result["quality_flags"]
    assert result["review_reason_code"] == "clean_text_ready"
    assert result["legacy_doc_bucket"] == "usable_text"


@pytest.mark.unit
@pytest.mark.contract
def test_parse_quality_allows_structured_legacy_info_form_when_noise_is_low():
    assess_parse_quality = require_symbol("app.core.parsers.quality", "assess_parse_quality")
    extracted_text = (
        "软件基本信息\n"
        "软件名称：线上中医心理辅导与干预平台系统\n"
        "版本号：V1.0\n"
        "软件简称：中医心理系统\n"
        "软件分类：应用软件\n"
        "开发完成日期：2026年3月22日\n"
        "著作权人：江西中医药大学\n"
        "合作方：杭州极光灵愈人工智能科技有限公司\n"
        "开发的硬件环境：Windows 11\n"
        "运行的硬件环境：Windows 11 操作系统\n"
        "软件开发环境：Visual Studio Code\n"
    )

    result = assess_parse_quality(
        raw_text=extracted_text,
        clean_text=extracted_text,
        parser_name="DocBinaryParser",
        file_header_bytes=b"\xd0\xcf\x11\xe0",
    )

    assert result["quality_level"] in {"high", "medium"}
    assert result["is_text_usable"] is True
    assert "binary_doc_text_extracted" in result["quality_flags"]
    assert result["review_reason_code"] == "clean_text_ready"
