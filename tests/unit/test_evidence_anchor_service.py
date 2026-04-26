from __future__ import annotations

import pytest

from tests.helpers.contracts import require_symbol


@pytest.mark.unit
@pytest.mark.contract
def test_attach_issue_evidence_anchors_adds_page_line_and_excerpt():
    attach_issue_evidence_anchors = require_symbol("app.core.services.evidence_anchors", "attach_issue_evidence_anchors")
    issues = [{"rule_key": "doc_required_sections", "field_label": "运行环境", "section_label": "六、运行环境"}]
    text = "\n".join(
        [
            "第 3 页",
            "五、系统概述",
            "六、运行环境",
            "硬件要求：8G 内存",
            "软件环境：Windows 10",
        ]
    )
    enriched = attach_issue_evidence_anchors(issues, text)
    anchor = dict(enriched[0].get("evidence_anchor", {}) or {})
    assert anchor.get("page") == 3
    assert anchor.get("line") == 3
    assert "运行环境" in str(anchor.get("excerpt", ""))
