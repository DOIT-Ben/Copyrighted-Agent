from __future__ import annotations

import pytest

from tests.helpers.contracts import require_symbol


@pytest.mark.unit
@pytest.mark.contract
def test_attach_issue_evidence_anchors_adds_path_and_match_text():
    attach_issue_evidence_anchors = require_symbol("app.core.services.evidence_anchors", "attach_issue_evidence_anchors")
    issues = [{"rule_key": "doc_required_sections", "field_label": "运行环境", "section_label": "六、运行环境"}]
    enriched = attach_issue_evidence_anchors(
        issues,
        "第 2 页\n六、运行环境\n硬件要求：8G 内存",
        page_segments=[
            {
                "page": 2,
                "line_start": 1,
                "line_end": 3,
                "text": "第 2 页\n六、运行环境\n硬件要求：8G 内存",
                "headings": ["六、运行环境"],
                "excerpt": "六、运行环境",
            }
        ],
    )
    issue = enriched[0]
    anchor = dict(issue.get("evidence_anchor", {}) or {})
    assert anchor.get("path")
    assert "第 2 页" in str(anchor.get("path", ""))
    assert issue.get("evidence_match_text") == "六、运行环境"
    assert issue.get("evidence_path")
