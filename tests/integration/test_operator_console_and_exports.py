from __future__ import annotations

import io
import os
import zipfile

import pytest


def _create_submission(api_client, zip_path, mode: str = "single_case_package") -> str:
    with zip_path.open("rb") as handle:
        response = api_client.post(
            "/api/submissions",
            files={"file": (zip_path.name, handle, "application/zip")},
            data={"mode": mode},
        )
    assert response.status_code in (200, 201, 202)
    return response.json()["id"]


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.web
def test_submission_detail_exposes_operator_console_and_export_sections(api_client, mode_a_zip_path):
    submission_id = _create_submission(api_client, mode_a_zip_path)
    response = api_client.get(f"/submissions/{submission_id}")

    assert response.status_code == 200
    assert "Operator Console" in response.text
    assert "Export Center" in response.text
    assert "Artifact Browser" in response.text
    assert "Import Digest" in response.text
    assert "浏览器端导入说明" in api_client.get("/").text


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.web
def test_ops_page_exposes_self_check_and_support_artifacts(api_client):
    response = api_client.get("/ops")

    assert response.status_code == 200
    assert "Support / Ops" in response.text
    assert "Release Gate" in response.text
    assert "Startup Self Check" in response.text
    assert "Provider Readiness" in response.text
    assert "Latest Backup" in response.text
    assert "Latest Baseline" in response.text
    assert "Latest Probe" in response.text
    assert "Provider Checklist" in response.text
    assert "Probe Observatory" in response.text or "Latest Provider Probe" in response.text
    assert "Probe History" in response.text
    assert "Trend Watch" in response.text or "Baseline History" in response.text
    assert "/downloads/logs/app" in response.text
    assert "app.tools.runtime_cleanup" in response.text
    assert "app.tools.runtime_backup" in response.text or "runtime_backup" in response.text
    assert "app.tools.provider_sandbox" in response.text or "provider_sandbox" in response.text
    assert "app.tools.provider_probe" in response.text or "provider_probe" in response.text
    assert "app.tools.release_gate" in response.text or "release_gate" in response.text
    assert "scripts\\start_mock_web.ps1" in response.text
    assert "scripts\\start_real_bridge.ps1" in response.text
    assert "scripts\\start_real_web.ps1" in response.text
    assert "scripts\\run_real_validation.ps1" in response.text
    assert "scripts\\show_stack_status.ps1" in response.text
    assert "app.tools.minimax_bridge" in response.text or "minimax_bridge" in response.text
    assert "Real Provider Smoke" in response.text
    assert "Rolling Baseline" in response.text


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.web
def test_ops_provider_probe_download_endpoints_work(tmp_path):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    create_app = __import__("app.api.main", fromlist=["create_app"]).create_app
    AppConfig = __import__("app.core.services.app_config", fromlist=["AppConfig"]).AppConfig
    list_provider_probe_history = __import__(
        "app.core.services.provider_probe",
        fromlist=["list_provider_probe_history"],
    ).list_provider_probe_history
    run_provider_probe = __import__("app.core.services.provider_probe", fromlist=["run_provider_probe"]).run_provider_probe

    runtime_root = tmp_path / "runtime"
    original_data_root = os.environ.get("SOFT_REVIEW_DATA_ROOT")
    original_log_path = os.environ.get("SOFT_REVIEW_LOG_PATH")
    os.environ["SOFT_REVIEW_DATA_ROOT"] = str(runtime_root)
    os.environ["SOFT_REVIEW_LOG_PATH"] = str(runtime_root / "logs" / "app.jsonl")

    try:
        config = AppConfig(
            data_root=str(runtime_root),
            log_path=str(runtime_root / "logs" / "app.jsonl"),
            ai_enabled=True,
            ai_provider="external_http",
            ai_endpoint="",
            ai_model="",
        )
        result = run_provider_probe(config, send_request=False, persist_result=True, persist_history=True, environ={})
        history = list_provider_probe_history(config, limit=5)

        client = TestClient(create_app(testing=True))
        latest_download = client.get("/downloads/ops/provider-probe/latest")
        history_download = client.get(f"/downloads/ops/provider-probe/history/{history[0]['file_name']}")

        assert result["artifact_path"].endswith("provider_probe_latest.json")
        assert latest_download.status_code == 200
        assert latest_download.content
        assert history_download.status_code == 200
        assert history_download.content
    finally:
        if original_data_root is None:
            os.environ.pop("SOFT_REVIEW_DATA_ROOT", None)
        else:
            os.environ["SOFT_REVIEW_DATA_ROOT"] = original_data_root

        if original_log_path is None:
            os.environ.pop("SOFT_REVIEW_LOG_PATH", None)
        else:
            os.environ["SOFT_REVIEW_LOG_PATH"] = original_log_path


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.web
def test_html_operator_actions_and_download_endpoints_work(api_client, mode_a_zip_path):
    submission_id = _create_submission(api_client, mode_a_zip_path)
    submission_payload = api_client.get(f"/api/submissions/{submission_id}").json()
    files_payload = api_client.get(f"/api/submissions/{submission_id}/files").json()

    material_id = files_payload["files"][0]["id"]
    case_id = submission_payload["case_ids"][0]
    report_id = submission_payload["report_ids"][0]

    change_response = api_client.post(
        f"/submissions/{submission_id}/actions/change-type",
        data={"material_id": material_id, "material_type": "agreement", "note": "html action"},
    )
    assert change_response.status_code == 303
    change_location = change_response.headers.get("Location", "")
    assert "notice=material_type_updated" in change_location
    assert "#correction-audit" in change_location

    submission_page = api_client.get(change_location.split("#", 1)[0])
    assert "change_material_type" in submission_page.text
    assert "Artifact Browser" in submission_page.text
    assert "Material type updated" in submission_page.text

    rerun_response = api_client.post(
        f"/submissions/{submission_id}/actions/rerun-review",
        data={"case_id": case_id, "note": "refresh"},
    )
    assert rerun_response.status_code == 303
    rerun_location = rerun_response.headers.get("Location", "")
    assert "notice=case_review_rerun" in rerun_location
    assert "#export-center" in rerun_location

    rerun_page = api_client.get(rerun_location.split("#", 1)[0])
    assert "Case review rerun" in rerun_page.text

    report_download = api_client.get(f"/downloads/reports/{report_id}")
    assert report_download.status_code == 200
    assert "attachment;" in report_download.headers.get("Content-Disposition", "")
    assert report_download.content

    artifact_download = api_client.get(f"/downloads/materials/{material_id}/desensitized")
    assert artifact_download.status_code == 200
    assert artifact_download.content

    bundle_download = api_client.get(f"/downloads/submissions/{submission_id}/bundle")
    assert bundle_download.status_code == 200
    with zipfile.ZipFile(io.BytesIO(bundle_download.content), "r") as archive:
        names = archive.namelist()
    assert "submission/submission.json" in names
    assert any(name.startswith("artifacts/") for name in names)

    log_download = api_client.get("/downloads/logs/app")
    assert log_download.status_code == 200
    assert b"ingest_submission_completed" in log_download.content or b"upload_submission_api" in log_download.content
