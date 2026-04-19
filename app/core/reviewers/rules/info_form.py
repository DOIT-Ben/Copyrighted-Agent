from __future__ import annotations

from app.core.utils.text import extract_company_name, extract_software_name, extract_version


def review_info_form_text(text: str) -> dict:
    metadata = {
        "software_name": extract_software_name(text),
        "version": extract_version(text),
        "company_name": extract_company_name(text),
    }
    issues: list[dict] = []
    if not metadata["software_name"]:
        issues.append({"severity": "moderate", "category": "字段缺失", "desc": "未提取到软件名称"})
    return {"issues": issues, "metadata": metadata}

