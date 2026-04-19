from __future__ import annotations

from pathlib import Path

from app.core.utils.text import best_effort_decode, calculate_garbled_ratio, clean_text, strip_control_chars


GENERIC_HINTS = (
    "甲方",
    "乙方",
    "软件名称",
    "著作权人",
    "版本",
    "说明书",
    "目录",
    "运行环境",
    "操作步骤",
    "合作",
    "协议",
    "用户",
    "签章",
    "签字",
    "统一社会信用代码",
    "法人证书号",
)

NOISE_HINTS = (
    "OLE_LINK",
    "KSOProductBuildVer",
    "KSOTemplate",
    "DocerSaveRecord",
    "commondata",
    "MC SYSTEM",
)


def _signal_ratio(text: str) -> float:
    chars = [char for char in text if not char.isspace()]
    if not chars:
        return 0.0

    signal = 0
    for char in chars:
        code_point = ord(char)
        if 0x4E00 <= code_point <= 0x9FFF:
            signal += 1
            continue
        if char.isascii() and (char.isalnum() or char in "._-:/#%()[]{}+,;"):
            signal += 1
            continue
        if char in "，。：；、（）《》【】“”‘’+-":
            signal += 1
    return signal / len(chars)


def _normalized_line(raw_line: str) -> str:
    return " ".join(strip_control_chars(raw_line).split())


def _keyword_hits(line: str) -> int:
    return sum(1 for hint in GENERIC_HINTS if hint in line)


def _extract_readable_lines(text: str) -> str:
    lines: list[str] = []
    seen: set[str] = set()
    for raw_line in text.replace("\r", "\n").split("\n"):
        line = _normalized_line(raw_line)
        if len(line) < 4:
            continue
        if any(noise in line for noise in NOISE_HINTS):
            continue

        signal_ratio = _signal_ratio(line)
        keyword_hits = _keyword_hits(line)
        garbled_ratio = calculate_garbled_ratio(line)

        if signal_ratio < 0.52 and keyword_hits == 0:
            continue
        if signal_ratio < 0.62 and len(line) < 8 and keyword_hits == 0:
            continue
        if garbled_ratio > 0.35 and keyword_hits == 0:
            continue
        if line in seen:
            continue

        seen.add(line)
        lines.append(line)
    return clean_text("\n".join(lines))


def _score_extracted_text(text: str) -> float:
    if not text.strip():
        return 0.0

    lines = [line for line in text.splitlines() if line.strip()]
    keyword_hits = sum(_keyword_hits(line) for line in lines)
    signal_ratio = _signal_ratio(text)
    garbled_ratio = calculate_garbled_ratio(text)
    char_count = sum(1 for char in text if not char.isspace())
    cjk_count = sum(1 for char in text if 0x4E00 <= ord(char) <= 0x9FFF)

    return (
        signal_ratio * 2.4
        + min(keyword_hits, 12) * 0.28
        + min(len(lines), 16) * 0.12
        + min(char_count, 1800) / 700
        + min(cjk_count, 400) / 260
        - garbled_ratio * 2.4
    )


def _decoded_candidates(data: bytes) -> list[str]:
    candidates: list[str] = []
    strict = clean_text(strip_control_chars(best_effort_decode(data)))
    if strict:
        candidates.append(strict)

    for encoding in ("utf-16-le", "utf-16", "gb18030", "utf-8", "latin1"):
        decoded = clean_text(strip_control_chars(data.decode(encoding, errors="ignore")))
        if decoded:
            candidates.append(decoded)

    return candidates


class DocBinaryParser:
    def parse(self, file_path: str | Path) -> str:
        data = Path(file_path).read_bytes()

        best_text = ""
        best_score = -1.0
        for candidate in _decoded_candidates(data):
            extracted = _extract_readable_lines(candidate)
            score = _score_extracted_text(extracted)
            if score > best_score:
                best_text = extracted
                best_score = score

        if best_text:
            return best_text
        return clean_text(best_effort_decode(data))
