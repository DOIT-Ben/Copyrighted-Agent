from __future__ import annotations

import io
import os
import zipfile

import pytest


def _create_submission(
    api_client,
    zip_path,
    mode: str = "single_case_package",
    review_strategy: str = "auto_review",
) -> str:
    with zip_path.open("rb") as handle:
        response = api_client.post(
            "/api/submissions",
            files={"file": (zip_path.name, handle, "application/zip")},
            data={"mode": mode, "review_strategy": review_strategy},
        )
    assert response.status_code in (200, 201, 202)
    return response.json()["id"]
    assert "解析复核队列" in response.text
    assert "纠错反馈闭环" in response.text


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.web
def test_submission_detail_exposes_operator_console_and_export_sections(api_client, mode_a_zip_path):
    submission_id = _create_submission(api_client, mode_a_zip_path)
    response = api_client.get(f"/submissions/{submission_id}")

    assert response.status_code == 200
    assert "人工干预台" in response.text
    assert "导出中心" in response.text
    assert "产物浏览" in response.text
    assert "导入摘要" in response.text
    assert "浏览器端导入说明" in api_client.get("/").text


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.web
def test_submission_detail_shows_retryable_job_history(api_client, mode_a_zip_path):
    Job = __import__("app.core.domain.models", fromlist=["Job"]).Job
    runtime_store = __import__("app.core.services.runtime_store", fromlist=["store"]).store

    submission_id = _create_submission(api_client, mode_a_zip_path)
    runtime_store.add_job(
        Job(
            id="job_submission_page_retry",
            job_type="ingest_submission",
            scope_type="submission",
            scope_id=submission_id,
            status="interrupted",
            progress=52,
            error_message="worker_interrupted_during_runtime",
            error_code="worker_interrupted_during_runtime",
            retryable=True,
            started_at="2026-05-02T12:00:00",
            updated_at="2026-05-02T12:05:00",
            finished_at="2026-05-02T12:05:00",
            metadata={
                "source_path": str(mode_a_zip_path),
                "original_filename": mode_a_zip_path.name,
                "mode": "single_case_package",
                "review_strategy": "auto_review",
                "review_profile": {},
                "retry_count": 0,
            },
        )
    )

    response = api_client.get(f"/submissions/{submission_id}")

    assert response.status_code == 200
    assert "任务链路" in response.text
    assert "worker_interrupted_during_runtime" in response.text
    assert "重试导入" in response.text
    assert f'/submissions/{submission_id}/actions/retry-job' in response.text


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.web
def test_html_retry_job_action_redirects_to_new_submission(api_client, mode_a_zip_path):
    Job = __import__("app.core.domain.models", fromlist=["Job"]).Job
    runtime_store = __import__("app.core.services.runtime_store", fromlist=["store"]).store

    submission_id = _create_submission(api_client, mode_a_zip_path)
    runtime_store.add_job(
        Job(
            id="job_html_retry",
            job_type="ingest_submission",
            scope_type="submission",
            scope_id=submission_id,
            status="interrupted",
            progress=61,
            error_message="worker_interrupted_during_runtime",
            error_code="worker_interrupted_during_runtime",
            retryable=True,
            started_at="2026-05-02T12:30:00",
            updated_at="2026-05-02T12:35:00",
            finished_at="2026-05-02T12:35:00",
            metadata={
                "source_path": str(mode_a_zip_path),
                "original_filename": mode_a_zip_path.name,
                "mode": "single_case_package",
                "review_strategy": "auto_review",
                "review_profile": {},
                "retry_count": 0,
            },
        )
    )

    response = api_client.post(
        f"/submissions/{submission_id}/actions/retry-job",
        data={"job_id": "job_html_retry"},
    )

    assert response.status_code == 303
    location = response.headers.get("Location", "")
    assert "notice=job_retried" in location
    assert "/submissions/sub_" in location


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.web
def test_export_page_separates_handoff_assets_from_support_logs(api_client, mode_a_zip_path):
    submission_id = _create_submission(api_client, mode_a_zip_path)

    response = api_client.get(f"/submissions/{submission_id}/exports")

    assert response.status_code == 200
    assert "导出中心" in response.text
    assert "下载批次包" in response.text
    assert "排障附件" in response.text
    assert "下载日志" in response.text


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.web
def test_export_page_delivery_confirmation_updates_internal_state(api_client, mode_a_zip_path):
    submission_id = _create_submission(api_client, mode_a_zip_path)

    exports_page = api_client.get(f"/submissions/{submission_id}/exports")
    assert exports_page.status_code == 200
    assert "交付确认" in exports_page.text
    assert "交付历史" in exports_page.text
    assert "暂无交付历史" in exports_page.text
    assert "标记为可交付" in exports_page.text
    assert "标记为已交付" in exports_page.text

    ready_response = api_client.post(
        f"/submissions/{submission_id}/actions/update-internal-state",
        data={
            "internal_status": "ready_to_deliver",
            "internal_next_step": "已生成内部交付包，待负责人复核后发送。",
            "internal_note": "已完成交付前检查，准备内部交付。",
            "updated_by": "delivery_center",
            "return_to": f"/submissions/{submission_id}/exports#delivery-check",
        },
    )
    assert ready_response.status_code == 303
    assert ready_response.headers.get("Location") == f"/submissions/{submission_id}/exports#delivery-check"
    ready_payload = api_client.get(f"/api/submissions/{submission_id}").json()
    assert ready_payload["internal_status"] == "ready_to_deliver"
    assert ready_payload["internal_next_step"] == "已生成内部交付包，待负责人复核后发送。"
    assert ready_payload["internal_updated_by"] == "delivery_center"

    delivered_response = api_client.post(
        f"/submissions/{submission_id}/actions/update-internal-state",
        data={
            "internal_status": "delivered",
            "internal_next_step": "本批次已交付并完成内部归档。",
            "internal_note": "导出中心确认已交付，交付结果已进入内部归档。",
            "updated_by": "delivery_center",
            "return_to": f"/submissions/{submission_id}/exports#delivery-check",
        },
    )
    assert delivered_response.status_code == 303
    delivered_payload = api_client.get(f"/api/submissions/{submission_id}").json()
    assert delivered_payload["internal_status"] == "delivered"
    assert delivered_payload["internal_next_step"] == "本批次已交付并完成内部归档。"
    assert delivered_payload["internal_note"] == "导出中心确认已交付，交付结果已进入内部归档。"

    history_page = api_client.get(f"/submissions/{submission_id}/exports")
    assert history_page.status_code == 200
    assert "交付历史" in history_page.text
    assert "已生成内部交付包，待负责人复核后发送。" in history_page.text
    assert "本批次已交付并完成内部归档。" in history_page.text
    assert "delivery_center" in history_page.text


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.web
def test_ops_page_exposes_self_check_and_support_artifacts(api_client):
    response = api_client.get("/ops")

    assert response.status_code == 200
    assert "运维中心" in response.text
    assert "发布闸门" in response.text
    assert "启动自检" in response.text
    assert "模型通道就绪度" in response.text
    assert "最新备份" in response.text
    assert "最新基线" in response.text
    assert "最新探针" in response.text
    assert "探针观测" in response.text
    assert "探针历史" in response.text
    assert "质量趋势" in response.text
    assert "业务收尾" in response.text
    assert "/downloads/logs/app" in response.text
    assert "/downloads/ops/delivery-closeout/latest-json" in response.text
    assert "/downloads/ops/delivery-closeout/latest-md" in response.text
    assert "app.tools.runtime_cleanup" in response.text
    assert "app.tools.runtime_backup" in response.text or "runtime_backup" in response.text
    assert "app.tools.provider_sandbox" in response.text or "provider_sandbox" in response.text
    assert "app.tools.provider_probe" in response.text or "provider_probe" in response.text
    assert "app.tools.release_gate" in response.text or "release_gate" in response.text
    assert "app.tools.delivery_closeout" in response.text or "delivery_closeout" in response.text
    assert "scripts\\start_mock_web.ps1" in response.text
    assert "scripts\\start_real_bridge.ps1" in response.text
    assert "scripts\\start_real_web.ps1" in response.text
    assert "scripts\\run_real_validation.ps1" in response.text
    assert "scripts\\show_stack_status.ps1" in response.text
    assert "app.tools.minimax_bridge" in response.text or "minimax_bridge" in response.text
    assert "真实通道冒烟" in response.text
    assert "滚动基线" in response.text


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.web
def test_ops_page_lists_retryable_jobs(api_client, mode_a_zip_path):
    Job = __import__("app.core.domain.models", fromlist=["Job"]).Job
    runtime_store = __import__("app.core.services.runtime_store", fromlist=["store"]).store

    runtime_store.add_job(
        Job(
            id="job_ops_retry",
            job_type="ingest_submission",
            scope_type="submission",
            scope_id="sub_ops_retry",
            status="failed",
            progress=100,
            error_message="disk busy",
            error_code="filesystem_io_error",
            retryable=True,
            started_at="2026-05-02T13:00:00",
            updated_at="2026-05-02T13:02:00",
            finished_at="2026-05-02T13:02:00",
            metadata={
                "source_path": str(mode_a_zip_path),
                "original_filename": mode_a_zip_path.name,
                "mode": "single_case_package",
                "review_strategy": "auto_review",
                "review_profile": {},
                "retry_count": 1,
            },
        )
    )

    response = api_client.get("/ops")

    assert response.status_code == 200
    assert "失败与重试" in response.text
    assert "filesystem_io_error" in response.text
    assert "sub_ops_retry" in response.text


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.web
def test_ops_page_can_filter_retryable_jobs(api_client, mode_a_zip_path):
    Job = __import__("app.core.domain.models", fromlist=["Job"]).Job
    runtime_store = __import__("app.core.services.runtime_store", fromlist=["store"]).store

    runtime_store.add_job(
        Job(
            id="job_ops_failed",
            job_type="ingest_submission",
            scope_type="submission",
            scope_id="sub_ops_failed",
            status="failed",
            progress=100,
            error_message="disk busy",
            error_code="filesystem_io_error",
            retryable=True,
            started_at="2026-05-02T13:10:00",
            updated_at="2026-05-02T13:11:00",
            finished_at="2026-05-02T13:11:00",
            metadata={"source_path": str(mode_a_zip_path), "mode": "single_case_package"},
        )
    )
    runtime_store.add_job(
        Job(
            id="job_ops_interrupted",
            job_type="ingest_submission",
            scope_type="submission",
            scope_id="sub_ops_interrupted",
            status="interrupted",
            progress=55,
            error_message="worker_interrupted_during_runtime",
            error_code="worker_interrupted_during_runtime",
            retryable=True,
            started_at="2026-05-02T13:12:00",
            updated_at="2026-05-02T13:13:00",
            finished_at="2026-05-02T13:13:00",
            metadata={"source_path": str(mode_a_zip_path), "mode": "single_case_package"},
        )
    )

    response = api_client.get("/ops?job_status=interrupted&job_error=worker")

    assert response.status_code == 200
    assert "sub_ops_interrupted" in response.text
    assert "sub_ops_failed" not in response.text


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.web
def test_ops_page_shows_correction_feedback_after_manual_fix(api_client, mode_a_zip_path):
    submission_id = _create_submission(api_client, mode_a_zip_path)
    files_payload = api_client.get(f"/api/submissions/{submission_id}/files").json()["files"]
    material_id = files_payload[0]["id"]

    fix_response = api_client.post(
        f"/api/materials/{material_id}/type",
        data={"material_type": "agreement", "corrected_by": "tester", "note": "ops feedback"},
    )
    assert fix_response.status_code == 200

    response = api_client.get("/ops")

    assert response.status_code == 200
    assert "纠错反馈闭环" in response.text
    assert "manual_material_reclassified" in response.text or "人工重分材料类型" in response.text
    assert 'name="job_status"' in response.text
    assert 'name="job_error"' in response.text


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
        closeout_json_download = client.get("/downloads/ops/delivery-closeout/latest-json")
        closeout_md_download = client.get("/downloads/ops/delivery-closeout/latest-md")

        assert result["artifact_path"].endswith("provider_probe_latest.json")
        assert latest_download.status_code == 200
        assert latest_download.content
        assert history_download.status_code == 200
        assert history_download.content
        assert closeout_json_download.status_code == 200
        assert closeout_json_download.content
        assert closeout_md_download.status_code == 200
        assert closeout_md_download.content
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
    assert "更正审计" in submission_page.text
    assert "产物浏览" in submission_page.text

    rerun_response = api_client.post(
        f"/submissions/{submission_id}/actions/rerun-review",
        data={"case_id": case_id, "note": "refresh"},
    )
    assert rerun_response.status_code == 303
    rerun_location = rerun_response.headers.get("Location", "")
    assert "notice=case_review_rerun" in rerun_location
    assert "#export-center" in rerun_location

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


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.web
def test_html_manual_desensitized_flow_exposes_continue_review_entry(api_client, mode_a_zip_path):
    submission_id = _create_submission(
        api_client,
        mode_a_zip_path,
        review_strategy="manual_desensitized_review",
    )
    submission_payload = api_client.get(f"/api/submissions/{submission_id}").json()
    case_id = submission_payload["case_ids"][0]

    materials_page = api_client.get(f"/submissions/{submission_id}/materials")
    assert materials_page.status_code == 200
    assert "脱敏工作台" in materials_page.text
    assert "脱敏件" in materials_page.text

    operator_page = api_client.get(f"/submissions/{submission_id}/operator")
    assert operator_page.status_code == 200
    assert "脱敏后继续审查" in operator_page.text
    assert "继续审查项目" in operator_page.text
    assert "材料与项目整理" in operator_page.text

    continue_response = api_client.post(
        f"/submissions/{submission_id}/actions/continue-review",
        data={"case_id": case_id, "note": "html continue"},
    )
    assert continue_response.status_code == 303
    continue_location = continue_response.headers.get("Location", "")
    assert "notice=case_review_continued" in continue_location
    assert "#export-center" in continue_location

    submission_after = api_client.get(f"/api/submissions/{submission_id}").json()
    assert submission_after["status"] == "completed"
    assert submission_after["review_stage"] == "review_completed"
    assert submission_after["report_ids"]


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.web
def test_html_manual_desensitized_flow_supports_uploading_desensitized_package(api_client, mode_a_zip_path, tmp_path):
    submission_id = _create_submission(
        api_client,
        mode_a_zip_path,
        review_strategy="manual_desensitized_review",
    )

    files_payload = api_client.get(f"/api/submissions/{submission_id}/files").json()["files"]
    zip_path = tmp_path / "desensitized-package.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for item in files_payload:
            download = api_client.get(f"/downloads/materials/{item['id']}/desensitized")
            assert download.status_code == 200
            archive.writestr(f"{item['original_filename']}.desensitized.txt", download.content)

    with zip_path.open("rb") as handle:
        upload_response = api_client.post(
            f"/submissions/{submission_id}/actions/upload-desensitized-package",
            files={"file": (zip_path.name, handle, "application/zip")},
            data={"note": "html upload package"},
        )

    assert upload_response.status_code == 303
    upload_location = upload_response.headers.get("Location", "")
    assert "notice=desensitized_package_uploaded" in upload_location
    assert "#operator-console" in upload_location

    submission_after = api_client.get(f"/api/submissions/{submission_id}").json()
    assert submission_after["status"] == "awaiting_manual_review"
    assert submission_after["review_stage"] == "desensitized_uploaded"
