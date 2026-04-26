from __future__ import annotations

import json

import pytest

from tests.helpers.contracts import require_symbol


@pytest.mark.unit
@pytest.mark.contract
def test_release_gate_warns_while_environment_remains_in_mock_mode(tmp_path):
    AppConfig = require_symbol("app.core.services.app_config", "AppConfig")
    evaluate_release_gate = require_symbol("app.core.services.release_gate", "evaluate_release_gate")

    result = evaluate_release_gate(
        AppConfig(
            data_root=str(tmp_path / "runtime"),
            log_path=str(tmp_path / "runtime" / "logs" / "app.jsonl"),
            ai_enabled=False,
            ai_provider="mock",
        ),
        dev_root=tmp_path / "docs" / "dev",
    )

    assert result["status"] == "warning"
    assert result["mode"] == "mock_local"
    check_map = {item["name"]: item for item in result["checks"]}
    assert check_map["provider_readiness"]["status"] == "warning"


@pytest.mark.unit
@pytest.mark.contract
def test_release_gate_blocks_when_external_provider_is_not_ready(tmp_path):
    AppConfig = require_symbol("app.core.services.app_config", "AppConfig")
    evaluate_release_gate = require_symbol("app.core.services.release_gate", "evaluate_release_gate")

    result = evaluate_release_gate(
        AppConfig(
            data_root=str(tmp_path / "runtime"),
            log_path=str(tmp_path / "runtime" / "logs" / "app.jsonl"),
            ai_enabled=True,
            ai_provider="external_http",
            ai_endpoint="",
            ai_model="",
        ),
        dev_root=tmp_path / "docs" / "dev",
    )

    assert result["status"] == "blocked"
    check_map = {item["name"]: item for item in result["checks"]}
    assert check_map["provider_readiness"]["status"] == "blocked"
    assert check_map["latest_probe"]["status"] == "blocked"


@pytest.mark.unit
@pytest.mark.contract
def test_release_gate_can_pass_with_ready_provider_probe_and_healthy_baseline(tmp_path):
    AppConfig = require_symbol("app.core.services.app_config", "AppConfig")
    evaluate_release_gate = require_symbol("app.core.services.release_gate", "evaluate_release_gate")
    write_provider_probe_artifact = require_symbol("app.core.services.provider_probe", "write_provider_probe_artifact")

    dev_root = tmp_path / "docs" / "dev"
    dev_root.mkdir(parents=True, exist_ok=True)
    baseline_path = dev_root / "real-sample-baseline.json"
    baseline_path.write_text(
        json.dumps(
            {
                "snapshot": {
                    "generated_at": "2026-04-20T01:00:00",
                    "targets": [
                        {
                            "label": "mode_a",
                            "aggregate": {
                                "materials": 24,
                                "cases": 6,
                                "reports": 6,
                                "unknown": 0,
                                "needs_review": 0,
                                "low_quality": 0,
                                "redactions": 252,
                            },
                        }
                    ],
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    config = AppConfig(
        data_root=str(tmp_path / "runtime"),
        log_path=str(tmp_path / "runtime" / "logs" / "app.jsonl"),
        ai_enabled=True,
        ai_provider="external_http",
        ai_endpoint="http://127.0.0.1:18010/review",
        ai_model="sandbox-model",
        ai_require_desensitized=True,
    )

    write_provider_probe_artifact(
        {
            "generated_at": "2026-04-20T01:05:00",
            "status": "ok",
            "phase": "probe_passed",
            "readiness_phase": "ready_for_probe",
            "summary": "Latest safe provider probe completed successfully.",
            "recommended_action": "Provider smoke passed.",
            "readiness": {
                "status": "ok",
                "phase": "ready_for_probe",
                "summary": "external_http configuration is ready for a safe probe.",
                "recommended_action": "Run provider probe when ready.",
                "provider": "external_http",
                "endpoint": "http://127.0.0.1:18010/review",
                "model": "sandbox-model",
                "api_key_env": "",
                "api_key_present": False,
                "blocking_items": [],
                "checks": [],
            },
            "request_payload": {},
            "request_summary": {"llm_safe": True, "contains_raw_user_material": False, "rule_issue_count": 1},
            "probe": {
                "attempted": True,
                "status": "ok",
                "detail": "Probe request completed successfully.",
                "endpoint": "http://127.0.0.1:18010/review",
                "http_status": 200,
                "error_code": "",
                "response_payload": {},
                "normalized_response": {"provider_status": "ok", "provider_request_id": "req-1"},
            },
        },
        config,
    )

    startup_report = {
        "status": "ok",
        "local_config": {"exists": True, "path": "config/local.json"},
        "provider_readiness": {
            "status": "ok",
            "phase": "ready_for_probe",
            "provider": "external_http",
            "summary": "external_http configuration is ready for a safe probe.",
            "recommended_action": "Run provider probe when ready.",
        },
        "provider_probe_status": {
            "exists": True,
            "probe_status": "ok",
            "status": "ok",
            "summary": "Latest safe provider probe completed successfully.",
            "recommended_action": "Provider smoke passed.",
        },
        "provider_probe_last_success": {
            "exists": True,
            "probe_status": "ok",
            "generated_at": "2026-04-20T01:05:00",
        },
        "provider_probe_last_failure": {
            "exists": False,
            "probe_status": "not_run",
        },
    }

    result = evaluate_release_gate(config, startup_report=startup_report, dev_root=dev_root)

    assert result["status"] == "pass"
    check_map = {item["name"]: item for item in result["checks"]}
    assert check_map["provider_readiness"]["status"] == "pass"
    assert check_map["latest_probe"]["status"] == "pass"
    assert check_map["latest_baseline"]["status"] == "pass"


@pytest.mark.unit
@pytest.mark.contract
def test_release_gate_ignores_older_failed_probe_when_newer_success_exists(tmp_path):
    AppConfig = require_symbol("app.core.services.app_config", "AppConfig")
    evaluate_release_gate = require_symbol("app.core.services.release_gate", "evaluate_release_gate")

    dev_root = tmp_path / "docs" / "dev"
    dev_root.mkdir(parents=True, exist_ok=True)
    baseline_path = dev_root / "real-sample-baseline.json"
    baseline_path.write_text(
        json.dumps(
            {
                "snapshot": {
                    "generated_at": "2026-04-20T01:00:00",
                    "targets": [
                        {
                            "label": "mode_a",
                            "aggregate": {
                                "materials": 24,
                                "cases": 6,
                                "reports": 6,
                                "unknown": 0,
                                "needs_review": 0,
                                "low_quality": 0,
                                "redactions": 252,
                            },
                        }
                    ],
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    config = AppConfig(
        data_root=str(tmp_path / "runtime"),
        log_path=str(tmp_path / "runtime" / "logs" / "app.jsonl"),
        ai_enabled=True,
        ai_provider="external_http",
        ai_endpoint="http://127.0.0.1:18010/review",
        ai_model="sandbox-model",
        ai_require_desensitized=True,
    )

    startup_report = {
        "status": "ok",
        "local_config": {"exists": True, "path": "config/local.json"},
        "provider_readiness": {
            "status": "ok",
            "phase": "ready_for_probe",
            "provider": "external_http",
            "summary": "external_http configuration is ready for a safe probe.",
            "recommended_action": "Run provider probe when ready.",
        },
        "provider_probe_status": {
            "exists": True,
            "probe_status": "ok",
            "status": "ok",
            "summary": "Latest safe provider probe completed successfully.",
            "recommended_action": "Provider smoke passed.",
        },
        "provider_probe_last_success": {
            "exists": True,
            "probe_status": "ok",
            "generated_at": "2026-04-20T01:05:00",
        },
        "provider_probe_last_failure": {
            "exists": True,
            "probe_status": "failed",
            "generated_at": "2026-04-20T01:00:00",
            "error_code": "external_http_http_error",
        },
    }

    result = evaluate_release_gate(config, startup_report=startup_report, dev_root=dev_root)

    assert result["status"] == "pass"
    check_map = {item["name"]: item for item in result["checks"]}
    assert check_map["latest_failure_probe"]["status"] == "pass"
