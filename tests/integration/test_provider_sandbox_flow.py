from __future__ import annotations

from contextlib import contextmanager
import threading
from pathlib import Path
from wsgiref.simple_server import make_server

import pytest


@contextmanager
def _live_provider_sandbox(settings):
    build_provider_sandbox_app = __import__("app.tools.provider_sandbox", fromlist=["build_provider_sandbox_app"]).build_provider_sandbox_app

    server = make_server("127.0.0.1", 0, build_provider_sandbox_app(settings))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        yield f"http://{host}:{port}{settings.endpoint_path}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.ai
def test_external_http_sandbox_accepts_safe_payload_and_returns_structured_review(tmp_path):
    ProviderSandboxSettings = __import__("app.tools.provider_sandbox", fromlist=["ProviderSandboxSettings"]).ProviderSandboxSettings
    AppConfig = __import__("app.core.services.app_config", fromlist=["AppConfig"]).AppConfig
    build_ai_safe_case_payload = __import__(
        "app.core.privacy.desensitization",
        fromlist=["build_ai_safe_case_payload"],
    ).build_ai_safe_case_payload
    generate_case_ai_review = __import__(
        "app.core.reviewers.ai.service",
        fromlist=["generate_case_ai_review"],
    ).generate_case_ai_review

    request_log_path = tmp_path / "provider_sandbox.jsonl"
    settings = ProviderSandboxSettings(request_log_path=str(request_log_path), mode="success")

    with _live_provider_sandbox(settings) as endpoint:
        config = AppConfig(
            ai_enabled=True,
            ai_provider="external_http",
            ai_endpoint=endpoint,
            ai_model="sandbox-model",
            ai_timeout_seconds=5,
            ai_fallback_to_mock=True,
        )
        result = generate_case_ai_review(
            case_payload=build_ai_safe_case_payload(
                {"software_name": "Aurora", "version": "V1.0", "company_name": "Aurora Medical"}
            ),
            rule_results={"issues": [{"severity": "minor", "desc": "demo"}]},
            provider="external_http",
            config=config,
        )

    assert result["provider"] == "external_http"
    assert result["provider_status"] == "ok"
    assert request_log_path.exists()
    log_text = request_log_path.read_text(encoding="utf-8")
    assert '"payload_marked_llm_safe": true' in log_text


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.ai
def test_external_http_sandbox_http_error_can_fallback_to_mock(tmp_path):
    ProviderSandboxSettings = __import__("app.tools.provider_sandbox", fromlist=["ProviderSandboxSettings"]).ProviderSandboxSettings
    AppConfig = __import__("app.core.services.app_config", fromlist=["AppConfig"]).AppConfig
    build_ai_safe_case_payload = __import__(
        "app.core.privacy.desensitization",
        fromlist=["build_ai_safe_case_payload"],
    ).build_ai_safe_case_payload
    generate_case_ai_review = __import__(
        "app.core.reviewers.ai.service",
        fromlist=["generate_case_ai_review"],
    ).generate_case_ai_review

    settings = ProviderSandboxSettings(mode="http_error")
    with _live_provider_sandbox(settings) as endpoint:
        config = AppConfig(
            ai_enabled=True,
            ai_provider="external_http",
            ai_endpoint=endpoint,
            ai_model="sandbox-model",
            ai_timeout_seconds=5,
            ai_fallback_to_mock=True,
        )
        result = generate_case_ai_review(
            case_payload=build_ai_safe_case_payload(
                {"software_name": "Aurora", "version": "V1.0", "company_name": "Aurora Medical"}
            ),
            rule_results={"issues": [{"severity": "minor", "desc": "demo"}]},
            provider="external_http",
            config=config,
        )

    assert result["provider"] == "mock"
    assert result["resolution"] == "provider_exception_fallback"
