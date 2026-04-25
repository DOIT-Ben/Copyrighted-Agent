from __future__ import annotations

from typing import Any


ONLINE_FILING_FIELDS = [
    "software_name",
    "version",
    "software_category",
    "development_mode",
    "subject_type",
    "apply_date",
    "completion_date",
    "address",
    "certificate_address",
]


def _clean_text(value: Any, *, limit: int = 120) -> str:
    return str(value or "").strip()[:limit]


def _split_lines(value: Any, *, limit: int = 12) -> list[str]:
    if isinstance(value, list):
        rows = [str(item or "").strip() for item in value]
    else:
        rows = [line.strip(" -\t") for line in str(value or "").splitlines()]
    return [item[:60] for item in rows if item][:limit]


def normalize_online_filing(payload: dict[str, Any] | None) -> dict[str, Any]:
    raw = dict(payload or {})
    normalized = {key: _clean_text(raw.get(key, "")) for key in ONLINE_FILING_FIELDS}
    normalized["applicants"] = _split_lines(raw.get("applicants", []))
    normalized["has_data"] = bool(
        normalized["software_name"]
        or normalized["version"]
        or normalized["software_category"]
        or normalized["development_mode"]
        or normalized["subject_type"]
        or normalized["apply_date"]
        or normalized["completion_date"]
        or normalized["address"]
        or normalized["certificate_address"]
        or normalized["applicants"]
    )
    return normalized


def parse_online_filing_form(form_data) -> dict[str, Any]:
    payload = {key: form_data.get(f"online_{key}", "") for key in ONLINE_FILING_FIELDS}
    payload["applicants"] = form_data.get("online_applicants", "")
    return normalize_online_filing(payload)


def online_filing_summary(payload: dict[str, Any] | None) -> list[tuple[str, str]]:
    filing = normalize_online_filing(payload)
    return [
        ("软件名称", filing.get("software_name", "") or "未填写"),
        ("版本号", filing.get("version", "") or "未填写"),
        ("软件分类", filing.get("software_category", "") or "未填写"),
        ("开发方式", filing.get("development_mode", "") or "未填写"),
        ("主体类型", filing.get("subject_type", "") or "未填写"),
        ("申请日期", filing.get("apply_date", "") or "未填写"),
        ("开发完成日期", filing.get("completion_date", "") or "未填写"),
        ("申请人顺序", "、".join(filing.get("applicants", [])) or "未填写"),
        ("地址", filing.get("address", "") or "未填写"),
        ("电子证书地址", filing.get("certificate_address", "") or "未填写"),
    ]


__all__ = [
    "ONLINE_FILING_FIELDS",
    "normalize_online_filing",
    "online_filing_summary",
    "parse_online_filing_form",
]
