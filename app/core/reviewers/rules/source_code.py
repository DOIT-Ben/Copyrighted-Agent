from __future__ import annotations

import re

from app.core.reviewers.rules.sensitive_terms import scan_sensitive_terms
from app.core.utils.text import calculate_garbled_ratio


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


SENSITIVE_PATTERNS = [
    (r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"][^'\"]{3,}['\"]", "疑似明文密码"),
    (r"(?i)(token|api[_-]?key|secret|authorization)\s*[:=]\s*['\"][^'\"]{6,}['\"]", "疑似真实 token 或密钥"),
    (r"\b(?:[1-9]\d{0,2}\.){3}[1-9]\d{0,2}\b", "疑似公网 IP"),
    (r"1[3-9]\d{9}", "疑似手机号"),
    (r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "疑似邮箱地址"),
]


def _detect_page_markers(text: str) -> list[int]:
    markers = re.findall(r"第\s*(\d+)\s*页", str(text or ""), flags=re.IGNORECASE)
    return [int(item) for item in markers if str(item).isdigit()]


def _extract_feature_terms(text: str) -> list[str]:
    patterns = [
        r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)",
        r"function\s+([a-zA-Z_][a-zA-Z0-9_]*)",
        r"class\s+([a-zA-Z_][a-zA-Z0-9_]*)",
    ]
    found: list[str] = []
    for pattern in patterns:
        for item in re.findall(pattern, str(text or "")):
            token = str(item).strip().lower()
            if not token or len(token) < 3:
                continue
            normalized = (
                token.replace("_service", "")
                .replace("_manager", "")
                .replace("_controller", "")
                .replace("_module", "")
            )
            if normalized not in found:
                found.append(normalized)
    for keyword in ["login", "query", "export", "report", "analysis", "audit", "collect", "monitor", "manage", "stat"]:
        if keyword in str(text or "").lower() and keyword not in found:
            found.append(keyword)
    return found[:12]


def review_source_code_text(text: str) -> dict:
    issues: list[dict] = []
    metadata = {
        "feature_terms": _extract_feature_terms(text),
    }
    ratio = calculate_garbled_ratio(text)
    suspicious_runs = re.findall(r"[^\x00-\x7F\s]{4,}", text)
    if ratio > 0.05 or suspicious_runs:
        issues.append(
            {
                "severity": "severe",
                "category": "源码可读性",
                "rule_key": "code_readable",
                "desc": f"源码乱码比例约为 {ratio:.1%}，并检测到异常字符片段，当前材料不适合直接审查。",
                **_anchor(field="源码可读性", section="源码正文", hint="检查源码 PDF 中是否存在乱码或异常字符片段", material_area="源码 PDF 正文"),
            }
        )

    lines = text.splitlines()
    indented_lines = sum(1 for line in lines if line.startswith(" "))
    blank_runs = 0
    for index in range(len(lines) - 1):
        if not lines[index].strip() and not lines[index + 1].strip():
            blank_runs += 1
    numbered_lines = sum(1 for line in lines[:80] if re.match(r"^\s*\d+\s", line))
    if indented_lines > 0 or blank_runs > 0 or numbered_lines == 0:
        issues.append(
            {
                "severity": "moderate",
                "category": "源码格式",
                "rule_key": "code_format_clean",
                "desc": "源码格式疑似不符合提交规范，请检查行首空格、连续空行以及行号是否完整。",
                **_anchor(field="源码格式", section="源码正文", hint="检查行首空格、连续空行和行号是否符合提交规范", material_area="源码 PDF 正文"),
            }
        )

    page_numbers = _detect_page_markers(text)
    if page_numbers:
        total_pages = max(page_numbers)
        if total_pages > 60:
            head_pages = {number for number in page_numbers if number <= 30}
            tail_pages = {number for number in page_numbers if number > total_pages - 30}
            if len(head_pages) < 10 or len(tail_pages) < 10:
                issues.append(
                    {
                        "severity": "severe",
                        "category": "页数策略",
                        "rule_key": "code_page_strategy",
                        "desc": f"源码页数疑似超过 60 页，但未识别到“前30页 + 后30页”的完整截取策略。当前页码范围最高到第 {total_pages} 页。",
                        "suggest": "源码超过 60 页时，导出前 30 页和后 30 页，避免只截取前半段。",
                        **_anchor(field="页码截取", section="页码策略", hint="检查源码 PDF 是否按前30页加后30页方式导出", material_area="源码 PDF 页码"),
                    }
                )

    for pattern, label in SENSITIVE_PATTERNS:
        if re.search(pattern, text):
            issues.append(
                {
                    "severity": "severe",
                    "category": "源码脱敏",
                    "rule_key": "code_desensitized",
                    "desc": f"源码中发现{label}信号，需先完成脱敏后再提交审查。",
                    **_anchor(field="敏感信息", section="源码脱敏", hint="检查源码中的密码、Token、手机号、邮箱和公网 IP 是否已脱敏", material_area="源码 PDF 正文"),
                }
            )
            break

    feature_terms = metadata["feature_terms"]
    if len(feature_terms) < 2:
        issues.append(
            {
                "severity": "minor",
                "category": "功能呼应",
                "rule_key": "code_logic_supports_doc",
                "desc": f"仅识别到 {len(feature_terms)} 个代表性函数或类名，当前源码展示可能不足以支撑文档中的功能描述。",
                "suggest": "确保提交的源码包含与说明文档对应的核心函数、类或模块。",
                **_anchor(field="核心逻辑", section="源码正文", hint="检查源码中是否展示了与说明文档对应的关键函数或核心流程", material_area="源码 PDF 正文"),
            }
        )

    comment_lines = sum(1 for line in lines if line.strip().startswith(("#", "//", "/*", "*")))
    code_lines = sum(1 for line in lines if line.strip() and not line.strip().startswith(("#", "//", "/*", "*")))
    if comment_lines > max(code_lines, 1):
        issues.append(
            {
                "severity": "minor",
                "category": "注释质量",
                "rule_key": "code_comment_ratio_reasonable",
                "desc": "注释量高于代码量，存在注释过多或凑数风险，建议人工复核。",
                **_anchor(field="注释比例", section="源码正文", hint="检查源码中注释量是否明显高于代码量", material_area="源码 PDF 正文"),
            }
        )

    if code_lines < 300:
        issues.append(
            {
                "severity": "severe",
                "category": "源码行数",
                "rule_key": "code_effective_lines",
                "desc": f"有效代码行数约 {code_lines} 行，低于软著登记通常要求的最低行数。",
                "suggest": "软著登记一般要求源代码不少于 3000 行（约 60 页），请补充完整核心代码。",
                **_anchor(field="有效行数", section="源码正文", hint="统计源码中去掉注释和空行后的有效代码行数", material_area="源码 PDF 正文"),
            }
        )

    issues.extend(
        scan_sensitive_terms(
            text,
            rule_key="code_sensitive_terms",
            category="敏感词排查",
            severity="moderate",
        )
    )

    return {"issues": issues, "metadata": metadata}
