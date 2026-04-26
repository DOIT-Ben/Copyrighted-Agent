from __future__ import annotations

import pytest

from tests.helpers.contracts import require_symbol


@pytest.mark.unit
@pytest.mark.contract
def test_build_page_segments_splits_text_by_page_markers():
    build_page_segments = require_symbol("app.core.parsers.page_segments", "build_page_segments")
    text = "\n".join(
        [
            "page 1",
            "1. Intro",
            "This is page one",
            "page 2",
            "2. Environment",
            "Memory: 8G",
        ]
    )
    segments = build_page_segments(text)
    assert len(segments) == 2
    assert segments[0]["page"] == 1
    assert "1. Intro" in segments[0]["text"]
    assert segments[1]["page"] == 2
    assert "2. Environment" in segments[1]["excerpt"]


@pytest.mark.unit
@pytest.mark.contract
def test_attach_issue_evidence_anchors_prefers_page_segments():
    attach_issue_evidence_anchors = require_symbol("app.core.services.evidence_anchors", "attach_issue_evidence_anchors")
    issues = [{"rule_key": "doc_required_sections", "field_label": "运行环境", "section_label": "六、运行环境"}]
    text = "\n".join(["第 2 页", "六、运行环境", "硬件要求：8G 内存"])
    enriched = attach_issue_evidence_anchors(
        issues,
        text,
        page_segments=[
            {
                "page": 2,
                "line_start": 1,
                "line_end": 3,
                "text": text,
                "headings": ["六、运行环境"],
                "excerpt": "六、运行环境",
            }
        ],
    )
    anchor = dict(enriched[0].get("evidence_anchor", {}) or {})
    assert anchor.get("page") == 2
    assert anchor.get("line") == 1
    assert "运行环境" in str(anchor.get("matched_text", ""))
