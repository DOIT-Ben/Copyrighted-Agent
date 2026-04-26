from __future__ import annotations

import argparse
import json
import os
import re
import socket
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from wsgiref.simple_server import make_server

from app.core.privacy.desensitization import is_ai_safe_case_payload
from app.core.reviewers.ai.adapters import EXTERNAL_HTTP_REQUEST_VERSION, EXTERNAL_HTTP_RESPONSE_VERSION
from app.core.reviewers.ai.prompt_builder import build_ai_prompt_snapshot
from app.core.utils.text import ensure_dir, now_iso


@dataclass(frozen=True)
class MiniMaxBridgeSettings:
    host: str = "127.0.0.1"
    port: int = 18011
    endpoint_path: str = "/review"
    upstream_base_url: str = "https://api.minimaxi.com/v1"
    upstream_model: str = "minimax-m2.7-highspeed"
    upstream_api_key_env: str = "MINIMAX_API_KEY"
    request_log_path: str = ""
    strict_desensitized: bool = True
    timeout_seconds: int = 30


def validate_bridge_request_payload(payload_json: dict, settings: MiniMaxBridgeSettings) -> list[str]:
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


def _append_request_log(settings: MiniMaxBridgeSettings, record: dict) -> None:
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


def build_minimax_bridge_messages(payload_json: dict) -> list[dict[str, str]]:
    case_payload = dict(payload_json.get("case_payload") or {})
    rule_results = dict(payload_json.get("rule_results") or {})
    review_profile = dict(payload_json.get("review_profile") or {})
    requested_provider = str(payload_json.get("requested_provider") or "external_http")
    prompt_snapshot = dict(payload_json.get("prompt_snapshot") or {}) or build_ai_prompt_snapshot(
        case_payload,
        rule_results,
        review_profile,
        requested_provider=requested_provider,
    )
    return [
        {"role": "system", "content": str(prompt_snapshot.get("system_prompt") or "")},
        {"role": "user", "content": str(prompt_snapshot.get("user_prompt") or "")},
    ]


def _extract_json_object(text: str) -> dict:
    normalized = str(text or "").strip()
    if not normalized:
        raise RuntimeError("minimax_bridge_empty_content")

    fenced_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", normalized, flags=re.IGNORECASE | re.DOTALL)
    candidates: list[str] = []
    if fenced_match:
        candidates.append(fenced_match.group(1))
    candidates.append(normalized)

    first_brace = normalized.find("{")
    if first_brace >= 0:
        depth = 0
        for index in range(first_brace, len(normalized)):
            character = normalized[index]
            if character == "{":
                depth += 1
            elif character == "}":
                depth -= 1
                if depth == 0:
                    candidates.append(normalized[first_brace : index + 1])
                    break

    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload

    raise RuntimeError("minimax_bridge_invalid_model_json")


def _summary_from_model_payload(model_payload: dict, raw_content: str) -> str:
    candidates = [
        model_payload.get("summary"),
        model_payload.get("ai_note"),
        model_payload.get("message"),
        model_payload.get("analysis"),
        model_payload.get("result"),
        model_payload.get("conclusion"),
        model_payload.get("结论"),
        model_payload.get("总结"),
    ]
    for candidate in candidates:
        summary = str(candidate or "").strip()
        if summary:
            return summary
    return str(raw_content or "").strip()


def _coerce_message_content(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
                continue
            if not isinstance(item, dict):
                continue
            item_type = str(item.get("type") or "").strip().lower()
            if item_type in {"text", "output_text"}:
                parts.append(str(item.get("text") or item.get("content") or ""))
            elif "text" in item:
                parts.append(str(item.get("text") or ""))
        return "\n".join(part for part in parts if part).strip()
    return str(value or "").strip()


def _extract_minimax_message_content(response_json: dict) -> str:
    choices = list(response_json.get("choices") or [])
    if not choices:
        raise RuntimeError("minimax_bridge_missing_choices")
    first_choice = dict(choices[0] or {})
    message = dict(first_choice.get("message") or {})
    content = _coerce_message_content(message.get("content"))
    if content:
        return content
    delta = dict(first_choice.get("delta") or {})
    delta_content = _coerce_message_content(delta.get("content"))
    if delta_content:
        return delta_content
    raise RuntimeError("minimax_bridge_missing_content")


def request_minimax_chat_completion(payload_json: dict, settings: MiniMaxBridgeSettings) -> dict:
    api_key = str(os.getenv(settings.upstream_api_key_env, "") or "").strip() if settings.upstream_api_key_env else ""
    if settings.upstream_api_key_env and not api_key:
        raise RuntimeError("minimax_bridge_missing_api_key")

    upstream_url = f"{str(settings.upstream_base_url or '').rstrip('/')}/chat/completions"
    request_payload = {
        "model": settings.upstream_model,
        "messages": build_minimax_bridge_messages(payload_json),
        "stream": False,
    }
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    body = json.dumps(request_payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(upstream_url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=settings.timeout_seconds) as response:
            response_text = response.read().decode("utf-8", errors="ignore")
    except (TimeoutError, socket.timeout) as exc:
        raise RuntimeError("minimax_bridge_timeout") from exc
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"minimax_bridge_http_error:{exc.code}:{detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError("minimax_bridge_request_failed") from exc

    try:
        return json.loads(response_text or "{}")
    except json.JSONDecodeError as exc:
        raise RuntimeError("minimax_bridge_invalid_upstream_json") from exc


def build_bridge_response_payload(payload_json: dict, upstream_response_json: dict, *, provider_request_id: str = "") -> dict:
    content = _extract_minimax_message_content(upstream_response_json)
    resolution = "minimax_bridge_success"
    try:
        model_payload = _extract_json_object(content)
    except RuntimeError:
        model_payload = {}
        resolution = "minimax_bridge_text_fallback"

    summary = _summary_from_model_payload(model_payload, content)
    if not summary:
        raise RuntimeError("minimax_bridge_missing_summary")

    conclusion = str(model_payload.get("conclusion") or summary).strip() or summary
    resolution = str(model_payload.get("resolution") or resolution).strip() or resolution
    upstream_id = str(upstream_response_json.get("id") or provider_request_id or "").strip()
    return {
        "contract_version": EXTERNAL_HTTP_RESPONSE_VERSION,
        "provider_request_id": upstream_id,
        "status": "ok",
        "resolution": resolution,
        "conclusion": conclusion,
        "summary": summary,
    }


def build_minimax_bridge_app(settings: MiniMaxBridgeSettings):
    endpoint_path = str(settings.endpoint_path or "/review").strip() or "/review"
    if not endpoint_path.startswith("/"):
        endpoint_path = f"/{endpoint_path}"

    def _app(environ, start_response):
        request_path = str(environ.get("PATH_INFO") or "/")
        request_method = str(environ.get("REQUEST_METHOD") or "GET").upper()
        if request_path != endpoint_path:
            return _text_response(start_response, "404 Not Found", "bridge endpoint not found")
        if request_method != "POST":
            return _text_response(start_response, "405 Method Not Allowed", "only POST is supported")

        content_length = int(str(environ.get("CONTENT_LENGTH") or "0") or "0")
        body_bytes = environ["wsgi.input"].read(content_length) if content_length else b""
        try:
            payload_json = json.loads(body_bytes.decode("utf-8", errors="ignore") or "{}")
        except json.JSONDecodeError:
            payload = {
                "contract_version": EXTERNAL_HTTP_RESPONSE_VERSION,
                "status": "invalid_json",
                "error_code": "bridge_invalid_json",
                "summary": "Bridge could not decode request JSON.",
            }
            return _json_response(start_response, "400 Bad Request", payload)

        validation_errors = validate_bridge_request_payload(payload_json, settings)
        request_id = f"minimax-bridge-{uuid.uuid4().hex[:8]}"
        _append_request_log(
            settings,
            {
                "ts": now_iso(),
                "bridge_request_id": request_id,
                "validation_errors": validation_errors,
                "requested_provider": payload_json.get("requested_provider"),
                "model": settings.upstream_model,
                "upstream_base_url": settings.upstream_base_url,
            },
        )
        if validation_errors:
            payload = {
                "contract_version": EXTERNAL_HTTP_RESPONSE_VERSION,
                "provider_request_id": request_id,
                "status": "invalid_request",
                "error_code": "bridge_invalid_request",
                "summary": "Bridge rejected request because validation failed.",
                "validation_errors": validation_errors,
            }
            return _json_response(start_response, "422 Unprocessable Entity", payload)

        try:
            upstream_response_json = request_minimax_chat_completion(payload_json, settings)
            payload = build_bridge_response_payload(payload_json, upstream_response_json, provider_request_id=request_id)
            _append_request_log(
                settings,
                {
                    "ts": now_iso(),
                    "bridge_request_id": request_id,
                    "upstream_id": payload.get("provider_request_id", ""),
                    "status": payload.get("status", ""),
                    "resolution": payload.get("resolution", ""),
                },
            )
            return _json_response(start_response, "200 OK", payload)
        except Exception as exc:
            payload = {
                "contract_version": EXTERNAL_HTTP_RESPONSE_VERSION,
                "provider_request_id": request_id,
                "status": "bridge_error",
                "error_code": str(exc),
                "summary": "MiniMax bridge failed while calling the upstream model.",
            }
            _append_request_log(
                settings,
                {
                    "ts": now_iso(),
                    "bridge_request_id": request_id,
                    "status": "bridge_error",
                    "error_code": str(exc),
                },
            )
            return _json_response(start_response, "502 Bad Gateway", payload)

    return _app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local bridge from project external_http contract to MiniMax chat completions.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind.")
    parser.add_argument("--port", type=int, default=18011, help="Port to bind.")
    parser.add_argument("--endpoint-path", default="/review", help="Bridge endpoint path.")
    parser.add_argument("--upstream-base-url", default="https://api.minimaxi.com/v1", help="MiniMax OpenAI-compatible base URL.")
    parser.add_argument("--upstream-model", default="minimax-m2.7-highspeed", help="MiniMax model name.")
    parser.add_argument("--upstream-api-key-env", default="MINIMAX_API_KEY", help="Environment variable that stores the MiniMax API key.")
    parser.add_argument("--request-log-path", default="", help="Optional JSONL bridge request log path.")
    parser.add_argument("--timeout-seconds", type=int, default=30, help="Upstream timeout in seconds.")
    parser.add_argument("--allow-unsafe", action="store_true", help="Disable llm_safe validation in the bridge.")
    parser.add_argument("--once", action="store_true", help="Handle one request and exit.")
    args = parser.parse_args()

    settings = MiniMaxBridgeSettings(
        host=args.host,
        port=args.port,
        endpoint_path=args.endpoint_path,
        upstream_base_url=args.upstream_base_url,
        upstream_model=args.upstream_model,
        upstream_api_key_env=args.upstream_api_key_env,
        request_log_path=args.request_log_path,
        strict_desensitized=not args.allow_unsafe,
        timeout_seconds=args.timeout_seconds,
    )

    app = build_minimax_bridge_app(settings)
    with make_server(settings.host, settings.port, app) as server:
        print(
            f"minimax_bridge listening on http://{settings.host}:{settings.port}{settings.endpoint_path} "
            f"model={settings.upstream_model}"
        )
        if args.once:
            server.handle_request()
            return
        server.serve_forever()


if __name__ == "__main__":
    main()
