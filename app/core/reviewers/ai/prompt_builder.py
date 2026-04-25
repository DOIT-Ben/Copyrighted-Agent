from __future__ import annotations

import json

from app.core.services.review_profile import dimension_title, normalize_review_profile
from app.core.services.review_rulebook import dimension_rulebook_from_profile


def _safe_text(value, *, fallback: str = "-", limit: int = 800) -> str:
    text = str(value or "").strip()
    if not text:
        return fallback
    return text[:limit]


def _issue_line(issue: dict) -> str:
    severity = _safe_text(issue.get("severity"), fallback="minor", limit=24)
    title = _safe_text(issue.get("title") or issue.get("rule") or issue.get("category"), fallback="issue", limit=80)
    message = _safe_text(issue.get("message") or issue.get("detail") or issue.get("desc"), fallback="-", limit=220)
    return f"- [{severity}] {title}: {message}"


def _dimension_block(dimension_key: str, rule: dict) -> str:
    checkpoints = list(rule.get("checkpoints") or [])
    rule_items = [
        item
        for item in list(rule.get("rules") or [])
        if bool(item.get("enabled", True))
    ]
    checkpoint_lines = "\n".join(
        f"  - {_safe_text(item, fallback='-', limit=160)}"
        for item in checkpoints[:8]
        if str(item or "").strip()
    ) or "  - None"
    rule_item_lines = "\n".join(
        f"  - [{_safe_text(item.get('severity'), fallback='moderate', limit=20)}] "
        f"{_safe_text(item.get('category'), fallback='general', limit=40)} / "
        f"{_safe_text(item.get('title'), fallback='rule', limit=80)}: "
        f"{_safe_text(item.get('prompt_hint'), fallback='-', limit=200)}"
        for item in rule_items[:12]
    ) or "  - None"
    return "\n".join(
        [
            f"[{dimension_key}] {_safe_text(rule.get('title') or dimension_title(dimension_key), fallback=dimension_key, limit=80)}",
            f"Objective: {_safe_text(rule.get('objective'), fallback='-', limit=280)}",
            "Checkpoints:",
            checkpoint_lines,
            "Structured rules:",
            rule_item_lines,
            f"LLM focus: {_safe_text(rule.get('llm_focus'), fallback='-', limit=280)}",
        ]
    )


def build_ai_prompt_snapshot(
    case_payload: dict,
    rule_results: dict,
    review_profile: dict | None = None,
    *,
    requested_provider: str = "external_http",
) -> dict:
    normalized_profile = normalize_review_profile(review_profile)
    enabled_dimensions = list(normalized_profile.get("enabled_dimensions", []) or [])
    rulebook = dimension_rulebook_from_profile(normalized_profile)
    active_rulebook = {key: dict(rulebook.get(key) or {}) for key in enabled_dimensions if key in rulebook}
    issues = list(rule_results.get("issues", []) or [])

    system_prompt = "\n".join(
        [
            "You are a software copyright review assistant.",
            "The material has already been desensitized and is safe for LLM processing.",
            "You must stay grounded in the provided payload and rule findings.",
            "Respect the active review profile, especially enabled dimensions, focus mode, strictness, custom instruction, and dimension rulebook.",
            'Return exactly one JSON object and nothing else.',
            'Required JSON keys: "summary", "conclusion", "resolution".',
            'Set "resolution" to "minimax_bridge_success".',
            "The summary must be concise, practical, and useful for an operator reviewing software copyright materials.",
            "Do not invent facts beyond the payload.",
        ]
    )

    profile_lines = [
        f"Requested provider: {_safe_text(requested_provider, fallback='external_http', limit=40)}",
        f"Preset: {_safe_text(normalized_profile.get('preset_key'), fallback='balanced_default', limit=40)}",
        f"Focus mode: {_safe_text(normalized_profile.get('focus_mode'), fallback='balanced', limit=40)}",
        f"Strictness: {_safe_text(normalized_profile.get('strictness'), fallback='standard', limit=40)}",
        f"Custom instruction: {_safe_text(normalized_profile.get('llm_instruction'), fallback='None', limit=400)}",
        "Enabled dimensions:",
    ]
    if enabled_dimensions:
        profile_lines.extend(f"- {key}: {_safe_text(dimension_title(key), fallback=key, limit=60)}" for key in enabled_dimensions)
    else:
        profile_lines.append("- None")

    dimension_sections = "\n\n".join(_dimension_block(key, active_rulebook.get(key, {})) for key in enabled_dimensions) or "[none]"
    issue_lines = "\n".join(_issue_line(issue) for issue in issues[:20]) or "- No rule issues were detected."

    user_prompt = "\n\n".join(
        [
            "Review the desensitized software copyright case and produce a concise operator-facing judgment.",
            "\n".join(profile_lines),
            "Dimension rulebook:\n" + dimension_sections,
            "Rule engine findings:\n" + issue_lines,
            "Desensitized case payload JSON:\n" + json.dumps(dict(case_payload or {}), ensure_ascii=False, indent=2),
            "Rule results JSON:\n" + json.dumps(dict(rule_results or {}), ensure_ascii=False, indent=2),
            'Output JSON schema:\n{"summary":"...", "conclusion":"...", "resolution":"minimax_bridge_success"}',
        ]
    )

    return {
        "requested_provider": _safe_text(requested_provider, fallback="external_http", limit=40),
        "review_profile_summary": {
            "preset_key": _safe_text(normalized_profile.get("preset_key"), fallback="balanced_default", limit=40),
            "focus_mode": _safe_text(normalized_profile.get("focus_mode"), fallback="balanced", limit=40),
            "strictness": _safe_text(normalized_profile.get("strictness"), fallback="standard", limit=40),
            "llm_instruction": _safe_text(normalized_profile.get("llm_instruction"), fallback="", limit=600),
            "enabled_dimensions": enabled_dimensions,
        },
        "active_dimensions": [
            {
                "key": key,
                "title": _safe_text(active_rulebook.get(key, {}).get("title") or dimension_title(key), fallback=key, limit=80),
                "objective": _safe_text(active_rulebook.get(key, {}).get("objective"), fallback="-", limit=280),
                "checkpoints": list(active_rulebook.get(key, {}).get("checkpoints") or [])[:8],
                "rules": [
                    {
                        "key": _safe_text(item.get("key"), fallback="", limit=60),
                        "title": _safe_text(item.get("title"), fallback="-", limit=80),
                        "category": _safe_text(item.get("category"), fallback="-", limit=40),
                        "severity": _safe_text(item.get("severity"), fallback="moderate", limit=20),
                        "prompt_hint": _safe_text(item.get("prompt_hint"), fallback="-", limit=240),
                        "enabled": bool(item.get("enabled", True)),
                    }
                    for item in list(active_rulebook.get(key, {}).get("rules") or [])[:16]
                ],
                "llm_focus": _safe_text(active_rulebook.get(key, {}).get("llm_focus"), fallback="-", limit=280),
            }
            for key in enabled_dimensions
        ],
        "issue_count": len(issues),
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
    }


__all__ = ["build_ai_prompt_snapshot"]
