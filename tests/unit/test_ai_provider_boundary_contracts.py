from __future__ import annotations

import pytest

from tests.helpers.contracts import renderable_text, require_symbol


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.review
@pytest.mark.ai
def test_resolve_case_ai_provider_honors_enable_switch():
    AppConfig = require_symbol("app.core.services.app_config", "AppConfig")
    resolve_case_ai_provider = require_symbol("app.core.reviewers.ai.service", "resolve_case_ai_provider")

    disabled_config = AppConfig(ai_enabled=False, ai_provider="safe_stub")
    enabled_config = AppConfig(ai_enabled=True, ai_provider="safe_stub")

    assert resolve_case_ai_provider(config=disabled_config) == "mock"
    assert resolve_case_ai_provider(config=enabled_config) == "safe_stub"


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.review
@pytest.mark.ai
def test_non_mock_provider_requires_desensitized_payload():
    AppConfig = require_symbol("app.core.services.app_config", "AppConfig")
    generate_case_ai_review = require_symbol("app.core.reviewers.ai.service", "generate_case_ai_review")

    config = AppConfig(ai_enabled=True, ai_provider="safe_stub")
    with pytest.raises(ValueError):
        generate_case_ai_review(
            case_payload={"software_name": "极光关节运动分析系统", "version": "V1.0", "company_name": "极光医疗"},
            rule_results={"issues": [{"severity": "moderate", "desc": "版本号不一致"}]},
            provider="safe_stub",
            config=config,
        )


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.review
@pytest.mark.ai
def test_non_mock_provider_accepts_ai_safe_payload():
    AppConfig = require_symbol("app.core.services.app_config", "AppConfig")
    build_ai_safe_case_payload = require_symbol("app.core.privacy.desensitization", "build_ai_safe_case_payload")
    generate_case_ai_review = require_symbol("app.core.reviewers.ai.service", "generate_case_ai_review")

    config = AppConfig(ai_enabled=True, ai_provider="safe_stub")
    safe_payload = build_ai_safe_case_payload(
        {
            "software_name": "极光关节运动分析系统",
            "version": "V1.0",
            "company_name": "极光医疗",
        }
    )

    result = generate_case_ai_review(
        case_payload=safe_payload,
        rule_results={"issues": [{"severity": "moderate", "desc": "版本号不一致"}]},
        provider="safe_stub",
        config=config,
    )
    text = renderable_text(result)
    assert result["provider"] == "safe_stub"
    assert "safe" in text or "llm_safe" in text


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.review
@pytest.mark.ai
def test_external_http_provider_can_fallback_to_mock_when_not_configured():
    AppConfig = require_symbol("app.core.services.app_config", "AppConfig")
    build_ai_safe_case_payload = require_symbol("app.core.privacy.desensitization", "build_ai_safe_case_payload")
    generate_case_ai_review = require_symbol("app.core.reviewers.ai.service", "generate_case_ai_review")

    config = AppConfig(ai_enabled=True, ai_provider="external_http", ai_fallback_to_mock=True)
    safe_payload = build_ai_safe_case_payload(
        {
            "software_name": "极光关节运动分析系统",
            "version": "V1.0",
            "company_name": "极光医疗",
        }
    )

    result = generate_case_ai_review(
        case_payload=safe_payload,
        rule_results={"issues": [{"severity": "moderate", "desc": "版本号不一致"}]},
        provider="external_http",
        config=config,
    )

    assert result["provider"] == "mock"
    assert result["resolution"] == "provider_exception_fallback"
