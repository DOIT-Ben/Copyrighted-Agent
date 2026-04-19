from __future__ import annotations

import re


def review_agreement_text(text: str) -> dict:
    issues: list[dict] = []
    if "签定" in text:
        issues.append(
            {
                "severity": "minor",
                "category": "用词问题",
                "desc": '发现"签定"写法，应统一为"签订"',
                "suggest": "将签定改为签订",
            }
        )

    dates = re.findall(r"\d{4}年\d{1,2}月\d{1,2}日", text)
    if len(set(dates)) > 1:
        issues.append(
            {
                "severity": "moderate",
                "category": "日期一致性",
                "desc": "合作协议中存在多个不同日期，建议核对签署与生效日期是否一致",
            }
        )

    return {"issues": issues}

