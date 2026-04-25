from __future__ import annotations

import html
import re
from pathlib import Path


DESENSITIZE_PATTERNS = [
    (r"\b\d{17}[\dXx]\b", "[身份证号]"),
    (r"\b\d{15}\b", "[身份证号]"),
    (r"\b[0-9A-Z]{18}\b", "[统一社会信用代码]"),
    (r"甲方：[^ \n]+", "甲方：[已脱敏]"),
    (r"乙方：[^ \n]+", "乙方：[已脱敏]"),
]


def now_iso() -> str:
    from datetime import datetime

    return datetime.now().isoformat(timespec="seconds")


def slug_id(prefix: str) -> str:
    import uuid

    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def ensure_dir(path: str | Path) -> Path:
    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    return target


def best_effort_decode(data: bytes) -> str:
    for encoding in ("utf-8", "utf-16-le", "utf-16", "gb18030", "latin1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="ignore")


def read_text_file(path: str | Path) -> str:
    data = Path(path).read_bytes()
    return best_effort_decode(data)


def strip_control_chars(text: str, *, keep_line_breaks: bool = True) -> str:
    if not text:
        return ""
    allowed = {"\n", "\r", "\t"} if keep_line_breaks else set()
    return "".join(char for char in text if char in allowed or ord(char) >= 32)


def clean_text(text: str) -> str:
    text = strip_control_chars(text).replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    compact = "\n".join(line for line in lines if line.strip())
    return compact.strip()


def desensitize_text(text: str) -> str:
    result = text
    for pattern, replacement in DESENSITIZE_PATTERNS:
        result = re.sub(pattern, replacement, result)
    return result


def extract_software_name(text: str) -> str:
    patterns = [
        r"软件名称[：:]\s*(.+?)(?:\n|$)",
        r"产品名称[：:]\s*(.+?)(?:\n|$)",
        r"([^\n]{2,50}(?:系统|软件|平台|应用|客户端|APP))",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip().strip("：:")
    return ""


def extract_version(text: str) -> str:
    patterns = [
        r"版本(?:号)?[：:]\s*([vV]?\d+\.\d+(?:\.\d+)?)",
        r"\b([vV]\d+\.\d+(?:\.\d+)?)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            value = match.group(1).strip()
            return value if value.upper().startswith("V") else f"V{value}"
    return ""


def extract_company_name(text: str) -> str:
    patterns = [
        r"著作权人[：:]\s*(.+?)(?:\n|$)",
        r"公司名称[：:]\s*(.+?)(?:\n|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return ""


def extract_date_candidates(text: str) -> list[str]:
    patterns = [
        r"\d{4}[-/年.]\d{1,2}[-/月.]\d{1,2}(?:日)?",
    ]
    dates: list[str] = []
    for pattern in patterns:
        for match in re.findall(pattern, text):
            value = str(match).strip()
            normalized = (
                value.replace("年", "-")
                .replace("月", "-")
                .replace("日", "")
                .replace("/", "-")
                .replace(".", "-")
            )
            dates.append(normalized)
    deduped: list[str] = []
    for item in dates:
        if item not in deduped:
            deduped.append(item)
    return deduped


def extract_party_sequence(text: str) -> list[str]:
    sequence: list[str] = []
    patterns = [
        r"(甲方|乙方|丙方|丁方)[：:\s]*([^\n，,；;]{2,40})",
        r"(申请人(?:一|二|三|四)?|著作权人(?:一|二|三|四)?)[：:\s]*([^\n，,；;]{2,40})",
    ]
    for pattern in patterns:
        for _, value in re.findall(pattern, text):
            cleaned = str(value).strip().strip("：:，,；;。.")
            if cleaned:
                sequence.append(cleaned)
    return sequence


def calculate_garbled_ratio(text: str) -> float:
    if not text:
        return 0.0
    weird = 0
    total = 0
    for char in text:
        if char.isspace():
            continue
        total += 1
        if ord(char) < 32:
            weird += 1
            continue
        if "\u2500" <= char <= "\u27ff":
            weird += 1
            continue
        if "\u0370" <= char <= "\u052f":
            weird += 1
            continue
        if char in {"�", "", "", ""}:
            weird += 1
    return weird / total if total else 0.0


def summarize_severity(issues: list[dict]) -> dict[str, int]:
    summary = {"severe": 0, "moderate": 0, "minor": 0}
    for issue in issues:
        severity = issue.get("severity", "").lower()
        if severity in summary:
            summary[severity] += 1
    return summary


def escape_html(value: str) -> str:
    return html.escape(value, quote=True)
