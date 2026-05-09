from __future__ import annotations

import re
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
            _rule_item("missing_fields_listed", "缺失字段要点化", category="输出要求", severity="minor", prompt_hint="如果有缺失字段，结论里必须明确指出缺的是哪一项。"),
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
        "objective": "检查源代码材料是否可读、格式是否达标、是否完成脱敏，并能支撑功能真实性判断。",
        "rules": [
            _rule_item("code_readable", "源码内容可读", category="可读性", severity="severe", prompt_hint="检查源码是否存在乱码、异常字符或无法阅读的内容。"),
            _rule_item("code_format_clean", "源码格式符合提交规范", category="格式规范", severity="moderate", prompt_hint="检查行首空格、连续空行、行号等格式问题。"),
            _rule_item("code_page_strategy", "页数截取方式合理", category="页数策略", severity="severe", prompt_hint="如果总页数超过 60 页，检查是否为前 30 页加后 30 页。"),
            _rule_item("code_desensitized", "敏感信息已脱敏", category="脱敏规范", severity="severe", prompt_hint="重点排查密码、IP、Token、手机号、邮箱等敏感信息。"),
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


DIMENSION_GUIDANCE_DEFAULTS = {
    "identity": {
        "evidence_targets": ["信息采集表首页", "设计文档封面或页眉", "源代码页眉", "合作协议标题与主体落款", "在线填报截图或导出字段"],
        "common_failures": ["软件全称少字、多字或别名混用", "版本号大小写不一致，如 V1.0 与 v1.0", "申请主体名称缺简称/全称不一致", "缺字段但结论未点名缺的是什么"],
        "operator_notes": ["先统一软件全称和版本号，再处理其他维度。", "如果基础字段提取不稳，不要直接重跑，先人工修正识别结果。"],
    },
    "completeness": {
        "evidence_targets": ["批次材料清单", "信息采集表", "源代码材料", "设计文档或用户手册", "合作协议及审批表"],
        "common_failures": ["缺少信息采集表或源代码", "材料已上传但类型识别错误", "只有协议没有正文支撑，导致无法形成完整结论", "未知材料未提示人工确认"],
        "operator_notes": ["先补齐材料，再做高成本分析。", "材料类型不确定时，优先人工归类，避免错判进入后续链路。"],
    },
    "consistency": {
        "evidence_targets": ["四份材料中的软件全称", "版本号写法", "开发完成日期", "申请人排序", "关键术语与功能名称"],
        "common_failures": ["三个文档名称一致，但协议名称不一致", "版本号前后混用大小写", "协议顺序与信息采集表顺序不一致", "术语前文写系统，后文写平台或 APP"],
        "operator_notes": ["这类问题通常最影响提交，建议优先修。", "如果存在多处冲突，结果页应按同一口径统一回改，不要逐个零碎修。"],
    },
    "source_code": {
        "evidence_targets": ["导出的源代码 PDF", "页眉与行号", "敏感变量和值", "核心功能实现片段", "前 30 页与后 30 页截取策略"],
        "common_failures": ["密码、Token、IP 未脱敏", "只有零散代码片段，没有关键逻辑", "页数超过 60 页但只提交前半段", "注释凑数、空行过多或排版异常"],
        "operator_notes": ["先拿脱敏件审查，再决定是否进入综合分析。", "代码问题既要看格式，也要看是否能支撑文档宣称功能。"],
    },
    "software_doc": {
        "evidence_targets": ["封面与目录", "运行环境章节", "安装说明章节", "页眉页脚", "UI 截图区域"],
        "common_failures": ["缺少运行环境或安装说明", "页数明显不足或过长", "系统/平台/APP 混用", "截图带状态栏、电池、运营商等无关元素"],
        "operator_notes": ["说明文档更适合先看结构，再看术语和截图。", "如果文档功能描述很多，记得回查代码是否真有对应实现。"],
    },
    "agreement": {
        "evidence_targets": ["协议首页主体信息", "甲乙方排序", "签署日期", "签章与手写签名", "审批表或合同类型勾选"],
        "common_failures": ["协议代称混用", "签订时间离申请时间过近", "缺鲜章或只用了电子章", "存在签定等错别字，或顺序与信息采集表冲突"],
        "operator_notes": ["协议问题往往既是文字问题，也是权属问题。", "先确认顺序和日期，再看签章、人员和术语。"],
    },
    "online_filing": {
        "evidence_targets": ["在线填报截图", "分类与开发方式字段", "主体类型字段", "完成日期与申请日期", "地址和证书邮寄地址"],
        "common_failures": ["应用软件误选成工具软件", "主体类型与学校/公司性质不匹配", "完成日期与材料不一致", "地址只写到省或市，精度不够"],
        "operator_notes": ["如果当前批次没有在线填报数据，要明确标记未覆盖。", "一旦有在线填报信息，优先核对与信息采集表的一致性。"],
    },
    "ai": {
        "evidence_targets": ["规则引擎问题清单", "跨材料冲突项", "各维度摘要", "材料覆盖情况", "模型补充判断"],
        "common_failures": ["只给结论，不说问题在哪", "没有按退回级/弱智问题/警告项分类", "建议不可执行，用户不知道怎么改", "信息不足时没有说明边界"],
        "operator_notes": ["这个维度不是替代规则，而是把规则结果翻译成更可执行的结论。", "如果前置证据不足，AI 输出必须保守。"],
    },
}


GUIDANCE_FIELDS = ("evidence_targets", "common_failures", "operator_notes")


def _default_rule_items(key: str) -> list[dict[str, Any]]:
    return [dict(item) for item in list(DIMENSION_RULE_DEFAULTS.get(key, {}).get("rules", []) or [])]


def _default_guidance_list(key: str, field: str) -> list[str]:
    return [str(item).strip() for item in list(DIMENSION_GUIDANCE_DEFAULTS.get(key, {}).get(field, []) or []) if str(item).strip()]


def _normalize_guidance_list(key: str, payload: dict[str, Any], field: str) -> list[str]:
    raw_value = payload.get(field)
    if isinstance(raw_value, str):
        items = [line.strip(" -\t") for line in raw_value.splitlines() if line.strip(" -\t")]
    elif raw_value is None:
        items = _default_guidance_list(key, field)
    else:
        items = [str(item).strip() for item in list(raw_value or []) if str(item).strip()]
    return items[:8] if items else _default_guidance_list(key, field)[:8]


def _normalize_rule_item_payload(default_item: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    item_key = str(payload.get("key", default_item.get("key", "")) or default_item.get("key", "")).strip()
    severity = str(payload.get("severity", default_item.get("severity", "moderate")) or default_item.get("severity", "moderate")).strip()
    if severity not in {"severe", "moderate", "minor"}:
        severity = "moderate"
    return {
        "key": item_key[:80],
        "title": str(payload.get("title", default_item.get("title", item_key)) or default_item.get("title", item_key)).strip()[:80],
        "category": str(payload.get("category", default_item.get("category", "")) or default_item.get("category", "")).strip()[:40],
        "severity": severity,
        "prompt_hint": str(payload.get("prompt_hint", default_item.get("prompt_hint", "")) or default_item.get("prompt_hint", "")).strip()[:300],
        "enabled": bool(payload.get("enabled", default_item.get("enabled", True))),
    }


def _slug_rule_key(title: str, existing: set[str]) -> str:
    base = re.sub(r"[^0-9a-zA-Z_]+", "_", str(title or "").strip().lower()).strip("_")
    if not base:
        base = "custom_rule"
    base = f"custom_{base}"[:56].strip("_") or "custom_rule"
    candidate = base
    index = 2
    while candidate in existing:
        candidate = f"{base}_{index}"[:80]
        index += 1
    existing.add(candidate)
    return candidate


def _normalize_rule_items(key: str, raw_rules: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    default_items = _default_rule_items(key)
    raw_map = {
        str(item.get("key", "") or ""): dict(item)
        for item in list(raw_rules or [])
        if str(item.get("key", "") or "").strip()
    }
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for default_item in default_items:
        item_key = str(default_item.get("key", "") or "")
        payload = {**default_item, **raw_map.get(item_key, {})}
        normalized.append(_normalize_rule_item_payload(default_item, payload))
        seen.add(item_key)
    for raw_item in list(raw_rules or []):
        item_key = str(raw_item.get("key", "") or "").strip()
        if not item_key or item_key in seen:
            continue
        normalized.append(_normalize_rule_item_payload({"key": item_key, "category": "自定义"}, dict(raw_item)))
        seen.add(item_key)
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

    normalized = {
        "key": key,
        "title": str(payload.get("title", default.get("title", key)) or default.get("title", key)).strip()[:40],
        "objective": str(payload.get("objective", default.get("objective", "")) or default.get("objective", "")).strip()[:300],
        "checkpoints": checkpoints[:12],
        "llm_focus": str(payload.get("llm_focus", default.get("llm_focus", "")) or default.get("llm_focus", "")).strip()[:300],
        "rules": rules,
    }
    for field in GUIDANCE_FIELDS:
        normalized[field] = _normalize_guidance_list(key, payload, field)
    return normalized


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


def format_rule_guidance_lines(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items if str(item).strip())


def parse_dimension_rule_items_from_form(form_data, dimension_key: str) -> list[dict[str, Any]]:
    default_items = _default_rule_items(dimension_key)
    default_map = {str(item.get("key", "") or ""): dict(item) for item in default_items}
    keys: list[str] = []
    for item in default_items:
        item_key = str(item.get("key", "") or "")
        if item_key:
            keys.append(item_key)
    hidden_keys = str(form_data.get(f"rule_{dimension_key}_item_keys", "") or "")
    for item_key in [item.strip() for item in hidden_keys.split(",") if item.strip()]:
        if item_key not in keys:
            keys.append(item_key)
    prefix = f"rule_{dimension_key}_item_"
    suffix = "_title"
    for name in list(form_data.keys()):
        name = str(name)
        if name.startswith(prefix) and name.endswith(suffix):
            item_key = name[len(prefix):-len(suffix)]
            if item_key and item_key not in keys:
                keys.append(item_key)

    parsed: list[dict[str, Any]] = []
    for item_key in keys:
        item = default_map.get(item_key, {"key": item_key, "category": str(form_data.get(f"rule_{dimension_key}_item_{item_key}_category", "自定义") or "自定义")})
        base = f"rule_{dimension_key}_item_{item_key}"
        enabled_raw = str(form_data.get(f"{base}_enabled", "") or "").strip()
        title = str(form_data.get(f"{base}_title", item.get("title", "")) or item.get("title", "")).strip()
        prompt_hint = str(form_data.get(f"{base}_prompt_hint", item.get("prompt_hint", "")) or item.get("prompt_hint", "")).strip()
        severity = str(form_data.get(f"{base}_severity", item.get("severity", "moderate")) or item.get("severity", "moderate")).strip()
        if not title and not prompt_hint:
            continue
        parsed.append(
            {
                "key": item_key,
                "title": title,
                "category": str(form_data.get(f"{base}_category", item.get("category", "")) or item.get("category", "")),
                "severity": severity,
                "prompt_hint": prompt_hint,
                "enabled": bool(enabled_raw),
            }
        )
    new_title = str(form_data.get(f"rule_{dimension_key}_new_title", "") or "").strip()
    new_prompt_hint = str(form_data.get(f"rule_{dimension_key}_new_prompt_hint", "") or "").strip()
    if new_title or new_prompt_hint:
        existing = {str(item.get("key", "") or "") for item in parsed}
        item_key = _slug_rule_key(new_title or new_prompt_hint, existing)
        parsed.append(
            {
                "key": item_key,
                "title": (new_title or "新规则")[:80],
                "category": "自定义",
                "severity": str(form_data.get(f"rule_{dimension_key}_new_severity", "moderate") or "moderate").strip(),
                "prompt_hint": new_prompt_hint[:300],
                "enabled": bool(str(form_data.get(f"rule_{dimension_key}_new_enabled", "") or "").strip()),
            }
        )
    return parsed


__all__ = [
    "DIMENSION_GUIDANCE_DEFAULTS",
    "DIMENSION_RULE_DEFAULTS",
    "GUIDANCE_FIELDS",
    "default_dimension_rule",
    "default_dimension_rulebook",
    "dimension_rulebook_from_profile",
    "format_rule_checkpoints",
    "format_rule_guidance_lines",
    "normalize_dimension_rulebook",
    "parse_dimension_rule_items_from_form",
    "reset_profile_dimension_rule",
    "update_profile_dimension_rule",
]
