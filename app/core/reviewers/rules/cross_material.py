from __future__ import annotations


def _normalized(value: str) -> str:
    return str(value or "").strip()


def _first_text(values) -> str:
    for value in list(values or []):
        text = _normalized(value)
        if text:
            return text
    return ""


def _joined(values) -> str:
    return " / ".join(_normalized(item) for item in list(values or []) if _normalized(item))


def _observed_map(
    info_form: dict,
    source_code: dict,
    software_doc: dict,
    agreement: dict,
    online_filing: dict | None = None,
) -> dict[str, dict[str, str]]:
    observed = {
        "信息采集表": {
            "software_name": _normalized(info_form.get("software_name", "")),
            "version": _normalized(info_form.get("version", "")),
            "completion_date": _first_text(info_form.get("completion_dates", [])),
            "party_order": _joined(info_form.get("party_sequence", [])),
        },
        "源代码": {
            "software_name": _normalized(source_code.get("software_name", "")),
            "version": _normalized(source_code.get("version", "")),
            "completion_date": "",
            "party_order": "",
        },
        "说明文档": {
            "software_name": _normalized(software_doc.get("software_name", "")),
            "version": _normalized(software_doc.get("version", "")),
            "completion_date": "",
            "party_order": "",
        },
        "合作协议": {
            "software_name": _normalized(agreement.get("software_name", "")),
            "version": _normalized(agreement.get("version", "")),
            "completion_date": _first_text(agreement.get("agreement_dates", [])),
            "party_order": _joined(agreement.get("party_sequence", [])),
        },
    }
    filing = dict(online_filing or {})
    if filing:
        observed["在线填报"] = {
            "software_name": _normalized(filing.get("software_name", "")),
            "version": _normalized(filing.get("version", "")),
            "completion_date": _normalized(filing.get("completion_date", "")),
            "party_order": _joined(filing.get("applicants", [])),
        }
    return observed


def _format_field_values(observed: dict[str, dict[str, str]], field: str) -> str:
    parts = [f"{label}={values[field]}" for label, values in observed.items() if values.get(field)]
    return "；".join(parts)


def _keyword_families(*values: str) -> set[str]:
    families: set[str] = set()
    combined = " ".join(_normalized(item).lower() for item in values if _normalized(item))
    if not combined:
        return families
    for token in ["系统", "平台", "app", "小程序"]:
        if token in combined:
            families.add(token)
    return families


def _feature_overlap(source_code: dict, software_doc: dict) -> tuple[list[str], list[str]]:
    doc_terms = [str(item).strip() for item in list(software_doc.get("feature_terms", []) or []) if str(item).strip()]
    code_terms = {str(item).strip().lower() for item in list(source_code.get("feature_terms", []) or []) if str(item).strip()}
    matched = [term for term in doc_terms if term.lower() in code_terms]
    return doc_terms, matched


def review_case_consistency(
    info_form: dict,
    source_code: dict,
    software_doc: dict,
    agreement: dict | None = None,
    online_filing: dict | None = None,
) -> dict:
    issues: list[dict] = []
    agreement = dict(agreement or {})
    filing = dict(online_filing or {})
    observed = _observed_map(info_form, source_code, software_doc, agreement, filing)

    names = {values.get("software_name", "") for values in observed.values() if values.get("software_name")}
    versions = {values.get("version", "") for values in observed.values() if values.get("version")}

    if len(names) > 1:
        detail = _format_field_values(observed, "software_name")
        issues.append(
            {
                "severity": "severe",
                "category": "名称一致性",
                "rule_key": "software_name_exact_match",
                "desc": f"不同材料中的软件名称不一致。当前识别到：{detail}。",
                "suggest": "统一信息采集表、源代码、说明文档、合作协议和在线填报中的软件全称，确保逐字一致。",
            }
        )
    if len(versions) > 1:
        detail = _format_field_values(observed, "version")
        issues.append(
            {
                "severity": "severe",
                "category": "版本号一致性",
                "rule_key": "version_exact_match",
                "desc": f"不同材料中的版本号不一致。当前识别到：{detail}。",
                "suggest": "统一所有材料中的版本号写法和大小写格式。",
            }
        )

    terminology_values = [values.get("software_name", "") for values in observed.values()]
    families = _keyword_families(*terminology_values)
    if len(families) > 1:
        issues.append(
            {
                "severity": "moderate",
                "category": "术语口径一致性",
                "rule_key": "cross_material_terms_match",
                "desc": f"不同材料中对软件形态的称呼不统一，检测到：{'、'.join(sorted(families))}。",
                "suggest": "统一使用一种对外口径，例如统一写为“系统”或“平台”，避免混用。",
            }
        )

    info_date = _first_text(info_form.get("completion_dates", []))
    agreement_date = _first_text(agreement.get("agreement_dates", []))
    online_date = _normalized(filing.get("completion_date", ""))
    if info_date and agreement_date and info_date != agreement_date:
        issues.append(
            {
                "severity": "severe",
                "category": "开发完成日期一致性",
                "rule_key": "completion_date_match",
                "desc": f"信息采集表中的开发完成日期与合作协议中的日期信号不一致。信息采集表={info_date}；合作协议={agreement_date}。",
                "suggest": "统一开发完成日期、协议日期和填报日期口径。",
            }
        )
    if info_date and online_date and info_date != online_date:
        issues.append(
            {
                "severity": "severe",
                "category": "开发完成日期一致性",
                "rule_key": "completion_date_match",
                "desc": f"信息采集表与在线填报的开发完成日期不一致。信息采集表={info_date}；在线填报={online_date}。",
                "suggest": "统一信息采集表、合作协议和在线填报中的开发完成日期口径。",
            }
        )

    info_party_sequence = [str(item).strip() for item in list(info_form.get("party_sequence", []) or []) if str(item).strip()]
    agreement_party_sequence = [str(item).strip() for item in list(agreement.get("party_sequence", []) or []) if str(item).strip()]
    online_party_sequence = [str(item).strip() for item in list(filing.get("applicants", []) or []) if str(item).strip()]
    if info_party_sequence and agreement_party_sequence:
        compare_len = min(len(info_party_sequence), len(agreement_party_sequence))
        if compare_len and info_party_sequence[:compare_len] != agreement_party_sequence[:compare_len]:
            issues.append(
                {
                    "severity": "severe",
                    "category": "申请人排序一致性",
                    "rule_key": "party_order_match",
                    "desc": f"合作协议中的各方排序与信息采集表中的主体顺序不一致。信息采集表={'、'.join(info_party_sequence)}；合作协议={'、'.join(agreement_party_sequence)}。",
                    "suggest": "统一合作协议、信息采集表和系统填报中的申请人顺序。",
                }
            )
    if info_party_sequence and online_party_sequence:
        compare_len = min(len(info_party_sequence), len(online_party_sequence))
        if compare_len and info_party_sequence[:compare_len] != online_party_sequence[:compare_len]:
            issues.append(
                {
                    "severity": "severe",
                    "category": "申请人排序一致性",
                    "rule_key": "party_order_match",
                    "desc": f"在线填报中的申请人顺序与信息采集表不一致。信息采集表={'、'.join(info_party_sequence)}；在线填报={'、'.join(online_party_sequence)}。",
                    "suggest": "统一信息采集表、合作协议和在线填报中的申请人顺序。",
                }
            )

    doc_terms, matched_terms = _feature_overlap(source_code, software_doc)
    if len(doc_terms) >= 2 and len(matched_terms) < max(1, min(2, len(doc_terms) // 2)):
        issues.append(
            {
                "severity": "moderate",
                "category": "功能呼应",
                "rule_key": "code_logic_supports_doc",
                "desc": f"说明文档提到的功能点与源代码信号呼应不足。文档功能词：{'、'.join(doc_terms[:6])}；源码命中：{'、'.join(matched_terms[:6]) or '未识别'}。",
                "suggest": "补充与文档功能对应的核心代码、函数名或关键流程片段。",
            }
        )

    return {"issues": issues}
