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
def test_delivery_closeout_can_pass_after_validation_backup_and_baseline(tmp_path: Path, mode_a_zip_path: Path, mode_b_zip_path: Path):
    ProviderSandboxSettings = __import__("app.tools.provider_sandbox", fromlist=["ProviderSandboxSettings"]).ProviderSandboxSettings
    AppConfig = __import__("app.core.services.app_config", fromlist=["AppConfig"]).AppConfig
    run_release_validation = __import__(
        "app.core.services.release_validation",
        fromlist=["run_release_validation"],
    ).run_release_validation
    create_runtime_backup = __import__(
        "app.tools.runtime_backup",
        fromlist=["create_runtime_backup"],
    ).create_runtime_backup
    run_delivery_closeout = __import__(
        "app.core.services.delivery_closeout",
        fromlist=["run_delivery_closeout"],
    ).run_delivery_closeout

    dev_root = tmp_path / "docs" / "dev"
    dev_root.mkdir(parents=True, exist_ok=True)
    backups_root = tmp_path / "data" / "backups"
    backups_root.mkdir(parents=True, exist_ok=True)

    (dev_root / "106-real-provider-acceptance-checklist.md").write_text(
        "# Acceptance Checklist\n\n- provider validated\n- baseline clean\n- backup recorded\n",
        encoding="utf-8",
    )
    (dev_root / "real-sample-baseline.json").write_text(
        json.dumps(
            {
                "snapshot": {
                    "generated_at": "2026-04-21T00:15:00",
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
        config = AppConfig(
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
        )
        validation = run_release_validation(
            config=config,
            mode_a_path=mode_a_zip_path,
            mode_b_path=mode_b_zip_path,
            dev_root=dev_root,
            send_probe=True,
            write_artifacts=True,
        )

    backup = create_runtime_backup(config, output_path=backups_root / "runtime_backup_test.zip")
    result = run_delivery_closeout(
        config=config,
        dev_root=dev_root,
        backups_root=backups_root,
        write_artifacts=True,
    )

    assert validation["status"] == "pass"
    assert backup["archive_path"].endswith("runtime_backup_test.zip")
    assert result["status"] == "pass"
    assert result["milestone"] == "ready_for_business_handoff"
    assert result["artifacts"]["latest_json_path"].endswith("delivery-closeout-latest.json")
    latest_payload = json.loads((dev_root / "delivery-closeout-latest.json").read_text(encoding="utf-8"))
    assert latest_payload["status"] == "pass"
