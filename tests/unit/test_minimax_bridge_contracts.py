from __future__ import annotations

import pytest

from tests.helpers.contracts import require_symbol


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.ai
def test_minimax_bridge_validates_desensitized_request_payload():
    MiniMaxBridgeSettings = require_symbol("app.tools.minimax_bridge", "MiniMaxBridgeSettings")
    validate_bridge_request_payload = require_symbol("app.tools.minimax_bridge", "validate_bridge_request_payload")
    build_ai_safe_case_payload = require_symbol("app.core.privacy.desensitization", "build_ai_safe_case_payload")
    request_version = require_symbol("app.core.reviewers.ai.adapters", "EXTERNAL_HTTP_REQUEST_VERSION")

    settings = MiniMaxBridgeSettings()
    payload = {
        "contract_version": request_version,
        "requested_provider": "external_http",
        "model": "bridge-model",
        "timeout_seconds": 10,
        "privacy_guard": {
            "require_desensitized": True,
            "payload_marked_llm_safe": True,
        },
        "case_payload": build_ai_safe_case_payload(
            {"software_name": "Aurora", "version": "V1.0", "company_name": "Aurora Medical"}
        ),
        "rule_results": {"issues": []},
    }

    assert validate_bridge_request_payload(payload, settings) == []


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.ai
def test_minimax_bridge_response_uses_external_http_contract():
    build_bridge_response_payload = require_symbol("app.tools.minimax_bridge", "build_bridge_response_payload")
    response_version = require_symbol("app.core.reviewers.ai.adapters", "EXTERNAL_HTTP_RESPONSE_VERSION")

    response = build_bridge_response_payload(
        {
            "rule_results": {"issues": [{"severity": "minor", "desc": "demo"}]},
        },
        {
            "id": "chatcmpl-demo",
            "choices": [
                {
                    "message": {
                        "content": '{"summary":"Bridge summary","conclusion":"Bridge conclusion","resolution":"minimax_bridge_success"}'
                    }
                }
            ],
        },
        provider_request_id="bridge-001",
    )

    assert response["contract_version"] == response_version
    assert response["provider_request_id"] == "chatcmpl-demo"
    assert response["status"] == "ok"
    assert response["summary"] == "Bridge summary"


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.ai
def test_minimax_bridge_extracts_json_from_fenced_content():
    extract_json_object = require_symbol("app.tools.minimax_bridge", "_extract_json_object")

    payload = extract_json_object(
        """```json
{"summary":"ok","conclusion":"ok","resolution":"minimax_bridge_success"}
```"""
    )

    assert payload["summary"] == "ok"
