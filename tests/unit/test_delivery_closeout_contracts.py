from __future__ import annotations

import json

import pytest

from tests.helpers.contracts import require_symbol


@pytest.mark.unit
@pytest.mark.contract
def test_delivery_closeout_reports_blocked_when_release_validation_is_missing(tmp_path):
    AppConfig = require_symbol("app.core.services.app_config", "AppConfig")
    run_delivery_closeout = require_symbol("app.core.services.delivery_closeout", "run_delivery_closeout")

    dev_root = tmp_path / "docs" / "dev"
    backups_root = tmp_path / "data" / "backups"
    dev_root.mkdir(parents=True, exist_ok=True)
    backups_root.mkdir(parents=True, exist_ok=True)

    result = run_delivery_closeout(
        config=AppConfig(
            data_root=str(tmp_path / "runtime"),
            sqlite_path=str(tmp_path / "runtime" / "soft_review.db"),
            log_path=str(tmp_path / "runtime" / "logs" / "app.jsonl"),
            ai_enabled=False,
            ai_provider="mock",
        ),
        dev_root=dev_root,
        backups_root=backups_root,
        write_artifacts=False,
    )

    assert result["status"] == "blocked"
    assert result["milestone"] == "blocked"
    check_map = {item["name"]: item for item in result["checks"]}
    assert check_map["latest_release_validation"]["status"] == "blocked"
    assert "release_validation" in check_map["latest_release_validation"]["recommended_action"]


@pytest.mark.unit
@pytest.mark.contract
def test_delivery_closeout_writes_latest_and_history_artifacts(tmp_path):
    write_delivery_closeout_artifacts = require_symbol(
        "app.core.services.delivery_closeout",
        "write_delivery_closeout_artifacts",
    )

    dev_root = tmp_path / "docs" / "dev"
    payload = {
        "generated_at": "2026-04-21T00:20:00",
        "status": "pass",
        "milestone": "ready_for_business_handoff",
        "summary": "Business closeout is complete.",
        "operator_actions": [],
        "checks": [
            {"name": "latest_release_validation", "label": "Latest Release Validation", "status": "pass", "value": "2026-04-21T00:18:00", "summary": "ok", "recommended_action": ""},
        ],
        "config": {"ai_provider": "external_http"},
        "release_validation": {"file_path": "docs/dev/real-provider-validation-latest.json"},
        "release_gate": {"status": "pass", "summary": "ok"},
        "baseline": {"file_path": "docs/dev/real-sample-baseline.json"},
        "backup": {"file_path": "data/backups/runtime_backup_20260421_001500.zip"},
        "acceptance_checklist": {"file_path": "docs/dev/106-real-provider-acceptance-checklist.md"},
        "artifacts": {},
    }

    artifact_paths = write_delivery_closeout_artifacts(payload, dev_root=dev_root)

    assert artifact_paths["latest_json_path"].endswith("delivery-closeout-latest.json")
    assert artifact_paths["latest_markdown_path"].endswith("delivery-closeout-latest.md")
    latest_json_text = (dev_root / "delivery-closeout-latest.json").read_text(encoding="utf-8")
    latest_markdown_text = (dev_root / "delivery-closeout-latest.md").read_text(encoding="utf-8")
    latest_payload = json.loads(latest_json_text)
    assert latest_payload["status"] == "pass"
    assert latest_payload["artifacts"]["latest_json_path"].endswith("delivery-closeout-latest.json")
    assert "# Delivery Closeout" in latest_markdown_text


@pytest.mark.unit
@pytest.mark.contract
def test_latest_delivery_closeout_status_can_load_latest_artifact(tmp_path):
    latest_delivery_closeout_status = require_symbol(
        "app.core.services.delivery_closeout",
        "latest_delivery_closeout_status",
    )

    dev_root = tmp_path / "docs" / "dev"
    dev_root.mkdir(parents=True, exist_ok=True)
    (dev_root / "delivery-closeout-latest.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-21T10:08:16",
                "status": "pass",
                "milestone": "ready_for_business_handoff",
                "summary": "Business closeout is complete.",
                "operator_actions": [],
                "checks": [{"name": "release_gate", "label": "Release Gate", "status": "pass", "summary": "ok", "value": "external_http"}],
                "artifacts": {"latest_json_path": str(dev_root / "delivery-closeout-latest.json")},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = latest_delivery_closeout_status(dev_root)

    assert result["exists"] is True
    assert result["status"] == "pass"
    assert result["milestone"] == "ready_for_business_handoff"
    assert result["file_name"] == "delivery-closeout-latest.json"


@pytest.mark.unit
@pytest.mark.contract
def test_delivery_closeout_download_helper_rejects_nested_paths(tmp_path):
    get_delivery_closeout_artifact_download = require_symbol(
        "app.core.services.delivery_closeout",
        "get_delivery_closeout_artifact_download",
    )

    with pytest.raises(ValueError):
        get_delivery_closeout_artifact_download(dev_root=tmp_path, file_name="../escape.json")


@pytest.mark.unit
@pytest.mark.contract
def test_delivery_closeout_clears_recommended_actions_for_passing_checks(tmp_path):
    AppConfig = require_symbol("app.core.services.app_config", "AppConfig")
    run_delivery_closeout = require_symbol("app.core.services.delivery_closeout", "run_delivery_closeout")

    dev_root = tmp_path / "docs" / "dev"
    backups_root = tmp_path / "data" / "backups"
    dev_root.mkdir(parents=True, exist_ok=True)
    backups_root.mkdir(parents=True, exist_ok=True)

    (dev_root / "real-provider-validation-latest.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-26T11:14:23",
                "status": "pass",
                "summary": "Real-provider validation passed for probe, release gate, and sample smokes.",
                "recommended_action": "Run py -m app.tools.release_validation before business closeout.",
                "provider_probe": {"probe_status": "ok"},
                "mode_a_smoke": {"status": "pass"},
                "mode_b_smoke": {"status": "pass"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (dev_root / "106-real-provider-acceptance-checklist.md").write_text("# checklist\n", encoding="utf-8")
    history_root = dev_root / "history"
    history_root.mkdir(parents=True, exist_ok=True)
    (history_root / "real-sample-baseline_20260426_110801.json").write_text(
        json.dumps(
            {
                "snapshot": {
                    "generated_at": "2026-04-26T11:08:01",
                    "targets": [
                        {
                            "label": "mode_a_real",
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
    (backups_root / "runtime_backup_20260419_2219.zip").write_bytes(b"backup")

    result = run_delivery_closeout(
        config=AppConfig(
            data_root=str(tmp_path / "runtime"),
            sqlite_path=str(tmp_path / "runtime" / "soft_review.db"),
            log_path=str(tmp_path / "runtime" / "logs" / "app.jsonl"),
            ai_enabled=True,
            ai_provider="external_http",
            ai_endpoint="http://127.0.0.1:18011/review",
            ai_model="minimax-m2.7-highspeed",
        ),
        dev_root=dev_root,
        backups_root=backups_root,
        write_artifacts=False,
    )

    check_map = {item["name"]: item for item in result["checks"]}
    assert check_map["latest_release_validation"]["recommended_action"] == ""
    assert check_map["latest_release_validation"]["status"] == "pass"
    assert check_map["release_gate"]["status"] in {"warning", "blocked", "pass"}
    assert check_map["acceptance_checklist"]["recommended_action"] == ""
    assert check_map["acceptance_checklist"]["status"] == "pass"
