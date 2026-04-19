from __future__ import annotations

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
            data={"mode": "single_case_package"},
        )
    assert response.status_code in (200, 201, 202)


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

