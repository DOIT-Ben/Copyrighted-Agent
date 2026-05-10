from __future__ import annotations

from tests.helpers.contracts import require_symbol


def test_desensitize_text_masks_labeled_fields_and_contacts():
    desensitize_text = require_symbol("app.core.privacy.desensitization", "desensitize_text")
    payload = (
        "软件名称：心脉监测平台\n"
        "著作权人：星河科技有限公司\n"
        "联系人：张三\n"
        "手机：13800138000\n"
        "邮箱：demo@example.com\n"
        "统一社会信用代码：91350100MA12345678\n"
    )

    result = desensitize_text(
        payload,
        metadata={"software_name": "心脉监测平台", "company_name": "星河科技有限公司", "version": "V1.0"},
    )

    assert "心脉监测平台" not in result["text"]
    assert "星河科技有限公司" not in result["text"]
    assert "13800138000" not in result["text"]
    assert "demo@example.com" not in result["text"]
    assert result["summary"]["llm_safe"] is True
    assert result["summary"]["total_replacements"] >= 4


def test_build_ai_safe_case_payload_masks_case_fields():
    build_ai_safe_case_payload = require_symbol("app.core.privacy.desensitization", "build_ai_safe_case_payload")
    safe_payload = build_ai_safe_case_payload(
        {
            "software_name": "心脉监测平台",
            "version": "V1.0",
            "company_name": "星河科技有限公司",
        }
    )

    assert safe_payload["software_name"] == "[已脱敏-软件名称]"
    assert safe_payload["version"] == "[已脱敏-版本号]"
    assert safe_payload["company_name"] == "[已脱敏-公司名称]"
    assert safe_payload["privacy_policy"] == "local_manual_redaction_v1"
def test_build_ai_safe_case_payload_keeps_safe_material_inventory_only():
    build_ai_safe_case_payload = require_symbol("app.core.privacy.desensitization", "build_ai_safe_case_payload")
    is_ai_safe_case_payload = require_symbol("app.core.privacy.desensitization", "is_ai_safe_case_payload")

    safe_payload = build_ai_safe_case_payload(
        {
            "software_name": "Sensitive Product",
            "version": "V1.0",
            "company_name": "Sensitive Company",
            "material_count": 2,
            "material_type_counts": {"source_code": 1, "software_doc": 1},
            "material_inventory": [
                {
                    "material_type": "source_code",
                    "file_ext": ".docx",
                    "parse_status": "completed",
                    "review_status": "completed",
                    "quality_level": "medium",
                    "original_filename": "Sensitive Product source.docx",
                }
            ],
        }
    )

    assert safe_payload["material_count"] == 2
    assert safe_payload["material_type_counts"]["source_code"] == 1
    assert safe_payload["material_inventory"][0]["material_type"] == "source_code"
    assert "original_filename" not in safe_payload["material_inventory"][0]
    assert "Sensitive Product" not in str(safe_payload)
    assert is_ai_safe_case_payload(safe_payload) is True


def test_build_ai_safe_rule_results_removes_external_evidence_values():
    build_ai_safe_rule_results = require_symbol("app.core.privacy.desensitization", "build_ai_safe_rule_results")
    is_ai_safe_rule_results = require_symbol("app.core.privacy.desensitization", "is_ai_safe_rule_results")

    safe_results = build_ai_safe_rule_results(
        {
            "issues": [
                {
                    "severity": "severe",
                    "category": "一致性",
                    "rule_key": "software_name_exact_match",
                    "desc": "不同材料中的软件名称不一致。当前识别到：设计文档=Sensitive Product；协议=Other Product。",
                    "suggest": "统一软件名称。",
                    "original_filename": "Sensitive Product 合作协议.docx",
                    "evidence_excerpt": "Sensitive Product V1.0 belongs to Sensitive Company",
                    "evidence_anchor": {"material_area": "合作协议正文", "matched_text": "Sensitive Product"},
                }
            ]
        }
    )

    rendered = str(safe_results)
    assert safe_results["llm_safe"] is True
    assert safe_results["issues"][0]["evidence_redacted"] is True
    assert "original_filename" not in safe_results["issues"][0]
    assert "evidence_excerpt" not in safe_results["issues"][0]
    assert "Sensitive Product" not in rendered
    assert "Other Product" not in rendered
    assert is_ai_safe_rule_results(safe_results) is True


def test_generate_case_ai_review_external_prompt_uses_safe_rule_results():
    AppConfig = require_symbol("app.core.services.app_config", "AppConfig")
    build_ai_safe_case_payload = require_symbol("app.core.privacy.desensitization", "build_ai_safe_case_payload")
    generate_case_ai_review = require_symbol("app.core.reviewers.ai.service", "generate_case_ai_review")

    safe_case = build_ai_safe_case_payload({"software_name": "Sensitive Product", "version": "V1.0"})
    result = generate_case_ai_review(
        safe_case,
        {
            "issues": [
                {
                    "severity": "severe",
                    "rule_key": "software_name_exact_match",
                    "desc": "当前识别到：设计文档=Sensitive Product；协议=Other Product。",
                    "evidence_excerpt": "Sensitive Product raw evidence",
                }
            ]
        },
        provider="safe_stub",
        config=AppConfig(ai_enabled=True, ai_provider="safe_stub"),
    )

    prompt_text = str(result.get("prompt_snapshot", {}))
    assert "Sensitive Product" not in prompt_text
    assert "Other Product" not in prompt_text
    assert "evidence_excerpt" not in prompt_text
