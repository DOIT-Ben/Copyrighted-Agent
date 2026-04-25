from __future__ import annotations

from typing import Any


def _rule_item(
    key: str,
    title: str,
    *,
    category: str,
    severity: str,
    prompt_hint: str,
    enabled: bool = True,
) -> dict[str, Any]:
    return {
        "key": key,
        "title": title,
        "category": category,
        "severity": severity,
        "prompt_hint": prompt_hint,
        "enabled": enabled,
    }


DIMENSION_RULE_DEFAULTS = {
    "identity": {
        "title": "基础信息完整性",
        "objective": "确认软件名称、版本号、申请主体等基础字段完整可用，并作为后续一致性比对的主索引。",
        "rules": [
            _rule_item("software_name_present", "软件名称可识别", category="基础字段", severity="severe", prompt_hint="检查软件名称是否为空、占位或无法提取。"),
            _rule_item("version_present", "版本号明确", category="基础字段", severity="moderate", prompt_hint="检查版本号是否存在且格式清晰。"),
            _rule_item("company_present", "申请主体明确", category="主体字段", severity="severe", prompt_hint="检查申请主体/单位名称是否可识别。"),
            _rule_item("missing_fields_listed", "缺失字段要点名", category="输出要求", severity="minor", prompt_hint="如果有缺失字段，结论里必须明确指出缺的是哪一项。"),
            _rule_item("info_sensitive_terms", "信息采集表敏感词已替换", category="敏感词排查", severity="moderate", prompt_hint="排查破解、刷机、爬虫、抓取、仿微信等敏感表述。"),
        ],
        "llm_focus": "优先检查名称、版本、主体是否齐全且表达一致。",
    },
    "completeness": {
        "title": "材料完整性",
        "objective": "确认软著审查所需核心材料已提交，避免因缺件导致结论不可靠。",
        "rules": [
            _rule_item("info_form_exists", "信息采集表已提供", category="核心材料", severity="severe", prompt_hint="确认信息采集表存在。"),
            _rule_item("source_code_exists", "源代码已提供", category="核心材料", severity="severe", prompt_hint="确认源代码材料存在。"),
            _rule_item("software_doc_exists", "设计文档或说明文档已提供", category="核心材料", severity="severe", prompt_hint="确认设计文档、用户手册或说明文档存在。"),
            _rule_item("agreement_optional_coverage", "协议材料覆盖情况明确", category="协议材料", severity="moderate", prompt_hint="有协议则审查，无协议则明确说明本维度未覆盖。"),
            _rule_item("unknown_material_flagged", "未知材料需要提示", category="归类质量", severity="minor", prompt_hint="未识别或未归类材料需要提示人工确认。"),
        ],
        "llm_focus": "概括当前材料覆盖情况，并指出缺件对审查结论的影响。",
    },
    "consistency": {
        "title": "跨材料一致性",
        "objective": "检查不同材料中的软件名称、版本号、主体、顺序和关键表述是否一致。",
        "rules": [
            _rule_item("software_name_exact_match", "软件全称逐字一致", category="五项一致性", severity="severe", prompt_hint="比对设计文档、源码、协议、信息采集表中的软件全称是否逐字一致。"),
            _rule_item("version_exact_match", "版本号完全一致", category="五项一致性", severity="severe", prompt_hint="比对不同材料中的版本号及大小写写法是否完全一致。"),
            _rule_item("completion_date_match", "开发完成日期一致", category="五项一致性", severity="severe", prompt_hint="关注信息采集表、协议和在线填报中的开发完成日期是否一致。"),
            _rule_item("party_order_match", "申请人或单位排序一致", category="排序关系", severity="severe", prompt_hint="检查协议中的甲乙方顺序、信息采集表顺序、系统填报顺序是否一致。"),
            _rule_item("cross_material_terms_match", "关键术语和口径一致", category="表述口径", severity="moderate", prompt_hint="检查功能描述、术语称呼和项目口径是否前后一致。"),
        ],
        "llm_focus": "优先归纳跨材料冲突，并提示最影响交付的矛盾点。",
    },
    "source_code": {
        "title": "源码可审查性",
        "objective": "检查源码材料是否可读、格式是否达标、是否完成脱敏，并能支撑功能真实性判断。",
        "rules": [
            _rule_item("code_readable", "源码内容可读", category="可读性", severity="severe", prompt_hint="检查源码是否存在乱码、异常字符或无法阅读的内容。"),
            _rule_item("code_format_clean", "源码格式符合提交规范", category="格式规范", severity="moderate", prompt_hint="检查行首空格、连续空行、行号等格式问题。"),
            _rule_item("code_page_strategy", "页数截取方式合理", category="页数策略", severity="severe", prompt_hint="如果总页数超过 60 页，检查是否为前 30 页加后 30 页。"),
            _rule_item("code_desensitized", "敏感信息已脱敏", category="脱敏规范", severity="severe", prompt_hint="重点排查密码、IP、token、手机号、邮箱等敏感信息。"),
            _rule_item("code_sensitive_terms", "敏感词已替换", category="敏感词排查", severity="moderate", prompt_hint="排查破解、外挂、爬虫、抓取等高风险敏感词。"),
            _rule_item("code_logic_supports_doc", "代码与文档功能呼应", category="功能呼应", severity="moderate", prompt_hint="检查文档声称的功能在代码中是否有实现支撑。"),
            _rule_item("code_comment_ratio_reasonable", "注释比例合理", category="注释质量", severity="minor", prompt_hint="避免注释过多、重复注释或恶意凑数。"),
        ],
        "llm_focus": "强调源码可读性、脱敏情况、功能真实性和提交规范风险。",
    },
    "software_doc": {
        "title": "说明文档规范",
        "objective": "确认设计文档或用户手册结构完整、表述规范、术语统一，并能与代码和项目口径互相印证。",
        "rules": [
            _rule_item("doc_page_count", "页数范围合理", category="页数审查", severity="moderate", prompt_hint="检查总页数是否过少、过多，是否低于基本底线。"),
            _rule_item("doc_required_sections", "必备章节齐全", category="结构审查", severity="severe", prompt_hint="重点检查运行环境、安装说明等硬性章节。"),
            _rule_item("doc_terms_consistent", "名词术语统一", category="名词统一", severity="moderate", prompt_hint="排查系统/平台/APP/小程序等混用。"),
            _rule_item("doc_header_footer_valid", "页眉页脚规范", category="版式规范", severity="moderate", prompt_hint="检查页眉是否为软件全称加版本号，页脚是否有连续页码。"),
            _rule_item("doc_sensitive_terms", "敏感词已替换", category="敏感词排查", severity="moderate", prompt_hint="排查破解、刷机、爬虫、仿微信等敏感表述。"),
            _rule_item("doc_text_quality", "文案质量达标", category="文字质量", severity="moderate", prompt_hint="关注 AI 腔、乱码、草稿感、内容过少等问题。"),
            _rule_item("doc_ui_screenshots_valid", "UI 截图符合要求", category="截图规范", severity="minor", prompt_hint="检查截图是否真实、是否裁掉状态栏和无关图标。"),
        ],
        "llm_focus": "关注说明文档结构完整性、术语统一性和内容可信度。",
    },
    "agreement": {
        "title": "协议与权属规范",
        "objective": "检查合作协议、审批表和权属材料中的主体、顺序、日期、签章和表述是否合规。",
        "rules": [
            _rule_item("agreement_alias_consistent", "代称体系统一", category="协议文本", severity="moderate", prompt_hint="检查协议是否统一使用甲乙丙丁等一套代称，禁止混用。"),
            _rule_item("agreement_party_order", "协议各方顺序正确", category="排序关系", severity="severe", prompt_hint="检查甲乙方顺序是否与信息采集表和系统填报一致。"),
            _rule_item("agreement_key_people", "关键人员完整", category="人员要素", severity="moderate", prompt_hint="检查指导老师、负责人等关键人员是否按要求出现。"),
            _rule_item("agreement_dates_valid", "签署日期逻辑合理", category="日期逻辑", severity="severe", prompt_hint="检查签署时间、开发完成时间、申请时间之间的逻辑是否合理。"),
            _rule_item("agreement_stamp_signature", "鲜章和手签达标", category="签章要求", severity="severe", prompt_hint="检查是否存在鲜章、手签，避免电子章和打印体签名。"),
            _rule_item("agreement_sensitive_terms", "敏感词已替换", category="敏感词排查", severity="moderate", prompt_hint="排查不合规词汇和容易引发误解的业务表述。"),
            _rule_item("agreement_approval_sheet", "审批手续齐全", category="审批手续", severity="moderate", prompt_hint="检查是否有科研合同审批表，以及技术开发合同勾选情况。"),
            _rule_item("agreement_typo_terms", "协议错别字和术语问题", category="文字质量", severity="minor", prompt_hint="检查签定/签订等错别字和不规范表述。"),
        ],
        "llm_focus": "突出主体关系、权属链条、日期逻辑和签章风险。",
    },
    "online_filing": {
        "title": "在线填报信息审查",
        "objective": "检查在线填报中的分类、开发方式、主体类型、申请日期和地址信息是否与材料口径一致。",
        "rules": [
            _rule_item("online_category_valid", "软件分类选择正确", category="分类准确性", severity="moderate", prompt_hint="检查是否选择了合适的软件分类，例如应用软件。"),
            _rule_item("online_development_mode_valid", "开发方式选择正确", category="开发方式", severity="moderate", prompt_hint="检查是否与实际情况一致，例如原创、合作开发等。"),
            _rule_item("online_subject_type_valid", "主体类型选择正确", category="主体类型", severity="moderate", prompt_hint="检查学校/公司等主体类型是否填写正确。"),
            _rule_item("online_address_precise", "地址信息足够精确", category="地址精度", severity="minor", prompt_hint="检查地址是否至少精确到省、市、区县。"),
            _rule_item("online_dates_consistent", "填报日期与材料口径一致", category="日期口径", severity="severe", prompt_hint="检查在线填报中的关键日期是否与信息采集表、协议一致。"),
        ],
        "llm_focus": "如果缺少在线填报数据，需要明确标注这一维度未覆盖；如果已有数据，优先比对分类、主体、日期和地址精度。",
    },
    "ai": {
        "title": "AI 补充研判",
        "objective": "在规则结论基础上补充高风险问题归纳、优先级判断和建议动作，避免遗漏隐性风险。",
        "rules": [
            _rule_item("ai_return_level", "输出退回级问题", category="结论结构", severity="severe", prompt_hint="将会导致直接退回的问题单独归类输出。"),
            _rule_item("ai_return_naive", "输出弱智问题", category="结论结构", severity="moderate", prompt_hint="将影响专业感但不一定退回的问题单独归类。"),
            _rule_item("ai_return_warning", "输出警告项", category="结论结构", severity="minor", prompt_hint="将可优化但非阻塞的问题单独归类。"),
            _rule_item("ai_actionable_advice", "结论要能直接修改", category="输出要求", severity="moderate", prompt_hint="用操作性语言说明哪里不对、怎么改。"),
            _rule_item("ai_boundary_notice", "信息不足要说明边界", category="输出要求", severity="minor", prompt_hint="如果无法判断，必须明确说出缺少哪类材料或证据。"),
        ],
        "llm_focus": "压缩总结最重要的问题、影响和建议动作，并按业务级别归类。",
    },
}


def _default_rule_items(key: str) -> list[dict[str, Any]]:
    return [dict(item) for item in list(DIMENSION_RULE_DEFAULTS.get(key, {}).get("rules", []) or [])]


def _normalize_rule_items(key: str, raw_rules: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    default_items = _default_rule_items(key)
    default_map = {str(item.get("key", "") or ""): dict(item) for item in default_items}
    raw_map = {str(item.get("key", "") or ""): dict(item) for item in list(raw_rules or []) if str(item.get("key", "") or "").strip()}
    normalized: list[dict[str, Any]] = []
    for default_item in default_items:
        item_key = str(default_item.get("key", "") or "")
        payload = {**default_item, **raw_map.get(item_key, {})}
        normalized.append(
            {
                "key": item_key,
                "title": str(payload.get("title", default_item.get("title", item_key)) or default_item.get("title", item_key)).strip()[:80],
                "category": str(payload.get("category", default_item.get("category", "")) or default_item.get("category", "")).strip()[:40],
                "severity": str(payload.get("severity", default_item.get("severity", "moderate")) or default_item.get("severity", "moderate")).strip()[:20],
                "prompt_hint": str(payload.get("prompt_hint", default_item.get("prompt_hint", "")) or default_item.get("prompt_hint", "")).strip()[:300],
                "enabled": bool(payload.get("enabled", default_item.get("enabled", True))),
            }
        )
    return normalized


def _build_checkpoints_from_items(items: list[dict[str, Any]]) -> list[str]:
    checkpoints: list[str] = []
    for item in items:
        if not item.get("enabled", True):
            continue
        title = str(item.get("title", "") or "").strip()
        hint = str(item.get("prompt_hint", "") or "").strip()
        if title and hint:
            checkpoints.append(f"{title}：{hint}")
        elif title:
            checkpoints.append(title)
        elif hint:
            checkpoints.append(hint)
    return checkpoints[:12]


def _normalize_rule_entry(key: str, raw: dict[str, Any] | None) -> dict[str, Any]:
    default = dict(DIMENSION_RULE_DEFAULTS.get(key, {}))
    payload = dict(raw or {})
    rules = _normalize_rule_items(key, payload.get("rules"))
    checkpoints_raw = payload.get("checkpoints")
    if isinstance(checkpoints_raw, str):
        checkpoints = [line.strip(" -\t") for line in checkpoints_raw.splitlines() if line.strip()]
    elif checkpoints_raw is not None:
        checkpoints = [str(item).strip() for item in list(checkpoints_raw or []) if str(item).strip()]
    else:
        checkpoints = _build_checkpoints_from_items(rules)
    if not checkpoints:
        checkpoints = _build_checkpoints_from_items(rules)

    return {
        "key": key,
        "title": str(payload.get("title", default.get("title", key)) or default.get("title", key)).strip()[:40],
        "objective": str(payload.get("objective", default.get("objective", "")) or default.get("objective", "")).strip()[:300],
        "checkpoints": checkpoints[:12],
        "llm_focus": str(payload.get("llm_focus", default.get("llm_focus", "")) or default.get("llm_focus", "")).strip()[:300],
        "rules": rules,
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


def parse_dimension_rule_items_from_form(form_data, dimension_key: str) -> list[dict[str, Any]]:
    default_items = _default_rule_items(dimension_key)
    parsed: list[dict[str, Any]] = []
    for item in default_items:
        item_key = str(item.get("key", "") or "")
        base = f"rule_{dimension_key}_item_{item_key}"
        enabled_raw = str(form_data.get(f"{base}_enabled", "") or "").strip()
        title = str(form_data.get(f"{base}_title", item.get("title", "")) or item.get("title", "")).strip()
        prompt_hint = str(form_data.get(f"{base}_prompt_hint", item.get("prompt_hint", "")) or item.get("prompt_hint", "")).strip()
        severity = str(form_data.get(f"{base}_severity", item.get("severity", "moderate")) or item.get("severity", "moderate")).strip()
        parsed.append(
            {
                "key": item_key,
                "title": title,
                "category": str(item.get("category", "") or ""),
                "severity": severity,
                "prompt_hint": prompt_hint,
                "enabled": bool(enabled_raw),
            }
        )
    return parsed


__all__ = [
    "DIMENSION_RULE_DEFAULTS",
    "default_dimension_rule",
    "default_dimension_rulebook",
    "dimension_rulebook_from_profile",
    "format_rule_checkpoints",
    "normalize_dimension_rulebook",
    "parse_dimension_rule_items_from_form",
    "reset_profile_dimension_rule",
    "update_profile_dimension_rule",
]
