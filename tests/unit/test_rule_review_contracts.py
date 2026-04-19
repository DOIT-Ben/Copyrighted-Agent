from __future__ import annotations

import pytest

from tests.helpers.contracts import get_metadata, issues_contain, require_symbol


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.review
def test_agreement_rule_review_detects_signing_word_issue():
    review_agreement_text = require_symbol("app.core.reviewers.rules.agreement", "review_agreement_text")
    result = review_agreement_text("本协议自双方签定之日起生效。")
    assert issues_contain(result, "签订")


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.review
def test_document_rule_review_detects_version_mismatch():
    review_document_text = require_symbol("app.core.reviewers.rules.document", "review_document_text")
    result = review_document_text("极光关节运动分析系统 V1.0\n页眉：极光关节运动分析系统 V2.0 第1页")
    assert issues_contain(result, "版本")


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.review
def test_source_code_rule_review_detects_garbled_ratio():
    review_source_code_text = require_symbol("app.core.reviewers.rules.source_code", "review_source_code_text")
    result = review_source_code_text("import numpy愠⁳灮椋灭牯⁴獯椋灭牯⁴慰摮獡")
    assert issues_contain(result, "乱码")


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.review
def test_info_form_rule_review_extracts_core_fields():
    review_info_form_text = require_symbol("app.core.reviewers.rules.info_form", "review_info_form_text")
    result = review_info_form_text("软件名称：极光关节运动分析系统\n版本号：V1.0\n著作权人：极光医疗科技有限公司")
    metadata = get_metadata(result)
    text = str(metadata)
    assert "极光关节运动分析系统" in text
    assert "V1.0" in text


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.review
def test_cross_material_review_detects_name_or_version_mismatch():
    review_case_consistency = require_symbol(
        "app.core.reviewers.rules.cross_material",
        "review_case_consistency",
    )
    result = review_case_consistency(
        info_form={"software_name": "极光关节运动分析系统", "version": "V1.0"},
        source_code={"software_name": "极光关节运动分析系统", "version": "V1.0"},
        software_doc={"software_name": "极光粗大关节分析系统", "version": "V2.0"},
    )
    assert issues_contain(result, "一致")

