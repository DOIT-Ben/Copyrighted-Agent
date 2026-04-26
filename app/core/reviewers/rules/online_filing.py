from __future__ import annotations

from app.core.services.online_filing import normalize_online_filing


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


def _looks_precise_address(value: str) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    keywords = sum(1 for token in ["省", "市", "区", "县"] if token in text)
    return keywords >= 2


def review_online_filing_payload(
    payload: dict | None,
    *,
    case_payload: dict | None = None,
    info_form: dict | None = None,
    agreement: dict | None = None,
) -> dict:
    filing = normalize_online_filing(payload)
    case_data = dict(case_payload or {})
    info_data = dict(info_form or {})
    agreement_data = dict(agreement or {})
    if not filing.get("has_data"):
        return {"issues": [], "metadata": filing}

    issues: list[dict] = []

    category = str(filing.get("software_category", "") or "")
    if category and category != "应用软件":
        issues.append(
            {
                "severity": "moderate",
                "category": "分类准确性",
                "rule_key": "online_category_valid",
                "desc": f"在线填报中的软件分类为“{category}”，建议确认是否应统一为“应用软件”。",
                "suggest": "核对在线填报的软件分类选项，避免与常规软著材料口径冲突。",
                **_anchor(field="软件分类", section="在线填报", hint="检查在线填报中的软件分类字段", material_area="在线填报基础信息"),
            }
        )

    development_mode = str(filing.get("development_mode", "") or "")
    applicants = list(filing.get("applicants", []) or [])
    if development_mode:
        expected_collaboration = len(applicants) > 1 or bool(agreement_data.get("party_sequence"))
        if expected_collaboration and "合作" not in development_mode:
            issues.append(
                {
                    "severity": "moderate",
                    "category": "开发方式",
                    "rule_key": "online_development_mode_valid",
                    "desc": f"在线填报中的开发方式为“{development_mode}”，但当前材料存在多方主体信号，建议确认是否应填写合作开发。",
                    "suggest": "核对开发方式是否需要体现“合作开发”或“原创 + 合作开发”。",
                    **_anchor(field="开发方式", section="在线填报", hint="检查在线填报中的开发方式字段", material_area="在线填报基础信息"),
                }
            )

    subject_type = str(filing.get("subject_type", "") or "")
    company_name = str(case_data.get("company_name", "") or info_data.get("company_name", "") or agreement_data.get("company_name", "") or "")
    if subject_type and company_name:
        expected = ""
        if any(token in company_name for token in ["学校", "大学", "学院"]):
            expected = "事业单位"
        elif any(token in company_name for token in ["公司", "有限公司", "科技"]):
            expected = "企业法人"
        if expected and expected not in subject_type:
            issues.append(
                {
                    "severity": "moderate",
                    "category": "主体类型",
                    "rule_key": "online_subject_type_valid",
                    "desc": f"在线填报中的主体类型为“{subject_type}”，但申请主体“{company_name}”更像“{expected}”。",
                    "suggest": "核对在线填报主体类型与申请主体性质是否一致。",
                    **_anchor(field="主体类型", section="在线填报", hint="检查在线填报中的主体类型字段", material_area="在线填报主体信息"),
                }
            )

    address = str(filing.get("address", "") or "")
    certificate_address = str(filing.get("certificate_address", "") or "")
    if (address and not _looks_precise_address(address)) or (certificate_address and not _looks_precise_address(certificate_address)):
        issues.append(
            {
                "severity": "minor",
                "category": "地址精度",
                "rule_key": "online_address_precise",
                "desc": "在线填报中的地址信息精度不足，建议至少精确到省、市、区县。",
                "suggest": "补全地址和电子证书地址，避免只写到省或市一级。",
                **_anchor(field="地址信息", section="在线填报", hint="检查在线填报中的地址和电子证书地址字段", material_area="在线填报地址信息"),
            }
        )

    completion_date = str(filing.get("completion_date", "") or "")
    apply_date = str(filing.get("apply_date", "") or "")
    info_completion_dates = [str(item).strip() for item in list(info_data.get("completion_dates", []) or []) if str(item).strip()]
    if completion_date and info_completion_dates and completion_date not in info_completion_dates:
        issues.append(
            {
                "severity": "severe",
                "category": "日期口径",
                "rule_key": "online_dates_consistent",
                "desc": f"在线填报中的开发完成日期为“{completion_date}”，与信息采集表中的日期信号“{'、'.join(info_completion_dates)}”不一致。",
                "suggest": "统一在线填报和信息采集表中的开发完成日期。",
                **_anchor(field="开发完成日期", section="在线填报", hint="检查在线填报中的开发完成日期字段", material_area="在线填报日期信息"),
            }
        )
    if apply_date and completion_date and apply_date <= completion_date:
        issues.append(
            {
                "severity": "severe",
                "category": "日期口径",
                "rule_key": "online_dates_consistent",
                "desc": f"在线填报中的申请日期“{apply_date}”不应早于或等于开发完成日期“{completion_date}”。",
                "suggest": "核对申请日期与开发完成日期的先后逻辑。",
                **_anchor(field="申请日期", section="在线填报", hint="检查在线填报中的申请日期和开发完成日期先后关系", material_area="在线填报日期信息"),
            }
        )

    return {"issues": issues, "metadata": filing}


__all__ = ["review_online_filing_payload"]
