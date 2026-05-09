from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.services.review_rulebook import dimension_rulebook_from_profile, parse_dimension_rule_items_from_form
from app.core.services.runtime_store import store
from app.core.utils.text import now_iso


DIMENSION_CATALOG = [
    {"key": "identity", "title": "基础信息完整性", "description": "软件名称、版本号、申请主体是否完整。"},
    {"key": "completeness", "title": "材料完整性", "description": "核心材料是否齐备，是否存在缺失项。"},
    {"key": "consistency", "title": "跨材料一致性", "description": "不同材料之间的名称、版本与描述口径是否一致。"},
    {"key": "source_code", "title": "源码可审查性", "description": "源码是否可读、是否存在关键逻辑缺失风险。"},
    {"key": "software_doc", "title": "说明文档规范", "description": "说明文档是否规范、版本描述是否清晰。"},
    {"key": "agreement", "title": "协议与权属规范", "description": "协议、权属类材料是否存在明显风险。"},
    {"key": "online_filing", "title": "在线填报信息审查", "description": "在线填报的分类、日期和主体类型是否与材料一致。"},
    {"key": "ai", "title": "AI 补充研判", "description": "让 LLM 从指定角度补充总结和提示。"},
]

DIMENSION_KEYS = [item["key"] for item in DIMENSION_CATALOG]

FOCUS_MODE_LABELS = {
    "balanced": "平衡审查",
    "consistency_first": "一致性优先",
    "source_code_first": "源码优先",
    "document_first": "文档优先",
    "ownership_first": "权属优先",
}

STRICTNESS_LABELS = {
    "standard": "标准模式",
    "strict": "严格模式",
    "lenient": "宽松模式",
}

REVIEW_PROFILE_PRESETS = [
    {
        "key": "balanced_default",
        "title": "标准平衡模板",
        "description": "默认模板，覆盖全部维度，适合常规软著审查。",
        "profile": {
            "enabled_dimensions": list(DIMENSION_KEYS),
            "focus_mode": "balanced",
            "strictness": "standard",
            "llm_instruction": "",
        },
    },
    {
        "key": "source_code_strict",
        "title": "源码严审模板",
        "description": "重点检查源码、命名和版本一致性，适合偏技术型项目。",
        "profile": {
            "enabled_dimensions": ["identity", "consistency", "source_code", "software_doc", "ai"],
            "focus_mode": "source_code_first",
            "strictness": "strict",
            "llm_instruction": "重点关注源码、说明文档与软件名称版本的一致性，并对技术描述偏差更严格。",
        },
    },
    {
        "key": "ownership_guard",
        "title": "权属优先模板",
        "description": "优先检查申请主体、协议和材料归属关系。",
        "profile": {
            "enabled_dimensions": ["identity", "completeness", "consistency", "agreement", "ai"],
            "focus_mode": "ownership_first",
            "strictness": "strict",
            "llm_instruction": "重点检查申请主体、协议权属和材料归属关系，优先提示可能影响权属判断的风险。",
        },
    },
    {
        "key": "document_consistency",
        "title": "文档核验模板",
        "description": "强调说明文档、信息采集表与项目口径的一致性。",
        "profile": {
            "enabled_dimensions": ["identity", "completeness", "consistency", "software_doc", "ai"],
            "focus_mode": "document_first",
            "strictness": "standard",
            "llm_instruction": "重点核验说明文档、信息采集表和项目命名描述是否一致。",
        },
    },
]

PRESET_MAP = {item["key"]: item for item in REVIEW_PROFILE_PRESETS}
REVIEW_PROFILE_SCHEMA_VERSION = 2


def _normalize_rulebook_meta(raw: dict[str, Any] | None, *, preset_key: str) -> dict[str, Any]:
    payload = dict(raw or {})
    revision = int(payload.get("revision", 1) or 1)
    return {
        "schema_version": REVIEW_PROFILE_SCHEMA_VERSION,
        "revision": max(1, revision),
        "updated_at": str(payload.get("updated_at", "") or "").strip(),
        "updated_by": str(payload.get("updated_by", "") or "").strip(),
        "change_note": str(payload.get("change_note", "") or "").strip(),
        "last_dimension_key": str(payload.get("last_dimension_key", "") or "").strip(),
        "change_type": str(payload.get("change_type", "preset_applied") or "preset_applied").strip(),
        "preset_key": preset_key,
    }


GLOBAL_REVIEW_PROFILE_PATH = Path("config") / "global_review_profile.json"


def _load_global_review_profile() -> dict[str, Any] | None:
    if not GLOBAL_REVIEW_PROFILE_PATH.exists():
        return None
    try:
        import json
        return json.loads(GLOBAL_REVIEW_PROFILE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_global_review_profile(profile: dict[str, Any]) -> None:
    import json
    GLOBAL_REVIEW_PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    GLOBAL_REVIEW_PROFILE_PATH.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")


def default_review_profile() -> dict[str, Any]:
    global_profile = _load_global_review_profile()
    if global_profile:
        base = normalize_review_profile(global_profile)
        return {
            **base,
            "dimension_rulebook": dimension_rulebook_from_profile(base),
            "rulebook_meta": _normalize_rulebook_meta(base, preset_key=base.get("preset_key", "balanced_default")),
        }
    return {
        **dict(PRESET_MAP["balanced_default"]["profile"]),
        "preset_key": "balanced_default",
        "dimension_rulebook": dimension_rulebook_from_profile({}),
        "rulebook_meta": _normalize_rulebook_meta({}, preset_key="balanced_default"),
    }


def apply_review_profile_preset(preset_key: str, *, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    base = normalize_review_profile(fallback)
    preset = PRESET_MAP.get(str(preset_key or "").strip())
    if not preset:
        return dict(base)
    merged = {**base, **dict(preset["profile"]), "preset_key": preset["key"]}
    return normalize_review_profile(merged)


def normalize_review_profile(raw: dict[str, Any] | None) -> dict[str, Any]:
    payload = dict(raw or {})
    default_payload = default_review_profile()
    preset_key = str(payload.get("preset_key", default_payload.get("preset_key", "balanced_default")) or "").strip().lower()
    if preset_key not in PRESET_MAP:
        preset_key = default_payload.get("preset_key", "balanced_default")

    enabled_dimensions_raw = payload.get("enabled_dimensions", default_payload["enabled_dimensions"])
    if isinstance(enabled_dimensions_raw, str):
        enabled_dimensions = [item.strip() for item in enabled_dimensions_raw.split(",") if item.strip()]
    else:
        enabled_dimensions = [str(item).strip() for item in list(enabled_dimensions_raw or []) if str(item).strip()]
    enabled_dimensions = [item for item in enabled_dimensions if item in DIMENSION_KEYS]
    if not enabled_dimensions:
        enabled_dimensions = list(default_payload["enabled_dimensions"])

    focus_mode = str(payload.get("focus_mode", default_payload["focus_mode"]) or default_payload["focus_mode"]).strip().lower()
    if focus_mode not in FOCUS_MODE_LABELS:
        focus_mode = default_payload["focus_mode"]

    strictness = str(payload.get("strictness", default_payload["strictness"]) or default_payload["strictness"]).strip().lower()
    if strictness not in STRICTNESS_LABELS:
        strictness = default_payload["strictness"]

    llm_instruction = str(payload.get("llm_instruction", "") or "").strip()
    llm_instruction = llm_instruction[:600]

    return {
        "preset_key": preset_key,
        "enabled_dimensions": enabled_dimensions,
        "focus_mode": focus_mode,
        "strictness": strictness,
        "llm_instruction": llm_instruction,
        "dimension_rulebook": dimension_rulebook_from_profile(payload),
        "rulebook_meta": _normalize_rulebook_meta(payload.get("rulebook_meta"), preset_key=preset_key),
    }


def bump_review_profile_revision(
    profile: dict[str, Any] | None,
    *,
    updated_by: str = "",
    change_note: str = "",
    last_dimension_key: str = "",
    change_type: str = "manual_update",
) -> dict[str, Any]:
    normalized = normalize_review_profile(profile)
    meta = dict(normalized.get("rulebook_meta", {}) or {})
    meta["revision"] = int(meta.get("revision", 1) or 1) + 1
    meta["updated_at"] = now_iso()
    meta["updated_by"] = str(updated_by or meta.get("updated_by", "")).strip()
    meta["change_note"] = str(change_note or "").strip()
    meta["last_dimension_key"] = str(last_dimension_key or "").strip()
    meta["change_type"] = str(change_type or "manual_update").strip()
    normalized["rulebook_meta"] = _normalize_rulebook_meta(meta, preset_key=normalized.get("preset_key", "balanced_default"))
    return normalized


def parse_review_profile_form(form_data, *, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    preset_key = str(form_data.get("review_profile_preset", "") or "").strip().lower()
    base = apply_review_profile_preset(preset_key, fallback=fallback) if preset_key else normalize_review_profile(fallback)
    dimensions_present = str(form_data.get("review_dimensions_present", "") or "").strip()
    selected_dimensions = [
        key for key in DIMENSION_KEYS if str(form_data.get(f"dimension_{key}", "") or "").strip()
    ]
    if dimensions_present:
        enabled_dimensions = selected_dimensions or list(base["enabled_dimensions"])
    else:
        enabled_dimensions = list(base["enabled_dimensions"])

    rulebook = dict(base.get("dimension_rulebook", {}) or {})
    for key in DIMENSION_KEYS:
        title = str(form_data.get(f"rule_{key}_title", "") or "").strip()
        objective = str(form_data.get(f"rule_{key}_objective", "") or "").strip()
        checkpoints_raw = str(form_data.get(f"rule_{key}_checkpoints", "") or "").strip()
        evidence_targets_raw = str(form_data.get(f"rule_{key}_evidence_targets", "") or "").strip()
        common_failures_raw = str(form_data.get(f"rule_{key}_common_failures", "") or "").strip()
        operator_notes_raw = str(form_data.get(f"rule_{key}_operator_notes", "") or "").strip()
        llm_focus = str(form_data.get(f"rule_{key}_llm_focus", "") or "").strip()
        rule_items = parse_dimension_rule_items_from_form(form_data, key)
        if not any([title, objective, checkpoints_raw, evidence_targets_raw, common_failures_raw, operator_notes_raw, llm_focus]):
            current = dict(rulebook.get(key, {}) or {})
            current["rules"] = rule_items
            rulebook[key] = current
            continue
        current = dict(rulebook.get(key, {}) or {})
        checkpoints = [
            line.strip(" -\t")
            for line in checkpoints_raw.splitlines()
            if line.strip(" -\t")
        ]
        if title:
            current["title"] = title
        if objective:
            current["objective"] = objective
        if checkpoints:
            current["checkpoints"] = checkpoints
        if evidence_targets_raw:
            current["evidence_targets"] = [line.strip(" -\t") for line in evidence_targets_raw.splitlines() if line.strip(" -\t")]
        if common_failures_raw:
            current["common_failures"] = [line.strip(" -\t") for line in common_failures_raw.splitlines() if line.strip(" -\t")]
        if operator_notes_raw:
            current["operator_notes"] = [line.strip(" -\t") for line in operator_notes_raw.splitlines() if line.strip(" -\t")]
        if llm_focus:
            current["llm_focus"] = llm_focus
        current["rules"] = rule_items
        rulebook[key] = current

    return normalize_review_profile(
        {
            "preset_key": preset_key or base.get("preset_key", "balanced_default"),
            "enabled_dimensions": enabled_dimensions,
            "focus_mode": form_data.get("focus_mode", base["focus_mode"]),
            "strictness": form_data.get("strictness", base["strictness"]),
            "llm_instruction": form_data.get("llm_instruction", base["llm_instruction"]),
            "dimension_rulebook": rulebook,
        }
    )


def dimension_title(key: str) -> str:
    for item in DIMENSION_CATALOG:
        if item["key"] == key:
            return str(item["title"])
    return key


def focus_mode_label(value: str) -> str:
    normalized = str(value or "").strip().lower()
    return FOCUS_MODE_LABELS.get(normalized, normalized or "-")


def strictness_label(value: str) -> str:
    normalized = str(value or "").strip().lower()
    return STRICTNESS_LABELS.get(normalized, normalized or "-")


def preset_title(preset_key: str) -> str:
    preset = PRESET_MAP.get(str(preset_key or "").strip().lower())
    if not preset:
        return "自定义配置"
    return str(preset["title"])


def review_profile_summary(profile: dict[str, Any] | None) -> list[tuple[str, str]]:
    normalized = normalize_review_profile(profile)
    dimensions = "、".join(dimension_title(item) for item in normalized["enabled_dimensions"])
    return [
        ("模板", preset_title(normalized.get("preset_key", ""))),
        ("审查侧重", focus_mode_label(normalized["focus_mode"])),
        ("严格程度", strictness_label(normalized["strictness"])),
        ("启用维度", dimensions),
        ("LLM 指令", normalized["llm_instruction"] or "未补充"),
    ]


def review_profile_summary_v2(profile: dict[str, Any] | None) -> list[tuple[str, str]]:
    normalized = normalize_review_profile(profile)
    meta = dict(normalized.get("rulebook_meta", {}) or {})
    dimensions = " / ".join(dimension_title(item) for item in normalized["enabled_dimensions"])
    return [
        ("模板", preset_title(normalized.get("preset_key", ""))),
        ("审查侧重", focus_mode_label(normalized["focus_mode"])),
        ("严格程度", strictness_label(normalized["strictness"])),
        ("规则版本", f"r{int(meta.get('revision', 1) or 1)}"),
        ("启用维度", dimensions),
        ("LLM 指令", normalized["llm_instruction"] or "未补充"),
    ]


def list_review_rule_history(submission_id: str, dimension_key: str = "", *, limit: int = 20) -> list[dict[str, Any]]:
    submission = store.submissions.get(str(submission_id or "").strip())
    if not submission:
        return []

    normalized_dimension_key = str(dimension_key or "").strip()
    rows: list[dict[str, Any]] = []
    for correction_id in reversed(list(getattr(submission, "correction_ids", []) or [])):
        correction = store.corrections.get(correction_id)
        if not correction:
            continue
        if correction.correction_type not in {"update_review_dimension_rule", "reset_review_dimension_rule"}:
            continue
        original_value = dict(getattr(correction, "original_value", {}) or {})
        corrected_value = dict(getattr(correction, "corrected_value", {}) or {})
        current_dimension_key = str(corrected_value.get("dimension_key") or original_value.get("dimension_key") or "").strip()
        if normalized_dimension_key and current_dimension_key != normalized_dimension_key:
            continue
        corrected_profile = normalize_review_profile(dict(corrected_value.get("review_profile", {}) or {}))
        meta = dict(corrected_profile.get("rulebook_meta", {}) or {})
        rows.append(
            {
                "correction_id": str(getattr(correction, "id", "") or ""),
                "submission_id": str(submission.id),
                "dimension_key": current_dimension_key,
                "dimension_title": dimension_title(current_dimension_key),
                "revision": int(meta.get("revision", 1) or 1),
                "change_type": str(meta.get("change_type", "") or getattr(correction, "correction_type", "") or "").strip(),
                "change_type_label": str(
                    getattr(correction, "reason_label", "")
                    or getattr(correction, "reason_code", "")
                    or getattr(correction, "correction_type", "")
                    or "-"
                ),
                "updated_by": str(meta.get("updated_by", "") or getattr(correction, "corrected_by", "") or "").strip(),
                "change_note": str(meta.get("change_note", "") or getattr(correction, "note", "") or "").strip(),
                "corrected_at": str(getattr(correction, "corrected_at", "") or "").strip(),
                "correction_type": str(getattr(correction, "correction_type", "") or "").strip(),
                "review_profile_meta": meta,
            }
        )
        if limit > 0 and len(rows) >= limit:
            break
    return rows


review_profile_summary = review_profile_summary_v2


__all__ = [
    "DIMENSION_CATALOG",
    "DIMENSION_KEYS",
    "FOCUS_MODE_LABELS",
    "PRESET_MAP",
    "REVIEW_PROFILE_PRESETS",
    "STRICTNESS_LABELS",
    "apply_review_profile_preset",
    "bump_review_profile_revision",
    "default_review_profile",
    "dimension_title",
    "focus_mode_label",
    "list_review_rule_history",
    "normalize_review_profile",
    "parse_review_profile_form",
    "preset_title",
    "review_profile_summary",
    "strictness_label",
]
