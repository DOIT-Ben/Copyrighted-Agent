from __future__ import annotations

import re

from app.core.utils.text import calculate_garbled_ratio


def review_source_code_text(text: str) -> dict:
    issues: list[dict] = []
    ratio = calculate_garbled_ratio(text)
    suspicious_runs = re.findall(r"[^\x00-\x7F\s]{4,}", text)
    if ratio > 0.05 or suspicious_runs:
        issues.append(
            {
                "severity": "moderate",
                "category": "代码乱码",
                "desc": f"代码乱码比例为 {ratio:.1%}，并检测到异常字符片段，建议转为 txt / py 后再审查",
            }
        )
    if "calculate_angle" not in text and "angle" not in text.lower():
        issues.append(
            {
                "severity": "minor",
                "category": "核心逻辑缺失",
                "desc": "未检测到明显的角度计算相关逻辑，建议确认样本是否完整",
            }
        )
    return {"issues": issues}
