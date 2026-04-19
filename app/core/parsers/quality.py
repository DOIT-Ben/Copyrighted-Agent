from __future__ import annotations

from app.core.utils.text import calculate_garbled_ratio


OLE_HEADER = "\xd0\xcf\x11\xe0"
OLE_HEADER_BYTES = b"\xd0\xcf\x11\xe0"
SIGNAL_PUNCTUATION = set("，。：；、（）《》【】“”‘’·○⊙")

REVIEW_REASON_LABELS = {
    "clean_text_ready": "文本可直接使用",
    "text_too_short": "文本过短",
    "noise_too_high": "噪音过多",
    "ole_readable_segments_insufficient": "OLE 可读段不足",
    "low_signal_ratio": "有效文本信号不足",
    "empty_text": "未提取到文本",
}

LEGACY_DOC_BUCKET_LABELS = {
    "usable_text": "可用文本",
    "partial_fragments": "半可读碎片",
    "binary_noise": "纯噪音",
}


def _non_whitespace_length(text: str) -> int:
    return sum(1 for char in text if not char.isspace())


def _control_ratio(text: str) -> float:
    total = 0
    control = 0
    for char in text:
        if char in {"\n", "\r", "\t"}:
            continue
        total += 1
        if ord(char) < 32:
            control += 1
    return control / total if total else 0.0


def _signal_ratio(text: str) -> float:
    total = 0
    signal = 0
    for char in text:
        if char.isspace():
            continue
        total += 1
        code_point = ord(char)
        if 0x4E00 <= code_point <= 0x9FFF:
            signal += 1
            continue
        if char.isascii() and (char.isalnum() or char in "._-:/#%()[]{}+,;"):
            signal += 1
            continue
        if char in SIGNAL_PUNCTUATION:
            signal += 1
    return signal / total if total else 0.0


def _legacy_doc_bucket(
    *,
    has_ole_header: bool,
    is_text_usable: bool,
    signal_ratio: float,
    garbled_ratio: float,
    control_ratio: float,
    char_count: int,
) -> str:
    if not has_ole_header:
        return ""
    if is_text_usable:
        return "usable_text"
    if char_count >= 120 and signal_ratio >= 0.5 and garbled_ratio <= 0.16 and not (control_ratio >= 0.08 and garbled_ratio >= 0.12):
        return "partial_fragments"
    return "binary_noise"


def _review_reason_code(
    *,
    clean_text: str,
    char_count: int,
    line_count: int,
    reasons: list[str],
    has_ole_header: bool,
    control_ratio: float,
    garbled_ratio: float,
    signal_ratio: float,
    parser_name: str,
    is_text_usable: bool,
) -> str:
    if not clean_text.strip():
        return "empty_text"
    if char_count < 40 or line_count < 2:
        return "text_too_short"
    if "high_control_ratio" in reasons or "high_garbled_ratio" in reasons:
        return "noise_too_high"
    if parser_name == "DocBinaryParser" and has_ole_header and not is_text_usable:
        bucket = _legacy_doc_bucket(
            has_ole_header=has_ole_header,
            is_text_usable=is_text_usable,
            signal_ratio=signal_ratio,
            garbled_ratio=garbled_ratio,
            control_ratio=control_ratio,
            char_count=char_count,
        )
        if bucket == "partial_fragments":
            return "ole_readable_segments_insufficient"
        return "noise_too_high"
    if "low_signal_ratio" in reasons:
        return "low_signal_ratio"
    return "clean_text_ready"


def assess_parse_quality(raw_text: str, clean_text: str, parser_name: str, file_header_bytes: bytes = b"") -> dict:
    line_count = len(clean_text.splitlines()) if clean_text else 0
    char_count = _non_whitespace_length(clean_text)
    garbled_ratio = calculate_garbled_ratio(clean_text)
    control_ratio = _control_ratio(raw_text)
    signal_ratio = _signal_ratio(clean_text)
    reasons: list[str] = []
    score = 0.98

    if not clean_text.strip():
        reasons.append("empty_text")
        score = 0.0

    has_ole_header = raw_text.startswith(OLE_HEADER) or file_header_bytes.startswith(OLE_HEADER_BYTES)

    if has_ole_header:
        reasons.append("ole_binary_header")
        if char_count < 40:
            score = min(score, 0.18)
        elif signal_ratio < 0.45 or garbled_ratio >= 0.18:
            score = min(score, 0.42)
        else:
            score = min(score, 0.78)

    if control_ratio >= 0.08:
        reasons.append("high_control_ratio")
        score = min(score, 0.18)

    if garbled_ratio >= 0.18:
        reasons.append("high_garbled_ratio")
        score = min(score, 0.35)

    if signal_ratio <= 0.45 and char_count >= 20:
        reasons.append("low_signal_ratio")
        score = min(score, 0.42)

    if char_count < 12 or line_count < 2:
        reasons.append("too_short")
        score = min(score, 0.62)

    if parser_name == "DocBinaryParser" and "ole_binary_header" in reasons:
        looks_like_structured_legacy_text = (
            signal_ratio >= 0.45 and garbled_ratio <= 0.05 and char_count >= 400 and line_count >= 8
        )
        if score >= 0.7 and (signal_ratio >= 0.6 or looks_like_structured_legacy_text) and garbled_ratio <= 0.12:
            reasons.append("binary_doc_text_extracted")
        else:
            reasons.append("binary_doc_needs_manual_review")

    if score >= 0.85:
        quality_level = "high"
    elif score >= 0.55:
        quality_level = "medium"
    else:
        quality_level = "low"

    is_text_usable = quality_level != "low" and "high_control_ratio" not in reasons
    if has_ole_header and "binary_doc_needs_manual_review" in reasons:
        is_text_usable = False
    summary_reason = reasons[0] if reasons else "clean_text_ready"
    review_reason_code = _review_reason_code(
        clean_text=clean_text,
        char_count=char_count,
        line_count=line_count,
        reasons=reasons,
        has_ole_header=has_ole_header,
        control_ratio=control_ratio,
        garbled_ratio=garbled_ratio,
        signal_ratio=signal_ratio,
        parser_name=parser_name,
        is_text_usable=is_text_usable,
    )
    legacy_doc_bucket = _legacy_doc_bucket(
        has_ole_header=has_ole_header,
        is_text_usable=is_text_usable,
        signal_ratio=signal_ratio,
        garbled_ratio=garbled_ratio,
        control_ratio=control_ratio,
        char_count=char_count,
    )

    return {
        "quality_score": round(score, 2),
        "quality_level": quality_level,
        "quality_reason": summary_reason,
        "review_reason_code": review_reason_code,
        "review_reason_label": REVIEW_REASON_LABELS.get(review_reason_code, review_reason_code),
        "is_text_usable": is_text_usable,
        "char_count": char_count,
        "line_count": line_count,
        "garbled_ratio": round(garbled_ratio, 3),
        "control_ratio": round(control_ratio, 3),
        "signal_ratio": round(signal_ratio, 3),
        "quality_flags": reasons,
        "legacy_doc_bucket": legacy_doc_bucket,
        "legacy_doc_bucket_label": LEGACY_DOC_BUCKET_LABELS.get(legacy_doc_bucket, ""),
    }
