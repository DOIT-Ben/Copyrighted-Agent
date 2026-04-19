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
def test_provider_probe_can_send_safe_probe_to_live_sandbox(tmp_path: Path):
    ProviderSandboxSettings = __import__("app.tools.provider_sandbox", fromlist=["ProviderSandboxSettings"]).ProviderSandboxSettings
    AppConfig = __import__("app.core.services.app_config", fromlist=["AppConfig"]).AppConfig
    latest_failed_provider_probe_status = __import__(
        "app.core.services.provider_probe",
        fromlist=["latest_failed_provider_probe_status"],
    ).latest_failed_provider_probe_status
    latest_provider_probe_status = __import__("app.core.services.provider_probe", fromlist=["latest_provider_probe_status"]).latest_provider_probe_status
    latest_successful_provider_probe_status = __import__(
        "app.core.services.provider_probe",
        fromlist=["latest_successful_provider_probe_status"],
    ).latest_successful_provider_probe_status
    list_provider_probe_history = __import__(
        "app.core.services.provider_probe",
        fromlist=["list_provider_probe_history"],
    ).list_provider_probe_history
    run_provider_probe = __import__("app.core.services.provider_probe", fromlist=["run_provider_probe"]).run_provider_probe

    request_log_path = tmp_path / "provider_probe_sandbox.jsonl"
    settings = ProviderSandboxSettings(request_log_path=str(request_log_path), mode="success")

    with _live_provider_sandbox(settings) as endpoint:
        config = AppConfig(
            data_root=str(tmp_path / "runtime"),
            log_path=str(tmp_path / "runtime" / "logs" / "app.jsonl"),
            ai_enabled=True,
            ai_provider="external_http",
            ai_endpoint=endpoint,
            ai_model="sandbox-model",
            ai_timeout_seconds=5,
            ai_fallback_to_mock=True,
        )
        result = run_provider_probe(
            config,
            send_request=True,
            persist_result=True,
            persist_history=True,
        )
    latest = latest_provider_probe_status(config)
    latest_success = latest_successful_provider_probe_status(config)
    latest_failure = latest_failed_provider_probe_status(config)
    history = list_provider_probe_history(config, limit=5)

    assert result["readiness"]["status"] == "ok"
    assert result["probe"]["attempted"] is True
    assert result["probe"]["status"] == "ok"
    assert result["probe"]["http_status"] == 200
    assert result["probe"]["normalized_response"]["provider_status"] == "ok"
    assert result["artifact_path"].endswith("provider_probe_latest.json")
    assert result["history_artifact_path"].endswith(".json")
    assert result["request_payload"]["case_payload"]["llm_safe"] is True
    assert result["request_summary"]["contains_raw_user_material"] is False
    assert latest["exists"] is True
    assert latest["probe_status"] == "ok"
    assert latest["provider_status"] == "ok"
    assert latest["provider_request_id"].startswith("sandbox-")
    assert latest_success["probe_status"] == "ok"
    assert latest_failure["exists"] is False
    assert history[0]["probe_status"] == "ok"
    assert history[0]["request_summary"]["contains_raw_user_material"] is False
    assert request_log_path.exists()
    log_text = request_log_path.read_text(encoding="utf-8")
    assert '"payload_marked_llm_safe": true' in log_text
