from __future__ import annotations

import re

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


def _extract_right_acquisition(text: str) -> str:
    patterns = [
        r"权利取得方式[：:\s]*([^\n\r]+)",
        r"取得方式[：:\s]*([^\n\r]+)",
        r"著作权取得[：:\s]*([^\n\r]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return str(match.group(1)).strip()
    return ""


def review_info_form_text(text: str) -> dict:
    metadata = {
        "software_name": extract_software_name(text),
        "version": extract_version(text),
        "company_name": extract_company_name(text),
        "completion_dates": extract_date_candidates(text),
        "party_sequence": extract_party_sequence(text),
        "right_acquisition": _extract_right_acquisition(text),
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
                **_anchor(field="缺失字段", section="基础信息", hint="检查信息采集表是否完整填写", material_area="信息采集表首页"),
            }
        )

    right_acquisition = metadata["right_acquisition"]
    party_sequence = metadata["party_sequence"]
    if right_acquisition and party_sequence:
        if "原始取得" in right_acquisition and len(party_sequence) > 1:
            issues.append(
                {
                    "severity": "moderate",
                    "category": "权利取得方式",
                    "rule_key": "right_acquisition_consistent",
                    "desc": "信息采集表权利取得方式为原始取得，但申请人列表包含多个主体，可能存在不一致。",
                    "suggest": "核对权利取得方式与申请人数量是否匹配，多人参与时通常选择继受取得。",
                    **_anchor(field="权利取得方式", section="权利取得", hint="检查权利取得方式与申请人数量是否匹配", material_area="信息采集表权利取得部分"),
                }
            )
        elif "继受取得" in right_acquisition and len(party_sequence) == 1:
            issues.append(
                {
                    "severity": "minor",
                    "category": "权利取得方式",
                    "rule_key": "right_acquisition_consistent",
                    "desc": "信息采集表权利取得方式为继受取得，但申请人列表仅有一个主体，请确认是否合理。",
                    "suggest": "单人申请通常选择原始取得，除非确实存在权利转让情况。",
                    **_anchor(field="权利取得方式", section="权利取得", hint="检查权利取得方式与申请人数量是否匹配", material_area="信息采集表权利取得部分"),
                }
            )

    issues.extend(
        scan_sensitive_terms(
            text,
            rule_key="info_form_sensitive_terms",
            category="敏感词排查",
            severity="moderate",
        )
    )

    return {"issues": issues, "metadata": metadata}
