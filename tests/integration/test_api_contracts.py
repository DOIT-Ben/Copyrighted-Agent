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
    assert len(payload["reports"]) == 1
    assert payload["reports"][0]["report_type"] == "batch_markdown"


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
