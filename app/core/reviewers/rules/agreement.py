from __future__ import annotations

from datetime import date, datetime
import re

from app.core.reviewers.rules.sensitive_terms import scan_sensitive_terms
from app.core.utils.text import extract_company_name, extract_date_candidates, extract_party_sequence, extract_software_name, extract_version


def _parse_cn_date(raw: str) -> date | None:
    text = str(raw or "").strip()
    if not text:
        return None
    normalized = text.replace("年", "-").replace("月", "-").replace("日", "").replace("/", "-").replace(".", "-")
    parts = [item for item in normalized.split("-") if item]
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        return None
    try:
        return date(int(parts[0]), int(parts[1]), int(parts[2]))
    except ValueError:
        return None


def _extract_labeled_dates(text: str, labels: list[str]) -> list[date]:
    values: list[date] = []
    for label in labels:
        matches = re.findall(rf"{label}[：:\s]{{0,4}}(\d{{4}}[-年/.]\d{{1,2}}[-月/.]\d{{1,2}}(?:日)?)", str(text or ""))
        for raw in matches:
            parsed = _parse_cn_date(raw)
            if parsed and parsed not in values:
                values.append(parsed)
    return values


def review_agreement_text(text: str) -> dict:
    issues: list[dict] = []
    metadata = {
        "software_name": extract_software_name(text),
        "version": extract_version(text),
        "company_name": extract_company_name(text),
        "agreement_dates": extract_date_candidates(text),
        "party_sequence": extract_party_sequence(text),
    }

    if "签定" in text:
        issues.append(
            {
                "severity": "minor",
                "category": "协议文字质量",
                "rule_key": "agreement_typo_terms",
                "desc": '发现“签定”写法，应统一修正为“签订”。',
                "suggest": "将协议中的“签定”统一修改为“签订”。",
            }
        )

    alias_markers = [marker for marker in ["甲方", "乙方", "丙方", "丁方", "子甲方", "副甲方"] if marker in text]
    if "子甲方" in text or "副甲方" in text:
        issues.append(
            {
                "severity": "moderate",
                "category": "代称体系",
                "rule_key": "agreement_alias_consistent",
                "desc": "合作协议中出现了“子甲方”或“副甲方”等不规范代称，建议统一为甲乙丙丁等标准称谓。",
            }
        )
    elif alias_markers and sum(marker in text for marker in ["甲方", "乙方"]) and ("天干" in text or "生肖" in text):
        issues.append(
            {
                "severity": "moderate",
                "category": "代称体系",
                "rule_key": "agreement_alias_consistent",
                "desc": "合作协议疑似混用了多套代称体系，请统一整份协议中的各方称谓。",
            }
        )

    if not any(keyword in text for keyword in ["项目负责人", "负责人", "指导老师"]):
        issues.append(
            {
                "severity": "moderate",
                "category": "人员要素",
                "rule_key": "agreement_key_people",
                "desc": "合作协议中未识别到项目负责人或指导老师等关键人员信息。",
                "suggest": "补充项目负责人、指导老师或其他关键责任人信息。",
            }
        )

    dates = re.findall(r"\d{4}[-年/.]\d{1,2}[-月/.]\d{1,2}(?:日)?", text)
    normalized_dates = {date.strip() for date in dates if date.strip()}
    if len(normalized_dates) > 1:
        issues.append(
            {
                "severity": "severe",
                "category": "日期逻辑",
                "rule_key": "agreement_dates_valid",
                "desc": "合作协议中存在多个不同日期，请核对签署日期、生效日期和开发完成日期是否前后一致。",
            }
        )

    sign_dates = _extract_labeled_dates(text, ["签订日期", "签署日期", "签约日期", "签订时间", "签署时间"])
    completion_dates = _extract_labeled_dates(text, ["开发完成日期", "完成日期", "完成时间"])
    apply_dates = _extract_labeled_dates(text, ["申请日期", "申报日期", "提交日期"])
    if sign_dates and completion_dates and sign_dates[0] > completion_dates[0]:
        issues.append(
            {
                "severity": "severe",
                "category": "日期逻辑",
                "rule_key": "agreement_dates_valid",
                "desc": f"协议签署日期晚于开发完成日期。签署日期={sign_dates[0].isoformat()}；开发完成日期={completion_dates[0].isoformat()}。",
                "suggest": "核对协议签署时间与开发完成时间的业务先后关系。",
            }
        )
    if sign_dates and apply_dates:
        if sign_dates[0] >= apply_dates[0]:
            issues.append(
                {
                    "severity": "severe",
                    "category": "日期逻辑",
                    "rule_key": "agreement_dates_valid",
                    "desc": f"协议签署日期不应晚于或等于申请日期。签署日期={sign_dates[0].isoformat()}；申请日期={apply_dates[0].isoformat()}。",
                    "suggest": "确保合作协议早于正式申请或提交日期。",
                }
            )
        elif (apply_dates[0] - sign_dates[0]).days < 240:
            issues.append(
                {
                    "severity": "moderate",
                    "category": "日期逻辑",
                    "rule_key": "agreement_dates_valid",
                    "desc": f"协议签署日期距离申请日期过近，间隔仅 {(apply_dates[0] - sign_dates[0]).days} 天。",
                    "suggest": "复核协议签署时间是否合理，避免给审核人造成倒签或临时补签的印象。",
                }
            )

    if "电子章" in text or "扫描件" in text:
        issues.append(
            {
                "severity": "severe",
                "category": "签章要求",
                "rule_key": "agreement_stamp_signature",
                "desc": "协议文本中出现电子章或扫描件信号，需人工确认是否满足鲜章和手签要求。",
            }
        )

    has_approval_sheet = any(keyword in text for keyword in ["科研合同审批表", "合同审批表", "审批表"])
    has_tech_contract = any(keyword in text for keyword in ["技术开发合同", "技术合同", "开发合同"])
    if not has_approval_sheet or not has_tech_contract:
        missing = []
        if not has_approval_sheet:
            missing.append("科研合同审批表")
        if not has_tech_contract:
            missing.append("技术开发合同勾选/表述")
        issues.append(
            {
                "severity": "moderate",
                "category": "审批手续",
                "rule_key": "agreement_approval_sheet",
                "desc": f"合作协议相关审批手续不完整，缺少：{'、'.join(missing)}。",
                "suggest": "补齐科研合同审批表，并确认合同类型为技术开发合同。",
            }
        )

    issues.extend(
        scan_sensitive_terms(
            text,
            rule_key="agreement_sensitive_terms",
            category="敏感词排查",
            severity="moderate",
        )
    )

    return {"issues": issues, "metadata": metadata}
