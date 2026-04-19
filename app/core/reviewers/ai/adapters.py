from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request

from app.core.services.app_config import AppConfig

EXTERNAL_HTTP_REQUEST_VERSION = "soft_review.external_http.v1"
EXTERNAL_HTTP_RESPONSE_VERSION = "soft_review.external_http.v1"


def build_rule_summary(rule_results: dict) -> str:
    issues = rule_results.get("issues", [])
    return f"规则引擎共发现 {len(issues)} 个问题，当前以规则结论为主。"


def review_with_safe_stub(case_payload: dict, rule_results: dict, requested_provider: str) -> dict:
    issues = rule_results.get("issues", [])
    rule_summary = build_rule_summary(rule_results)
    return {
        "provider": "safe_stub",
        "requested_provider": requested_provider,
        "resolution": "non_mock_safe_payload",
        "conclusion": rule_summary,
        "rule_summary": rule_summary,
        "summary": f"Stub provider received llm_safe={case_payload.get('llm_safe')} and {len(issues)} rule issues.",
        "ai_note": "当前为本地 safe_stub，仅验证真实 provider 接口边界，不向外发送原文。",
        "issues": issues,
    }


def build_external_http_request_payload(case_payload: dict, rule_results: dict, requested_provider: str, config: AppConfig) -> dict:
    return {
        "contract_version": EXTERNAL_HTTP_REQUEST_VERSION,
        "requested_provider": requested_provider,
        "model": config.ai_model,
        "timeout_seconds": config.ai_timeout_seconds,
        "privacy_guard": {
            "require_desensitized": config.ai_require_desensitized,
            "payload_marked_llm_safe": bool(case_payload.get("llm_safe")),
        },
        "case_payload": case_payload,
        "rule_results": rule_results,
    }


def external_http_error_code(exc: Exception) -> str:
    if isinstance(exc, TimeoutError):
        return "external_http_timeout"
    if isinstance(exc, urllib.error.HTTPError):
        return "external_http_http_error"
    if isinstance(exc, urllib.error.URLError):
        return "external_http_request_failed"
    if isinstance(exc, json.JSONDecodeError):
        return "external_http_invalid_json"
    return "external_http_unknown_error"


def normalize_external_http_response(payload_json: dict, rule_results: dict, requested_provider: str, config: AppConfig) -> dict:
    issues = rule_results.get("issues", [])
    rule_summary = build_rule_summary(rule_results)
    contract_version = str(payload_json.get("contract_version") or EXTERNAL_HTTP_RESPONSE_VERSION).strip()
    ai_summary = str(payload_json.get("summary") or payload_json.get("ai_note") or "").strip()
    if not ai_summary:
        raise RuntimeError("external_http_missing_summary")

    conclusion = str(payload_json.get("conclusion") or rule_summary).strip() or rule_summary
    resolution = str(payload_json.get("resolution") or "external_http_success").strip() or "external_http_success"
    return {
        "provider": "external_http",
        "requested_provider": requested_provider,
        "resolution": resolution,
        "conclusion": conclusion,
        "rule_summary": rule_summary,
        "summary": ai_summary,
        "ai_note": ai_summary,
        "issues": issues,
        "timeout_seconds": config.ai_timeout_seconds,
        "contract_version": contract_version,
        "provider_request_id": str(payload_json.get("provider_request_id") or "").strip(),
        "provider_status": str(payload_json.get("status") or "ok").strip() or "ok",
    }


def review_with_external_http(case_payload: dict, rule_results: dict, requested_provider: str, config: AppConfig) -> dict:
    endpoint = str(config.ai_endpoint or "").strip()
    if not endpoint:
        raise RuntimeError("external_http_missing_endpoint")

    payload = build_external_http_request_payload(case_payload, rule_results, requested_provider, config)
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if config.ai_api_key_env:
        api_key = os.getenv(config.ai_api_key_env, "").strip()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

    request = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=config.ai_timeout_seconds) as response:
            response_text = response.read().decode("utf-8", errors="ignore")
    except (TimeoutError, socket.timeout) as exc:
        raise TimeoutError("external_http_timeout") from exc
    except urllib.error.HTTPError as exc:
        raise RuntimeError("external_http_http_error") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError("external_http_request_failed") from exc

    try:
        payload_json = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("external_http_invalid_json") from exc

    return normalize_external_http_response(payload_json, rule_results, requested_provider, config)
