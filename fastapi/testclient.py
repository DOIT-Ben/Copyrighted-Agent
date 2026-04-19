from __future__ import annotations

from dataclasses import dataclass


@dataclass
class _UploadedFile:
    filename: str
    content: bytes
    content_type: str = "application/octet-stream"


class TestClient:
    def __init__(self, app):
        self.app = app

    def get(self, path: str, headers: dict | None = None):
        return self.app.handle_request("GET", path, headers=headers or {})

    def post(self, path: str, data: dict | None = None, files: dict | None = None, headers: dict | None = None):
        prepared_files = {}
        if files:
            for key, value in files.items():
                filename, file_obj, content_type = value
                prepared_files[key] = _UploadedFile(
                    filename=filename,
                    content=file_obj.read(),
                    content_type=content_type,
                )
        return self.app.handle_request(
            "POST",
            path,
            headers=headers or {},
            form_data=data or {},
            files=prepared_files,
        )

