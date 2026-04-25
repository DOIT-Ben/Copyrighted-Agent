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
