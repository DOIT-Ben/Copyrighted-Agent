from __future__ import annotations

from app.core.reviewers.rules.sensitive_terms import scan_sensitive_terms
from app.core.utils.text import extract_company_name, extract_date_candidates, extract_party_sequence, extract_software_name, extract_version


def _anchor(*, field: str = "", section: str = "", hint: str = "", material_area: str = "") -> dict:
    data = {
        "field_label": field,
        "section_label": section,
        "anchor_hint": hint,
    }
    if material_area:
        data["evidence_anchor"] = {
            "field": field,
            "section": section,
            "material_area": material_area,
            "hint": hint,
        }
    return data


def review_info_form_text(text: str) -> dict:
    metadata = {
        "software_name": extract_software_name(text),
        "version": extract_version(text),
        "company_name": extract_company_name(text),
        "completion_dates": extract_date_candidates(text),
        "party_sequence": extract_party_sequence(text),
    }
    issues: list[dict] = []
    missing_fields: list[str] = []
    if not metadata["software_name"]:
        missing_fields.append("软件名称")
        issues.append(
            {
                "severity": "severe",
                "category": "基础字段",
                "rule_key": "software_name_present",
                "desc": "未从信息采集表中提取到软件名称。",
                **_anchor(field="软件名称", section="基础信息", hint="检查信息采集表首页的软件名称字段", material_area="信息采集表首页"),
            }
        )
    if not metadata["version"]:
        missing_fields.append("版本号")
        issues.append(
            {
                "severity": "moderate",
                "category": "基础字段",
                "rule_key": "version_present",
                "desc": "未从信息采集表中提取到版本号。",
                **_anchor(field="版本号", section="基础信息", hint="检查信息采集表首页的版本号字段", material_area="信息采集表首页"),
            }
        )
    if not metadata["company_name"]:
        missing_fields.append("申请主体")
        issues.append(
            {
                "severity": "severe",
                "category": "主体字段",
                "rule_key": "company_present",
                "desc": "未从信息采集表中提取到申请主体或单位名称。",
                **_anchor(field="申请主体", section="基础信息", hint="检查信息采集表中的著作权人或申请主体字段", material_area="信息采集表首页"),
            }
        )
    if missing_fields:
        issues.append(
            {
                "severity": "minor",
                "category": "输出要求",
                "rule_key": "missing_fields_listed",
                "desc": f"信息采集表缺少关键信息：{'、'.join(missing_fields)}。",
                "suggest": "补齐缺失字段后再进行跨材料一致性审查。",
                **_anchor(field="基础字段", section="基础信息", hint="逐项核对软件名称、版本号、申请主体等首页字段", material_area="信息采集表首页"),
            }
        )
    issues.extend(
        scan_sensitive_terms(
            text,
            rule_key="info_sensitive_terms",
            category="敏感词排查",
            severity="moderate",
        )
    )
    return {"issues": issues, "metadata": metadata}
