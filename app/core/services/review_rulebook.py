from __future__ import annotations

from typing import Any


DIMENSION_RULE_DEFAULTS = {
    "identity": {
        "title": "基础信息完整性",
        "objective": "确认软件名称、版本号、申请主体等基础字段完整且可用于后续审查。",
        "checkpoints": [
            "软件名称必须可识别，不能留空或仅为占位文本。",
            "版本号应明确且在主要材料间保持一致。",
            "申请主体应能从信息采集表或相关材料中明确识别。",
            "发现缺失字段时，需要在结论中明确指出缺少的是哪一项。",
        ],
        "llm_focus": "优先检查名称、版本、主体是否齐全且表达一致。",
    },
    "completeness": {
        "title": "材料完整性",
        "objective": "确认软著审查所需的核心材料已提供，避免因缺件影响判断。",
        "checkpoints": [
            "至少检查是否存在信息采集表、源码、说明文档三类核心材料。",
            "如缺少核心材料，需要明确标注缺失项。",
            "未知类型或未归类材料应提示人工确认。",
            "材料数量异常时，需要提醒可能影响审查覆盖范围。",
        ],
        "llm_focus": "概括当前材料覆盖情况，并指出缺件对审查结论的影响。",
    },
    "consistency": {
        "title": "跨材料一致性",
        "objective": "检查不同材料中的项目命名、版本、主体和描述口径是否一致。",
        "checkpoints": [
            "软件名称在信息表、源码、说明文档中应尽量一致。",
            "版本号不一致时应作为重点问题输出。",
            "主体、项目归属、功能描述存在明显冲突时需要单独提示。",
            "结论应明确冲突出现在哪些材料之间。",
        ],
        "llm_focus": "优先归纳跨材料冲突，并提示最影响交付的矛盾点。",
    },
    "source_code": {
        "title": "源码可审查性",
        "objective": "检查源码材料是否可读、是否存在明显缺页、乱码或核心逻辑缺失。",
        "checkpoints": [
            "源码文本应具备基本可读性，不应大面积乱码。",
            "命名、头部说明和版本信息应与项目主信息尽量一致。",
            "如存在明显缺页、截断或内容过短，应提示可审查性不足。",
            "发现技术描述与源码信号不一致时，应纳入问题列表。",
        ],
        "llm_focus": "强调源码可读性、命名一致性和技术描述可信度。",
    },
    "software_doc": {
        "title": "说明文档规范",
        "objective": "确认说明文档具备基本规范性，能支撑软件功能和版本描述。",
        "checkpoints": [
            "说明文档应能识别出项目名称、版本或功能描述。",
            "文档中的项目命名应与其他材料尽量一致。",
            "版本、模块命名或说明结构明显异常时需要提示。",
            "如文档过于简略，应提示可能影响说明充分性。",
        ],
        "llm_focus": "关注说明文档与主信息的一致性，以及描述是否足够支撑审查。",
    },
    "agreement": {
        "title": "协议与权属规范",
        "objective": "检查协议、授权或权属相关材料是否存在主体、日期或归属风险。",
        "checkpoints": [
            "协议中的主体名称应与项目申请主体尽量匹配。",
            "日期、签署状态和权属表述异常时需要提示。",
            "无法明确归属关系时应标注为权属风险。",
            "若无协议材料，应明确说明该维度未覆盖而非直接判定通过。",
        ],
        "llm_focus": "突出主体关系、权属链条和可能影响登记的风险点。",
    },
    "ai": {
        "title": "AI 补充研判",
        "objective": "在规则结论基础上补充归纳风险重点、优先级和建议动作。",
        "checkpoints": [
            "必须基于现有规则结果总结，不能脱离材料臆造事实。",
            "应优先总结高风险和跨材料冲突问题。",
            "需要给出适合人工复核的简短建议。",
            "若信息不足，应明确说明判断边界。",
        ],
        "llm_focus": "压缩总结最重要的问题、影响和建议动作。",
    },
}


def _normalize_rule_entry(key: str, raw: dict[str, Any] | None) -> dict[str, Any]:
    default = dict(DIMENSION_RULE_DEFAULTS.get(key, {}))
    payload = dict(raw or {})
    checkpoints_raw = payload.get("checkpoints", default.get("checkpoints", []))
    if isinstance(checkpoints_raw, str):
        checkpoints = [line.strip(" -\t") for line in checkpoints_raw.splitlines() if line.strip()]
    else:
        checkpoints = [str(item).strip() for item in list(checkpoints_raw or []) if str(item).strip()]
    if not checkpoints:
        checkpoints = list(default.get("checkpoints", []))
    checkpoints = checkpoints[:12]

    return {
        "key": key,
        "title": str(payload.get("title", default.get("title", key)) or default.get("title", key)).strip()[:40],
        "objective": str(payload.get("objective", default.get("objective", "")) or default.get("objective", "")).strip()[:300],
        "checkpoints": checkpoints,
        "llm_focus": str(payload.get("llm_focus", default.get("llm_focus", "")) or default.get("llm_focus", "")).strip()[:300],
    }


def default_dimension_rulebook() -> dict[str, dict[str, Any]]:
    return {key: _normalize_rule_entry(key, value) for key, value in DIMENSION_RULE_DEFAULTS.items()}


def default_dimension_rule(dimension_key: str) -> dict[str, Any]:
    rulebook = default_dimension_rulebook()
    if dimension_key not in rulebook:
        raise ValueError(f"Unsupported dimension key: {dimension_key}")
    return dict(rulebook[dimension_key])


def normalize_dimension_rulebook(raw: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    payload = dict(raw or {})
    normalized = default_dimension_rulebook()
    for key in list(normalized.keys()):
        if key in payload:
            normalized[key] = _normalize_rule_entry(key, payload.get(key))
    return normalized


def dimension_rulebook_from_profile(profile: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    payload = dict(profile or {})
    return normalize_dimension_rulebook(payload.get("dimension_rulebook"))


def update_profile_dimension_rule(profile: dict[str, Any] | None, dimension_key: str, updates: dict[str, Any]) -> dict[str, Any]:
    payload = dict(profile or {})
    rulebook = dimension_rulebook_from_profile(payload)
    if dimension_key not in rulebook:
        raise ValueError(f"Unsupported dimension key: {dimension_key}")
    rulebook[dimension_key] = _normalize_rule_entry(dimension_key, {**rulebook[dimension_key], **dict(updates or {})})
    payload["dimension_rulebook"] = rulebook
    return payload


def reset_profile_dimension_rule(profile: dict[str, Any] | None, dimension_key: str) -> dict[str, Any]:
    payload = dict(profile or {})
    rulebook = dimension_rulebook_from_profile(payload)
    rulebook[dimension_key] = default_dimension_rule(dimension_key)
    payload["dimension_rulebook"] = rulebook
    return payload


def format_rule_checkpoints(checkpoints: list[str]) -> str:
    return "\n".join(f"- {item}" for item in checkpoints if str(item).strip())


__all__ = [
    "DIMENSION_RULE_DEFAULTS",
    "default_dimension_rule",
    "default_dimension_rulebook",
    "dimension_rulebook_from_profile",
    "format_rule_checkpoints",
    "normalize_dimension_rulebook",
    "reset_profile_dimension_rule",
    "update_profile_dimension_rule",
]
