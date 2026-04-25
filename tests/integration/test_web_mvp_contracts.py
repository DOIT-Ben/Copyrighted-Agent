from __future__ import annotations

import time

import pytest


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.web
def test_home_page_renders_upload_controls(api_client):
    response = api_client.get("/")
    assert response.status_code == 200
    assert 'action="/upload"' in response.text
    assert 'name="review_strategy"' in response.text
    assert 'data-pending-steps=' in response.text
    assert 'data-inline-pending' in response.text
    assert 'id="submit-feedback"' in response.text
    assert 'id="submit-feedback-step"' in response.text
    assert 'data-async-upload-url="/api/submissions/async"' in response.text
    assert 'name="focus_mode"' in response.text
    assert 'name="strictness"' in response.text
    assert 'name="llm_instruction"' in response.text
    assert "导入前编辑规则" in response.text
    assert 'name="rule_source_code_checkpoints"' in response.text
    assert 'data-review-preset="source_code_strict"' in response.text


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
            data={"mode": "single_case_package", "review_strategy": "auto_review"},
        )

    assert response.status_code == 302
    location = response.headers.get("Location", "")
    assert location.startswith("/submissions/")

    submission_page = api_client.get(location)
    assert submission_page.status_code == 200
    assert mode_a_zip_path.name in submission_page.text
    assert "导入摘要" in submission_page.text
    assert "下一步" in submission_page.text
    assert "更多信息" in submission_page.text

    submission_id = location.rsplit("/", 1)[-1]
    submission_payload = api_client.get(f"/api/submissions/{submission_id}").json()
    assert submission_payload["case_ids"]
    assert submission_payload["report_ids"]

    case_page = api_client.get(f"/cases/{submission_payload['case_ids'][0]}")
    assert case_page.status_code == 200
    assert "风险队列" in case_page.text
    assert "AI 辅助研判" in case_page.text
    assert "审查维度" in case_page.text
    assert "更多信息" in case_page.text

    report_page = api_client.get(f"/reports/{submission_payload['report_ids'][0]}")
    assert report_page.status_code == 200
    assert "审查结果" in report_page.text
    assert "审查维度" in report_page.text
    assert "更多信息" in report_page.text
    assert "保存为 PDF" in report_page.text

    index_page = api_client.get("/submissions")
    assert index_page.status_code == 200
    assert mode_a_zip_path.name in index_page.text


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.web
def test_async_submission_api_returns_job_and_completes(api_client, mode_a_zip_path):
    with mode_a_zip_path.open("rb") as handle:
        response = api_client.post(
            "/api/submissions/async",
            files={"file": (mode_a_zip_path.name, handle, "application/zip")},
            data={"mode": "single_case_package", "review_strategy": "auto_review"},
        )

    assert response.status_code == 202
    payload = response.json()
    assert payload["job_id"]
    assert payload["submission_id"]
    assert payload["status_url"].endswith(payload["job_id"])
    assert payload["redirect_url"].endswith(payload["submission_id"])

    job_payload = {}
    for _ in range(100):
        job_response = api_client.get(payload["status_url"])
        assert job_response.status_code == 200
        job_payload = job_response.json()
        if job_payload["status"] in {"completed", "failed"}:
            break
        time.sleep(0.02)

    assert job_payload["status"] == "completed"
    assert job_payload["scope_id"] == payload["submission_id"]
    assert job_payload["progress"] == 100
    assert job_payload["stage"]


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.web
def test_rerun_review_persists_review_profile(api_client, mode_a_zip_path):
    with mode_a_zip_path.open("rb") as handle:
        response = api_client.post(
            "/upload",
            files={"file": (mode_a_zip_path.name, handle, "application/zip")},
            data={"mode": "single_case_package", "review_strategy": "auto_review"},
        )

    submission_location = response.headers.get("Location", "")
    submission_id = submission_location.rsplit("/", 1)[-1]
    submission_payload = api_client.get(f"/api/submissions/{submission_id}").json()
    case_id = submission_payload["case_ids"][0]

    rerun_response = api_client.post(
        f"/submissions/{submission_id}/actions/rerun-review",
        data={
            "case_id": case_id,
            "review_profile_preset": "source_code_strict",
            "focus_mode": "source_code_first",
            "strictness": "strict",
            "llm_instruction": "重点检查源码说明与软件名称是否一致。",
            "review_dimensions_present": "1",
            "dimension_identity": "1",
            "dimension_consistency": "1",
            "dimension_source_code": "1",
            "dimension_ai": "1",
        },
    )

    assert rerun_response.status_code == 303
    updated_submission = api_client.get(f"/api/submissions/{submission_id}").json()
    assert updated_submission["review_profile"]["preset_key"] == "source_code_strict"
    assert updated_submission["review_profile"]["focus_mode"] == "source_code_first"
    assert updated_submission["review_profile"]["strictness"] == "strict"
    assert updated_submission["review_profile"]["llm_instruction"] == "重点检查源码说明与软件名称是否一致。"

    case_page = api_client.get(f"/cases/{case_id}")
    assert case_page.status_code == 200
    assert "更多信息" in case_page.text


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.web
def test_upload_flow_persists_import_time_rule_edits(api_client, mode_a_zip_path):
    with mode_a_zip_path.open("rb") as handle:
        response = api_client.post(
            "/upload",
            files={"file": (mode_a_zip_path.name, handle, "application/zip")},
            data={
                "mode": "single_case_package",
                "review_strategy": "auto_review",
                "review_dimensions_present": "1",
                "dimension_identity": "1",
                "dimension_source_code": "1",
                "dimension_ai": "1",
                "rule_source_code_title": "导入前源码规则",
                "rule_source_code_objective": "导入前就要求重点检查源码可读性。",
                "rule_source_code_checkpoints": "- 源码必须可读\n- 入口函数需要明确",
                "rule_source_code_llm_focus": "优先提示源码不可审查风险。",
            },
        )

    assert response.status_code == 302
    submission_id = response.headers.get("Location", "").rsplit("/", 1)[-1]
    submission_payload = api_client.get(f"/api/submissions/{submission_id}").json()
    source_rule = submission_payload["review_profile"]["dimension_rulebook"]["source_code"]

    assert source_rule["title"] == "导入前源码规则"
    assert source_rule["objective"] == "导入前就要求重点检查源码可读性。"
    assert source_rule["checkpoints"][:2] == ["源码必须可读", "入口函数需要明确"]
    assert source_rule["llm_focus"] == "优先提示源码不可审查风险。"


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.web
def test_review_rule_page_can_save_rule_and_persist_to_submission(api_client, mode_a_zip_path):
    with mode_a_zip_path.open("rb") as handle:
        response = api_client.post(
            "/upload",
            files={"file": (mode_a_zip_path.name, handle, "application/zip")},
            data={"mode": "single_case_package", "review_strategy": "auto_review"},
        )

    submission_location = response.headers.get("Location", "")
    submission_id = submission_location.rsplit("/", 1)[-1]
    submission_payload = api_client.get(f"/api/submissions/{submission_id}").json()
    case_id = submission_payload["case_ids"][0]

    rule_page = api_client.get(f"/submissions/{submission_id}/review-rules/source_code?case_id={case_id}")
    assert rule_page.status_code == 200

    save_response = api_client.post(
        f"/submissions/{submission_id}/review-rules/source_code",
        data={
            "title": "源码校验规则",
            "objective": "重点检查源码可读性、命名一致性和版本信号。",
            "checkpoints": "- 源码需要可读\n- 名称和版本应一致\n- 技术描述不能明显冲突",
            "llm_focus": "优先总结源码相关高风险问题。",
            "case_id": case_id,
            "action": "save",
            "note": "更新源码规则",
        },
    )

    assert save_response.status_code == 303
    updated_submission = api_client.get(f"/api/submissions/{submission_id}").json()
    source_rule = updated_submission["review_profile"]["dimension_rulebook"]["source_code"]
    assert source_rule["title"] == "源码校验规则"
    assert source_rule["objective"] == "重点检查源码可读性、命名一致性和版本信号。"
    assert source_rule["llm_focus"] == "优先总结源码相关高风险问题。"
    assert source_rule["checkpoints"][:2] == ["源码需要可读", "名称和版本应一致"]

    restore_response = api_client.post(
        f"/submissions/{submission_id}/review-rules/source_code",
        data={
            "case_id": case_id,
            "action": "restore_default",
            "note": "恢复默认",
        },
    )

    assert restore_response.status_code == 303
    restored_submission = api_client.get(f"/api/submissions/{submission_id}").json()
    restored_rule = restored_submission["review_profile"]["dimension_rulebook"]["source_code"]
    assert restored_rule["title"] != "源码校验规则"
