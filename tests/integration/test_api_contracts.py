from __future__ import annotations

import time

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from tests.helpers.contracts import require_symbol


@pytest.fixture
def api_client():
    create_app = require_symbol("app.api.main", "create_app")
    app = create_app(testing=True)
    return TestClient(app)


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.api
def test_upload_submission_accepts_zip_and_mode(api_client, mode_a_zip_path):
    with mode_a_zip_path.open("rb") as handle:
        response = api_client.post(
            "/api/submissions",
            files={"file": (mode_a_zip_path.name, handle, "application/zip")},
            data={"mode": "single_case_package", "review_strategy": "auto_review"},
        )
    assert response.status_code in (200, 201, 202)


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.api
def test_upload_submission_accepts_manual_desensitized_review_strategy(api_client, mode_a_zip_path):
    with mode_a_zip_path.open("rb") as handle:
        response = api_client.post(
            "/api/submissions",
            files={"file": (mode_a_zip_path.name, handle, "application/zip")},
            data={"mode": "single_case_package", "review_strategy": "manual_desensitized_review"},
        )
    assert response.status_code in (200, 201, 202)
    payload = response.json()
    assert payload["status"] == "awaiting_manual_review"
    assert payload["review_strategy"] == "manual_desensitized_review"


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.api
def test_upload_submission_rejects_non_zip(api_client, tmp_path):
    fake_file = tmp_path / "notes.txt"
    fake_file.write_text("not a zip archive", encoding="utf-8")
    with fake_file.open("rb") as handle:
        response = api_client.post(
            "/api/submissions",
            files={"file": (fake_file.name, handle, "text/plain")},
            data={"mode": "single_case_package"},
        )
    assert response.status_code in (400, 415, 422)


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.api
def test_upload_submission_supports_batch_mode_and_returns_batch_report(api_client, mode_b_zip_path):
    with mode_b_zip_path.open("rb") as handle:
        response = api_client.post(
            "/api/submissions",
            files={"file": (mode_b_zip_path.name, handle, "application/zip")},
            data={"mode": "batch_same_material", "review_strategy": "auto_review"},
        )

    assert response.status_code in (200, 201, 202)
    payload = response.json()
    assert payload["status"] == "completed"
    assert len(payload["materials"]) == 3
    assert len(payload["reports"]) == 2
    assert {item["report_type"] for item in payload["reports"]} == {
        "batch_markdown",
        "submission_global_review_markdown",
    }
    assert payload["review_profile"]["submission_global_review"]["material_inventory"]["total"] == 3


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.api
def test_async_submission_supports_manual_desensitized_review_strategy(api_client, mode_a_zip_path):
    with mode_a_zip_path.open("rb") as handle:
        response = api_client.post(
            "/api/submissions/async",
            files={"file": (mode_a_zip_path.name, handle, "application/zip")},
            data={"mode": "single_case_package", "review_strategy": "manual_desensitized_review"},
        )

    assert response.status_code == 202
    payload = response.json()
    assert payload["job_id"]
    assert payload["submission_id"]

    submission_payload = {}
    for _ in range(100):
        job_response = api_client.get(payload["status_url"])
        assert job_response.status_code == 200
        job_payload = job_response.json()
        if job_payload["status"] in {"completed", "failed"}:
            break
        time.sleep(0.02)
    else:
        pytest.fail("async manual desensitized submission did not finish in time")

    assert job_payload["status"] == "completed"
    submission_payload = api_client.get(f"/api/submissions/{payload['submission_id']}").json()
    assert submission_payload["status"] == "awaiting_manual_review"
    assert submission_payload["review_stage"] == "desensitized_ready"


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.api
def test_async_submission_supports_batch_mode(api_client, mode_b_zip_path):
    with mode_b_zip_path.open("rb") as handle:
        response = api_client.post(
            "/api/submissions/async",
            files={"file": (mode_b_zip_path.name, handle, "application/zip")},
            data={"mode": "batch_same_material", "review_strategy": "auto_review"},
        )

    assert response.status_code == 202
    payload = response.json()

    for _ in range(100):
        job_response = api_client.get(payload["status_url"])
        assert job_response.status_code == 200
        job_payload = job_response.json()
        if job_payload["status"] in {"completed", "failed"}:
            break
        time.sleep(0.02)
    else:
        pytest.fail("async batch submission did not finish in time")

    assert job_payload["status"] == "completed"
    submission_payload = api_client.get(f"/api/submissions/{payload['submission_id']}").json()
    assert submission_payload["status"] == "completed"
    assert submission_payload["mode"] == "batch_same_material"
    assert submission_payload["report_ids"]


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.api
def test_interrupted_ingest_job_can_be_retried(api_client, mode_a_zip_path):
    Job = require_symbol("app.core.domain.models", "Job")
    runtime_store = require_symbol("app.core.services.runtime_store", "store")

    interrupted_job = runtime_store.add_job(
        Job(
            id="job_retry_source",
            job_type="ingest_submission",
            scope_type="submission",
            scope_id="sub_retry_source",
            status="interrupted",
            progress=44,
            error_message="worker_interrupted_during_runtime",
            error_code="worker_interrupted_during_runtime",
            retryable=True,
            started_at="2026-05-02T11:00:00",
            updated_at="2026-05-02T11:05:00",
            finished_at="2026-05-02T11:05:00",
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

    job_payload = api_client.get(f"/api/jobs/{interrupted_job.id}").json()
    assert job_payload["can_retry"] is True
    assert job_payload["retry_url"] == f"/api/jobs/{interrupted_job.id}/retry"

    retry_response = api_client.post(job_payload["retry_url"])
    assert retry_response.status_code == 202
    retry_payload = retry_response.json()
    assert retry_payload["retry_of_job_id"] == interrupted_job.id

    for _ in range(100):
        polled = api_client.get(retry_payload["status_url"])
        assert polled.status_code == 200
        polled_payload = polled.json()
        if polled_payload["status"] in {"completed", "failed"}:
            break
        time.sleep(0.02)
    else:
        pytest.fail("retried async submission did not finish in time")

    assert polled_payload["status"] == "completed"
    assert polled_payload["metadata"]["retry_count"] == 1
    assert polled_payload["metadata"]["retry_of_job_id"] == interrupted_job.id
    submission_payload = api_client.get(f"/api/submissions/{retry_payload['submission_id']}").json()
    assert submission_payload["status"] == "completed"


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.api
def test_submission_diagnostics_and_corrections_api_expose_summary(api_client, mode_a_zip_path):
    with mode_a_zip_path.open("rb") as handle:
        response = api_client.post(
            "/api/submissions",
            files={"file": (mode_a_zip_path.name, handle, "application/zip")},
            data={"mode": "single_case_package", "review_strategy": "auto_review"},
        )
    assert response.status_code in (200, 201, 202)
    submission_id = response.json()["id"]

    files_payload = api_client.get(f"/api/submissions/{submission_id}/files").json()["files"]
    material_id = files_payload[0]["id"]
    fix_response = api_client.post(
        f"/api/materials/{material_id}/type",
        data={"material_type": "agreement", "corrected_by": "tester", "note": "api summary"},
    )
    assert fix_response.status_code == 200

    diagnostics_response = api_client.get(f"/api/submissions/{submission_id}/diagnostics")
    assert diagnostics_response.status_code == 200
    diagnostics_payload = diagnostics_response.json()
    assert diagnostics_payload["submission_id"] == submission_id
    assert "summary" in diagnostics_payload
    assert diagnostics_payload["diagnostics"]
    assert "parse_reason_code" in diagnostics_payload["diagnostics"][0]

    corrections_response = api_client.get(f"/api/submissions/{submission_id}/corrections")
    assert corrections_response.status_code == 200
    corrections_payload = corrections_response.json()
    assert corrections_payload["submission_id"] == submission_id
    assert "summary" in corrections_payload
    assert "review_profile_meta" in corrections_payload
    assert corrections_payload["corrections"][0]["reason_code"] == "manual_material_reclassified"


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.api
def test_submission_review_rule_history_api_exposes_revision_timeline(api_client, mode_a_zip_path):
    with mode_a_zip_path.open("rb") as handle:
        response = api_client.post(
            "/upload",
            files={"file": (mode_a_zip_path.name, handle, "application/zip")},
            data={"mode": "single_case_package", "review_strategy": "auto_review"},
        )

    submission_id = response.headers.get("Location", "").rsplit("/", 1)[-1]
    submission_payload = api_client.get(f"/api/submissions/{submission_id}").json()
    case_id = submission_payload["case_ids"][0]

    save_response = api_client.post(
        f"/submissions/{submission_id}/review-rules/source_code",
        data={
            "title": "源码校验规则",
            "objective": "重点检查源码可读性。",
            "checkpoints": "- 源码需要可读",
            "llm_focus": "优先总结源码风险。",
            "rule_source_code_item_code_desensitized_enabled": "1",
            "rule_source_code_item_code_desensitized_title": "源码脱敏必须完成",
            "rule_source_code_item_code_desensitized_severity": "severe",
            "rule_source_code_item_code_desensitized_prompt_hint": "检查敏感信息。",
            "case_id": case_id,
            "action": "save",
            "note": "第一次调整源码规则",
        },
    )
    assert save_response.status_code == 303

    restore_response = api_client.post(
        f"/submissions/{submission_id}/review-rules/source_code",
        data={"case_id": case_id, "action": "restore_default", "note": "恢复默认"},
    )
    assert restore_response.status_code == 303

    history_response = api_client.get(f"/api/submissions/{submission_id}/review-rules/source_code/history")
    assert history_response.status_code == 200
    history_payload = history_response.json()
    assert history_payload["submission_id"] == submission_id
    assert history_payload["dimension_key"] == "source_code"
    assert history_payload["items"]
    assert history_payload["items"][0]["dimension_key"] == "source_code"
    assert history_payload["items"][0]["revision"] >= 2
    assert any(item["change_note"] == "第一次调整源码规则" for item in history_payload["items"])
    assert any(item["correction_type"] == "reset_review_dimension_rule" for item in history_payload["items"])


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.api
def test_ops_api_endpoints_expose_retry_queue_and_feedback(api_client, mode_a_zip_path):
    Job = require_symbol("app.core.domain.models", "Job")
    runtime_store = require_symbol("app.core.services.runtime_store", "store")

    runtime_store.add_job(
        Job(
            id="job_ops_api_retry",
            job_type="ingest_submission",
            scope_type="submission",
            scope_id="sub_ops_api_retry",
            status="failed",
            progress=100,
            error_message="disk busy",
            error_code="filesystem_io_error",
            retryable=True,
            started_at="2026-05-02T13:00:00",
            updated_at="2026-05-02T13:02:00",
            finished_at="2026-05-02T13:02:00",
            metadata={"source_path": str(mode_a_zip_path), "mode": "single_case_package", "retry_count": 1},
        )
    )

    with mode_a_zip_path.open("rb") as handle:
        response = api_client.post(
            "/api/submissions",
            files={"file": (mode_a_zip_path.name, handle, "application/zip")},
            data={"mode": "single_case_package", "review_strategy": "auto_review"},
        )
    submission_id = response.json()["id"]
    material_id = api_client.get(f"/api/submissions/{submission_id}/files").json()["files"][0]["id"]
    api_client.post(
        f"/api/materials/{material_id}/type",
        data={"material_type": "agreement", "corrected_by": "tester", "note": "ops api"},
    )

    retryable_response = api_client.get("/api/ops/retryable-jobs")
    manual_queue_response = api_client.get("/api/ops/manual-review-queue")
    correction_feedback_response = api_client.get("/api/ops/correction-feedback")

    assert retryable_response.status_code == 200
    assert any(item["id"] == "job_ops_api_retry" for item in retryable_response.json()["items"])
    assert manual_queue_response.status_code == 200
    assert "items" in manual_queue_response.json()
    assert correction_feedback_response.status_code == 200
    assert any(item["reason_code"] == "manual_material_reclassified" for item in correction_feedback_response.json()["items"])
