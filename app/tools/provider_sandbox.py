from __future__ import annotations

import argparse
import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from wsgiref.simple_server import make_server

from app.core.privacy.desensitization import is_ai_safe_case_payload
from app.core.reviewers.ai.adapters import EXTERNAL_HTTP_REQUEST_VERSION, EXTERNAL_HTTP_RESPONSE_VERSION
from app.core.utils.text import ensure_dir, now_iso


SANDBOX_MODES = {"success", "missing_summary", "invalid_json", "http_error"}


@dataclass(frozen=True)
class ProviderSandboxSettings:
    host: str = "127.0.0.1"
    port: int = 8010
    endpoint_path: str = "/review"
    mode: str = "success"
    request_log_path: str = ""
    require_auth_token: str = ""
    strict_desensitized: bool = True


def validate_sandbox_request_payload(payload_json: dict, settings: ProviderSandboxSettings) -> list[str]:
    errors: list[str] = []
    if str(payload_json.get("contract_version") or "").strip() != EXTERNAL_HTTP_REQUEST_VERSION:
        errors.append("contract_version_mismatch")
    if not str(payload_json.get("requested_provider") or "").strip():
        errors.append("requested_provider_missing")
    if not str(payload_json.get("model") or "").strip():
        errors.append("model_missing")

    privacy_guard = payload_json.get("privacy_guard") or {}
    case_payload = payload_json.get("case_payload") or {}
    if settings.strict_desensitized:
        if not bool(privacy_guard.get("require_desensitized")):
            errors.append("privacy_guard_require_desensitized_false")
        if not bool(privacy_guard.get("payload_marked_llm_safe")):
            errors.append("privacy_guard_payload_not_marked_safe")
        if not is_ai_safe_case_payload(case_payload):
            errors.append("case_payload_not_ai_safe")
    return errors


def build_sandbox_response_payload(payload_json: dict, *, mode: str, provider_request_id: str) -> dict:
    issues = (payload_json.get("rule_results") or {}).get("issues", [])
    case_payload = payload_json.get("case_payload") or {}
    base_payload = {
        "contract_version": EXTERNAL_HTTP_RESPONSE_VERSION,
        "provider_request_id": provider_request_id,
        "status": "ok",
        "resolution": "sandbox_completed",
        "conclusion": f"Sandbox accepted request with {len(issues)} rule issues.",
        "summary": f"Sandbox accepted llm_safe={case_payload.get('llm_safe')} issues={len(issues)}.",
    }
    if mode == "missing_summary":
        base_payload.pop("summary", None)
    return base_payload


def _append_request_log(settings: ProviderSandboxSettings, record: dict) -> None:
    if not settings.request_log_path:
        return
    target = Path(settings.request_log_path)
    ensure_dir(target.parent)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _json_response(start_response, status: str, payload: dict) -> list[bytes]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    start_response(status, [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(body)))])
    return [body]


def _text_response(start_response, status: str, text: str, content_type: str = "text/plain; charset=utf-8") -> list[bytes]:
    body = text.encode("utf-8")
    start_response(status, [("Content-Type", content_type), ("Content-Length", str(len(body)))])
    return [body]


def build_provider_sandbox_app(settings: ProviderSandboxSettings):
    endpoint_path = str(settings.endpoint_path or "/review").strip() or "/review"
    if not endpoint_path.startswith("/"):
        endpoint_path = f"/{endpoint_path}"

    def _app(environ, start_response):
        request_path = str(environ.get("PATH_INFO") or "/")
        request_method = str(environ.get("REQUEST_METHOD") or "GET").upper()
        if request_path != endpoint_path:
            return _text_response(start_response, "404 Not Found", "sandbox endpoint not found")
        if request_method != "POST":
            return _text_response(start_response, "405 Method Not Allowed", "only POST is supported")

        if settings.require_auth_token:
            authorization = str(environ.get("HTTP_AUTHORIZATION") or "").strip()
            expected = f"Bearer {settings.require_auth_token}"
            if authorization != expected:
                payload = {
                    "contract_version": EXTERNAL_HTTP_RESPONSE_VERSION,
                    "status": "unauthorized",
                    "error_code": "sandbox_auth_required",
                    "summary": "Sandbox rejected request because Authorization header is missing or invalid.",
                }
                return _json_response(start_response, "401 Unauthorized", payload)

        content_length = int(str(environ.get("CONTENT_LENGTH") or "0") or "0")
        body_bytes = environ["wsgi.input"].read(content_length) if content_length else b""

        if settings.mode == "invalid_json":
            return _text_response(start_response, "200 OK", "not-json", "application/json; charset=utf-8")

        try:
            payload_json = json.loads(body_bytes.decode("utf-8", errors="ignore") or "{}")
        except json.JSONDecodeError:
            payload = {
                "contract_version": EXTERNAL_HTTP_RESPONSE_VERSION,
                "status": "invalid_json",
                "error_code": "sandbox_invalid_json",
                "summary": "Sandbox could not decode request JSON.",
            }
            return _json_response(start_response, "400 Bad Request", payload)

        validation_errors = validate_sandbox_request_payload(payload_json, settings)
        provider_request_id = f"sandbox-{uuid.uuid4().hex[:8]}"
        _append_request_log(
            settings,
            {
                "ts": now_iso(),
                "provider_request_id": provider_request_id,
                "mode": settings.mode,
                "validation_errors": validation_errors,
                "payload": payload_json,
            },
        )

        if validation_errors:
            payload = {
                "contract_version": EXTERNAL_HTTP_RESPONSE_VERSION,
                "provider_request_id": provider_request_id,
                "status": "invalid_request",
                "error_code": "sandbox_invalid_request",
                "summary": "Sandbox rejected request because validation failed.",
                "validation_errors": validation_errors,
            }
            return _json_response(start_response, "422 Unprocessable Entity", payload)

        if settings.mode == "http_error":
            payload = {
                "contract_version": EXTERNAL_HTTP_RESPONSE_VERSION,
                "provider_request_id": provider_request_id,
                "status": "http_error",
                "error_code": "sandbox_http_error",
                "summary": "Sandbox intentionally returned an HTTP error for fallback validation.",
            }
            return _json_response(start_response, "503 Service Unavailable", payload)

        payload = build_sandbox_response_payload(payload_json, mode=settings.mode, provider_request_id=provider_request_id)
        return _json_response(start_response, "200 OK", payload)

    return _app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local external_http provider sandbox.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind.")
    parser.add_argument("--port", type=int, default=8010, help="Port to bind.")
    parser.add_argument("--endpoint-path", default="/review", help="Review endpoint path.")
    parser.add_argument("--mode", choices=sorted(SANDBOX_MODES), default="success", help="Response mode.")
    parser.add_argument("--request-log-path", default="", help="Optional JSONL request log path.")
    parser.add_argument("--require-auth-token", default="", help="Optional bearer token expected by the sandbox.")
    parser.add_argument("--allow-unsafe", action="store_true", help="Disable llm_safe validation in sandbox.")
    parser.add_argument("--once", action="store_true", help="Handle one request and exit.")
    args = parser.parse_args()

    settings = ProviderSandboxSettings(
        host=args.host,
        port=args.port,
        endpoint_path=args.endpoint_path,
        mode=args.mode,
        request_log_path=args.request_log_path,
        require_auth_token=args.require_auth_token,
        strict_desensitized=not args.allow_unsafe,
    )

    app = build_provider_sandbox_app(settings)
    with make_server(settings.host, settings.port, app) as server:
        print(f"provider_sandbox listening on http://{settings.host}:{settings.port}{settings.endpoint_path} mode={settings.mode}")
        if args.once:
            server.handle_request()
            return
        server.serve_forever()


if __name__ == "__main__":
    main()
