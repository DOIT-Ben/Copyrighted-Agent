from __future__ import annotations

import json

import pytest

from tests.helpers.contracts import require_symbol


@pytest.mark.unit
@pytest.mark.contract
def test_release_validation_reports_blocked_when_provider_is_not_ready(tmp_path):
    AppConfig = require_symbol("app.core.services.app_config", "AppConfig")
    run_release_validation = require_symbol("app.core.services.release_validation", "run_release_validation")

    dev_root = tmp_path / "docs" / "dev"
    dev_root.mkdir(parents=True, exist_ok=True)

    result = run_release_validation(
        config=AppConfig(
            data_root=str(tmp_path / "runtime"),
            sqlite_path=str(tmp_path / "runtime" / "soft_review.db"),
            log_path=str(tmp_path / "runtime" / "logs" / "app.jsonl"),
            ai_enabled=False,
            ai_provider="mock",
        ),
        mode_a_path=tmp_path / "missing_mode_a.zip",
        mode_b_path=tmp_path / "missing_mode_b",
        dev_root=dev_root,
        send_probe=True,
        write_artifacts=False,
    )

    assert result["status"] == "blocked"
    assert result["provider_probe"]["probe_status"] == "skipped"
    assert result["mode_a_smoke"]["attempted"] is False
    assert result["mode_b_smoke"]["attempted"] is False


@pytest.mark.unit
@pytest.mark.contract
def test_release_validation_writes_latest_and_history_artifacts(tmp_path):
    write_release_validation_artifacts = require_symbol(
        "app.core.services.release_validation",
        "write_release_validation_artifacts",
    )

    dev_root = tmp_path / "docs" / "dev"
    payload = {
        "generated_at": "2026-04-20T02:00:00",
        "status": "pass",
        "summary": "Validation passed.",
        "recommended_action": "",
        "config": {"ai_provider": "external_http"},
        "provider_probe": {"status": "pass", "probe_status": "ok", "summary": "ok"},
        "release_gate": {"status": "pass", "summary": "ok"},
        "mode_a_smoke": {"status": "pass", "path": "input\\mode_a.zip", "summary": "ok"},
        "mode_b_smoke": {"status": "pass", "path": "input\\mode_b", "summary": "ok"},
        "artifacts": {},
    }

    artifact_paths = write_release_validation_artifacts(payload, dev_root=dev_root)

    assert artifact_paths["latest_json_path"].endswith("real-provider-validation-latest.json")
    assert artifact_paths["latest_markdown_path"].endswith("real-provider-validation-latest.md")
    latest_json_text = (dev_root / "real-provider-validation-latest.json").read_text(encoding="utf-8")
    latest_markdown_text = (dev_root / "real-provider-validation-latest.md").read_text(encoding="utf-8")
    latest_payload = json.loads(latest_json_text)
    assert latest_payload["status"] == "pass"
    assert latest_payload["artifacts"]["latest_json_path"].endswith("real-provider-validation-latest.json")
    assert "# Real Provider Validation" in latest_markdown_text
