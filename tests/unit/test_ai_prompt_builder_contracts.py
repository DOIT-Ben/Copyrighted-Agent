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
    assert snapshot["review_profile_summary"]["focus_mode"] == "source_code_first"
    assert snapshot["review_profile_summary"]["strictness"] == "strict"
    assert snapshot["review_profile_summary"]["enabled_dimensions"] == ["identity", "source_code", "ai"]
    assert len(snapshot["active_dimensions"]) == 3


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
