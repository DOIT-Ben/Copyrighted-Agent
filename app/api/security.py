from __future__ import annotations

import hmac
import re
import secrets
from urllib.parse import quote

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response


CSRF_FIELD_NAME = "csrf_token"
CSRF_HEADER_NAME = "x-csrf-token"
SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'"
    ),
    "Referrer-Policy": "same-origin",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}
POST_FORM_PATTERN = re.compile(
    r"(<form\b(?=[^>]*\bmethod=[\"']post[\"'])[^>]*>)(.*?</form>)",
    re.IGNORECASE | re.DOTALL,
)


def _request_header(request: Request, name: str) -> str:
    target = name.lower()
    for key, value in (request.headers or {}).items():
        if str(key).lower() == target:
            return str(value)
    return ""


def _csrf_token_input(token: str) -> str:
    return f'<input type="hidden" name="{CSRF_FIELD_NAME}" value="{quote(token, safe="")}">'


def _inject_csrf_tokens(html: str, token: str) -> str:
    if not token:
        return html

    def replace(match: re.Match[str]) -> str:
        opening_tag = match.group(1)
        form_body = match.group(2)
        if f'name="{CSRF_FIELD_NAME}"' in form_body or f"name='{CSRF_FIELD_NAME}'" in form_body:
            return match.group(0)
        return opening_tag + "\n        " + _csrf_token_input(token) + form_body

    return POST_FORM_PATTERN.sub(replace, html)


def _apply_security_headers(response: Response) -> Response:
    for key, value in SECURITY_HEADERS.items():
        response.headers.setdefault(key, value)
    return response


def _requires_csrf(path: str) -> bool:
    return path == "/upload" or (
        path.startswith("/submissions/") and ("/actions/" in path or "/review-rules/" in path)
    )


def _validate_csrf_request(request: Request) -> Response | None:
    if request.method != "POST" or not getattr(request.app, "csrf_enforced", True):
        return None
    if not _requires_csrf(request.path):
        return None
    expected = str(getattr(request.app, "csrf_token", "") or "")
    provided = str(request.form_data.get(CSRF_FIELD_NAME, "") or _request_header(request, CSRF_HEADER_NAME))
    if expected and hmac.compare_digest(provided, expected):
        return None
    return JSONResponse({"detail": "CSRF token missing or invalid"}, status_code=403)


def _harden_response(request: Request, response: Response) -> Response:
    token = str(getattr(request.app, "csrf_token", "") or "")
    media_type = str(getattr(response, "media_type", "") or "")
    if response.status_code == 200 and media_type.startswith("text/html"):
        html = response.body.decode("utf-8", errors="ignore")
        response.body = _inject_csrf_tokens(html, token).encode("utf-8")
    return _apply_security_headers(response)


def configure_security(app: FastAPI, *, testing: bool = False) -> None:
    app.csrf_token = secrets.token_urlsafe(32)
    app.csrf_enforced = not testing
    app.add_before_request_hook(_validate_csrf_request)
    app.add_after_response_hook(_harden_response)
