from __future__ import annotations

import pytest

from tests.helpers.contracts import require_symbol


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.ai
def test_provider_sandbox_validates_desensitized_external_http_request():
    ProviderSandboxSettings = require_symbol("app.tools.provider_sandbox", "ProviderSandboxSettings")
    validate_sandbox_request_payload = require_symbol("app.tools.provider_sandbox", "validate_sandbox_request_payload")
    build_ai_safe_case_payload = require_symbol("app.core.privacy.desensitization", "build_ai_safe_case_payload")
    request_version = require_symbol("app.core.reviewers.ai.adapters", "EXTERNAL_HTTP_REQUEST_VERSION")

    settings = ProviderSandboxSettings()
    payload = {
        "contract_version": request_version,
        "requested_provider": "external_http",
        "model": "sandbox-model",
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

    assert validate_sandbox_request_payload(payload, settings) == []


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.ai
def test_provider_sandbox_rejects_non_safe_payload_when_strict_mode_enabled():
    ProviderSandboxSettings = require_symbol("app.tools.provider_sandbox", "ProviderSandboxSettings")
    validate_sandbox_request_payload = require_symbol("app.tools.provider_sandbox", "validate_sandbox_request_payload")
    request_version = require_symbol("app.core.reviewers.ai.adapters", "EXTERNAL_HTTP_REQUEST_VERSION")

    settings = ProviderSandboxSettings(strict_desensitized=True)
    payload = {
        "contract_version": request_version,
        "requested_provider": "external_http",
        "model": "sandbox-model",
        "timeout_seconds": 10,
        "privacy_guard": {
            "require_desensitized": True,
            "payload_marked_llm_safe": False,
        },
        "case_payload": {
            "software_name": "Aurora",
            "version": "V1.0",
            "company_name": "Aurora Medical",
        },
        "rule_results": {"issues": []},
    }

    errors = validate_sandbox_request_payload(payload, settings)
    assert "privacy_guard_payload_not_marked_safe" in errors
    assert "case_payload_not_ai_safe" in errors


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.ai
def test_provider_sandbox_success_response_uses_external_http_contract():
    build_sandbox_response_payload = require_symbol("app.tools.provider_sandbox", "build_sandbox_response_payload")
    response_version = require_symbol("app.core.reviewers.ai.adapters", "EXTERNAL_HTTP_RESPONSE_VERSION")

    response = build_sandbox_response_payload(
        {
            "case_payload": {"llm_safe": True},
            "rule_results": {"issues": [{"severity": "minor", "desc": "demo"}]},
        },
        mode="success",
        provider_request_id="sandbox-001",
    )

    assert response["contract_version"] == response_version
    assert response["provider_request_id"] == "sandbox-001"
    assert response["status"] == "ok"
    assert "summary" in response
