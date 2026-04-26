from __future__ import annotations

import re


_PAGE_PATTERN = re.compile(
    r"(?:^|\s)(?:\u7b2c\s*(\d+)\s*\u9875|\bpage\s*(\d+)\b)(?:\s|$)",
    re.IGNORECASE,
)
_HEADING_PATTERN = re.compile(
    r"^\s*(?:[\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341]+\u3001|\d+(?:\.\d+)*[.\u3001]?)[^\n]{0,80}$"
)


def build_page_segments(text: str) -> list[dict]:
    lines = [str(line).strip() for line in str(text or "").splitlines()]
    segments: list[dict] = []
    current: dict | None = None

    def flush() -> None:
        nonlocal current
        if not current:
            return
        segment_lines = [line for line in list(current.get("lines", []) or []) if line]
        if not segment_lines:
            current = None
            return
        text_value = "\n".join(segment_lines).strip()
        if not text_value:
            current = None
            return
        headings = [line for line in segment_lines if _HEADING_PATTERN.match(line)]
        excerpt = ""
        for line in segment_lines:
            if line and not _PAGE_PATTERN.search(line):
                excerpt = line[:120]
                break
        segments.append(
            {
                "page": current.get("page"),
                "line_start": current.get("line_start"),
                "line_end": current.get("line_end"),
                "text": text_value,
                "headings": headings[:6],
                "excerpt": excerpt or text_value[:120],
            }
        )
        current = None

    for index, line in enumerate(lines, start=1):
        page_match = _PAGE_PATTERN.search(line)
        if page_match:
            flush()
            raw_page = page_match.group(1) or page_match.group(2)
            current = {
                "page": int(raw_page) if raw_page and raw_page.isdigit() else None,
                "line_start": index,
                "line_end": index,
                "lines": [line],
            }
            continue
        if current is None:
            current = {
                "page": None,
                "line_start": index,
                "line_end": index,
                "lines": [line] if line else [],
            }
            continue
        current["line_end"] = index
        if line:
            current["lines"].append(line)
    flush()
    return [segment for segment in segments if segment.get("text")]


__all__ = ["build_page_segments"]
