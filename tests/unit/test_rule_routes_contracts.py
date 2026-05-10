from __future__ import annotations

import pytest


@pytest.mark.unit
@pytest.mark.contract
def test_global_dimension_rule_route_saves_rule_items(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient

    from app.api.main import create_app
    from app.core.services import review_profile

    profile_path = tmp_path / "config" / "global_review_profile.json"
    monkeypatch.setattr(review_profile, "GLOBAL_REVIEW_PROFILE_PATH", profile_path)

    client = TestClient(create_app(testing=True))
    response = client.post(
        "/api/global-rules/source_code",
        data={
            "rule_source_code_item_code_desensitized_enabled": "1",
            "rule_source_code_item_code_desensitized_title": "源码脱敏必须完成",
            "rule_source_code_item_code_desensitized_severity": "severe",
            "rule_source_code_item_code_desensitized_prompt_hint": "重点排查密码和 token。",
        },
    )

    assert response.status_code == 200
    assert response.json()["success"] is True

    saved_profile = review_profile._load_global_review_profile()
    source_rules = saved_profile["dimension_rulebook"]["source_code"]["rules"]
    desensitized_rule = next(item for item in source_rules if item["key"] == "code_desensitized")
    assert desensitized_rule["title"] == "源码脱敏必须完成"
    assert desensitized_rule["severity"] == "severe"
