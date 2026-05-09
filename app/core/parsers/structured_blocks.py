from __future__ import annotations


def build_segments_from_blocks(blocks: list[dict]) -> list[dict]:
    segments: list[dict] = []
    current_page: int | None = None
    current_lines: list[str] = []
    current_headings: list[str] = []
    current_line_start = 1

    def flush() -> None:
        nonlocal current_lines, current_headings
        text = "\n".join(line for line in current_lines if str(line).strip()).strip()
        if not text:
            current_lines = []
            current_headings = []
            return
        excerpt = ""
        for line in current_lines:
            line_text = str(line).strip()
            if line_text:
                excerpt = line_text[:120]
                break
        segments.append(
            {
                "page": current_page,
                "line_start": current_line_start,
                "line_end": current_line_start + len(current_lines) - 1,
                "text": text,
                "headings": current_headings[:6],
                "excerpt": excerpt or text[:120],
            }
        )
        current_lines = []
        current_headings = []

    for block in list(blocks or []):
        page = block.get("page")
        text = str(block.get("text", "") or "").strip()
        if not text:
            continue
        if current_lines and page != current_page:
            flush()
        if not current_lines:
            current_page = page
            current_line_start = 1
        current_lines.append(text)
        if block.get("is_heading"):
            current_headings.append(text[:80])
    flush()
    return segments


__all__ = ["build_segments_from_blocks"]
