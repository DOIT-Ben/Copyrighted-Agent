from __future__ import annotations

import pytest

from tests.helpers.contracts import require_symbol


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.review
def test_rule_review_issues_include_structured_anchor_fields():
    review_info_form_text = require_symbol("app.core.reviewers.rules.info_form", "review_info_form_text")
    result = review_info_form_text("著作权人：测试公司")
    issue = next(item for item in result["issues"] if item.get("rule_key") == "software_name_present")
    assert issue.get("field_label") == "软件名称"
    assert issue.get("section_label") == "基础信息"
    assert "软件名称字段" in str(issue.get("anchor_hint", ""))
    evidence_anchor = dict(issue.get("evidence_anchor", {}) or {})
    assert evidence_anchor.get("material_area") == "信息采集表首页"


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.review
def test_cross_material_issue_includes_anchor_for_party_order():
    review_case_consistency = require_symbol("app.core.reviewers.rules.cross_material", "review_case_consistency")
    result = review_case_consistency(
        info_form={"party_sequence": ["甲公司", "乙公司"]},
        source_code={},
        software_doc={},
        agreement={"party_sequence": ["乙公司", "甲公司"]},
    )
    issue = next(item for item in result["issues"] if item.get("rule_key") == "party_order_match")
    assert issue.get("field_label") == "申请人排序"
    assert issue.get("section_label") == "跨材料一致性"
    assert "排序" in str(issue.get("anchor_hint", ""))
