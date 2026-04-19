from __future__ import annotations

import json
import os
import urllib.error

import pytest

from tests.helpers.contracts import require_module, require_symbol, renderable_text


class _FakeResponse:
    def __init__(self, payload: bytes):
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.review
@pytest.mark.ai
def test_external_http_request_payload_includes_contract_and_privacy_guard():
    AppConfig = require_symbol("app.core.services.app_config", "AppConfig")
    build_ai_safe_case_payload = require_symbol("app.core.privacy.desensitization", "build_ai_safe_case_payload")
    build_external_http_request_payload = require_symbol(
        "app.core.reviewers.ai.adapters",
        "build_external_http_request_payload",
    )
    request_version = require_symbol("app.core.reviewers.ai.adapters", "EXTERNAL_HTTP_REQUEST_VERSION")

    config = AppConfig(ai_enabled=True, ai_provider="external_http", ai_model="demo-model", ai_timeout_seconds=12)
    safe_payload = build_ai_safe_case_payload(
        {
            "software_name": "Aurora Review Desk",
            "version": "V1.0",
            "company_name": "Aurora Medical",
        }
    )

    payload = build_external_http_request_payload(
        safe_payload,
        {"issues": [{"severity": "minor", "desc": "example"}]},
        "external_http",
        config,
    )

    assert payload["contract_version"] == request_version
    assert payload["requested_provider"] == "external_http"
    assert payload["model"] == "demo-model"
    assert payload["timeout_seconds"] == 12
    assert payload["privacy_guard"]["require_desensitized"] is True
    assert payload["privacy_guard"]["payload_marked_llm_safe"] is True


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.review
@pytest.mark.ai
def test_normalize_external_http_response_maps_required_fields():
    AppConfig = require_symbol("app.core.services.app_config", "AppConfig")
    normalize_external_http_response = require_symbol(
        "app.core.reviewers.ai.adapters",
        "normalize_external_http_response",
    )
    response_version = require_symbol("app.core.reviewers.ai.adapters", "EXTERNAL_HTTP_RESPONSE_VERSION")

    config = AppConfig(ai_enabled=True, ai_provider="external_http", ai_timeout_seconds=18)
    result = normalize_external_http_response(
        {
            "contract_version": response_version,
            "summary": "Remote provider summary",
            "conclusion": "Remote provider conclusion",
            "resolution": "remote_completed",
            "provider_request_id": "req-123",
            "status": "ok",
        },
        {"issues": [{"severity": "moderate", "desc": "version mismatch"}]},
        "external_http",
        config,
    )

    assert result["provider"] == "external_http"
    assert result["requested_provider"] == "external_http"
    assert result["resolution"] == "remote_completed"
    assert result["summary"] == "Remote provider summary"
    assert result["ai_note"] == "Remote provider summary"
    assert result["provider_request_id"] == "req-123"
    assert result["provider_status"] == "ok"
    assert result["timeout_seconds"] == 18
    assert result["contract_version"] == response_version


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.review
@pytest.mark.ai
def test_normalize_external_http_response_requires_summary():
    AppConfig = require_symbol("app.core.services.app_config", "AppConfig")
    normalize_external_http_response = require_symbol(
        "app.core.reviewers.ai.adapters",
        "normalize_external_http_response",
    )

    config = AppConfig(ai_enabled=True, ai_provider="external_http")
    try:
        normalize_external_http_response({}, {"issues": []}, "external_http", config)
    except RuntimeError as exc:
        assert "external_http_missing_summary" in str(exc)
    else:  # pragma: no cover - contract guard
        pytest.fail("expected external_http_missing_summary")


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.review
@pytest.mark.ai
def test_review_with_external_http_posts_json_contract_and_normalizes_response():
    adapters = require_module("app.core.reviewers.ai.adapters")
    AppConfig = require_symbol("app.core.services.app_config", "AppConfig")
    build_ai_safe_case_payload = require_symbol("app.core.privacy.desensitization", "build_ai_safe_case_payload")

    safe_payload = build_ai_safe_case_payload(
        {
            "software_name": "Aurora Review Desk",
            "version": "V1.0",
            "company_name": "Aurora Medical",
        }
    )
    config = AppConfig(
        ai_enabled=True,
        ai_provider="external_http",
        ai_endpoint="https://example.invalid/review",
        ai_model="demo-model",
        ai_timeout_seconds=9,
        ai_api_key_env="SOFT_REVIEW_TEST_KEY",
    )

    captured_request: dict[str, object] = {}
    original_urlopen = adapters.urllib.request.urlopen
    previous_env = os.environ.get("SOFT_REVIEW_TEST_KEY")
    os.environ["SOFT_REVIEW_TEST_KEY"] = "secret-token"

    def _fake_urlopen(request, timeout=0):
        captured_request["url"] = request.full_url
        captured_request["timeout"] = timeout
        captured_request["headers"] = dict(request.header_items())
        captured_request["body"] = request.data
        return _FakeResponse(
            json.dumps(
                {
                    "contract_version": adapters.EXTERNAL_HTTP_RESPONSE_VERSION,
                    "summary": "Remote summary",
                    "conclusion": "Remote conclusion",
                    "resolution": "remote_completed",
                    "provider_request_id": "req-200",
                    "status": "ok",
                },
                ensure_ascii=False,
            ).encode("utf-8")
        )

    adapters.urllib.request.urlopen = _fake_urlopen
    try:
        result = adapters.review_with_external_http(
            safe_payload,
            {"issues": [{"severity": "minor", "desc": "demo"}]},
            "external_http",
            config,
        )
    finally:
        adapters.urllib.request.urlopen = original_urlopen
        if previous_env is None:
            os.environ.pop("SOFT_REVIEW_TEST_KEY", None)
        else:
            os.environ["SOFT_REVIEW_TEST_KEY"] = previous_env

    posted_payload = json.loads(captured_request["body"].decode("utf-8"))
    assert captured_request["url"] == "https://example.invalid/review"
    assert captured_request["timeout"] == 9
    assert posted_payload["contract_version"] == adapters.EXTERNAL_HTTP_REQUEST_VERSION
    assert posted_payload["model"] == "demo-model"
    assert posted_payload["privacy_guard"]["payload_marked_llm_safe"] is True
    assert captured_request["headers"]["Authorization"] == "Bearer secret-token"
    assert result["provider"] == "external_http"
    assert result["resolution"] == "remote_completed"
    assert result["summary"] == "Remote summary"
    assert result["provider_request_id"] == "req-200"


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.review
@pytest.mark.ai
def test_review_with_external_http_rejects_invalid_json():
    adapters = require_module("app.core.reviewers.ai.adapters")
    AppConfig = require_symbol("app.core.services.app_config", "AppConfig")
    build_ai_safe_case_payload = require_symbol("app.core.privacy.desensitization", "build_ai_safe_case_payload")

    safe_payload = build_ai_safe_case_payload({"software_name": "Aurora Review Desk", "version": "V1.0"})
    config = AppConfig(ai_enabled=True, ai_provider="external_http", ai_endpoint="https://example.invalid/review")

    original_urlopen = adapters.urllib.request.urlopen

    def _fake_urlopen(request, timeout=0):
        return _FakeResponse(b"not-json")

    adapters.urllib.request.urlopen = _fake_urlopen
    try:
        try:
            adapters.review_with_external_http(safe_payload, {"issues": []}, "external_http", config)
        except RuntimeError as exc:
            assert "external_http_invalid_json" in str(exc)
        else:  # pragma: no cover - contract guard
            pytest.fail("expected external_http_invalid_json")
    finally:
        adapters.urllib.request.urlopen = original_urlopen


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.review
@pytest.mark.ai
def test_external_http_error_code_covers_expected_error_types():
    external_http_error_code = require_symbol("app.core.reviewers.ai.adapters", "external_http_error_code")

    http_error = urllib.error.HTTPError("https://example.invalid", 502, "Bad Gateway", hdrs=None, fp=None)
    url_error = urllib.error.URLError("connection reset")
    json_error = json.JSONDecodeError("invalid", "{}", 1)

    assert external_http_error_code(TimeoutError()) == "external_http_timeout"
    assert external_http_error_code(http_error) == "external_http_http_error"
    assert external_http_error_code(url_error) == "external_http_request_failed"
    assert external_http_error_code(json_error) == "external_http_invalid_json"


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.review
@pytest.mark.ai
def test_generate_case_ai_review_surfaces_provider_fallback_context_for_external_http():
    service = require_module("app.core.reviewers.ai.service")
    AppConfig = require_symbol("app.core.services.app_config", "AppConfig")
    build_ai_safe_case_payload = require_symbol("app.core.privacy.desensitization", "build_ai_safe_case_payload")

    config = AppConfig(
        ai_enabled=True,
        ai_provider="external_http",
        ai_endpoint="https://example.invalid/review",
        ai_model="demo-model",
        ai_fallback_to_mock=True,
    )
    safe_payload = build_ai_safe_case_payload(
        {
            "software_name": "Aurora Review Desk",
            "version": "V1.0",
            "company_name": "Aurora Medical",
        }
    )

    original_review_with_external_http = service.review_with_external_http
    service.review_with_external_http = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("external_http_missing_summary"))
    try:
        result = service.generate_case_ai_review(
            case_payload=safe_payload,
            rule_results={"issues": [{"severity": "moderate", "desc": "version mismatch"}]},
            provider="external_http",
            config=config,
        )
    finally:
        service.review_with_external_http = original_review_with_external_http

    assert result["provider"] == "mock"
    assert result["resolution"] == "provider_exception_fallback"
    assert "requested_provider=external_http" in renderable_text(result)
