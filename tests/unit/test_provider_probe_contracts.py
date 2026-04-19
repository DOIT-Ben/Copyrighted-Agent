from __future__ import annotations

import pytest

from tests.helpers.contracts import require_symbol


@pytest.mark.unit
@pytest.mark.contract
def test_provider_probe_payload_uses_safe_external_http_contract():
    AppConfig = require_symbol("app.core.services.app_config", "AppConfig")
    build_provider_probe_request_payload = require_symbol(
        "app.core.services.provider_probe",
        "build_provider_probe_request_payload",
    )

    payload = build_provider_probe_request_payload(
        AppConfig(
            ai_enabled=True,
            ai_provider="external_http",
            ai_endpoint="http://127.0.0.1:8010/review",
            ai_model="sandbox-model",
        )
    )

    assert payload["contract_version"] == "soft_review.external_http.v1"
    assert payload["requested_provider"] == "external_http"
    assert payload["case_payload"]["llm_safe"] is True
    assert payload["privacy_guard"]["require_desensitized"] is True
    assert payload["privacy_guard"]["payload_marked_llm_safe"] is True


@pytest.mark.unit
@pytest.mark.contract
def test_provider_readiness_warns_when_external_http_config_is_incomplete():
    AppConfig = require_symbol("app.core.services.app_config", "AppConfig")
    evaluate_provider_readiness = require_symbol("app.core.services.provider_probe", "evaluate_provider_readiness")

    readiness = evaluate_provider_readiness(
        AppConfig(
            ai_enabled=True,
            ai_provider="external_http",
            ai_endpoint="",
            ai_model="",
            ai_api_key_env="SOFT_REVIEW_API_KEY",
        ),
        environ={},
    )

    assert readiness["status"] == "warning"
    assert readiness["phase"] in {"not_configured", "partially_configured"}
    check_map = {item["name"]: item for item in readiness["checks"]}
    assert check_map["endpoint"]["status"] == "warning"
    assert check_map["model"]["status"] == "warning"
    assert check_map["api_key_env"]["status"] == "warning"


@pytest.mark.unit
@pytest.mark.contract
def test_provider_probe_skips_request_when_endpoint_or_model_is_missing():
    AppConfig = require_symbol("app.core.services.app_config", "AppConfig")
    run_provider_probe = require_symbol("app.core.services.provider_probe", "run_provider_probe")

    result = run_provider_probe(
        AppConfig(
            ai_enabled=True,
            ai_provider="external_http",
            ai_endpoint="",
            ai_model="",
        ),
        send_request=True,
        environ={},
    )

    assert result["status"] == "warning"
    assert result["probe"]["attempted"] is False
    assert result["probe"]["status"] == "skipped"
    assert result["phase"] == "probe_skipped"


@pytest.mark.unit
@pytest.mark.contract
def test_provider_readiness_reports_ready_for_probe_phase_when_external_http_is_complete():
    AppConfig = require_symbol("app.core.services.app_config", "AppConfig")
    evaluate_provider_readiness = require_symbol("app.core.services.provider_probe", "evaluate_provider_readiness")

    readiness = evaluate_provider_readiness(
        AppConfig(
            ai_enabled=True,
            ai_provider="external_http",
            ai_endpoint="http://127.0.0.1:18010/review",
            ai_model="sandbox-model",
            ai_api_key_env="SOFT_REVIEW_API_KEY",
            ai_require_desensitized=True,
        ),
        environ={"SOFT_REVIEW_API_KEY": "secret"},
    )

    assert readiness["status"] == "ok"
    assert readiness["phase"] == "ready_for_probe"
    assert readiness["api_key_present"] is True
    assert "provider_probe" in readiness["recommended_action"]


@pytest.mark.unit
@pytest.mark.contract
def test_provider_probe_can_persist_latest_artifact_without_request(tmp_path):
    AppConfig = require_symbol("app.core.services.app_config", "AppConfig")
    list_provider_probe_history = require_symbol("app.core.services.provider_probe", "list_provider_probe_history")
    latest_provider_probe_status = require_symbol("app.core.services.provider_probe", "latest_provider_probe_status")
    run_provider_probe = require_symbol("app.core.services.provider_probe", "run_provider_probe")

    config = AppConfig(
        data_root=str(tmp_path / "runtime"),
        log_path=str(tmp_path / "runtime" / "logs" / "app.jsonl"),
        ai_enabled=True,
        ai_provider="external_http",
        ai_endpoint="",
        ai_model="",
    )

    result = run_provider_probe(config, send_request=False, persist_result=True, persist_history=True, environ={})
    latest = latest_provider_probe_status(config)
    history = list_provider_probe_history(config, limit=5)

    assert result["artifact_path"].endswith("provider_probe_latest.json")
    assert result["history_artifact_path"].endswith(".json")
    assert latest["exists"] is True
    assert latest["phase"] == "not_configured"
    assert latest["probe_status"] == "skipped"
    assert latest["request_summary"]["llm_safe"] is True
    assert latest["request_summary"]["contains_raw_user_material"] is False
    assert history[0]["file_name"].startswith("provider_probe_")
    assert history[0]["request_summary"]["contains_raw_user_material"] is False


@pytest.mark.unit
@pytest.mark.contract
def test_provider_probe_request_summary_exposes_safe_audit_fields_only():
    AppConfig = require_symbol("app.core.services.app_config", "AppConfig")
    build_provider_probe_request_payload = require_symbol("app.core.services.provider_probe", "build_provider_probe_request_payload")
    summarize_provider_probe_request = require_symbol("app.core.services.provider_probe", "summarize_provider_probe_request")

    payload = build_provider_probe_request_payload(
        AppConfig(
            ai_enabled=True,
            ai_provider="external_http",
            ai_endpoint="http://127.0.0.1:18010/review",
            ai_model="sandbox-model",
        )
    )
    summary = summarize_provider_probe_request(payload)

    assert summary["probe_kind"] == "synthetic_safe_probe"
    assert summary["llm_safe"] is True
    assert summary["contains_raw_user_material"] is False
    assert summary["rule_issue_count"] == 1
    assert "software_name" in summary["case_payload_keys"]
    assert "provider_probe_sample" in summary["rule_issue_codes"]


@pytest.mark.unit
@pytest.mark.contract
def test_provider_probe_download_helper_rejects_nested_history_paths(tmp_path):
    AppConfig = require_symbol("app.core.services.app_config", "AppConfig")
    get_provider_probe_artifact_download = require_symbol(
        "app.core.services.provider_probe",
        "get_provider_probe_artifact_download",
    )

    config = AppConfig(
        data_root=str(tmp_path / "runtime"),
        log_path=str(tmp_path / "runtime" / "logs" / "app.jsonl"),
    )

    with pytest.raises(ValueError):
        get_provider_probe_artifact_download(config_or_root=config, file_name="../escape.json")
