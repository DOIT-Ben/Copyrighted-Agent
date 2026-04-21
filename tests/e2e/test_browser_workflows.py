from __future__ import annotations

from contextlib import contextmanager
import io
import json
import threading
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from wsgiref.simple_server import make_server


def _multipart_request_body(file_field: str, file_path: Path, extra_fields: dict[str, str]) -> tuple[bytes, str]:
    boundary = "----SoftReviewBoundary7MA4YWxkTrZu0gW"
    parts: list[bytes] = []

    for key, value in extra_fields.items():
        parts.append(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{key}"\r\n\r\n'
                f"{value}\r\n"
            ).encode("utf-8")
        )

    payload = file_path.read_bytes()
    parts.append(
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{file_field}"; filename="{file_path.name}"\r\n'
            "Content-Type: application/zip\r\n\r\n"
        ).encode("utf-8")
        + payload
        + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def _request(url: str, method: str = "GET", *, body: bytes | None = None, headers: dict[str, str] | None = None) -> dict:
    request = urllib.request.Request(url, data=body, headers=headers or {}, method=method)
    with urllib.request.urlopen(request, timeout=15) as response:
        payload = response.read()
        return {
            "status": response.status,
            "url": response.geturl(),
            "body": payload,
            "text": payload.decode("utf-8", errors="ignore"),
            "headers": dict(response.headers.items()),
        }


def _post_form(url: str, data: dict[str, str]) -> dict:
    body = urllib.parse.urlencode(data).encode("utf-8")
    return _request(
        url,
        method="POST",
        body=body,
        headers={"Content-Type": "application/x-www-form-urlencoded; charset=utf-8"},
    )


def _build_desensitized_zip_payload(live_server_url: str, submission_id: str) -> tuple[bytes, str]:
    files_payload = json.loads(_request(f"{live_server_url}/api/submissions/{submission_id}/files")["body"])
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for item in files_payload["files"]:
            artifact = _request(f"{live_server_url}/downloads/materials/{item['id']}/desensitized")
            archive.writestr(f"{item['original_filename']}.desensitized.txt", artifact["body"])
    temp_path = Path("desensitized_package.zip")
    temp_path.write_bytes(buffer.getvalue())
    try:
        return _multipart_request_body("file", temp_path, {})
    finally:
        temp_path.unlink(missing_ok=True)


@contextmanager
def _live_server_url():
    from app.api.main import create_app

    server = make_server("127.0.0.1", 0, create_app(testing=True))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_browser_mode_a_workflow_covers_upload_correction_report_and_ops(mode_a_zip_path):
    with _live_server_url() as live_server_url:
        upload_body, content_type = _multipart_request_body(
            file_field="file",
            file_path=mode_a_zip_path,
            extra_fields={"mode": "single_case_package"},
        )
        upload_response = _request(
            f"{live_server_url}/upload",
            method="POST",
            body=upload_body,
            headers={"Content-Type": content_type},
        )

        assert upload_response["status"] == 200
        assert "/submissions/" in upload_response["url"]

        submission_id = upload_response["url"].rstrip("/").rsplit("/", 1)[-1]
        submission_payload = json.loads(_request(f"{live_server_url}/api/submissions/{submission_id}")["body"])
        files_payload = json.loads(_request(f"{live_server_url}/api/submissions/{submission_id}/files")["body"])

        material_id = files_payload["files"][0]["id"]
        case_id = submission_payload["case_ids"][0]
        report_id = submission_payload["report_ids"][0]

        change_response = _post_form(
            f"{live_server_url}/submissions/{submission_id}/actions/change-type",
            {"material_id": material_id, "material_type": "agreement", "note": "browser e2e"},
        )
        assert change_response["status"] == 200
        assert "notice=material_type_updated" in change_response["url"]

        rerun_response = _post_form(
            f"{live_server_url}/submissions/{submission_id}/actions/rerun-review",
            {"case_id": case_id, "note": "browser e2e rerun"},
        )
        assert rerun_response["status"] == 200
        assert "notice=case_review_rerun" in rerun_response["url"]

        report_response = _request(f"{live_server_url}/reports/{report_id}")
        assert report_response["status"] == 200
        assert report_id in report_response["text"]

        log_download = _request(f"{live_server_url}/downloads/logs/app")
        assert log_download["status"] == 200
        assert b"download_app_log" in log_download["body"] or b"upload_submission_html" in log_download["body"]

        ops_response = _request(f"{live_server_url}/ops")
        assert ops_response["status"] == 200
        assert "/downloads/logs/app" in ops_response["text"]
        assert "/downloads/ops/delivery-closeout/latest-json" in ops_response["text"]


def test_browser_mode_b_workflow_supports_case_regroup_after_batch_upload(mode_b_ambiguous_zip_path):
    with _live_server_url() as live_server_url:
        upload_body, content_type = _multipart_request_body(
            file_field="file",
            file_path=mode_b_ambiguous_zip_path,
            extra_fields={"mode": "batch_same_material"},
        )
        upload_response = _request(
            f"{live_server_url}/upload",
            method="POST",
            body=upload_body,
            headers={"Content-Type": content_type},
        )

        assert upload_response["status"] == 200
        assert "/submissions/" in upload_response["url"]

        submission_id = upload_response["url"].rstrip("/").rsplit("/", 1)[-1]
        files_payload = json.loads(_request(f"{live_server_url}/api/submissions/{submission_id}/files")["body"])
        material_ids = [item["id"] for item in files_payload["files"]]

        create_a = _post_form(
            f"{live_server_url}/submissions/{submission_id}/actions/create-case",
            {
                "material_ids": material_ids[0],
                "case_name": "妯″紡B椤圭洰A",
                "version": "V1.0",
                "company_name": "娴嬭瘯鍏徃A",
                "note": "browser e2e create a",
            },
        )
        assert create_a["status"] == 200
        assert "notice=case_created" in create_a["url"]

        create_b = _post_form(
            f"{live_server_url}/submissions/{submission_id}/actions/create-case",
            {
                "material_ids": material_ids[1],
                "case_name": "妯″紡B椤圭洰B",
                "version": "V1.0",
                "company_name": "娴嬭瘯鍏徃B",
                "note": "browser e2e create b",
            },
        )
        assert create_b["status"] == 200

        submission_after_create = json.loads(_request(f"{live_server_url}/api/submissions/{submission_id}")["body"])
        case_ids = submission_after_create["case_ids"]
        assert len(case_ids) == 2

        merge_response = _post_form(
            f"{live_server_url}/submissions/{submission_id}/actions/merge-cases",
            {
                "source_case_id": case_ids[1],
                "target_case_id": case_ids[0],
                "note": "browser e2e merge",
            },
        )
        assert merge_response["status"] == 200
        assert "notice=cases_merged" in merge_response["url"]

        rerun_response = _post_form(
            f"{live_server_url}/submissions/{submission_id}/actions/rerun-review",
            {"case_id": case_ids[0], "note": "browser e2e rerun mode b"},
        )
        assert rerun_response["status"] == 200
        assert "notice=case_review_rerun" in rerun_response["url"]

        submission_after_merge = json.loads(_request(f"{live_server_url}/api/submissions/{submission_id}")["body"])
        assert submission_after_merge["case_ids"] == [case_ids[0]]

        case_page = _request(f"{live_server_url}/cases/{case_ids[0]}")
        assert case_page["status"] == 200


def test_browser_manual_desensitized_workflow_supports_upload_and_continue(mode_a_zip_path):
    with _live_server_url() as live_server_url:
        upload_body, content_type = _multipart_request_body(
            file_field="file",
            file_path=mode_a_zip_path,
            extra_fields={
                "mode": "single_case_package",
                "review_strategy": "manual_desensitized_review",
            },
        )
        upload_response = _request(
            f"{live_server_url}/upload",
            method="POST",
            body=upload_body,
            headers={"Content-Type": content_type},
        )

        assert upload_response["status"] == 200
        assert "/submissions/" in upload_response["url"]

        submission_id = upload_response["url"].rstrip("/").rsplit("/", 1)[-1]
        submission_payload = json.loads(_request(f"{live_server_url}/api/submissions/{submission_id}")["body"])

        assert submission_payload["status"] == "awaiting_manual_review"
        assert submission_payload["review_stage"] == "desensitized_ready"
        assert submission_payload["case_ids"]
        assert submission_payload["report_ids"] == []

        case_id = submission_payload["case_ids"][0]

        operator_page = _request(f"{live_server_url}/submissions/{submission_id}/operator")
        assert operator_page["status"] == 200
        assert f"/submissions/{submission_id}/actions/upload-desensitized-package" in operator_page["text"]
        assert f"/submissions/{submission_id}/actions/continue-review" in operator_page["text"]

        package_body, package_content_type = _build_desensitized_zip_payload(live_server_url, submission_id)
        upload_package_response = _request(
            f"{live_server_url}/submissions/{submission_id}/actions/upload-desensitized-package",
            method="POST",
            body=package_body,
            headers={"Content-Type": package_content_type},
        )

        assert upload_package_response["status"] == 200
        assert "notice=desensitized_package_uploaded" in upload_package_response["url"]

        submission_after_upload = json.loads(_request(f"{live_server_url}/api/submissions/{submission_id}")["body"])
        assert submission_after_upload["status"] == "awaiting_manual_review"
        assert submission_after_upload["review_stage"] == "desensitized_uploaded"

        continue_response = _post_form(
            f"{live_server_url}/submissions/{submission_id}/actions/continue-review",
            {"case_id": case_id, "note": "browser manual continue"},
        )
        assert continue_response["status"] == 200
        assert "notice=case_review_continued" in continue_response["url"]

        submission_after_continue = json.loads(_request(f"{live_server_url}/api/submissions/{submission_id}")["body"])
        assert submission_after_continue["status"] == "completed"
        assert submission_after_continue["review_stage"] == "review_completed"
        assert submission_after_continue["report_ids"]
