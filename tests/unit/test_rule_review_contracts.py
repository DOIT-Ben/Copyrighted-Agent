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
def test_agreement_rule_review_detects_approval_sheet_gap():
    review_agreement_text = require_symbol("app.core.reviewers.rules.agreement", "review_agreement_text")
    result = review_agreement_text("甲方与乙方签订合作开发协议。项目负责人为张三。")
    assert issues_contain(result, "审批手续不完整")


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.review
def test_agreement_rule_review_detects_missing_key_people():
    review_agreement_text = require_symbol("app.core.reviewers.rules.agreement", "review_agreement_text")
    result = review_agreement_text("甲方与乙方签订技术开发合同，并附科研合同审批表。")
    assert issues_contain(result, "关键人员")


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.review
def test_agreement_rule_review_detects_date_gap_to_apply_date():
    review_agreement_text = require_symbol("app.core.reviewers.rules.agreement", "review_agreement_text")
    result = review_agreement_text("签订日期：2026-01-01\n申请日期：2026-03-01")
    assert issues_contain(result, "距离申请日期过近")


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
def test_document_rule_review_detects_environment_detail_gap():
    review_document_text = require_symbol("app.core.reviewers.rules.document", "review_document_text")
    result = review_document_text("软件名称：极光关节运动分析系统\n版本号：V1.0\n六、运行环境\n操作系统：Windows 10\n七、安装说明\n双击运行")
    assert issues_contain(result, "硬件要求")


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.review
def test_document_rule_review_detects_term_mix():
    review_document_text = require_symbol("app.core.reviewers.rules.document", "review_document_text")
    result = review_document_text("软件名称：极光分析系统\n版本号：V1.0\n六、运行环境\n硬件：8G 内存\n软件：Windows 10\n七、安装说明/初始化步骤\n双击运行\n本系统用于动作分析。本平台支持数据导出。")
    assert issues_contain(result, "系统")


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.review
def test_document_rule_review_detects_page_count_gap():
    review_document_text = require_symbol("app.core.reviewers.rules.document", "review_document_text")
    result = review_document_text("\n".join([f"第{i}页" for i in range(1, 7)]))
    assert issues_contain(result, "页数偏少")


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.review
def test_document_rule_review_detects_screenshot_hint_issue():
    review_document_text = require_symbol("app.core.reviewers.rules.document", "review_document_text")
    result = review_document_text("系统页面展示如下，包含登录页截图，顶部有时间、电池和信号图标。")
    assert issues_contain(result, "状态栏")


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.review
def test_source_code_rule_review_detects_garbled_ratio():
    review_source_code_text = require_symbol("app.core.reviewers.rules.source_code", "review_source_code_text")
    result = review_source_code_text("import numpy愠伋火档火烈鈦种药妞嬬伃铁伌愤懏鐛")
    assert issues_contain(result, "乱码")


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.review
def test_source_code_rule_review_detects_page_strategy_gap():
    review_source_code_text = require_symbol("app.core.reviewers.rules.source_code", "review_source_code_text")
    text = "\n".join([f"第{i}页" for i in range(1, 36)] + ["第99页"])
    result = review_source_code_text(text)
    assert issues_contain(result, "前30页 + 后30页")


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
def test_info_form_rule_review_detects_sensitive_terms():
    review_info_form_text = require_symbol("app.core.reviewers.rules.info_form", "review_info_form_text")
    result = review_info_form_text("软件名称：某某爬虫平台\n版本号：V1.0\n著作权人：测试公司")
    assert issues_contain(result, "敏感词")
    assert issues_contain(result, "爬虫")


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.review
def test_info_form_rule_review_lists_missing_fields():
    review_info_form_text = require_symbol("app.core.reviewers.rules.info_form", "review_info_form_text")
    result = review_info_form_text("著作权人：测试公司")
    assert issues_contain(result, "缺少关键信息")


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.review
def test_cross_material_review_detects_name_or_version_mismatch():
    review_case_consistency = require_symbol("app.core.reviewers.rules.cross_material", "review_case_consistency")
    result = review_case_consistency(
        info_form={"software_name": "极光关节运动分析系统", "version": "V1.0"},
        source_code={"software_name": "极光关节运动分析系统", "version": "V1.0"},
        software_doc={"software_name": "极光粗大关节分析系统", "version": "V2.0"},
    )
    assert issues_contain(result, "一致")


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.review
def test_cross_material_review_includes_observed_values_and_agreement():
    review_case_consistency = require_symbol("app.core.reviewers.rules.cross_material", "review_case_consistency")
    result = review_case_consistency(
        info_form={"software_name": "极光关节运动分析系统", "version": "V1.0"},
        source_code={"software_name": "极光关节运动分析系统", "version": "V1.0"},
        software_doc={"software_name": "极光姿态分析平台", "version": "V2.0"},
        agreement={"software_name": "极光姿态分析平台", "version": "v2.0"},
    )
    assert issues_contain(result, "信息采集表=")
    assert issues_contain(result, "合作协议=")


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.review
def test_cross_material_review_detects_term_family_mismatch():
    review_case_consistency = require_symbol("app.core.reviewers.rules.cross_material", "review_case_consistency")
    result = review_case_consistency(
        info_form={"software_name": "极光运动分析系统", "version": "V1.0"},
        source_code={"software_name": "极光运动分析系统", "version": "V1.0"},
        software_doc={"software_name": "极光运动分析平台", "version": "V1.0"},
        agreement={},
    )
    assert issues_contain(result, "称呼不统一")


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.review
def test_cross_material_review_detects_doc_code_feature_gap():
    review_case_consistency = require_symbol("app.core.reviewers.rules.cross_material", "review_case_consistency")
    result = review_case_consistency(
        info_form={},
        source_code={"feature_terms": ["login", "query"]},
        software_doc={"feature_terms": ["报表分析", "数据导出", "审核功能", "统计模块"]},
        agreement={},
    )
    assert issues_contain(result, "功能点与源代码信号呼应不足")


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.review
def test_online_filing_review_detects_category_subject_address_and_date_issues():
    review_online_filing_payload = require_symbol("app.core.reviewers.rules.online_filing", "review_online_filing_payload")
    result = review_online_filing_payload(
        {
            "software_category": "工具软件",
            "development_mode": "原创",
            "subject_type": "自然人",
            "completion_date": "2026-04-20",
            "apply_date": "2026-04-19",
            "address": "北京市",
            "certificate_address": "上海市",
            "applicants": ["甲公司", "乙公司"],
        },
        case_payload={"company_name": "极光科技有限公司"},
        info_form={"completion_dates": ["2026-04-18"]},
        agreement={"party_sequence": ["甲公司", "乙公司"]},
    )
    assert issues_contain(result, "应用软件")
    assert issues_contain(result, "合作开发")
    assert issues_contain(result, "企业法人")
    assert issues_contain(result, "地址信息精度不足")
    assert issues_contain(result, "开发完成日期")


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.review
def test_cross_material_review_includes_online_filing_values():
    review_case_consistency = require_symbol("app.core.reviewers.rules.cross_material", "review_case_consistency")
    result = review_case_consistency(
        info_form={"software_name": "极光分析系统", "version": "V1.0", "completion_dates": ["2026-04-01"], "party_sequence": ["甲公司", "乙公司"]},
        source_code={"software_name": "极光分析系统", "version": "V1.0"},
        software_doc={"software_name": "极光分析系统", "version": "V1.0"},
        agreement={"software_name": "极光分析系统", "version": "V1.0"},
        online_filing={"software_name": "极光分析平台", "version": "V2.0", "completion_date": "2026-04-02", "applicants": ["乙公司", "甲公司"]},
    )
    assert issues_contain(result, "在线填报=")
    assert issues_contain(result, "在线填报中的申请人顺序")
