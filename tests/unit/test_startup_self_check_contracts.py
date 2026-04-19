from __future__ import annotations

import pytest

from tests.helpers.contracts import require_symbol


@pytest.mark.unit
@pytest.mark.contract
def test_startup_self_check_reports_expected_paths(tmp_path):
    AppConfig = require_symbol("app.core.services.app_config", "AppConfig")
    run_startup_self_check = require_symbol("app.core.services.startup_checks", "run_startup_self_check")

    config = AppConfig(
        data_root=str(tmp_path / "runtime"),
        sqlite_path=str(tmp_path / "runtime" / "soft_review.db"),
        log_path=str(tmp_path / "runtime" / "logs" / "app.jsonl"),
    )

    result = run_startup_self_check(config=config)

    assert result["status"] in {"ok", "warning"}
    check_names = {item["name"] for item in result["checks"]}
    assert {
        "data_root",
        "uploads_dir",
        "sqlite_parent",
        "log_dir",
        "config_template",
        "config_local",
        "ai_boundary",
        "ai_provider_readiness",
    } <= check_names
    assert result["paths"]["sqlite_path"].endswith("soft_review.db")
    assert result["provider_readiness"]["provider"] == "mock"
    assert result["local_config"]["exists"] is True
    assert result["local_config"]["path"].replace("\\", "/").endswith("config/local.json")
    assert result["provider_probe_status"]["exists"] is False


@pytest.mark.unit
@pytest.mark.contract
def test_startup_self_check_warns_when_external_http_provider_is_incomplete(tmp_path):
    AppConfig = require_symbol("app.core.services.app_config", "AppConfig")
    run_startup_self_check = require_symbol("app.core.services.startup_checks", "run_startup_self_check")

    config = AppConfig(
        data_root=str(tmp_path / "runtime"),
        sqlite_path=str(tmp_path / "runtime" / "soft_review.db"),
        log_path=str(tmp_path / "runtime" / "logs" / "app.jsonl"),
        ai_enabled=True,
        ai_provider="external_http",
        ai_endpoint="",
        ai_model="",
    )

    result = run_startup_self_check(config=config)
    readiness = next(item for item in result["checks"] if item["name"] == "ai_provider_readiness")

    assert readiness["status"] == "warning"
    assert result["provider_readiness"]["provider"] == "external_http"
    assert result["provider_readiness"]["phase"] in {"not_configured", "partially_configured"}
    assert "provider" in readiness["detail"].lower() or "external_http" in readiness["detail"].lower()
    assert result["local_config"]["exists"] is True
    assert result["local_config"]["path"].replace("\\", "/").endswith("config/local.json")
