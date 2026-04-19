from __future__ import annotations

from app.core.domain.enums import MaterialType


FILENAME_KEYWORDS = {
    MaterialType.INFO_FORM.value: (
        "\u4fe1\u606f\u91c7\u96c6\u8868",
        "\u4fe1\u606f\u8868",
        "\u91c7\u96c6\u8868",
        "\u7533\u8bf7\u8868",
        "\u767b\u8bb0\u8868",
    ),
    MaterialType.SOURCE_CODE.value: (
        "\u6e90\u4ee3\u7801",
        "\u6e90\u7801",
        "\u4ee3\u7801",
        "\u7a0b\u5e8f",
    ),
    MaterialType.SOFTWARE_DOC.value: (
        "\u8f6f\u8457\u6587\u6863",
        "\u8f6f\u4ef6\u6587\u6863",
        "\u7528\u6237\u4f7f\u7528\u8bf4\u660e\u4e66",
        "\u7528\u6237\u624b\u518c",
        "\u8bf4\u660e\u4e66",
        "\u64cd\u4f5c\u624b\u518c",
        "\u6587\u6863",
    ),
    MaterialType.AGREEMENT.value: (
        "\u5408\u4f5c\u534f\u8bae",
        "\u5f00\u53d1\u534f\u8bae",
        "\u59d4\u6258\u534f\u8bae",
        "\u534f\u8bae",
    ),
}

INFO_FORM_CONTENT_HINTS = (
    "\u8f6f\u4ef6\u540d\u79f0",
    "\u8457\u4f5c\u6743\u4eba",
    "\u7248\u672c\u53f7",
    "\u516c\u53f8\u540d\u79f0",
)
SOFTWARE_DOC_CONTENT_HINTS = (
    "\u76ee\u5f55",
    "\u8fd0\u884c\u73af\u5883",
    "\u64cd\u4f5c\u6b65\u9aa4",
    "\u754c\u9762\u622a\u56fe",
    "\u7528\u6237\u624b\u518c",
    "\u7cfb\u7edf\u7b80\u4ecb",
    "\u4e3b\u8981\u529f\u80fd",
)
AGREEMENT_CONTENT_HINTS = (
    "\u7532\u65b9",
    "\u4e59\u65b9",
    "\u534f\u8bae",
    "\u5408\u4f5c\u5f00\u53d1",
    "\u59d4\u6258\u5f00\u53d1",
    "\u7b7e\u8ba2",
    "\u7b7e\u7f72",
)
SOURCE_CODE_TOKENS = (
    "def ",
    "class ",
    "return ",
    "#include",
    "public class ",
    "using system",
    "function ",
    "const ",
    "wx.",
)


def _from_filename(file_name: str) -> dict | None:
    lower_name = (file_name or "").lower()
    for material_type, keywords in FILENAME_KEYWORDS.items():
        if any(keyword.lower() in lower_name for keyword in keywords):
            return {"material_type": material_type, "confidence": 0.95, "reason": "filename"}
    return None


def _from_directory(directory_hint: str) -> dict | None:
    lower_dir = (directory_hint or "").lower()
    for material_type, keywords in FILENAME_KEYWORDS.items():
        if any(keyword.lower() in lower_dir for keyword in keywords):
            return {"material_type": material_type, "confidence": 0.8, "reason": "directory"}
    return None


def _looks_like_info_form(raw_content: str) -> bool:
    return "\u8f6f\u4ef6\u540d\u79f0" in raw_content and sum(
        1 for hint in INFO_FORM_CONTENT_HINTS if hint in raw_content
    ) >= 2


def _looks_like_source_code(lower_content: str) -> bool:
    return any(token in lower_content for token in SOURCE_CODE_TOKENS)


def _looks_like_software_doc(raw_content: str) -> bool:
    return sum(1 for hint in SOFTWARE_DOC_CONTENT_HINTS if hint in raw_content) >= 2


def _looks_like_agreement(raw_content: str) -> bool:
    if "\u7532\u65b9" in raw_content and "\u4e59\u65b9" in raw_content:
        return True
    return sum(1 for hint in AGREEMENT_CONTENT_HINTS if hint in raw_content) >= 2


def classify_material(file_name: str, content: str, directory_hint: str = "") -> dict:
    raw_content = content or ""
    lower_content = raw_content.lower()

    filename_match = _from_filename(file_name)
    if filename_match:
        return filename_match

    directory_match = _from_directory(directory_hint)
    if directory_match:
        return directory_match

    if _looks_like_info_form(raw_content):
        return {"material_type": MaterialType.INFO_FORM.value, "confidence": 0.9, "reason": "content"}

    if _looks_like_source_code(lower_content):
        return {"material_type": MaterialType.SOURCE_CODE.value, "confidence": 0.86, "reason": "content"}

    if _looks_like_software_doc(raw_content):
        return {"material_type": MaterialType.SOFTWARE_DOC.value, "confidence": 0.88, "reason": "content"}

    if _looks_like_agreement(raw_content):
        return {"material_type": MaterialType.AGREEMENT.value, "confidence": 0.9, "reason": "content"}

    return {"material_type": MaterialType.UNKNOWN.value, "confidence": 0.2, "reason": "fallback"}
