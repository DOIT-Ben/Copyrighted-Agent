from __future__ import annotations

import pytest


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.web
def test_home_page_renders_upload_controls(api_client):
    response = api_client.get("/")
    assert response.status_code == 200
    assert "总控台" in response.text
    assert "导入台" in response.text
    assert 'action="/upload"' in response.text


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.web
def test_stylesheet_route_serves_css_media_type(api_client):
    response = api_client.get("/static/styles.css")
    assert response.status_code == 200
    assert getattr(response, "media_type", "").startswith("text/css")
    assert response.headers.get("Cache-Control") == "no-store"
    assert ".admin-shell" in response.text


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.web
def test_upload_flow_exposes_submission_case_report_and_index_pages(api_client, mode_a_zip_path):
    with mode_a_zip_path.open("rb") as handle:
        response = api_client.post(
            "/upload",
            files={"file": (mode_a_zip_path.name, handle, "application/zip")},
            data={"mode": "single_case_package"},
        )

    assert response.status_code == 302
    location = response.headers.get("Location", "")
    assert location.startswith("/submissions/")

    submission_page = api_client.get(location)
    assert submission_page.status_code == 200
    assert mode_a_zip_path.name in submission_page.text
    assert "材料矩阵" in submission_page.text
    assert "待复核队列" in submission_page.text

    submission_id = location.rsplit("/", 1)[-1]
    submission_payload = api_client.get(f"/api/submissions/{submission_id}").json()
    assert submission_payload["case_ids"]
    assert submission_payload["report_ids"]

    case_page = api_client.get(f"/cases/{submission_payload['case_ids'][0]}")
    assert case_page.status_code == 200
    assert "风险队列" in case_page.text
    assert "AI 辅助研判" in case_page.text

    report_page = api_client.get(f"/reports/{submission_payload['report_ids'][0]}")
    assert report_page.status_code == 200
    assert "报告阅读器" in report_page.text

    index_page = api_client.get("/submissions")
    assert index_page.status_code == 200
    assert mode_a_zip_path.name in index_page.text
    assert "批次台账" in index_page.text
