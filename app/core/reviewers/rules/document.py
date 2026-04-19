from __future__ import annotations

import re


def review_document_text(text: str) -> dict:
    issues: list[dict] = []
    v1 = len(re.findall(r"\b[Vv]1\.0\b", text))
    v2 = len(re.findall(r"\b[Vv]2\.0\b", text))
    if v1 and v2:
        issues.append(
            {
                "severity": "moderate",
                "category": "版本号不一致",
                "desc": f"文档内同时出现 V1.0({v1}) 与 V2.0({v2})，版本描述不一致",
            }
        )
    if "Media Pipe" in text:
        issues.append(
            {
                "severity": "minor",
                "category": "命名不一致",
                "desc": '发现 "Media Pipe" 写法，应统一为 "MediaPipe"',
            }
        )
    return {"issues": issues}

