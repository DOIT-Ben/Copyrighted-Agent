from __future__ import annotations


def review_case_consistency(info_form: dict, source_code: dict, software_doc: dict) -> dict:
    issues: list[dict] = []

    names = {
        value
        for value in (
            info_form.get("software_name", ""),
            source_code.get("software_name", ""),
            software_doc.get("software_name", ""),
        )
        if value
    }
    versions = {
        value
        for value in (
            info_form.get("version", ""),
            source_code.get("version", ""),
            software_doc.get("version", ""),
        )
        if value
    }

    if len(names) > 1:
        issues.append(
            {
                "severity": "moderate",
                "category": "名称一致性",
                "desc": "不同材料中的软件名称不一致，请核对统一命名",
            }
        )
    if len(versions) > 1:
        issues.append(
            {
                "severity": "moderate",
                "category": "版本一致性",
                "desc": "不同材料中的版本号不一致，请统一版本描述",
            }
        )

    return {"issues": issues}

