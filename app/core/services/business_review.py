from __future__ import annotations


RETURN_LEVEL_RULES = {
    "software_name_present",
    "company_present",
    "software_name_exact_match",
    "version_exact_match",
    "completion_date_match",
    "party_order_match",
    "code_readable",
    "code_page_strategy",
    "code_desensitized",
    "doc_required_sections",
    "agreement_dates_valid",
    "agreement_party_order",
    "agreement_stamp_signature",
}

NAIVE_LEVEL_RULES = {
    "version_present",
    "info_sensitive_terms",
    "cross_material_terms_match",
    "code_format_clean",
    "code_sensitive_terms",
    "code_logic_supports_doc",
    "doc_page_count",
    "doc_sensitive_terms",
    "doc_terms_consistent",
    "doc_header_footer_valid",
    "agreement_alias_consistent",
    "agreement_key_people",
    "agreement_approval_sheet",
    "agreement_sensitive_terms",
    "agreement_typo_terms",
}


def business_level(issue: dict) -> tuple[str, str]:
    rule_key = str(issue.get("rule_key", "") or "").strip()
    severity = str(issue.get("severity", "") or "minor").strip().lower()
    if rule_key in RETURN_LEVEL_RULES:
        return ("退回级问题", "danger")
    if rule_key in NAIVE_LEVEL_RULES:
        return ("弱智问题", "warning")
    if severity == "severe":
        return ("退回级问题", "danger")
    if severity == "moderate":
        return ("弱智问题", "warning")
    return ("警告项", "info")


def summarize_business_levels(issues: list[dict]) -> dict[str, int]:
    summary = {"退回级问题": 0, "弱智问题": 0, "警告项": 0}
    for issue in issues:
        label, _ = business_level(issue)
        summary[label] += 1
    return summary


__all__ = ["NAIVE_LEVEL_RULES", "RETURN_LEVEL_RULES", "business_level", "summarize_business_levels"]
