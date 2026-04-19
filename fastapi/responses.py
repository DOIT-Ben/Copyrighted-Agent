from __future__ import annotations

import json


class Response:
    media_type = "text/plain; charset=utf-8"

    def __init__(self, content="", status_code: int = 200, headers: dict | None = None):
        self.status_code = status_code
        self.headers = headers or {}
        self.body = content.encode("utf-8") if isinstance(content, str) else content

    @property
    def content(self) -> bytes:
        return self.body

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="ignore")

    def json(self):
        return json.loads(self.text or "{}")


class HTMLResponse(Response):
    media_type = "text/html; charset=utf-8"


class PlainTextResponse(Response):
    media_type = "text/plain; charset=utf-8"


class JSONResponse(Response):
    media_type = "application/json; charset=utf-8"

    def __init__(self, content=None, status_code: int = 200, headers: dict | None = None):
        payload = json.dumps(content or {}, ensure_ascii=False)
        super().__init__(payload, status_code=status_code, headers=headers)


class RedirectResponse(Response):
    media_type = "text/plain; charset=utf-8"

    def __init__(self, location: str, status_code: int = 302, headers: dict | None = None):
        merged_headers = {"Location": location}
        if headers:
            merged_headers.update(headers)
        super().__init__("", status_code=status_code, headers=merged_headers)
