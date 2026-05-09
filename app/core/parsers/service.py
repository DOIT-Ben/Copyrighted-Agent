from __future__ import annotations

from pathlib import Path

from app.core.domain.enums import MaterialType
from app.core.parsers.code_material import CodeMaterialParser
from app.core.parsers.doc_binary import DocBinaryParser
from app.core.parsers.docx_parser import DocxParser
from app.core.parsers.page_segments import build_page_segments
from app.core.parsers.pdf_parser import PdfParser
from app.core.parsers.structured_blocks import build_segments_from_blocks
from app.core.parsers.quality import assess_parse_quality
from app.core.privacy.desensitization import desensitize_text
from app.core.services.submission_insights import label_for_parse_reason
from app.core.utils.text import (
    clean_text,
    extract_company_name,
    extract_software_name,
    extract_version,
    strip_control_chars,
)


def parse_material(file_path: str | Path, material_type: str) -> dict:
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()
    file_header_bytes = file_path.read_bytes()[:8]

    if suffix == ".docx":
        parser = DocxParser()
        parser_name = "DocxParser"
    elif suffix == ".pdf":
        parser = PdfParser()
        parser_name = "PdfParser"
    elif material_type == MaterialType.SOURCE_CODE.value:
        parser = CodeMaterialParser()
        parser_name = "CodeMaterialParser"
    else:
        parser = DocBinaryParser()
        parser_name = "DocBinaryParser"

    raw_text = strip_control_chars(parser.parse(file_path))
    cleaned_text = clean_text(raw_text)
    parse_blocks = getattr(parser, "parse_blocks", None)
    blocks = parse_blocks(file_path) if callable(parse_blocks) else []
    quality = assess_parse_quality(
        raw_text=raw_text,
        clean_text=cleaned_text,
        parser_name=parser_name,
        file_header_bytes=file_header_bytes,
    )
    page_segments = build_segments_from_blocks(blocks) if blocks else build_page_segments(cleaned_text)
    metadata = {
        "software_name": extract_software_name(cleaned_text),
        "version": extract_version(cleaned_text),
        "company_name": extract_company_name(cleaned_text),
        "line_count": len(cleaned_text.splitlines()) if cleaned_text else 0,
        "parse_blocks": blocks,
        "page_segments": page_segments,
        "parser_name": parser_name,
        "parse_quality": quality,
        "garbled_ratio": quality["garbled_ratio"],
        "diagnostics": {
            "parse_reason_code": str(quality.get("review_reason_code", "") or ""),
            "parse_reason_label": label_for_parse_reason(str(quality.get("review_reason_code", "") or "")),
            "quality_level": str(quality.get("quality_level", "") or ""),
        },
    }
    privacy = desensitize_text(cleaned_text, metadata=metadata)
    metadata["privacy"] = privacy["summary"]
    return {
        "raw_text": raw_text,
        "clean_text": cleaned_text,
        "desensitized_text": privacy["text"],
        "metadata": metadata,
        "parser_name": parser_name,
        "privacy": privacy,
        "quality": quality,
    }
