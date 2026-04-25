from __future__ import annotations

import re


SENSITIVE_TERM_RULES = [
    ("破解", "兼容适配、兼容处理"),
    ("刷机", "兼容适配、兼容处理"),
    ("破解版", "兼容版本"),
    ("外挂", "数据处理、辅助功能"),
    ("辅助脚本", "数据处理、辅助功能"),
    ("刷单", "批量导入、批量处理"),
    ("批量注册", "批量导入、批量处理"),
    ("爬虫", "数据采集、数据同步"),
    ("抓取", "数据采集、数据同步"),
    ("仿抖音", "短视频系统"),
    ("仿微信", "即时通讯辅助"),
    ("淘宝", "电商辅助"),
]


def scan_sensitive_terms(text: str, *, rule_key: str, category: str, severity: str = "moderate") -> list[dict]:
    issues: list[dict] = []
    lowered = str(text or "")
    for term, replacement in SENSITIVE_TERM_RULES:
        if not term:
            continue
        if re.search(re.escape(term), lowered, flags=re.IGNORECASE):
            issues.append(
                {
                    "severity": severity,
                    "category": category,
                    "rule_key": rule_key,
                    "desc": f'检测到敏感词“{term}”，建议替换为“{replacement}”等更合规表述。',
                    "suggest": f'将“{term}”替换为“{replacement}”。',
                }
            )
    return issues


__all__ = ["SENSITIVE_TERM_RULES", "scan_sensitive_terms"]
