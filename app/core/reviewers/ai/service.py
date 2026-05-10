from __future__ import annotations

from app.core.privacy.desensitization import build_ai_safe_rule_results, is_ai_safe_case_payload, is_ai_safe_rule_results
from app.core.reviewers.ai.adapters import (
    build_rule_summary,
    external_http_error_code,
    review_with_external_http,
    review_with_safe_stub,
)
from app.core.reviewers.ai.prompt_builder import build_ai_prompt_snapshot
from app.core.services.app_config import AppConfig, load_app_config
from app.core.services.app_logging import log_event


SUPPORTED_AI_PROVIDERS = {"mock", "safe_stub", "external_http"}


def resolve_case_ai_provider(provider: str | None = None, config: AppConfig | None = None) -> str:
    settings = config or load_app_config()
    requested_provider = str(provider or settings.ai_provider or "mock").strip().lower() or "mock"
    if requested_provider == "mock":
        return "mock"
    if requested_provider not in SUPPORTED_AI_PROVIDERS:
        return "mock"
    if not settings.ai_enabled:
        return "mock"
    return requested_provider


def _mock_review(case_payload: dict, rule_results: dict, requested_provider: str, resolution: str) -> dict:
    issues = rule_results.get("issues", [])
    software_name = case_payload.get("software_name", "未命名项目")
    version = case_payload.get("version", "未知版本")
    rule_summary = build_rule_summary(rule_results)
    ai_note = "当前为本地 mock 说明，没有调用外部 provider。"
    if resolution == "provider_exception_fallback":
        ai_note = f"外部 provider 调用失败，系统已安全回退到 mock。requested_provider={requested_provider}"
    elif resolution == "mock_fallback" and requested_provider != "mock":
        ai_note = f"provider 未启用或不可用，当前回退为 mock。requested_provider={requested_provider}"
    return {
        "provider": "mock",
        "requested_provider": requested_provider,
        "resolution": resolution,
        "conclusion": rule_summary,
        "rule_summary": rule_summary,
        "summary": f"{software_name} {version} 共发现 {len(issues)} 个规则问题，建议先处理版本与一致性问题。",
        "ai_note": ai_note,
        "issues": issues,
        "prompt_snapshot": {},
    }


def generate_case_ai_review(
    case_payload: dict,
    rule_results: dict,
    provider: str | None = None,
    config: AppConfig | None = None,
    *,
    review_profile: dict | None = None,
) -> dict:
    settings = config or load_app_config()
    requested_provider = str(provider or settings.ai_provider or "mock").strip().lower() or "mock"
    active_provider = resolve_case_ai_provider(requested_provider, config=settings)
    original_rule_results = dict(rule_results or {})
    external_rule_results = build_ai_safe_rule_results(original_rule_results) if active_provider != "mock" else original_rule_results
    issue_count = len(original_rule_results.get("issues", []))
    prompt_snapshot = build_ai_prompt_snapshot(
        case_payload,
        external_rule_results,
        review_profile,
        requested_provider=requested_provider,
    )

    if active_provider == "mock":
        if requested_provider == "mock":
            resolution = "explicit_mock"
        elif not settings.ai_enabled:
            resolution = "ai_disabled_fallback"
        elif requested_provider not in SUPPORTED_AI_PROVIDERS:
            resolution = "unsupported_provider_fallback"
        else:
            resolution = "mock_fallback"
        result = _mock_review(case_payload, rule_results, requested_provider, resolution)
        result["prompt_snapshot"] = prompt_snapshot
        return result

    if settings.ai_require_desensitized and not is_ai_safe_case_payload(case_payload):
        raise ValueError("Non-mock AI provider requires desensitized payload")
    if settings.ai_require_desensitized and not is_ai_safe_rule_results(external_rule_results):
        raise ValueError("Non-mock AI provider requires desensitized rule results")

    log_event(
        "ai_provider_call_started",
        {
            "provider": active_provider,
            "requested_provider": requested_provider,
            "issue_count": issue_count,
            "timeout_seconds": settings.ai_timeout_seconds,
        },
    )

    try:
        if active_provider == "safe_stub":
            result = review_with_safe_stub(case_payload, external_rule_results, requested_provider)
        elif active_provider == "external_http":
            result = review_with_external_http(
                case_payload,
                external_rule_results,
                requested_provider,
                settings,
                review_profile=review_profile,
            )
        else:
            result = _mock_review(case_payload, original_rule_results, requested_provider, "unsupported_provider_fallback")
    except Exception as exc:
        error_code = str(exc).strip()
        if active_provider == "external_http":
            if not error_code or not error_code.startswith("external_http_"):
                mapped_error_code = external_http_error_code(exc)
                if mapped_error_code != "external_http_unknown_error" or not error_code:
                    error_code = mapped_error_code
        log_event(
            "ai_provider_call_failed",
            {
                "provider": active_provider,
                "requested_provider": requested_provider,
                "issue_count": issue_count,
                "error": error_code,
                "fallback_to_mock": settings.ai_fallback_to_mock,
            },
        )
        if not settings.ai_fallback_to_mock:
            raise
        result = _mock_review(case_payload, rule_results, requested_provider, "provider_exception_fallback")
        result["prompt_snapshot"] = prompt_snapshot
        return result

    log_event(
        "ai_provider_call_completed",
        {
            "provider": result.get("provider", active_provider),
            "requested_provider": requested_provider,
            "resolution": result.get("resolution", ""),
            "issue_count": issue_count,
        },
    )
    if not result.get("prompt_snapshot"):
        result["prompt_snapshot"] = prompt_snapshot
    return result
