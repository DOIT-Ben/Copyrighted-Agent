from __future__ import annotations

import re


_PAGE_PATTERN = re.compile(r"(?:第\s*(\d+)\s*页|\bpage\s*(\d+)\b)", re.IGNORECASE)
_HEADING_PATTERN = re.compile(r"^\s*(?:[一二三四五六七八九十]+、|\d+(?:\.\d+)*[\.、]?)[^\n]{0,40}$")


def _normalized_lines(text: str) -> list[str]:
    return [str(line).strip() for line in str(text or "").splitlines()]


def _page_markers(lines: list[str]) -> list[tuple[int, int]]:
    markers: list[tuple[int, int]] = []
    for index, line in enumerate(lines, start=1):
        match = _PAGE_PATTERN.search(line)
        if not match:
            continue
        raw = match.group(1) or match.group(2)
        if raw and raw.isdigit():
            markers.append((index, int(raw)))
    return markers


def _page_for_line(line_number: int, markers: list[tuple[int, int]]) -> int | None:
    page: int | None = None
    for marker_line, marker_page in markers:
        if marker_line > line_number:
            break
        page = marker_page
    return page


def _find_heading(lines: list[str], keyword: str) -> tuple[int, str] | None:
    needle = str(keyword or "").strip()
    if not needle:
        return None
    for index, line in enumerate(lines, start=1):
        if needle in line and _HEADING_PATTERN.match(line):
            return index, line
    for index, line in enumerate(lines, start=1):
        if needle in line:
            return index, line
    return None


def _keyword_candidates(issue: dict) -> list[str]:
    rule_key = str(issue.get("rule_key", "") or "").strip().lower()
    mapping = {
        "software_name_present": ["软件名称"],
        "version_present": ["版本号"],
        "company_present": ["著作权人", "申请主体", "单位名称"],
        "missing_fields_listed": ["软件名称", "版本号", "著作权人"],
        "doc_required_sections": ["运行环境", "安装说明", "初始化步骤"],
        "doc_terms_consistent": ["系统", "平台", "APP", "小程序", "MediaPipe", "Media Pipe"],
        "doc_page_count": ["第 1 页", "第1页", "page 1"],
        "doc_header_footer_valid": ["页眉", "页脚", "第 1 页", "第1页"],
        "doc_ui_screenshots_valid": ["截图", "界面", "页面展示"],
        "doc_text_quality": ["引言", "系统概述", "功能介绍"],
        "code_readable": ["import", "class", "def"],
        "code_format_clean": ["1 ", "2 ", "3 "],
        "code_page_strategy": ["第 1 页", "第1页", "page 1"],
        "code_desensitized": ["password", "token", "secret", "Authorization", "@"],
        "code_logic_supports_doc": ["def ", "class ", "function ", "calculate", "login", "query", "report"],
        "code_comment_ratio_reasonable": ["#", "//", "/*"],
        "agreement_typo_terms": ["签定", "签订"],
        "agreement_alias_consistent": ["甲方", "乙方", "子甲方", "副甲方"],
        "agreement_key_people": ["项目负责人", "指导老师"],
        "agreement_dates_valid": ["签署日期", "申请日期", "完成日期"],
        "agreement_stamp_signature": ["电子章", "扫描件", "签字", "签章"],
        "agreement_approval_sheet": ["审批表", "技术开发合同", "科研合同审批表"],
        "online_category_valid": ["软件分类"],
        "online_development_mode_valid": ["开发方式"],
        "online_subject_type_valid": ["主体类型"],
        "online_address_precise": ["地址", "证书地址"],
        "online_dates_consistent": ["申请日期", "开发完成日期"],
    }
    candidates = list(mapping.get(rule_key, []))
    for key in ("field_label", "section_label"):
        value = str(issue.get(key, "") or "").strip()
        if value and value not in candidates:
            candidates.append(value)
    return candidates[:6]


def _excerpt(lines: list[str], line_number: int) -> str:
    start = max(0, line_number - 1)
    for index in range(start, min(start + 3, len(lines))):
        line = lines[index].strip()
        if line:
            return line[:80]
    return ""


def attach_issue_evidence_anchors(issues: list[dict], text: str) -> list[dict]:
    lines = _normalized_lines(text)
    markers = _page_markers(lines)
    enriched: list[dict] = []
    for raw_issue in list(issues or []):
        issue = dict(raw_issue or {})
        if issue.get("evidence_anchor", {}).get("page"):
            enriched.append(issue)
            continue
        match_line: int | None = None
        match_text = ""
        for keyword in _keyword_candidates(issue):
            found = _find_heading(lines, keyword)
            if found:
                match_line, match_text = found
                break
        if not match_line:
            enriched.append(issue)
            continue
        anchor = dict(issue.get("evidence_anchor", {}) or {})
        anchor.setdefault("line", match_line)
        page = _page_for_line(match_line, markers)
        if page is not None:
            anchor.setdefault("page", page)
        if match_text:
            anchor.setdefault("matched_text", match_text[:80])
        snippet = _excerpt(lines, match_line)
        if snippet:
            anchor.setdefault("excerpt", snippet)
        issue["evidence_anchor"] = anchor
        if snippet and not issue.get("evidence_excerpt"):
            issue["evidence_excerpt"] = snippet
        if page is not None and not issue.get("evidence_page"):
            issue["evidence_page"] = page
        enriched.append(issue)
    return enriched


__all__ = ["attach_issue_evidence_anchors"]
