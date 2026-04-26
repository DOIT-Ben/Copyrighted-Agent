from __future__ import annotations

from contextlib import contextmanager
import os
import threading
from wsgiref.simple_server import make_server

import pytest


def _build_fake_minimax_app():
    def _app(environ, start_response):
        request_path = str(environ.get("PATH_INFO") or "/")
        request_method = str(environ.get("REQUEST_METHOD") or "GET").upper()
        if request_path != "/chat/completions" or request_method != "POST":
            body = b"not found"
            start_response("404 Not Found", [("Content-Type", "text/plain"), ("Content-Length", str(len(body)))])
            return [body]

        body = (
            b'{"id":"chatcmpl-fake-001","choices":[{"message":{"content":"{\\"summary\\":\\"MiniMax bridge ok\\",'
            b'\\"conclusion\\":\\"MiniMax bridge conclusion\\",\\"resolution\\":\\"minimax_bridge_success\\"}"}}]}'
        )
        start_response("200 OK", [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(body)))])
        return [body]

    return _app


def _build_fake_minimax_text_app():
    def _app(environ, start_response):
        request_path = str(environ.get("PATH_INFO") or "/")
        request_method = str(environ.get("REQUEST_METHOD") or "GET").upper()
        if request_path != "/chat/completions" or request_method != "POST":
            body = b"not found"
            start_response("404 Not Found", [("Content-Type", "text/plain"), ("Content-Length", str(len(body)))])
            return [body]

        body = (
            b'{"id":"chatcmpl-fake-002","choices":[{"message":{"content":"'
            b'\xe5\x8f\x91\xe7\x8e\xb0\xe8\xaf\xb4\xe6\x98\x8e\xe6\x96\x87\xe6\xa1\xa3\xe4\xb8\x8e\xe6\xba\x90\xe7\xa0\x81\xe7\x9a\x84\xe7\x89\x88\xe6\x9c\xac\xe5\x8f\xb7\xe4\xb8\x8d\xe4\xb8\x80\xe8\x87\xb4\xef\xbc\x8c\xe5\xbb\xba\xe8\xae\xae\xe5\x85\x88\xe7\xbb\x9f\xe4\xb8\x80\xe5\x90\x8e\xe5\x86\x8d\xe6\x8f\x90\xe4\xba\xa4\xe3\x80\x82'
            b'"}}]}'
        )
        start_response("200 OK", [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(body)))])
        return [body]

    return _app


@contextmanager
def _live_server(app):
    server = make_server("127.0.0.1", 0, app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        yield host, port
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.ai
def test_minimax_bridge_forwards_safe_request_to_upstream_and_returns_external_http_contract(tmp_path):
    MiniMaxBridgeSettings = __import__("app.tools.minimax_bridge", fromlist=["MiniMaxBridgeSettings"]).MiniMaxBridgeSettings
    build_minimax_bridge_app = __import__("app.tools.minimax_bridge", fromlist=["build_minimax_bridge_app"]).build_minimax_bridge_app
    AppConfig = __import__("app.core.services.app_config", fromlist=["AppConfig"]).AppConfig
    build_ai_safe_case_payload = __import__(
        "app.core.privacy.desensitization",
        fromlist=["build_ai_safe_case_payload"],
    ).build_ai_safe_case_payload
    generate_case_ai_review = __import__(
        "app.core.reviewers.ai.service",
        fromlist=["generate_case_ai_review"],
    ).generate_case_ai_review

    original_key = os.environ.get("MINIMAX_API_KEY")
    os.environ["MINIMAX_API_KEY"] = "bridge-test-key"
    try:
        with _live_server(_build_fake_minimax_app()) as (upstream_host, upstream_port):
            settings = MiniMaxBridgeSettings(
                upstream_base_url=f"http://{upstream_host}:{upstream_port}",
                upstream_model="MiniMax-M2.7-highspeed",
                upstream_api_key_env="MINIMAX_API_KEY",
                request_log_path=str(tmp_path / "bridge.jsonl"),
            )
            with _live_server(build_minimax_bridge_app(settings)) as (bridge_host, bridge_port):
                config = AppConfig(
                    ai_enabled=True,
                    ai_provider="external_http",
                    ai_endpoint=f"http://{bridge_host}:{bridge_port}/review",
                    ai_model="MiniMax-M2.7-highspeed",
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
    finally:
        if original_key is None:
            os.environ.pop("MINIMAX_API_KEY", None)
        else:
            os.environ["MINIMAX_API_KEY"] = original_key

    assert result["provider"] == "external_http"
    assert result["provider_status"] == "ok"
    assert result["summary"] == "MiniMax bridge ok"
    assert result["provider_request_id"] == "chatcmpl-fake-001"


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.ai
def test_minimax_bridge_accepts_plain_text_upstream_content_without_mock_fallback(tmp_path):
    MiniMaxBridgeSettings = __import__("app.tools.minimax_bridge", fromlist=["MiniMaxBridgeSettings"]).MiniMaxBridgeSettings
    build_minimax_bridge_app = __import__("app.tools.minimax_bridge", fromlist=["build_minimax_bridge_app"]).build_minimax_bridge_app
    AppConfig = __import__("app.core.services.app_config", fromlist=["AppConfig"]).AppConfig
    build_ai_safe_case_payload = __import__(
        "app.core.privacy.desensitization",
        fromlist=["build_ai_safe_case_payload"],
    ).build_ai_safe_case_payload
    generate_case_ai_review = __import__(
        "app.core.reviewers.ai.service",
        fromlist=["generate_case_ai_review"],
    ).generate_case_ai_review

    original_key = os.environ.get("MINIMAX_API_KEY")
    os.environ["MINIMAX_API_KEY"] = "bridge-test-key"
    try:
        with _live_server(_build_fake_minimax_text_app()) as (upstream_host, upstream_port):
            settings = MiniMaxBridgeSettings(
                upstream_base_url=f"http://{upstream_host}:{upstream_port}",
                upstream_model="MiniMax-M2.7-highspeed",
                upstream_api_key_env="MINIMAX_API_KEY",
                request_log_path=str(tmp_path / "bridge.jsonl"),
            )
            with _live_server(build_minimax_bridge_app(settings)) as (bridge_host, bridge_port):
                config = AppConfig(
                    ai_enabled=True,
                    ai_provider="external_http",
                    ai_endpoint=f"http://{bridge_host}:{bridge_port}/review",
                    ai_model="MiniMax-M2.7-highspeed",
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
    finally:
        if original_key is None:
            os.environ.pop("MINIMAX_API_KEY", None)
        else:
            os.environ["MINIMAX_API_KEY"] = original_key

    assert result["provider"] == "external_http"
    assert result["provider_status"] == "ok"
    assert result["resolution"] == "minimax_bridge_text_fallback"
    assert "版本号不一致" in result["summary"]
