from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from tests.helpers.contracts import require_symbol


def _create_test_client(*, testing: bool = True):
    from fastapi.testclient import TestClient

    create_app = require_symbol("app.api.main", "create_app")
    return TestClient(create_app(testing=testing))


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.security
def test_html_responses_include_browser_security_headers_and_csrf_token():
    client = _create_test_client(testing=False)

    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["Content-Security-Policy"].startswith("default-src 'self'")
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "same-origin"
    assert 'name="csrf_token"' in response.text


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.security
def test_production_html_post_rejects_missing_csrf_token():
    client = _create_test_client(testing=False)

    response = client.post("/upload", data={"mode": "single_case_package"})

    assert response.status_code == 403
    assert response.json()["detail"] == "CSRF token missing or invalid"


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.security
def test_production_api_post_is_not_blocked_by_browser_csrf_guard(mode_a_zip_path):
    client = _create_test_client(testing=False)

    with mode_a_zip_path.open("rb") as handle:
        response = client.post(
            "/api/submissions",
            files={"file": (mode_a_zip_path.name, handle, "application/zip")},
            data={"mode": "single_case_package"},
        )

    assert response.status_code != 403


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.security
def test_every_html_post_form_receives_csrf_token():
    client = _create_test_client(testing=False)

    response = client.get("/submissions")

    assert response.status_code == 200
    assert response.text.count('method="post"') == response.text.count('name="csrf_token"')


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.security
@pytest.mark.zip
def test_safe_extract_zip_blocks_zip_slip_entries(zip_with_zip_slip_path, tmp_path: Path):
    safe_extract_zip = require_symbol("app.core.services.zip_ingestion", "safe_extract_zip")
    with pytest.raises(Exception):
        safe_extract_zip(zip_path=zip_with_zip_slip_path, destination=tmp_path)


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.security
@pytest.mark.zip
def test_safe_extract_zip_rejects_executable_files(zip_with_executable_path, tmp_path: Path):
    safe_extract_zip = require_symbol("app.core.services.zip_ingestion", "safe_extract_zip")
    with pytest.raises(Exception):
        safe_extract_zip(zip_path=zip_with_executable_path, destination=tmp_path)


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.security
@pytest.mark.zip
def test_safe_extract_zip_sanitizes_windows_unsafe_filenames(zip_with_windows_unsafe_names_path, tmp_path: Path):
    safe_extract_zip = require_symbol("app.core.services.zip_ingestion", "safe_extract_zip")
    extracted = safe_extract_zip(zip_path=zip_with_windows_unsafe_names_path, destination=tmp_path)
    invalid_chars = '<>:"\\|?*'
    assert extracted
    assert all(not any(char in path.name for char in invalid_chars) for path in extracted)


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.security
@pytest.mark.zip
def test_safe_extract_zip_rejects_member_count_over_limit(make_zip, tmp_path: Path):
    safe_extract_zip = require_symbol("app.core.services.zip_ingestion", "safe_extract_zip")
    zip_path = make_zip("too_many_members.zip", {"a.txt": "a", "b.txt": "b"})

    with pytest.raises(ValueError):
        safe_extract_zip(zip_path=zip_path, destination=tmp_path, max_members=1)


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.security
@pytest.mark.zip
def test_safe_extract_zip_rejects_uncompressed_size_over_limit(tmp_path: Path):
    safe_extract_zip = require_symbol("app.core.services.zip_ingestion", "safe_extract_zip")
    zip_path = tmp_path / "oversized_uncompressed.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("large.txt", "x" * 128)

    with pytest.raises(ValueError):
        safe_extract_zip(zip_path=zip_path, destination=tmp_path / "out", max_total_uncompressed_bytes=16)


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.security
def test_api_upload_rejects_zip_over_configured_size(monkeypatch, mode_a_zip_path):
    monkeypatch.setenv("SOFT_REVIEW_MAX_UPLOAD_BYTES", "1")
    client = _create_test_client(testing=True)

    with mode_a_zip_path.open("rb") as handle:
        response = client.post(
            "/api/submissions",
            files={"file": (mode_a_zip_path.name, handle, "application/zip")},
            data={"mode": "single_case_package"},
        )

    assert response.status_code == 413


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.security
def test_log_download_returns_configured_tail(monkeypatch, tmp_path: Path):
    log_path = tmp_path / "runtime" / "logs" / "app.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("old-line\n" + "x" * 80 + "\nnew-line\n", encoding="utf-8")
    monkeypatch.setenv("SOFT_REVIEW_LOG_PATH", str(log_path))
    monkeypatch.setenv("SOFT_REVIEW_MAX_LOG_DOWNLOAD_BYTES", "24")
    client = _create_test_client(testing=True)

    response = client.get("/downloads/logs/app")

    assert response.status_code == 200
    assert "new-line" in response.text
    assert "old-line" not in response.text
