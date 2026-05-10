from __future__ import annotations

import io

import pytest


@pytest.mark.unit
@pytest.mark.contract
def test_wsgi_multipart_upload_populates_form_data_and_files():
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse

    app = FastAPI()

    @app.post("/echo")
    def echo(request: Request):
        upload = request.files["file"]
        return JSONResponse(
            {
                "mode": request.form_data["mode"],
                "filename": upload.filename,
                "content_type": upload.content_type,
                "content": upload.read().decode("utf-8"),
            }
        )

    boundary = "----soft-review-test-boundary"
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="mode"\r\n'
        "\r\n"
        "single_case_package\r\n"
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="demo.txt"\r\n'
        "Content-Type: text/plain\r\n"
        "\r\n"
        "hello upload\r\n"
        f"--{boundary}--\r\n"
    ).encode("utf-8")
    environ = {
        "REQUEST_METHOD": "POST",
        "PATH_INFO": "/echo",
        "QUERY_STRING": "",
        "CONTENT_TYPE": f"multipart/form-data; boundary={boundary}",
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": io.BytesIO(body),
    }
    response_meta = {}

    def start_response(status, headers):
        response_meta["status"] = status
        response_meta["headers"] = headers

    response_body = b"".join(app(environ, start_response))

    assert response_meta["status"].startswith("200")
    assert b'"mode": "single_case_package"' in response_body
    assert b'"filename": "demo.txt"' in response_body
    assert b'"content": "hello upload"' in response_body
