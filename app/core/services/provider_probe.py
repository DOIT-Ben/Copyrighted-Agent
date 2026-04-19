from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from app.core.privacy.desensitization import build_ai_safe_case_payload
from app.core.reviewers.ai.adapters import (
    build_external_http_request_payload,
    external_http_error_code,
    normalize_external_http_response,
)
from app.core.services.app_config import AppConfig, load_app_config
from app.core.services.app_logging import log_event
from app.core.utils.text import ensure_dir, now_iso


PROVIDER_PROBE_ARTIFACT_NAME = "provider_probe_latest.json"
PROVIDER_PROBE_HISTORY_DIR_NAME = "provider_probe_history"
PROVIDER_PROBE_HISTORY_STEM = "provider_probe"
PROVIDER_PROBE_MEDIA_TYPE = "application/json; charset=utf-8"


def build_provider_probe_request_payload(config: AppConfig, requested_provider: str | None = None) -> dict:
    provider_name = str(requested_provider or config.ai_provider or "external_http").strip().lower() or "external_http"
    safe_case_payload = build_ai_safe_case_payload(
        {
            "software_name": "provider_probe_sample",
            "version": "V1.0",
            "company_name": "provider_probe_org",
        }
    )
    rule_results = {
        "issues": [
            {
                "code": "provider_probe_sample",
                "severity": "minor",
                "message": "Synthetic llm_safe probe payload for contract validation.",
            }
        ]
    }
    return build_external_http_request_payload(safe_case_payload, rule_results, provider_name, config)


def summarize_provider_probe_request(request_payload: dict) -> dict:
    case_payload = dict(request_payload.get("case_payload", {}) or {})
    privacy_guard = dict(request_payload.get("privacy_guard", {}) or {})
    rule_results = dict(request_payload.get("rule_results", {}) or {})
    issues = list(rule_results.get("issues", []) or [])
    non_empty_case_fields = sorted(key for key, value in case_payload.items() if str(value or "").strip())
    return {
        "probe_kind": "synthetic_safe_probe",
        "contract_version": str(request_payload.get("contract_version", "") or ""),
        "requested_provider": str(request_payload.get("requested_provider", "") or ""),
        "model": str(request_payload.get("model", "") or ""),
        "timeout_seconds": int(request_payload.get("timeout_seconds", 0) or 0),
        "privacy_guard": {
            "require_desensitized": bool(privacy_guard.get("require_desensitized", False)),
            "payload_marked_llm_safe": bool(privacy_guard.get("payload_marked_llm_safe", False)),
        },
        "case_payload_keys": sorted(str(key) for key in case_payload.keys()),
        "non_empty_case_fields": non_empty_case_fields,
        "privacy_policy": str(case_payload.get("privacy_policy", "") or ""),
        "llm_safe": bool(case_payload.get("llm_safe", False)),
        "rule_issue_count": len(issues),
        "rule_issue_codes": [str(item.get("code", "") or "") for item in issues if str(item.get("code", "")).strip()],
        "contains_raw_user_material": False,
        "authorization_header_used": False,
    }


def _check_record(name: str, label: str, status: str, detail: str, value: str = "") -> dict:
    return {
        "name": name,
        "label": label,
        "status": status,
        "detail": detail,
        "value": value,
    }


def _blocking_label(name: str) -> str:
    mapping = {
        "ai_enabled": "AI enabled",
        "endpoint": "endpoint",
        "model": "model",
        "api_key_env": "API key env",
        "desensitized_boundary": "desensitized boundary",
    }
    return mapping.get(name, name.replace("_", " "))


def _provider_probe_artifact_path(config_or_root: AppConfig | str | Path | None = None) -> Path:
    target = _provider_probe_ops_dir(config_or_root) / PROVIDER_PROBE_ARTIFACT_NAME
    ensure_dir(target.parent)
    return target


def _provider_probe_data_root(config_or_root: AppConfig | str | Path | None = None) -> Path:
    if isinstance(config_or_root, AppConfig):
        return Path(config_or_root.data_root)
    if config_or_root is None:
        return Path(load_app_config().data_root)
    return Path(config_or_root)


def _provider_probe_ops_dir(config_or_root: AppConfig | str | Path | None = None) -> Path:
    target = _provider_probe_data_root(config_or_root) / "ops"
    ensure_dir(target)
    return target


def _provider_probe_history_dir(config_or_root: AppConfig | str | Path | None = None) -> Path:
    target = _provider_probe_ops_dir(config_or_root) / PROVIDER_PROBE_HISTORY_DIR_NAME
    ensure_dir(target)
    return target


def _provider_probe_history_path(
    config_or_root: AppConfig | str | Path | None = None,
    *,
    generated_at: str = "",
    history_dir: str | Path | None = None,
) -> Path:
    target_dir = Path(history_dir) if history_dir else _provider_probe_history_dir(config_or_root)
    ensure_dir(target_dir)
    timestamp_text = "".join(character for character in str(generated_at or now_iso()) if character.isdigit())
    if len(timestamp_text) >= 14:
        stamp = f"{timestamp_text[:8]}_{timestamp_text[8:14]}"
    else:
        stamp = timestamp_text or "latest"
    return target_dir / f"{PROVIDER_PROBE_HISTORY_STEM}_{stamp}.json"


def _iso_from_timestamp(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp).isoformat(timespec="seconds")


def _safe_log_event(event_type: str, payload: dict[str, Any]) -> None:
    try:
        log_event(event_type, payload)
    except OSError:
        return


def _readiness_phase(
    *,
    provider_name: str,
    ai_enabled: bool,
    endpoint: str,
    model: str,
    api_key_env: str,
    api_key_present: bool,
    require_desensitized: bool,
) -> tuple[str, list[str]]:
    if provider_name == "mock":
        return "mock_mode", []
    if provider_name != "external_http":
        return "provider_no_probe_required", []

    blocking_items: list[str] = []
    has_any_provider_config = bool(endpoint or model or api_key_env)
    if not require_desensitized:
        blocking_items.append("desensitized_boundary")
    if not ai_enabled:
        blocking_items.append("ai_enabled")
    if not endpoint:
        blocking_items.append("endpoint")
    if not model:
        blocking_items.append("model")
    if api_key_env and not api_key_present:
        blocking_items.append("api_key_env")

    if not ai_enabled and not has_any_provider_config:
        return "disabled", blocking_items
    if not ai_enabled:
        return "configured_disabled", blocking_items
    if not has_any_provider_config:
        return "not_configured", blocking_items
    if blocking_items:
        return "partially_configured", blocking_items
    return "ready_for_probe", blocking_items


def _readiness_summary(provider_name: str, phase: str, blocking_items: list[str]) -> str:
    if phase == "mock_mode":
        return "Current provider is mock; live external_http probe is not required."
    if phase == "provider_no_probe_required":
        return f"Current provider is {provider_name}; live external_http probe is not required."
    if phase == "disabled":
        return "external_http probe is disabled and provider config is still missing."
    if phase == "configured_disabled":
        return "external_http settings exist, but AI is disabled so probe is blocked."
    if phase == "not_configured":
        return "external_http is selected, but provider configuration is still missing."
    if phase == "partially_configured":
        missing = ", ".join(_blocking_label(item) for item in blocking_items) or "configuration"
        return f"external_http is partially configured: {missing}."
    return "external_http configuration is ready for a safe probe."


def _readiness_recommended_action(phase: str, blocking_items: list[str]) -> str:
    if phase == "mock_mode":
        return r"Keep mock mode for normal local work, or create config\local.json / env overrides and switch ai_provider to external_http when you are ready for a live probe."
    if phase == "provider_no_probe_required":
        return "Use the current provider as configured, or switch to external_http only if you need gateway smoke validation."
    if phase in {"disabled", "configured_disabled"}:
        return "Enable AI and keep the desensitized boundary on before running a live provider probe."
    if phase == "not_configured":
        return "Create config/local.json or env overrides for ai_endpoint and ai_model before running provider_probe."
    if phase == "partially_configured":
        missing = ", ".join(_blocking_label(item) for item in blocking_items) or "provider configuration"
        return f"Complete the missing requirements: {missing}."
    return r"Run py -m app.tools.provider_probe --config config\local.json --probe when you are ready."


def evaluate_provider_readiness(config: AppConfig, environ: Mapping[str, str] | None = None) -> dict:
    env = environ or os.environ
    provider_name = str(config.ai_provider or "mock").strip().lower() or "mock"
    endpoint = str(config.ai_endpoint or "").strip()
    model = str(config.ai_model or "").strip()
    api_key_env = str(config.ai_api_key_env or "").strip()
    api_key_value = str(env.get(api_key_env, "") or "").strip() if api_key_env else ""
    api_key_present = bool(api_key_value)
    phase, blocking_items = _readiness_phase(
        provider_name=provider_name,
        ai_enabled=config.ai_enabled,
        endpoint=endpoint,
        model=model,
        api_key_env=api_key_env,
        api_key_present=api_key_present,
        require_desensitized=config.ai_require_desensitized,
    )

    checks: list[dict] = []
    checks.append(
        _check_record(
            "ai_enabled",
            "AI Enabled",
            "ok" if config.ai_enabled or provider_name != "external_http" else "warning",
            "AI provider calls are enabled."
            if config.ai_enabled
            else (
                "AI provider calls are disabled; external_http probe will not run."
                if provider_name == "external_http"
                else "AI provider calls are disabled; current local mode remains valid."
            ),
            str(config.ai_enabled),
        )
    )
    checks.append(
        _check_record(
            "provider",
            "Provider",
            "ok",
            "Configured provider selection.",
            provider_name,
        )
    )
    checks.append(
        _check_record(
            "desensitized_boundary",
            "Boundary",
            "ok" if config.ai_require_desensitized else "warning",
            "Only desensitized payload may cross the non-mock boundary."
            if config.ai_require_desensitized
            else "Desensitized boundary is disabled for non-mock provider traffic.",
            str(config.ai_require_desensitized),
        )
    )

    if provider_name != "external_http":
        checks.append(
            _check_record(
                "external_http_probe",
                "HTTP Probe",
                "ok",
                f"Current provider is {provider_name}; live external_http probe is not required.",
                provider_name,
            )
        )
        status = "warning" if any(item["status"] == "warning" for item in checks) else "ok"
        return {
            "status": status,
            "phase": phase,
            "provider": provider_name,
            "mode": "non_external_http",
            "endpoint": endpoint,
            "model": model,
            "api_key_env": api_key_env,
            "api_key_present": api_key_present,
            "blocking_items": blocking_items,
            "checks": checks,
            "summary": _readiness_summary(provider_name, phase, blocking_items),
            "recommended_action": _readiness_recommended_action(phase, blocking_items),
        }

    checks.append(
        _check_record(
            "endpoint",
            "Endpoint",
            "ok" if endpoint else "warning",
            "external_http endpoint is configured." if endpoint else "external_http requires ai_endpoint.",
            endpoint,
        )
    )
    checks.append(
        _check_record(
            "model",
            "Model",
            "ok" if model else "warning",
            "Provider model is configured." if model else "external_http requires ai_model.",
            model,
        )
    )
    if api_key_env:
        checks.append(
            _check_record(
                "api_key_env",
                "API Key Env",
                "ok" if api_key_present else "warning",
                f"Environment variable {api_key_env} is available."
                if api_key_present
                else f"Environment variable {api_key_env} is configured but currently empty.",
                api_key_env,
            )
        )
    else:
        checks.append(
            _check_record(
                "api_key_env",
                "API Key Env",
                "ok",
                "No API key env is configured in local config; auth may still be optional.",
                "",
            )
        )
    checks.append(
        _check_record(
            "fallback",
            "Fallback",
            "ok" if config.ai_fallback_to_mock else "warning",
            "mock fallback is enabled for provider failures."
            if config.ai_fallback_to_mock
            else "mock fallback is disabled; provider failures will surface directly.",
            str(config.ai_fallback_to_mock),
        )
    )

    status = "warning" if any(item["status"] == "warning" for item in checks) else "ok"
    return {
        "status": status,
        "phase": phase,
        "provider": provider_name,
        "mode": "external_http",
        "endpoint": endpoint,
        "model": model,
        "api_key_env": api_key_env,
        "api_key_present": api_key_present,
        "blocking_items": blocking_items,
        "checks": checks,
        "summary": _readiness_summary(provider_name, phase, blocking_items),
        "recommended_action": _readiness_recommended_action(phase, blocking_items),
    }


def _resolve_probe_error_code(exc: Exception) -> str:
    error_code = str(exc or "").strip()
    if error_code.startswith("external_http_"):
        return error_code
    mapped = external_http_error_code(exc)
    if mapped != "external_http_unknown_error":
        return mapped
    return error_code or "external_http_unknown_error"


def _probe_failure_recommended_action(error_code: str, readiness: dict) -> str:
    if error_code == "external_http_connection_refused":
        return "The endpoint refused the connection. Confirm the provider service is running and reachable, then rerun provider_probe."
    if error_code == "external_http_request_failed":
        return "The probe request failed before a valid response was received. Verify the endpoint, working directory, and provider service reachability, then retry."
    if error_code == "external_http_timeout":
        return "The probe timed out. Check connectivity or raise ai_timeout_seconds before retrying."
    if error_code == "external_http_invalid_json":
        return "The provider response did not match the external_http JSON contract. Fix the gateway response shape and retry."
    if error_code == "external_http_http_error":
        return "The provider returned an HTTP error. Check upstream logs and response body handling before retrying."
    return readiness.get("recommended_action", "Review provider readiness and retry the safe probe.")


def _build_probe_result(readiness: dict, request_payload: dict) -> dict:
    return {
        "generated_at": now_iso(),
        "status": readiness["status"],
        "phase": readiness["phase"],
        "readiness_phase": readiness["phase"],
        "summary": readiness["summary"],
        "recommended_action": readiness["recommended_action"],
        "artifact_path": "",
        "history_artifact_path": "",
        "readiness": readiness,
        "request_payload": request_payload,
        "request_summary": summarize_provider_probe_request(request_payload),
        "probe": {
            "attempted": False,
            "status": "skipped",
            "detail": "Probe request was not requested.",
            "endpoint": str(readiness.get("endpoint", "")),
            "http_status": 0,
            "error_code": "",
            "response_payload": {},
            "normalized_response": {},
        },
    }


def _artifact_payload_from_result(result: dict) -> dict:
    readiness = result.get("readiness", {})
    probe = result.get("probe", {})
    normalized = probe.get("normalized_response") or {}
    request_summary = dict(result.get("request_summary", {}) or summarize_provider_probe_request(result.get("request_payload", {}) or {}))
    return {
        "generated_at": result.get("generated_at", ""),
        "status": result.get("status", "unknown"),
        "phase": result.get("phase", ""),
        "readiness_phase": result.get("readiness_phase", ""),
        "summary": result.get("summary", ""),
        "recommended_action": result.get("recommended_action", ""),
        "request_summary": request_summary,
        "provider": readiness.get("provider", ""),
        "endpoint": readiness.get("endpoint", ""),
        "model": readiness.get("model", ""),
        "api_key_env": readiness.get("api_key_env", ""),
        "api_key_present": bool(readiness.get("api_key_present", False)),
        "readiness": {
            "status": readiness.get("status", "unknown"),
            "phase": readiness.get("phase", ""),
            "summary": readiness.get("summary", ""),
            "recommended_action": readiness.get("recommended_action", ""),
            "blocking_items": list(readiness.get("blocking_items", [])),
            "checks": list(readiness.get("checks", [])),
        },
        "probe": {
            "attempted": bool(probe.get("attempted", False)),
            "status": probe.get("status", "skipped"),
            "detail": probe.get("detail", ""),
            "endpoint": probe.get("endpoint", ""),
            "http_status": int(probe.get("http_status", 0) or 0),
            "error_code": probe.get("error_code", ""),
            "provider_status": normalized.get("provider_status", ""),
            "provider_request_id": normalized.get("provider_request_id", ""),
        },
    }


def write_provider_probe_artifact(
    result: dict,
    config: AppConfig | None = None,
    *,
    artifact_path: str | Path | None = None,
) -> Path:
    target = Path(artifact_path) if artifact_path else _provider_probe_artifact_path(config)
    ensure_dir(target.parent)
    target.write_text(json.dumps(_artifact_payload_from_result(result), ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def write_provider_probe_history_artifact(
    result: dict,
    config: AppConfig | None = None,
    *,
    history_dir: str | Path | None = None,
) -> Path:
    target = _provider_probe_history_path(config, generated_at=str(result.get("generated_at", "") or ""), history_dir=history_dir)
    candidate = target
    suffix_index = 1
    while candidate.exists():
        candidate = target.parent / f"{target.stem}_{suffix_index}{target.suffix}"
        suffix_index += 1
    ensure_dir(candidate.parent)
    candidate.write_text(json.dumps(_artifact_payload_from_result(result), ensure_ascii=False, indent=2), encoding="utf-8")
    return candidate


def _persist_provider_probe_outputs(
    result: dict,
    config: AppConfig,
    *,
    persist_latest: bool,
    artifact_path: str | Path | None,
    persist_history: bool,
    history_dir: str | Path | None,
) -> None:
    if persist_latest:
        target = write_provider_probe_artifact(result, config, artifact_path=artifact_path)
        result["artifact_path"] = str(target)
    if persist_history:
        history_target = write_provider_probe_history_artifact(result, config, history_dir=history_dir)
        result["history_artifact_path"] = str(history_target)


def _empty_provider_probe_status(
    summary: str,
    *,
    target: Path | None = None,
    config_or_root: AppConfig | str | Path | None = None,
) -> dict:
    target = target or _provider_probe_artifact_path(config_or_root)
    return {
        "exists": False,
        "status": "warning",
        "phase": "not_run",
        "readiness_phase": "",
        "summary": summary,
        "recommended_action": r"Run py -m app.tools.provider_probe --config config\local.json --probe once provider config is ready.",
        "file_name": target.name,
        "file_path": str(target),
        "generated_at": "",
        "updated_at": "",
        "provider": "",
        "endpoint": "",
        "model": "",
        "probe_status": "not_run",
        "attempted": False,
        "detail": summary,
        "http_status": 0,
        "error_code": "",
        "provider_status": "",
        "provider_request_id": "",
        "request_summary": {},
    }


def _load_provider_probe_status_from_path(path: Path, *, fallback_summary: str = "Provider probe artifact loaded.") -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        result = _empty_provider_probe_status(
            f"Provider probe artifact exists but could not be parsed: {exc}",
            target=path,
        )
        result["exists"] = True
        result["updated_at"] = _iso_from_timestamp(path.stat().st_mtime)
        return result

    probe = payload.get("probe", {})
    return {
        "exists": True,
        "status": str(payload.get("status", "warning") or "warning"),
        "phase": str(payload.get("phase", "") or "not_run"),
        "readiness_phase": str(payload.get("readiness_phase", "") or ""),
        "summary": str(payload.get("summary", "") or fallback_summary),
        "recommended_action": str(payload.get("recommended_action", "") or ""),
        "file_name": path.name,
        "file_path": str(path),
        "generated_at": str(payload.get("generated_at", "") or ""),
        "updated_at": _iso_from_timestamp(path.stat().st_mtime),
        "provider": str(payload.get("provider", "") or ""),
        "endpoint": str(payload.get("endpoint", "") or ""),
        "model": str(payload.get("model", "") or ""),
        "probe_status": str(probe.get("status", "skipped") or "skipped"),
        "attempted": bool(probe.get("attempted", False)),
        "detail": str(probe.get("detail", "") or payload.get("summary", "") or ""),
        "http_status": int(probe.get("http_status", 0) or 0),
        "error_code": str(probe.get("error_code", "") or ""),
        "provider_status": str(probe.get("provider_status", "") or ""),
        "provider_request_id": str(probe.get("provider_request_id", "") or ""),
        "request_summary": dict(payload.get("request_summary", {}) or {}),
    }


def latest_provider_probe_status(config_or_root: AppConfig | str | Path | None = None) -> dict:
    target = _provider_probe_artifact_path(config_or_root)
    if not target.exists():
        return _empty_provider_probe_status("No persisted provider probe result is available yet.", config_or_root=config_or_root)
    return _load_provider_probe_status_from_path(target)


def list_provider_probe_history(config_or_root: AppConfig | str | Path | None = None, *, limit: int = 10) -> list[dict]:
    history_root = _provider_probe_history_dir(config_or_root)
    if not history_root.exists():
        return []
    candidates = sorted((path for path in history_root.glob("*.json") if path.is_file()), key=lambda path: path.stat().st_mtime, reverse=True)
    history: list[dict] = []
    for path in candidates[: max(limit, 0)]:
        history.append(_load_provider_probe_status_from_path(path))
    return history


def latest_successful_provider_probe_status(config_or_root: AppConfig | str | Path | None = None) -> dict:
    latest = latest_provider_probe_status(config_or_root)
    if latest.get("exists") and latest.get("probe_status") == "ok":
        return latest
    for item in list_provider_probe_history(config_or_root, limit=20):
        if item.get("probe_status") == "ok":
            return item
    return _empty_provider_probe_status(
        "No successful provider probe is available yet.",
        target=_provider_probe_history_dir(config_or_root) / f"{PROVIDER_PROBE_HISTORY_STEM}_latest.json",
        config_or_root=config_or_root,
    )


def latest_failed_provider_probe_status(config_or_root: AppConfig | str | Path | None = None) -> dict:
    latest = latest_provider_probe_status(config_or_root)
    if latest.get("exists") and latest.get("probe_status") == "failed":
        return latest
    for item in list_provider_probe_history(config_or_root, limit=20):
        if item.get("probe_status") == "failed":
            return item
    return _empty_provider_probe_status(
        "No failed provider probe is available yet.",
        target=_provider_probe_history_dir(config_or_root) / f"{PROVIDER_PROBE_HISTORY_STEM}_latest.json",
        config_or_root=config_or_root,
    )


def get_provider_probe_artifact_download(
    *,
    config_or_root: AppConfig | str | Path | None = None,
    file_name: str = "",
) -> dict:
    if file_name:
        normalized_name = Path(file_name).name
        if normalized_name != file_name:
            raise ValueError("Provider probe history file name must not include directory segments.")
        target = _provider_probe_history_dir(config_or_root) / normalized_name
    else:
        target = _provider_probe_artifact_path(config_or_root)
    if not target.exists():
        raise ValueError(f"Provider probe artifact not found: {target.name}")
    return {
        "path": target,
        "filename": target.name,
        "media_type": PROVIDER_PROBE_MEDIA_TYPE,
    }


def run_provider_probe(
    config: AppConfig,
    *,
    send_request: bool = False,
    environ: Mapping[str, str] | None = None,
    persist_result: bool = False,
    persist_history: bool = False,
    artifact_path: str | Path | None = None,
    history_dir: str | Path | None = None,
) -> dict:
    readiness = evaluate_provider_readiness(config, environ=environ)
    request_payload = build_provider_probe_request_payload(config)
    result = _build_probe_result(readiness, request_payload)

    _safe_log_event(
        "provider_probe_started",
        {
            "provider": readiness.get("provider", ""),
            "phase": readiness.get("phase", ""),
            "send_request": send_request,
            "endpoint": readiness.get("endpoint", ""),
            "request_summary": result.get("request_summary", {}),
        },
    )

    if not send_request:
        _persist_provider_probe_outputs(
            result,
            config,
            persist_latest=persist_result,
            artifact_path=artifact_path,
            persist_history=persist_history,
            history_dir=history_dir,
        )
        _safe_log_event(
            "provider_probe_completed",
            {
                "provider": readiness.get("provider", ""),
                "phase": result.get("phase", ""),
                "status": result.get("status", "unknown"),
                "probe_status": result["probe"].get("status", "skipped"),
                "artifact_path": result.get("artifact_path", ""),
                "history_artifact_path": result.get("history_artifact_path", ""),
            },
        )
        return result

    if readiness["provider"] != "external_http":
        result["phase"] = "probe_skipped"
        result["summary"] = f"Live external_http probe skipped because provider={readiness['provider']}."
        result["recommended_action"] = readiness.get("recommended_action", "")
        result["probe"] = {
            **result["probe"],
            "detail": f"Current provider is {readiness['provider']}; live external_http probe skipped.",
        }
        _persist_provider_probe_outputs(
            result,
            config,
            persist_latest=persist_result,
            artifact_path=artifact_path,
            persist_history=persist_history,
            history_dir=history_dir,
        )
        _safe_log_event(
            "provider_probe_skipped",
            {
                "provider": readiness.get("provider", ""),
                "phase": result.get("phase", ""),
                "detail": result["probe"].get("detail", ""),
                "artifact_path": result.get("artifact_path", ""),
                "history_artifact_path": result.get("history_artifact_path", ""),
            },
        )
        return result

    if readiness["phase"] != "ready_for_probe":
        result["status"] = "warning"
        result["phase"] = "probe_skipped"
        result["summary"] = readiness.get("summary", "Provider readiness is incomplete.")
        result["recommended_action"] = readiness.get("recommended_action", "")
        result["probe"] = {
            **result["probe"],
            "detail": "Probe skipped because provider readiness is incomplete.",
        }
        _persist_provider_probe_outputs(
            result,
            config,
            persist_latest=persist_result,
            artifact_path=artifact_path,
            persist_history=persist_history,
            history_dir=history_dir,
        )
        _safe_log_event(
            "provider_probe_skipped",
            {
                "provider": readiness.get("provider", ""),
                "phase": readiness.get("phase", ""),
                "detail": result["probe"].get("detail", ""),
                "artifact_path": result.get("artifact_path", ""),
                "history_artifact_path": result.get("history_artifact_path", ""),
            },
        )
        return result

    env = environ or os.environ
    body = json.dumps(request_payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if readiness["api_key_env"]:
        api_key = str(env.get(readiness["api_key_env"], "") or "").strip()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
    result["request_summary"]["authorization_header_used"] = "Authorization" in headers

    request = urllib.request.Request(readiness["endpoint"], data=body, headers=headers, method="POST")
    http_status = 0
    try:
        with urllib.request.urlopen(request, timeout=config.ai_timeout_seconds) as response:
            http_status = int(getattr(response, "status", 200) or 200)
            response_bytes = response.read()
            response_text = response_bytes.decode("utf-8", errors="ignore")
            response_payload = json.loads(response_text)
            normalized = normalize_external_http_response(
                response_payload,
                request_payload["rule_results"],
                request_payload["requested_provider"],
                config,
            )
            result["phase"] = "probe_passed"
            result["summary"] = "Latest safe provider probe completed successfully."
            result["recommended_action"] = "Provider smoke passed. You can continue with non-user-data gateway validation while keeping the desensitized boundary enabled."
            result["probe"] = {
                "attempted": True,
                "status": "ok",
                "detail": "Probe request completed successfully.",
                "endpoint": readiness["endpoint"],
                "http_status": http_status,
                "error_code": "",
                "response_payload": response_payload,
                "normalized_response": normalized,
            }
            result["status"] = "ok"
            _persist_provider_probe_outputs(
                result,
                config,
                persist_latest=persist_result,
                artifact_path=artifact_path,
                persist_history=persist_history,
                history_dir=history_dir,
            )
            _safe_log_event(
                "provider_probe_completed",
                {
                    "provider": readiness.get("provider", ""),
                    "phase": result.get("phase", ""),
                    "status": result.get("status", "unknown"),
                    "probe_status": result["probe"].get("status", "skipped"),
                    "http_status": http_status,
                    "provider_request_id": normalized.get("provider_request_id", ""),
                    "artifact_path": result.get("artifact_path", ""),
                    "history_artifact_path": result.get("history_artifact_path", ""),
                    "request_summary": result.get("request_summary", {}),
                },
            )
            return result
    except (TimeoutError, socket.timeout) as exc:
        error_code = _resolve_probe_error_code(exc)
    except urllib.error.HTTPError as exc:
        http_status = int(getattr(exc, "code", 0) or 0)
        error_code = _resolve_probe_error_code(exc)
    except urllib.error.URLError as exc:
        error_code = _resolve_probe_error_code(exc)
    except json.JSONDecodeError as exc:
        error_code = _resolve_probe_error_code(exc)
    except Exception as exc:
        error_code = _resolve_probe_error_code(exc)

    result["phase"] = "probe_failed"
    result["probe"] = {
        "attempted": True,
        "status": "failed",
        "detail": "Probe request failed.",
        "endpoint": readiness["endpoint"],
        "http_status": http_status,
        "error_code": error_code,
        "response_payload": {},
        "normalized_response": {},
    }
    result["status"] = "warning"
    result["summary"] = f"Latest safe provider probe failed: {error_code}."
    result["recommended_action"] = _probe_failure_recommended_action(error_code, readiness)
    _persist_provider_probe_outputs(
        result,
        config,
        persist_latest=persist_result,
        artifact_path=artifact_path,
        persist_history=persist_history,
        history_dir=history_dir,
    )
    _safe_log_event(
        "provider_probe_failed",
        {
            "provider": readiness.get("provider", ""),
            "phase": result.get("phase", ""),
            "status": result.get("status", "unknown"),
            "error_code": error_code,
            "http_status": http_status,
            "artifact_path": result.get("artifact_path", ""),
            "history_artifact_path": result.get("history_artifact_path", ""),
            "request_summary": result.get("request_summary", {}),
        },
    )
    return result


def build_provider_probe_config(base_config: AppConfig, **overrides: object) -> AppConfig:
    allowed = {
        "ai_enabled",
        "ai_provider",
        "ai_endpoint",
        "ai_model",
        "ai_api_key_env",
        "ai_timeout_seconds",
        "ai_require_desensitized",
        "ai_fallback_to_mock",
        "data_root",
        "log_path",
    }
    filtered = {key: value for key, value in overrides.items() if key in allowed and value is not None}
    return replace(base_config, **filtered)
