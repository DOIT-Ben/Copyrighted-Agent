from __future__ import annotations

import pytest

from tests.helpers.contracts import require_symbol


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.review
@pytest.mark.ai
def test_build_ai_prompt_snapshot_includes_profile_dimensions_and_output_contract():
    build_ai_prompt_snapshot = require_symbol("app.core.reviewers.ai.prompt_builder", "build_ai_prompt_snapshot")

    snapshot = build_ai_prompt_snapshot(
        {"software_name": "Aurora Review Desk", "version": "V1.0", "company_name": "Aurora Medical", "llm_safe": True},
        {"issues": [{"severity": "moderate", "title": "Version mismatch", "message": "Version differs between files"}]},
        {
            "preset_key": "source_code_strict",
            "enabled_dimensions": ["identity", "source_code", "ai"],
            "focus_mode": "source_code_first",
            "strictness": "strict",
            "llm_instruction": "Focus on code naming and version alignment.",
        },
        requested_provider="external_http",
    )

    assert snapshot["system_prompt"]
    assert 'Required JSON keys: "summary", "conclusion", "resolution".' in snapshot["system_prompt"]
    assert "Dimension rulebook:" in snapshot["user_prompt"]
    assert "Desensitized case payload JSON:" in snapshot["user_prompt"]
    assert "Rule engine findings:" in snapshot["user_prompt"]
    assert "Evidence targets:" in snapshot["user_prompt"]
    assert "Common failure patterns:" in snapshot["user_prompt"]
    assert snapshot["review_profile_summary"]["focus_mode"] == "source_code_first"
    assert snapshot["review_profile_summary"]["strictness"] == "strict"
    assert snapshot["review_profile_summary"]["enabled_dimensions"] == ["identity", "source_code", "ai"]
    assert len(snapshot["active_dimensions"]) == 3
    source_dimension = next(item for item in snapshot["active_dimensions"] if item["key"] == "source_code")
    assert source_dimension["evidence_targets"]
    assert source_dimension["common_failures"]
    assert source_dimension["operator_notes"]


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.review
@pytest.mark.ai
def test_build_ai_prompt_snapshot_exposes_safe_material_inventory():
    build_ai_prompt_snapshot = require_symbol("app.core.reviewers.ai.prompt_builder", "build_ai_prompt_snapshot")

    snapshot = build_ai_prompt_snapshot(
        {
            "software_name": "[safe-name]",
            "version": "[safe-version]",
            "company_name": "",
            "llm_safe": True,
            "privacy_policy": "local_manual_redaction_v1",
            "material_count": 3,
            "material_type_counts": {"source_code": 1, "software_doc": 1, "agreement": 1},
            "material_inventory": [{"material_type": "source_code", "parse_status": "completed"}],
        },
        {"issues": []},
        {"enabled_dimensions": ["completeness", "source_code", "ai"]},
        requested_provider="external_http",
    )

    assert '"material_count": 3' in snapshot["user_prompt"]
    assert '"source_code": 1' in snapshot["user_prompt"]
    assert '"material_type": "source_code"' in snapshot["user_prompt"]


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.review
@pytest.mark.ai
def test_build_ai_prompt_snapshot_supports_online_filing_dimension():
    build_ai_prompt_snapshot = require_symbol("app.core.reviewers.ai.prompt_builder", "build_ai_prompt_snapshot")

    snapshot = build_ai_prompt_snapshot(
        {"software_name": "Aurora Review Desk", "version": "V1.0", "company_name": "Aurora Medical", "llm_safe": True},
        {"issues": []},
        {
            "enabled_dimensions": ["identity", "online_filing", "ai"],
            "focus_mode": "balanced",
            "strictness": "standard",
            "llm_instruction": "If online filing data is missing, say that explicitly.",
        },
        requested_provider="external_http",
    )

    keys = [item["key"] for item in snapshot["active_dimensions"]]
    assert "online_filing" in keys
    assert "在线填报信息审查" in snapshot["user_prompt"]


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.review
def test_dimension_rulebook_normalizes_guidance_lists():
    dimension_rulebook_from_profile = require_symbol("app.core.services.review_rulebook", "dimension_rulebook_from_profile")

    rulebook = dimension_rulebook_from_profile(
        {
            "dimension_rulebook": {
                "consistency": {
                    "evidence_targets": "- 信息采集表软件名称\n- 协议主体排序",
                    "common_failures": ["名称不一致", "顺序不一致"],
                    "operator_notes": "- 先统一名称\n- 再统一顺序",
                }
            }
        }
    )

    entry = rulebook["consistency"]
    assert entry["evidence_targets"][:2] == ["信息采集表软件名称", "协议主体排序"]
    assert entry["common_failures"][:2] == ["名称不一致", "顺序不一致"]
    assert entry["operator_notes"][:2] == ["先统一名称", "再统一顺序"]
