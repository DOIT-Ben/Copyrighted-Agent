from __future__ import annotations

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


def _build_desensitized_zip(api_client, submission_id: str, tmp_path):
    files_payload = api_client.get(f"/api/submissions/{submission_id}/files").json()["files"]
    zip_path = tmp_path / "desensitized-upload.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for item in files_payload:
            download = api_client.get(f"/downloads/materials/{item['id']}/desensitized")
            assert download.status_code == 200
            archive.writestr(f"{item['original_filename']}.desensitized.txt", download.content)
    return zip_path


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.api
def test_change_material_type_creates_correction_record(api_client, mode_a_zip_path):
    submission_id = _create_submission(api_client, mode_a_zip_path)
    files_payload = api_client.get(f"/api/submissions/{submission_id}/files").json()
    material = files_payload["files"][0]

    response = api_client.post(
        f"/api/materials/{material['id']}/type",
        data={"material_type": "agreement", "corrected_by": "tester", "note": "manual correction"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["material"]["material_type"] == "agreement"
    assert payload["correction"]["correction_type"] == "change_material_type"
    assert payload["correction"]["corrected_by"] == "tester"

    corrections = api_client.get(f"/api/submissions/{submission_id}/corrections").json()["corrections"]
    assert len(corrections) == 1
    assert corrections[0]["material_id"] == material["id"]

    submission_page = api_client.get(f"/submissions/{submission_id}")
    assert submission_page.status_code == 200
    assert "更正审计" in submission_page.text
    assert "更正材料类型" in submission_page.text


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.api
def test_manual_case_regroup_flow_supports_create_assign_merge_and_rerun(api_client, mode_a_zip_path):
    submission_id = _create_submission(api_client, mode_a_zip_path)
    submission_payload = api_client.get(f"/api/submissions/{submission_id}").json()
    original_case_id = submission_payload["case_ids"][0]
    files_payload = api_client.get(f"/api/submissions/{submission_id}/files").json()
    material_ids = [item["id"] for item in files_payload["files"]]

    create_response = api_client.post(
        f"/api/submissions/{submission_id}/cases",
        data={
            "material_ids": ",".join(material_ids[:2]),
            "case_name": "Manual Regroup Case",
            "corrected_by": "tester",
        },
    )
    assert create_response.status_code == 200
    new_case_id = create_response.json()["case"]["id"]
    assert new_case_id != original_case_id

    assign_response = api_client.post(
        f"/api/materials/{material_ids[2]}/assign-case",
        data={"case_id": new_case_id, "corrected_by": "tester"},
    )
    assert assign_response.status_code == 200
    assert assign_response.json()["material"]["case_id"] == new_case_id

    rerun_response = api_client.post(
        f"/api/cases/{new_case_id}/rerun-review",
        data={"corrected_by": "tester", "note": "after regroup"},
    )
    assert rerun_response.status_code == 200
    assert rerun_response.json()["report"]["scope_id"] == new_case_id

    merge_response = api_client.post(
        f"/api/cases/{original_case_id}/merge",
        data={"target_case_id": new_case_id, "corrected_by": "tester"},
    )
    assert merge_response.status_code == 200
    assert merge_response.json()["case"]["id"] == new_case_id

    submission_after = api_client.get(f"/api/submissions/{submission_id}").json()
    assert submission_after["case_ids"] == [new_case_id]

    corrections = api_client.get(f"/api/submissions/{submission_id}/corrections").json()["corrections"]
    correction_types = [item["correction_type"] for item in corrections]
    assert correction_types == [
        "create_case_from_materials",
        "assign_material_to_case",
        "rerun_case_review",
        "merge_cases",
    ]


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.api
def test_manual_desensitized_review_can_continue_after_download_stage(api_client, mode_a_zip_path):
    submission_id = _create_submission(
        api_client,
        mode_a_zip_path,
        review_strategy="manual_desensitized_review",
    )
    submission_payload = api_client.get(f"/api/submissions/{submission_id}").json()
    files_payload = api_client.get(f"/api/submissions/{submission_id}/files").json()

    assert submission_payload["status"] == "awaiting_manual_review"
    assert submission_payload["review_stage"] == "desensitized_ready"
    assert submission_payload["report_ids"] == []
    assert submission_payload["case_ids"]

    case_id = submission_payload["case_ids"][0]
    case_before = api_client.get(f"/api/cases/{case_id}").json()
    assert case_before["status"] == "awaiting_manual_review"
    assert case_before["review_stage"] == "desensitized_ready"
    assert case_before["report_id"] == ""
    assert files_payload["files"]

    artifact_download = api_client.get(f"/downloads/materials/{files_payload['files'][0]['id']}/desensitized")
    assert artifact_download.status_code == 200
    assert artifact_download.content

    continue_response = api_client.post(
        f"/api/cases/{case_id}/continue-review",
        data={"corrected_by": "tester", "note": "desensitized confirmed"},
    )
    assert continue_response.status_code == 200
    continue_payload = continue_response.json()
    assert continue_payload["case"]["status"] == "completed"
    assert continue_payload["report"]["scope_id"] == case_id
    assert continue_payload["correction"]["correction_type"] == "continue_case_review_from_desensitized"

    submission_after = api_client.get(f"/api/submissions/{submission_id}").json()
    assert submission_after["status"] == "completed"
    assert submission_after["review_stage"] == "review_completed"
    assert submission_after["report_ids"]

    corrections = api_client.get(f"/api/submissions/{submission_id}/corrections").json()["corrections"]
    assert corrections[0]["correction_type"] == "continue_case_review_from_desensitized"


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.api
def test_manual_desensitized_review_accepts_uploaded_desensitized_package(api_client, mode_a_zip_path, tmp_path):
    submission_id = _create_submission(api_client, mode_a_zip_path, review_strategy="manual_desensitized_review")
    zip_path = _build_desensitized_zip(api_client, submission_id, tmp_path)

    with zip_path.open("rb") as handle:
        response = api_client.post(
            f"/api/submissions/{submission_id}/desensitized-package",
            files={"file": (zip_path.name, handle, "application/zip")},
            data={"corrected_by": "tester", "note": "upload reviewed package"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["matched_material_ids"]
    assert payload["submission"]["review_stage"] == "desensitized_uploaded"

    submission_after = api_client.get(f"/api/submissions/{submission_id}").json()
    assert submission_after["status"] == "awaiting_manual_review"
    assert submission_after["review_stage"] == "desensitized_uploaded"

    corrections = api_client.get(f"/api/submissions/{submission_id}/corrections").json()["corrections"]
    assert corrections[0]["correction_type"] == "upload_desensitized_package"
