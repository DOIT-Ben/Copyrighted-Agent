from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Callable


RedactionReplacement = str | Callable[[re.Match[str]], str]


@dataclass(frozen=True)
class RedactionRule:
    key: str
    category: str
    pattern: re.Pattern[str]
    replacement: RedactionReplacement


LABEL_PLACEHOLDERS = {
    "软件名称": "[已脱敏-软件名称]",
    "产品名称": "[已脱敏-产品名称]",
    "系统名称": "[已脱敏-系统名称]",
    "平台名称": "[已脱敏-平台名称]",
    "著作权人": "[已脱敏-著作权人]",
    "申请人": "[已脱敏-申请人]",
    "权利人": "[已脱敏-权利人]",
    "公司名称": "[已脱敏-公司名称]",
    "企业名称": "[已脱敏-企业名称]",
    "联系人": "[已脱敏-联系人]",
    "联系电话": "[已脱敏-联系电话]",
    "电话": "[已脱敏-电话]",
    "手机": "[已脱敏-手机号]",
    "手机号码": "[已脱敏-手机号]",
    "电子邮箱": "[已脱敏-邮箱]",
    "邮箱": "[已脱敏-邮箱]",
    "地址": "[已脱敏-地址]",
    "联系地址": "[已脱敏-地址]",
    "通信地址": "[已脱敏-地址]",
    "身份证号": "[已脱敏-身份证号]",
    "证件号码": "[已脱敏-证件号码]",
    "统一社会信用代码": "[已脱敏-统一社会信用代码]",
    "法定代表人": "[已脱敏-法定代表人]",
    "代理人": "[已脱敏-代理人]",
    "甲方": "[已脱敏-甲方主体]",
    "乙方": "[已脱敏-乙方主体]",
    "版本号": "[已脱敏-版本号]",
}

EXPLICIT_VALUE_FIELDS = {
    "software_name": "[已脱敏-软件名称]",
    "company_name": "[已脱敏-公司名称]",
    "version": "[已脱敏-版本号]",
}

AI_SAFE_POLICY = "local_manual_redaction_v1"


def _build_label_rule(label: str, placeholder: str) -> RedactionRule:
    pattern = re.compile(
        rf"(?P<label>{re.escape(label)})(?P<sep>\s*[：:]\s*)(?P<value>[^\n]{{1,160}})"
    )

    def _replace(match: re.Match[str]) -> str:
        return f"{match.group('label')}{match.group('sep')}{placeholder}"

    return RedactionRule(
        key=f"label:{label}",
        category="labeled_field",
        pattern=pattern,
        replacement=_replace,
    )


MANUAL_RULES: list[RedactionRule] = [
    *[_build_label_rule(label, placeholder) for label, placeholder in LABEL_PLACEHOLDERS.items()],
    RedactionRule(
        key="email",
        category="contact",
        pattern=re.compile(r"(?<![\w.\-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![\w.\-])"),
        replacement="[已脱敏-邮箱]",
    ),
    RedactionRule(
        key="phone",
        category="contact",
        pattern=re.compile(r"(?<!\d)(?:\+?86[-\s]?)?1[3-9]\d{9}(?!\d)"),
        replacement="[已脱敏-手机号]",
    ),
    RedactionRule(
        key="telephone",
        category="contact",
        pattern=re.compile(r"(?<!\d)(?:0\d{2,3}[-\s]?)?\d{7,8}(?!\d)"),
        replacement="[已脱敏-电话]",
    ),
    RedactionRule(
        key="id_card_18",
        category="identity",
        pattern=re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)"),
        replacement="[已脱敏-身份证号]",
    ),
    RedactionRule(
        key="id_card_15",
        category="identity",
        pattern=re.compile(r"(?<!\d)\d{15}(?!\d)"),
        replacement="[已脱敏-身份证号]",
    ),
    RedactionRule(
        key="social_credit_code",
        category="organization",
        pattern=re.compile(r"(?<![A-Z0-9])[0-9A-Z]{18}(?![A-Z0-9])"),
        replacement="[已脱敏-统一社会信用代码]",
    ),
    RedactionRule(
        key="bank_card",
        category="financial",
        pattern=re.compile(r"(?<!\d)\d{16,19}(?!\d)"),
        replacement="[已脱敏-银行卡号]",
    ),
    RedactionRule(
        key="url",
        category="network",
        pattern=re.compile(r"https?://[^\s)]+", flags=re.IGNORECASE),
        replacement="[已脱敏-网址]",
    ),
]


def _apply_rule(text: str, rule: RedactionRule) -> tuple[str, int]:
    hit_count = 0

    def _replace(match: re.Match[str]) -> str:
        nonlocal hit_count
        hit_count += 1
        if callable(rule.replacement):
            return rule.replacement(match)
        return rule.replacement

    return rule.pattern.sub(_replace, text), hit_count


def _apply_explicit_values(text: str, metadata: dict[str, str] | None) -> tuple[str, list[dict[str, str | int]]]:
    if not metadata:
        return text, []

    result = text
    hits: list[dict[str, str | int]] = []
    for field_name, placeholder in EXPLICIT_VALUE_FIELDS.items():
        value = str(metadata.get(field_name, "") or "").strip()
        if len(value) < 2 or value == placeholder:
            continue
        pattern = re.compile(re.escape(value))
        count = len(pattern.findall(result))
        if not count:
            continue
        result = pattern.sub(placeholder, result)
        hits.append(
            {
                "rule": f"explicit:{field_name}",
                "category": "explicit_value",
                "count": count,
            }
        )
    return result, hits


def desensitize_text(text: str, metadata: dict[str, str] | None = None) -> dict:
    result = text or ""
    matches: list[dict[str, str | int]] = []

    for rule in MANUAL_RULES:
        result, count = _apply_rule(result, rule)
        if count:
            matches.append({"rule": rule.key, "category": rule.category, "count": count})

    result, explicit_hits = _apply_explicit_values(result, metadata)
    matches.extend(explicit_hits)

    category_counts: dict[str, int] = {}
    for item in matches:
        category = str(item["category"])
        category_counts[category] = category_counts.get(category, 0) + int(item["count"])

    summary = {
        "policy": AI_SAFE_POLICY,
        "llm_safe": True,
        "total_replacements": sum(int(item["count"]) for item in matches),
        "rules_triggered": [str(item["rule"]) for item in matches],
        "category_counts": category_counts,
        "input_chars": len(text or ""),
        "output_chars": len(result),
    }
    return {
        "text": result,
        "summary": summary,
        "matches": matches,
    }


def build_ai_safe_case_payload(case_payload: dict) -> dict:
    version = case_payload.get("version", "")
    return {
        "software_name": "[已脱敏-软件名称]" if case_payload.get("software_name") else "",
        "version": "[已脱敏-版本号]" if version else "",
        "company_name": "[已脱敏-公司名称]" if case_payload.get("company_name") else "",
        "privacy_policy": AI_SAFE_POLICY,
        "llm_safe": True,
    }


def is_ai_safe_case_payload(case_payload: dict) -> bool:
    if not isinstance(case_payload, dict):
        return False

    if case_payload.get("privacy_policy") != AI_SAFE_POLICY:
        return False

    allowed_keys = set(EXPLICIT_VALUE_FIELDS) | {"privacy_policy", "llm_safe"}
    for key, value in case_payload.items():
        if key not in allowed_keys and value not in ("", None, False):
            return False

    for field_name, placeholder in EXPLICIT_VALUE_FIELDS.items():
        value = str(case_payload.get(field_name, "") or "")
        if value and value != placeholder:
            return False

    return bool(case_payload.get("llm_safe"))
