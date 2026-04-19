from __future__ import annotations

import json
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
def test_release_validation_can_pass_with_live_sandbox_and_sample_smokes(tmp_path: Path, mode_a_zip_path: Path, mode_b_zip_path: Path):
    ProviderSandboxSettings = __import__("app.tools.provider_sandbox", fromlist=["ProviderSandboxSettings"]).ProviderSandboxSettings
    AppConfig = __import__("app.core.services.app_config", fromlist=["AppConfig"]).AppConfig
    run_release_validation = __import__(
        "app.core.services.release_validation",
        fromlist=["run_release_validation"],
    ).run_release_validation

    dev_root = tmp_path / "docs" / "dev"
    dev_root.mkdir(parents=True, exist_ok=True)
    (dev_root / "real-sample-baseline.json").write_text(
        json.dumps(
            {
                "snapshot": {
                    "generated_at": "2026-04-20T02:05:00",
                    "targets": [
                        {
                            "label": "mode_a_real",
                            "aggregate": {
                                "materials": 4,
                                "cases": 1,
                                "reports": 1,
                                "unknown": 0,
                                "needs_review": 0,
                                "low_quality": 0,
                                "redactions": 43,
                            },
                        },
                        {
                            "label": "mode_b_real",
                            "aggregate": {
                                "materials": 3,
                                "cases": 3,
                                "reports": 1,
                                "unknown": 0,
                                "needs_review": 0,
                                "low_quality": 0,
                                "redactions": 6,
                            },
                        },
                    ],
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    settings = ProviderSandboxSettings(request_log_path=str(tmp_path / "provider_sandbox.jsonl"), mode="success")

    with _live_provider_sandbox(settings) as endpoint:
        result = run_release_validation(
            config=AppConfig(
                data_root=str(tmp_path / "runtime"),
                sqlite_path=str(tmp_path / "runtime" / "soft_review.db"),
                log_path=str(tmp_path / "runtime" / "logs" / "app.jsonl"),
                ai_enabled=True,
                ai_provider="external_http",
                ai_endpoint=endpoint,
                ai_model="sandbox-model",
                ai_timeout_seconds=5,
                ai_require_desensitized=True,
                ai_fallback_to_mock=True,
            ),
            mode_a_path=mode_a_zip_path,
            mode_b_path=mode_b_zip_path,
            dev_root=dev_root,
            send_probe=True,
            write_artifacts=True,
        )

    assert result["status"] == "pass"
    assert result["provider_probe"]["probe_status"] == "ok"
    assert result["release_gate"]["status"] == "pass"
    assert result["mode_a_smoke"]["status"] == "pass"
    assert result["mode_a_smoke"]["review_provider"] == "external_http"
    assert result["mode_b_smoke"]["status"] == "pass"
    assert result["artifacts"]["latest_json_path"].endswith("real-provider-validation-latest.json")
    latest_payload = json.loads((dev_root / "real-provider-validation-latest.json").read_text(encoding="utf-8"))
    assert latest_payload["status"] == "pass"
