from __future__ import annotations

from collections import Counter
from pathlib import Path

from app.core.services.business_review import business_level, summarize_business_levels
from app.core.services.review_dimensions import build_case_review_dimensions
from app.core.services.review_profile import normalize_review_profile, review_profile_summary
from app.core.services.runtime_store import store
from app.core.utils.text import escape_html
from app.web.prompt_views import render_prompt_snapshot
from app.web.view_helpers import (
    contract_markers,
    download_chip,
    empty_state,
    layout,
    list_pairs,
    metric_card,
    panel,
    pill,
    read_text_file,
    report_label,
    severity_label,
    status_tone,
    table,
    type_label,
)


def _issue_text(issue: dict, *keys: str, fallback: str = "-") -> str:
    for key in keys:
        value = str(issue.get(key, "") or "").strip()
        if value:
            return value
    return fallback


def _issue_dimension_key(issue: dict) -> str:
    rule_key = str(issue.get("rule_key", "") or "").strip().lower()
    if rule_key in {"software_name_present", "version_present", "company_present", "missing_fields_listed", "info_sensitive_terms"}:
        return "identity"
    if rule_key in {"software_name_exact_match", "version_exact_match", "completion_date_match", "party_order_match", "cross_material_terms_match"}:
        return "consistency"
    if rule_key.startswith("online_"):
        return "online_filing"
    if rule_key.startswith("agreement_"):
        return "agreement"
    if rule_key.startswith("doc_"):
        return "software_doc"
    if rule_key.startswith("code_"):
        return "source_code"
    text = _issue_text(issue, "rule", "title", "category", "desc", "message", "detail", fallback="").lower()
    if any(token in text for token in ["源码", "代码", "angle", "logic"]):
        return "source_code"
    if any(token in text for token in ["文档", "说明", "mediapipe", "命名"]):
        return "software_doc"
    if any(token in text for token in ["协议", "签订", "签定", "日期", "权属"]):
        return "agreement"
    if any(token in text for token in ["版本一致", "名称一致", "跨材料"]):
        return "consistency"
    if any(token in text for token in ["字段缺失", "软件名称", "申请主体", "基础信息"]):
        return "identity"
    return ""


def _find_prompt_rule_item(prompt_snapshot: dict, dimension_key: str, rule_key: str) -> dict:
    if not dimension_key or not rule_key:
        return {}
    for dimension in list(prompt_snapshot.get("active_dimensions", []) or []):
        if str(dimension.get("key", "") or "") != dimension_key:
            continue
        for item in list(dimension.get("rules", []) or []):
            if str(item.get("key", "") or "") == rule_key:
                return dict(item or {})
    return {}


def _business_issue_board(issues: list[dict]) -> str:
    groups = {
        "退回级问题": [],
        "弱智问题": [],
        "警告项": [],
    }
    for issue in issues:
        label, _ = business_level(issue)
        groups[label].append(issue)

    cards = []
    for title in ["退回级问题", "弱智问题", "警告项"]:
        tone = "danger" if title == "退回级问题" else ("warning" if title == "弱智问题" else "info")
        items = groups[title]
        if items:
            lines = "".join(
                f"<li>{escape_html(_issue_text(item, 'desc', 'message', 'detail', 'category'))}</li>"
                for item in items[:6]
            )
        else:
            lines = "<li>当前没有这一类问题。</li>"
        cards.append(
            '<article class="report-card">'
            '<div class="report-card-copy">'
            f"<strong>{escape_html(title)}</strong>"
            f"<span>{pill(str(len(items)), tone)}</span>"
            "</div>"
            f'<div class="rule-checkpoint-list"><ul>{lines}</ul></div>'
            "</article>"
        )
    return f'<div class="report-card-grid">{"".join(cards)}</div>'


def _friendly_issue_summary(issue: dict, materials: list[dict]) -> tuple[str, str]:
    rule_key = str(issue.get("rule_key", "") or "").strip()
    text = _issue_text(issue, "desc", "message", "detail", fallback="")
    category = _issue_text(issue, "category", "title", "rule", fallback="问题")
    normalized = f"{category} {text}".lower()
    material_count = max(len(materials), 1)

    if rule_key == "party_order_match":
        return ("合作协议顺序和信息采集表顺序不一致", "统一协议中的甲乙方排序，以及信息采集表和系统填报中的申请人顺序。")
    if rule_key == "doc_required_sections":
        return ("说明文档缺少必备章节", "补齐运行环境、安装说明或初始化步骤等硬性章节。")
    if rule_key == "doc_page_count":
        return ("说明文档页数不在建议区间内", "补齐或精简说明文档内容，让页数更接近常规提交范围。")
    if rule_key == "doc_ui_screenshots_valid":
        return ("说明文档中的截图展示不够规范", "补真实截图并裁掉状态栏、导航条等无关界面元素。")
    if rule_key == "code_desensitized":
        return ("源码中仍有敏感信息未脱敏", "先替换密码、token、手机号、邮箱和公网 IP，再重新提交审查。")
    if rule_key == "code_format_clean":
        return ("源码格式不符合提交规范", "整理行首空格、连续空行和行号后再导出提交。")
    if rule_key == "code_page_strategy":
        return ("源码页数截取方式不符合提交策略", "源码超过 60 页时，按前30页 + 后30页重新导出。")
    if rule_key == "agreement_approval_sheet":
        return ("合作协议相关审批手续不完整", "补齐审批表和技术开发合同类型表述，再重新检查协议链路。")
    if rule_key == "agreement_key_people":
        return ("合作协议缺少关键人员信息", "补充项目负责人、指导老师或关键责任人信息。")
    if rule_key.startswith("online_"):
        return ("在线填报信息需要同步修正", "核对在线填报中的分类、主体类型、日期和地址信息，并与材料保持一致。")
    if rule_key == "missing_fields_listed":
        return ("信息采集表基础信息不完整", "先补齐软件名称、版本号或申请主体，再继续做一致性核对。")
    if rule_key == "info_sensitive_terms":
        return ("信息采集表中存在敏感表述", "把敏感词替换为更合规的业务表述，再重新发起审查。")
    if "软件名称" in text and "不一致" in text:
        return (f"{material_count} 份材料中的软件名称不一致", "统一信息采集表、源码和说明文档中的软件名称写法。")
    if "版本" in text and "不一致" in text:
        return (f"{material_count} 份材料中的版本号不一致", "统一所有材料中的版本号和版本描述。")
    if "签定" in text or "签定" in normalized:
        return ("合作协议存在错别字", "将“签定”统一修正为“签订”，再复核全文用词。")
    if "多个不同日期" in text or ("日期" in text and "一致" in text):
        return ("合作协议中的日期前后不一致", "核对签署日期、生效日期和其他日期字段后统一。")
    if "距离申请日期过近" in text:
        return ("合作协议签署时间距离申请时间过近", "建议复核协议时间，避免显得像临时补签。")
    if "Media Pipe" in text or "mediapipe" in normalized:
        return ("说明文档中的术语写法不一致", "统一使用“MediaPipe”等正式术语，不要混用空格写法。")
    if "V1.0" in text and "V2.0" in text:
        return ("说明文档内部版本号前后不一致", "只保留一个正确版本号，并检查目录、封面、正文是否一致。")
    if "乱码" in text or "异常字符" in text:
        return ("源码存在乱码或异常字符", "先整理为可读源码文件，再继续做正式审查。")
    if "核心逻辑缺失" in category or "角度计算" in text or "关键逻辑" in text:
        return ("源码关键逻辑展示不足", "补充核心函数、入口逻辑或关键流程代码，避免只上传零散片段。")
    if "功能点与源码信号呼应不足" in text:
        return ("说明文档里的功能与源码呼应不足", "补充文档所述功能对应的核心代码或更有代表性的源码片段。")
    return (text or category or "发现待修正问题", "请根据命中的规则和原文证据逐项修正。")


def _dimension_diagnosis(item: dict) -> tuple[str, str] | None:
    status = str(item.get("status", "") or "")
    tone = str(item.get("tone", "neutral") or "neutral")
    summary = str(item.get("summary", "") or "").strip()
    findings = [str(text).strip() for text in list(item.get("findings", []) or []) if str(text).strip()]
    title = str(item.get("title", "") or "审查维度")
    if tone not in {"warning", "danger"} and status not in {"需要复核", "材料不足", "缺少主索引", "存在冲突"}:
        return None
    if title == "材料完整性":
        return ("材料还不完整", summary or "核心材料缺失，暂时无法完成完整审查。")
    if title == "基础信息完整性":
        return ("基础信息还不完整", summary or "软件名称、版本号或申请主体仍需补齐。")
    if title == "跨材料一致性":
        return ("多份材料之间存在内容不一致", findings[0] if findings else (summary or "请统一名称、版本和关键术语。"))
    if title == "源码可审查性":
        return ("源码材料还不适合直接审查", findings[0] if findings else (summary or "请先补全或清洗源码。"))
    if title == "说明文档规范":
        return ("说明文档存在规范性问题", findings[0] if findings else (summary or "请统一版本、术语和文档表述。"))
    if title == "协议与权属规范":
        return ("协议材料存在待修正项", findings[0] if findings else (summary or "请核对协议日期、用词和签署信息。"))
    if title == "在线填报信息审查":
        if status in {"未覆盖", "未提供"}:
            return ("在线填报信息尚未录入", findings[0] if findings else (summary or "先录入在线填报字段，再做分类、日期和主体类型核对。"))
        return ("在线填报信息需要同步修正", findings[0] if findings else (summary or "请同步核对分类、日期、主体类型和地址精度。"))
    return (f"{title}存在待处理项", findings[0] if findings else (summary or "请按本维度结果继续修正。"))


def _issue_source_label(issue: dict) -> tuple[str, str]:
    material_name = str(issue.get("material_name", "") or "").strip()
    material_type = str(issue.get("material_type", "") or "").strip()
    if material_name:
        tone = "info"
        if material_type == "source_code":
            tone = "warning"
        elif material_type == "agreement":
            tone = "danger"
        return (material_name, tone)
    if material_type:
        tone = "info"
        if material_type == "source_code":
            tone = "warning"
        elif material_type == "agreement":
            tone = "danger"
        return (type_label(material_type), tone)
    dimension = _issue_dimension_key(issue)
    if dimension == "consistency":
        return ("跨材料比对", "warning")
    if dimension == "online_filing":
        return ("在线填报", "info")
    return ("规则归纳", "neutral")


def _issue_source_board(issues: list[dict]) -> str:
    if not issues:
        return empty_state("暂无来源分布", "")
    groups: dict[str, list[dict]] = {}
    tones: dict[str, str] = {}
    for issue in issues:
        label, tone = _issue_source_label(issue)
        groups.setdefault(label, []).append(issue)
        tones[label] = tone
    cards = []
    for label, items in sorted(groups.items(), key=lambda pair: len(pair[1]), reverse=True):
        lines = "".join(
            f"<li>{escape_html(_issue_text(item, 'desc', 'message', 'detail', 'category'))}</li>"
            for item in items[:4]
        )
        cards.append(
            '<article class="report-card">'
            '<div class="report-card-copy">'
            f"<strong>{escape_html(label)}</strong>"
            f"<span>{pill(str(len(items)), tones.get(label, 'neutral'))}</span>"
            "</div>"
            f'<div class="rule-checkpoint-list"><ul>{lines}</ul></div>'
            "</article>"
        )
    return f'<div class="report-card-grid">{"".join(cards)}</div>'


def _issue_fix_summary(issue: dict, materials: list[dict]) -> tuple[str, str, str]:
    title, action = _friendly_issue_summary(issue, materials)
    material_label = _issue_material_label(issue)
    return material_label, title, action


def _material_fix_plan_board(
    issues: list[dict],
    materials: list[dict],
    submission_id: str,
    case_id: str,
) -> str:
    if not issues:
        return empty_state("暂无修复清单", "")

    grouped: dict[str, list[tuple[str, str, dict]]] = {}
    for issue in issues:
        material_label, title, action = _issue_fix_summary(issue, materials)
        grouped.setdefault(material_label, []).append((title, action, issue))

    cards = []
    for material_label, items in sorted(grouped.items(), key=lambda pair: len(pair[1]), reverse=True):
        lines = []
        seen: set[tuple[str, str]] = set()
        for title, action, issue in items:
            key = (title, action)
            if key in seen:
                continue
            seen.add(key)
            lines.append(
                "<li>"
                f"<strong>{escape_html(title)}</strong>"
                f"<span class=\"table-subtext\">{escape_html(action)}</span>"
                "</li>"
            )
            if len(lines) >= 4:
                break
        actions = ['<a class="button-secondary button-compact" href="/submissions/' + escape_html(submission_id) + '/materials">查看材料</a>'] if submission_id else []
        if submission_id and case_id:
            first_issue = items[0][2]
            dimension_key = _issue_dimension_key(first_issue)
            if dimension_key:
                actions.append(
                    f'<a class="button-secondary button-compact" href="/submissions/{escape_html(submission_id)}/review-rules/{escape_html(dimension_key)}?case_id={escape_html(case_id)}">调整规则</a>'
                )
        cards.append(
            '<article class="report-card">'
            '<div class="report-card-copy">'
            f"<strong>{escape_html(material_label)}</strong>"
            f"<span>{pill(str(len(items)), 'warning' if len(items) > 1 else 'info')}</span>"
            "</div>"
            f'<div class="rule-checkpoint-list"><ul>{"".join(lines) or "<li>-</li>"}</ul></div>'
            f'<div class="inline-actions">{"".join(actions)}</div>'
            "</article>"
        )
    return f'<div class="report-card-grid">{"".join(cards)}</div>'


def _friendly_diagnosis_panel(issues: list[dict], review_dimensions: list[dict], materials: list[dict]) -> str:
    diagnoses: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str]] = set()

    for item in review_dimensions:
        diagnosis = _dimension_diagnosis(item)
        if not diagnosis:
            continue
        key = (diagnosis[0], diagnosis[1])
        if key in seen:
            continue
        seen.add(key)
        diagnoses.append((diagnosis[0], diagnosis[1], str(item.get("tone", "warning") or "warning")))

    for issue in issues:
        title, action = _friendly_issue_summary(issue, materials)
        key = (title, action)
        if key in seen:
            continue
        seen.add(key)
        _, tone = business_level(issue)
        diagnoses.append((title, action, tone))

    if not diagnoses:
        return empty_state("暂无优先修正项", "")

    cards = []
    for index, (title, action, tone) in enumerate(diagnoses[:8], start=1):
        cards.append(
            '<article class="report-card">'
            '<div class="report-card-copy">'
            f"<strong>{index}. {escape_html(title)}</strong>"
            f"<span>{pill('优先处理' if tone in {'danger', 'warning'} else '提示', tone)}</span>"
            "</div>"
            '<div class="rule-checkpoint-list">'
            f"<p>{escape_html(action)}</p>"
            "</div>"
            "</article>"
        )
    return f'<div class="report-card-grid">{"".join(cards)}</div>'


def _rule_title_for_issue(issue: dict, review_dimensions: list[dict], prompt_snapshot: dict) -> str:
    dimension_key = _issue_dimension_key(issue)
    rule_key = str(issue.get("rule_key", "") or "").strip()
    rule_item = _find_prompt_rule_item(prompt_snapshot, dimension_key, rule_key)
    if rule_item:
        return str(rule_item.get("title", "") or rule_key or "规则引擎")
    for item in review_dimensions:
        if str(item.get("key", "") or "") == dimension_key:
            return str(item.get("title", "") or dimension_key or "规则引擎")
    return str(issue.get("category", "") or issue.get("title", "") or "规则引擎")


def _prompt_dimension_item(prompt_snapshot: dict, dimension_key: str) -> dict:
    for item in list(prompt_snapshot.get("active_dimensions", []) or []):
        if str(item.get("key", "") or "") == dimension_key:
            return dict(item or {})
    return {}


def _issue_material_label(issue: dict) -> str:
    material_name = str(issue.get("material_name", "") or "").strip()
    if material_name:
        return material_name
    material_type = str(issue.get("material_type", "") or "").strip()
    if material_type:
        return type_label(material_type)
    dimension_key = _issue_dimension_key(issue)
    if dimension_key == "consistency":
        return "跨材料比对"
    if dimension_key == "online_filing":
        return "在线填报"
    return "规则归纳"


def _issue_fix_actions(submission_id: str, case_id: str, dimension_key: str, issue: dict) -> str:
    actions: list[str] = []
    if submission_id:
        actions.append(
            f'<a class="button-secondary button-compact" href="/submissions/{escape_html(submission_id)}/materials">查看材料</a>'
        )
    if submission_id and case_id and dimension_key:
        actions.append(
            f'<a class="button-secondary button-compact" href="/submissions/{escape_html(submission_id)}/review-rules/{escape_html(dimension_key)}?case_id={escape_html(case_id)}">编辑规则</a>'
        )
    return f'<div class="inline-actions">{"".join(actions)}</div>' if actions else ""


def _issue_precision_hints(issue: dict, prompt_snapshot: dict) -> list[str]:
    hints: list[str] = []
    for key in ("anchor_hint", "field_label", "section_label"):
        value = str(issue.get(key, "") or "").strip()
        if value and value not in hints:
            hints.append(value)
    evidence_anchor = dict(issue.get("evidence_anchor", {}) or {})
    page = evidence_anchor.get("page")
    if str(page).strip():
        hints.append(f"约第 {page} 页")
    line = evidence_anchor.get("line")
    if str(line).strip():
        hints.append(f"第 {line} 行附近")
    for key in ("field", "section", "material_area", "hint"):
        value = str(evidence_anchor.get(key, "") or "").strip()
        if value and value not in hints:
            hints.append(value)
    rule_key = str(issue.get("rule_key", "") or "").strip().lower()
    prompt_item = _prompt_dimension_item(prompt_snapshot, _issue_dimension_key(issue))
    hint_map = {
        "software_name_present": ["信息采集表的软件名称字段", "设计文档封面或页眉", "源代码页眉"],
        "version_present": ["信息采集表版本号字段", "设计文档页眉版本号", "源代码页眉版本号"],
        "company_present": ["信息采集表申请主体字段", "合作协议主体名称", "在线填报主体字段"],
        "missing_fields_listed": ["信息采集表首页基础字段", "软件名称/版本号/申请主体字段"],
        "software_name_exact_match": ["信息采集表的软件名称字段", "设计文档封面或页眉", "源代码页眉", "合作协议标题或首页主体"],
        "version_exact_match": ["信息采集表版本号字段", "设计文档页眉版本号", "源代码页眉版本号", "合作协议中的版本号"],
        "completion_date_match": ["信息采集表开发完成日期", "合作协议日期字段", "在线填报完成日期"],
        "party_order_match": ["合作协议甲乙方顺序", "信息采集表申请人顺序", "在线填报申请人顺序"],
        "cross_material_terms_match": ["设计文档功能章节", "协议与信息采集表中的术语写法", "源代码中的核心命名"],
        "doc_page_count": ["说明文档目录与正文总页数", "说明文档页码区间"],
        "doc_required_sections": ["说明文档“运行环境”章节", "说明文档“安装说明/初始化步骤”章节"],
        "doc_terms_consistent": ["说明文档中的系统/平台/APP术语", "标题、目录和正文中的名称写法"],
        "doc_header_footer_valid": ["说明文档页眉", "说明文档页脚连续页码"],
        "doc_ui_screenshots_valid": ["说明文档截图区域", "截图顶部状态栏和底部导航条"],
        "doc_text_quality": ["说明文档正文段落", "术语、错别字和描述完整度"],
        "code_desensitized": ["源代码中的配置常量", "数据库连接信息", "Token/手机号/邮箱等敏感值"],
        "code_format_clean": ["源代码 PDF 行号区域", "行首缩进和连续空行"],
        "code_page_strategy": ["源代码 PDF 页码标记", "前30页与后30页截取范围"],
        "code_logic_supports_doc": ["说明文档功能章节", "对应核心函数或入口逻辑"],
        "code_comment_ratio_reasonable": ["源代码注释段落", "核心代码与注释比例"],
        "agreement_alias_consistent": ["合作协议甲乙方代称", "全文主体称谓"],
        "agreement_party_order": ["合作协议甲乙方顺序", "信息采集表申请人顺序"],
        "agreement_key_people": ["合作协议项目成员段落", "指导老师/负责人信息"],
        "agreement_dates_valid": ["合作协议签署日期", "开发完成日期与申请日期"],
        "agreement_stamp_signature": ["合作协议签章页", "手写签名位置"],
        "agreement_approval_sheet": ["合作协议附件审批表", "合同类型勾选项"],
        "agreement_typo_terms": ["合作协议正文术语", "签订/签定等高频词"],
        "online_category_valid": ["在线填报软件分类字段"],
        "online_development_mode_valid": ["在线填报开发方式字段"],
        "online_subject_type_valid": ["在线填报主体类型字段"],
        "online_address_precise": ["在线填报地址字段", "电子证书地址字段"],
        "online_dates_consistent": ["在线填报完成日期", "在线填报申请日期", "信息采集表日期字段"],
    }
    for item in list(hint_map.get(rule_key, [])):
        if item and item not in hints:
            hints.append(item)
    for target in list(prompt_item.get("evidence_targets", []) or []):
        target_text = str(target).strip()
        if target_text and target_text not in hints:
            hints.append(target_text)
    return hints[:4]


def _issue_evidence_points(issue: dict, review_dimensions: list[dict], prompt_snapshot: dict) -> list[str]:
    points: list[str] = []
    excerpt = str(issue.get("evidence_excerpt", "") or dict(issue.get("evidence_anchor", {}) or {}).get("excerpt", "") or "").strip()
    if excerpt:
        points.append(f"摘录：{excerpt}")
    detail = _issue_text(issue, "desc", "message", "detail", fallback="")
    if detail:
        normalized = detail.replace("；", ". ").replace(";", ". ").replace("\n", ". ")
        for chunk in normalized.split("."):
            text = str(chunk).strip(" ：:")
            if text and text not in points:
                points.append(text)
            if len(points) >= 3:
                break

    material_label = _issue_material_label(issue)
    if material_label:
        points.append(f"命中材料：{material_label}")

    dimension_key = _issue_dimension_key(issue)
    prompt_item = _prompt_dimension_item(prompt_snapshot, dimension_key)
    for hint in _issue_precision_hints(issue, prompt_snapshot):
        marker = f"定位：{hint}"
        if marker not in points:
            points.append(marker)
        if len(points) >= 5:
            return points[:5]
    for target in list(prompt_item.get("evidence_targets", []) or []):
        target_text = str(target).strip()
        marker = f"重点回查：{target_text}"
        if target_text and marker not in points:
            points.append(marker)
        if len(points) >= 5:
            return points[:5]

    for item in review_dimensions:
        if str(item.get("key", "") or "") != dimension_key:
            continue
        for finding in list(item.get("findings", []) or []):
            finding_text = str(finding).strip()
            if finding_text and finding_text not in points:
                points.append(finding_text)
            if len(points) >= 5:
                return points[:5]
        break
    return points[:5]


def _issue_explainer_board(
    issues: list[dict],
    review_dimensions: list[dict],
    prompt_snapshot: dict,
    submission_id: str,
    case_id: str,
) -> str:
    if not issues:
        return empty_state("暂无重点问题", "")

    cards = []
    for index, issue in enumerate(issues[:8], start=1):
        title, action = _friendly_issue_summary(issue, [])
        _, tone = business_level(issue)
        dimension_key = _issue_dimension_key(issue)
        prompt_item = _prompt_dimension_item(prompt_snapshot, dimension_key)
        evidence_points = _issue_evidence_points(issue, review_dimensions, prompt_snapshot)
        evidence_html = "".join(f"<li>{escape_html(text)}</li>" for text in evidence_points) or "<li>-</li>"
        rule_hint = str(prompt_item.get("llm_focus", "") or "").strip()
        fix_actions = _issue_fix_actions(submission_id, case_id, dimension_key, issue)
        cards.append(
            '<article class="report-card">'
            '<div class="report-card-copy">'
            f"<strong>{index}. {escape_html(title)}</strong>"
            f"<span>{pill(_rule_title_for_issue(issue, review_dimensions, prompt_snapshot), tone)}</span>"
            "</div>"
            '<div class="rule-checkpoint-list">'
            f"<p><strong>问题说明：</strong>{escape_html(_issue_text(issue, 'desc', 'message', 'detail', fallback='-'))}</p>"
            f"<p><strong>命中材料：</strong>{escape_html(_issue_material_label(issue))}</p>"
            f"<p><strong>建议动作：</strong>{escape_html(action)}</p>"
            f"<p><strong>规则关注点：</strong>{escape_html(rule_hint or '-')}</p>"
            f"<ul>{evidence_html}</ul>"
            f"{fix_actions}"
            "</div>"
            "</article>"
        )
    return f'<div class="report-card-grid">{"".join(cards)}</div>'


def _issue_snapshot_board(
    issues: list[dict],
    review_dimensions: list[dict],
    prompt_snapshot: dict,
    submission_id: str,
    case_id: str,
) -> str:
    if not issues:
        return empty_state("暂无重点问题", "")

    cards = []
    for index, issue in enumerate(issues[:3], start=1):
        title, action = _friendly_issue_summary(issue, [])
        dimension_key = _issue_dimension_key(issue)
        dimension_title_text = "-"
        for item in review_dimensions:
            if str(item.get("key", "") or "") == dimension_key:
                dimension_title_text = str(item.get("title", "") or "-")
                break
        evidence_points = _issue_evidence_points(issue, review_dimensions, prompt_snapshot)
        first_evidence = evidence_points[0] if evidence_points else _issue_text(issue, "desc", "message", "detail", fallback="-")
        _, tone = business_level(issue)
        fix_actions = _issue_fix_actions(submission_id, case_id, dimension_key, issue)
        cards.append(
            '<article class="report-card">'
            '<div class="report-card-copy">'
            f"<strong>{index}. {escape_html(title)}</strong>"
            f"<span>{pill(severity_label(_issue_text(issue, 'severity', fallback='minor')), tone)}</span>"
            "</div>"
            '<div class="rule-checkpoint-list">'
            f"<p><strong>哪里不对：</strong>{escape_html(_issue_text(issue, 'desc', 'message', 'detail', fallback='-'))}</p>"
            f"<p><strong>怎么发现的：</strong>{escape_html(first_evidence)}</p>"
            f"<p><strong>命中规则：</strong>{escape_html(_rule_title_for_issue(issue, review_dimensions, prompt_snapshot))}</p>"
            f"<p><strong>建议动作：</strong>{escape_html(action)}</p>"
            f"<p><strong>命中维度：</strong>{escape_html(dimension_title_text)}</p>"
            f"<p><strong>回查位置：</strong>{escape_html(_issue_material_label(issue))}</p>"
            f"{fix_actions}"
            "</div>"
            "</article>"
        )
    return f'<div class="report-card-grid">{"".join(cards)}</div>'


def _review_method_table(prompt_snapshot: dict) -> str:
    rows = [
        [
            escape_html(str(item.get("title", "") or item.get("key", "-"))),
            escape_html(str(item.get("objective", "") or "-")),
            escape_html(str(item.get("llm_focus", "") or "-")),
        ]
        for item in list(prompt_snapshot.get("active_dimensions", []) or [])
    ]
    if not rows:
        return empty_state("暂无审查维度数据", "")
    return table(["审查维度", "目标", "LLM 补充指令"], rows)


def _issue_trace_table(
    issues: list[dict],
    review_dimensions: list[dict],
    prompt_snapshot: dict,
    submission_id: str,
    case_id: str,
) -> str:
    if not issues:
        return empty_state("暂无问题", "")
    dimension_map = {str(item.get("key", "") or ""): dict(item or {}) for item in review_dimensions}
    prompt_map = {
        str(item.get("key", "") or ""): dict(item or {})
        for item in list(prompt_snapshot.get("active_dimensions", []) or [])
    }
    rows: list[list[str]] = []
    for issue in issues:
        dimension_key = _issue_dimension_key(issue)
        rule_key = str(issue.get("rule_key", "") or "").strip()
        dimension_item = dimension_map.get(dimension_key, {})
        prompt_item = prompt_map.get(dimension_key, {})
        rule_item = _find_prompt_rule_item(prompt_snapshot, dimension_key, rule_key)
        findings = list(dimension_item.get("findings", []) or [])
        evidence = escape_html(_issue_text(issue, "desc", "message", "detail"))
        if findings:
            evidence += f'<br><span class="table-subtext">依据：{escape_html(findings[0])}</span>'
        evidence += f'<br><span class="table-subtext">材料：{escape_html(_issue_material_label(issue))}</span>'
        precision_hints = _issue_precision_hints(issue, prompt_snapshot)
        if precision_hints:
            evidence += f'<br><span class="table-subtext">定位：{escape_html(precision_hints[0])}</span>'
        excerpt = str(issue.get("evidence_excerpt", "") or dict(issue.get("evidence_anchor", {}) or {}).get("excerpt", "") or "").strip()
        if excerpt:
            evidence += f'<br><span class="table-subtext">摘录：{escape_html(excerpt)}</span>'
        evidence_targets = list(prompt_item.get("evidence_targets", []) or [])
        if evidence_targets:
            evidence += f'<br><span class="table-subtext">建议回查：{escape_html(evidence_targets[0])}</span>'
        actions = _issue_fix_actions(submission_id, case_id, dimension_key, issue)
        rows.append(
            [
                pill(severity_label(_issue_text(issue, "severity", fallback="minor")), status_tone(_issue_text(issue, "severity", fallback="minor"))),
                escape_html(_issue_text(issue, "category", "title", "rule")),
                _dimension_rule_link(submission_id, case_id, dimension_item) if dimension_item else "-",
                escape_html(str(rule_item.get("title", "") or prompt_item.get("title", "") or dimension_item.get("title", "") or "规则引擎")),
                evidence,
                escape_html(_issue_text(issue, "suggest", fallback=str(prompt_item.get("llm_focus", "") or "建议结合原文复核并修正。"))) + (f"<br>{actions}" if actions else ""),
            ]
        )
    return table(["级别", "发现的问题", "命中维度", "命中规则", "怎么发现的", "建议动作"], rows)


def _dimension_evidence_board(review_dimensions: list[dict], prompt_snapshot: dict, submission_id: str, case_id: str) -> str:
    if not review_dimensions:
        return empty_state("暂无审查维度数据", "")
    prompt_map = {
        str(item.get("key", "") or ""): dict(item or {})
        for item in list(prompt_snapshot.get("active_dimensions", []) or [])
    }
    cards = []
    for item in review_dimensions:
        prompt_item = prompt_map.get(str(item.get("key", "") or ""), {})
        findings = list(item.get("findings", []) or [])
        finding_list = "".join(f"<li>{escape_html(text)}</li>" for text in findings[:4]) or "<li>-</li>"
        target_list = "".join(f"<li>{escape_html(text)}</li>" for text in list(prompt_item.get("evidence_targets", []) or [])[:3]) or "<li>-</li>"
        failure_list = "".join(f"<li>{escape_html(text)}</li>" for text in list(prompt_item.get("common_failures", []) or [])[:3]) or "<li>-</li>"
        cards.append(
            '<article class="report-card">'
            '<div class="report-card-copy">'
            f"<strong>{_dimension_rule_link(submission_id, case_id, item)}</strong>"
            f"<span>{pill(str(item.get('status', '') or '-'), str(item.get('tone', 'neutral') or 'neutral'))}</span>"
            "</div>"
            '<div class="rule-checkpoint-list">'
            f"<p>{escape_html(str(item.get('summary', '') or '-'))}</p>"
            f"<p><strong>审查目标：</strong>{escape_html(str(prompt_item.get('objective', '') or '-'))}</p>"
            f"<p><strong>重点回查：</strong></p><ul>{target_list}</ul>"
            f"<ul>{finding_list}</ul>"
            f"<p><strong>常见退回点：</strong></p><ul>{failure_list}</ul>"
            f"<p><strong>LLM 补充：</strong>{escape_html(str(prompt_item.get('llm_focus', '') or '-'))}</p>"
            "</div>"
            "</article>"
        )
    return f'<div class="report-card-grid">{"".join(cards)}</div>'


def _dimension_rule_link(submission_id: str, case_id: str, item: dict) -> str:
    key = str(item.get("key", "") or "")
    title = str(item.get("title", "") or key or "-")
    if not submission_id or not case_id or not key:
        return escape_html(title)
    return f'<a href="/submissions/{escape_html(submission_id)}/review-rules/{escape_html(key)}?case_id={escape_html(case_id)}">{escape_html(title)}</a>'


def _report_toolbar_legacy(report: dict) -> str:
    report_id = str(report.get("id", "") or "")
    return (
        '<div class="report-toolbar print-hidden">'
        f"{download_chip(f'/downloads/reports/{report_id}', '保存为 MD') if report_id else ''}"
        '<button class="button-secondary button-compact" type="button" data-print-page>保存为 PDF</button>'
        "</div>"
    )


def _raw_markdown_panel(report_content: str) -> str:
    return (
        '<div class="report-source">'
        '<details>'
        "<summary>原始 Markdown</summary>"
        f'<div class="report-panel"><pre>{escape_html(report_content or "当前没有可显示的报告内容。")}</pre></div>'
        "</details>"
        "</div>"
    )


def _fold_group(index: int, title: str, note: str, body: str, *, open_by_default: bool = False) -> str:
    open_attr = " open" if open_by_default else ""
    return (
        f'<details class="operator-group"{open_attr}>'
        "<summary>"
        f'<span class="operator-group-index">{index}</span>'
        "<div>"
        f"<strong>{escape_html(title)}</strong>"
        f"<small>{escape_html(note)}</small>"
        "</div>"
        "</summary>"
        f"{body}"
        "</details>"
    )


def _render_case_report(report: dict, report_content: str) -> tuple[str, str]:
    case = store.cases.get(str(report.get("scope_id", "") or ""))
    if not case:
        return "", empty_state("未找到关联项目", "当前报告对应的项目数据不存在。") + _raw_markdown_panel(report_content)

    case_payload = case.to_dict()
    materials = [store.materials[item_id].to_dict() for item_id in case.material_ids if item_id in store.materials]
    review_result = store.review_results.get(case.review_result_id)
    review_payload = review_result.to_dict() if review_result else {}
    review_profile = normalize_review_profile(review_payload.get("review_profile_snapshot", {}))
    prompt_snapshot = dict(review_payload.get("prompt_snapshot_json", {}) or {})
    issues = list(review_payload.get("issues_json", []) or [])
    business_summary = summarize_business_levels(issues)
    review_dimensions = build_case_review_dimensions(
        case_payload,
        materials,
        cross_material_issues=issues,
        ai_resolution=str(review_payload.get("ai_resolution", "") or ""),
        review_profile=review_profile,
    )
    source_submission_id = str(case.source_submission_id or "")
    case_id = str(case.id or "")

    metrics = "".join(
        [
            metric_card("评分", str(review_payload.get("score", "-")), "综合审查得分", "success", icon_name="trend"),
            metric_card("问题数", str(len(issues)), "需要关注的问题数量", "warning" if issues else "success", icon_name="alert"),
            metric_card("维度数", str(len(review_dimensions)), "本次审查覆盖的维度", "neutral", icon_name="shield"),
        ]
    )

    overview_pairs = [
        ("软件名称", escape_html(case_payload.get("software_name", "") or "-")),
        ("版本", escape_html(case_payload.get("version", "") or "-")),
        ("申请主体", escape_html(case_payload.get("company_name", "") or "-")),
        ("退回级问题", escape_html(str(business_summary.get("退回级问题", 0)))),
        ("弱智问题", escape_html(str(business_summary.get("弱智问题", 0)))),
        ("警告项", escape_html(str(business_summary.get("警告项", 0)))),
    ]
    conclusion_body = list_pairs(overview_pairs, css_class="dossier-list dossier-list-single") + list_pairs(
        [
            ("规则结论", escape_html(review_payload.get("rule_conclusion", "") or review_payload.get("conclusion", "") or "-")),
            ("AI 补充摘要", escape_html(review_payload.get("ai_summary", "") or "当前没有额外 AI 补充说明")),
        ],
        css_class="dossier-list dossier-list-single",
    )

    dimension_rows = [
        [
            _dimension_rule_link(source_submission_id, case_id, item),
            pill(str(item.get("status", "") or "-"), str(item.get("tone", "neutral") or "neutral")),
            escape_html(item.get("summary", "") or "-"),
        ]
        for item in review_dimensions
    ]
    issue_rows = [
        [
            pill(severity_label(str(issue.get("severity", "") or "minor")), status_tone(str(issue.get("severity", "") or "minor"))),
            escape_html(str(issue.get("title", "") or issue.get("rule", "") or issue.get("category", "") or "-")),
            escape_html(str(issue.get("message", "") or issue.get("detail", "") or issue.get("desc", "") or "-")),
        ]
        for issue in issues
    ]
    material_rows = [
        [
            escape_html(item.get("original_filename", "") or item.get("id", "material")),
            pill(type_label(item.get("material_type", "unknown")), status_tone(item.get("review_status", "unknown"))),
            escape_html(item.get("detected_software_name", "") or case_payload.get("software_name", "") or "-"),
        ]
        for item in materials
    ]

    profile_pairs = review_profile_summary(review_profile)
    friendly_diagnosis = _friendly_diagnosis_panel(issues, review_dimensions, materials)
    issue_snapshot = _issue_snapshot_board(issues, review_dimensions, prompt_snapshot, source_submission_id, case_id)
    business_issue_board = _business_issue_board(issues)
    source_issue_board = _issue_source_board(issues)
    material_fix_plan = _material_fix_plan_board(issues, materials, source_submission_id, case_id)
    issue_explainer = _issue_explainer_board(issues, review_dimensions, prompt_snapshot, source_submission_id, case_id)
    issue_trace = _issue_trace_table(issues, review_dimensions, prompt_snapshot, source_submission_id, case_id)
    evidence_board = _dimension_evidence_board(review_dimensions, prompt_snapshot, source_submission_id, case_id)
    method_table = _review_method_table(prompt_snapshot)
    rule_links = (
        '<div class="inline-actions">'
        + "".join(
            f'<a class="button-secondary button-compact" href="/submissions/{escape_html(source_submission_id)}/review-rules/{escape_html(item.get("key", ""))}?case_id={escape_html(case_id)}">{escape_html(item.get("title", item.get("key", "")))}规则</a>'
            for item in review_dimensions
        )
        + "</div>"
        if review_dimensions and source_submission_id and case_id
        else ""
    )

    advanced_groups = '<div class="operator-group-grid">'
    advanced_groups += _fold_group(
        1,
        "问题级别归类",
        "按退回级、弱智问题和警告项查看全量分组。",
        business_issue_board,
        open_by_default=False,
    )
    advanced_groups += _fold_group(
        2,
        "按材料来源看问题",
        "按说明文档、源代码、协议、信息采集表或跨材料来源拆开查看。",
        source_issue_board,
        open_by_default=False,
    )
    advanced_groups += _fold_group(
        3,
        "怎么判定出来的",
        "按维度查看证据链、摘要和模型关注点。",
        evidence_board,
        open_by_default=False,
    )
    advanced_groups += _fold_group(
        4,
        "用了哪些审查规则",
        "查看本次分析实际启用的规则和 LLM 关注点。",
        method_table,
        open_by_default=False,
    )
    advanced_groups += _fold_group(
        5,
        "审查维度",
        "查看每个审查维度当前的状态和摘要。",
        table(["审查维度", "当前状态", "摘要"], dimension_rows)
        if dimension_rows
        else empty_state("暂无审查维度", ""),
        open_by_default=False,
    )
    advanced_groups += _fold_group(
        6,
        "发现的问题",
        "保留完整的问题表，便于逐条复核。",
        table(["严重级别", "问题", "说明"], issue_rows)
        if issue_rows
        else empty_state("暂无跨材料问题", ""),
        open_by_default=False,
    )
    advanced_groups += _fold_group(
        7,
        "审查材料",
        "查看参与审查的材料清单和来源。",
        table(["文件名", "材料类型", "软件名称"], material_rows)
        if material_rows
        else empty_state("暂无材料", ""),
        open_by_default=False,
    )
    advanced_groups += _fold_group(
        8,
        "审查配置",
        "查看本次报告对应的规则和模式。",
        list_pairs(profile_pairs, css_class="dossier-list dossier-list-single") + rule_links,
        open_by_default=False,
    )
    advanced_groups += _fold_group(
        9,
        "LLM 审查提示词",
        "需要追查模型判断时再展开。",
        render_prompt_snapshot(prompt_snapshot) if prompt_snapshot else empty_state("暂无提示词快照", ""),
        open_by_default=False,
    )
    advanced_groups += _fold_group(
        10,
        "原始 Markdown",
        "如需核对原始导出内容再展开。",
        _raw_markdown_panel(report_content),
        open_by_default=False,
    )
    advanced_groups += "</div>"

    body = f"""
    <div class="report-rich">
      {_report_toolbar(report)}
      <div class="report-section-stack">
        {panel('审查结果', conclusion_body, kicker='核心结论', extra_class='span-12', icon_name='report', description='', panel_id='report-overview')}
        {panel('先改这些地方', friendly_diagnosis, kicker='直观诊断', extra_class='span-12', icon_name='alert', description='直接告诉你哪里不对，以及应该先改什么。', panel_id='report-diagnosis')}
        {panel('问题一眼看懂', issue_snapshot, kicker='3 个重点问题', extra_class='span-12', icon_name='search', description='把最关键的问题、证据、规则和建议动作压成一屏，先看这个再决定往下钻。', panel_id='report-snapshot')}
        {panel('按材料怎么改', material_fix_plan, kicker='修复清单', extra_class='span-12', icon_name='layers', description='把问题按材料归组，方便你一份一份改。', panel_id='report-fix-plan')}
        {panel('重点问题说明', issue_explainer, kicker='先看卡片', extra_class='span-12', icon_name='report', description='把重点问题直接翻译成人话，展示触发规则、判定依据和处理建议。', panel_id='report-explainer')}
        {panel('发现了什么不足', issue_trace, kicker='问题追踪', extra_class='span-12', icon_name='alert', description='直接展示问题、命中维度、规则依据和建议动作。', panel_id='report-trace')}
        {panel('更多信息', advanced_groups, kicker='按需展开', extra_class='span-12', icon_name='search', description='', panel_id='report-profile')}
      </div>
    </div>
    """
    return metrics, body


def _render_material_report(report: dict, report_content: str) -> tuple[str, str]:
    material = store.materials.get(str(report.get("scope_id", "") or ""))
    if not material:
        return "", empty_state("未找到关联材料", "当前报告对应的材料数据不存在。") + _raw_markdown_panel(report_content)

    material_payload = material.to_dict()
    parse_result = store.parse_results.get(material.id)
    parse_payload = parse_result.to_dict() if parse_result else {}
    metadata = dict(parse_payload.get("metadata_json", {}) or {})
    triage = dict(metadata.get("triage", {}) or {})
    parse_quality = dict(metadata.get("parse_quality", {}) or metadata.get("quality", {}) or {})
    issues = list(material_payload.get("issues", []) or [])

    metrics = "".join(
        [
            metric_card("材料类型", type_label(material_payload.get("material_type", "unknown")), "当前材料识别类型", "info", icon_name="file"),
            metric_card("解析质量", str(parse_quality.get("quality_level", "unknown")), "文本解析质量等级", "success", icon_name="bar"),
            metric_card("问题数", str(len(issues)), "当前材料识别的问题数", "warning" if issues else "success", icon_name="alert"),
        ]
    )

    issue_rows = [
        [
            pill(severity_label(str(issue.get("severity", "") or "minor")), status_tone(str(issue.get("severity", "") or "minor"))),
            escape_html(str(issue.get("title", "") or issue.get("rule", "") or issue.get("category", "") or "-")),
            escape_html(str(issue.get("message", "") or issue.get("detail", "") or issue.get("desc", "") or "-")),
        ]
        for issue in issues
    ]
    info_pairs = [
        ("文件名", escape_html(material_payload.get("original_filename", "") or "-")),
        ("材料类型", escape_html(type_label(material_payload.get("material_type", "unknown")))),
        ("软件名称", escape_html(material_payload.get("detected_software_name", "") or "-")),
        ("版本", escape_html(material_payload.get("detected_version", "") or "-")),
        ("解析质量", escape_html(str(parse_quality.get("quality_level", "unknown")))),
        ("建议人工复核", escape_html("是" if triage.get("needs_manual_review", False) else "否")),
    ]

    body = f"""
    <div class="report-rich">
      {_report_toolbar(report)}
      <div class="report-section-stack">
        {panel('审查结果', list_pairs(info_pairs, css_class='dossier-list dossier-list-single'), kicker='基本信息', extra_class='span-12', icon_name='layers', description='', panel_id='report-overview')}
        {panel('发现的问题', table(['严重级别', '问题', '说明'], issue_rows) if issue_rows else empty_state('当前未发现明显问题', '这份材料暂未识别出规则问题。'), kicker='问题结果', extra_class='span-12', icon_name='alert', description='', panel_id='report-issues')}
        {panel('原始 Markdown', _raw_markdown_panel(report_content), kicker='按需展开', extra_class='span-12', icon_name='file', description='', panel_id='report-source')}
      </div>
    </div>
    """
    return metrics, body


def _render_batch_report(report: dict, report_content: str) -> tuple[str, str]:
    submission = store.submissions.get(str(report.get("scope_id", "") or ""))
    if not submission:
        return "", empty_state("未找到关联批次", "当前报告对应的批次数据不存在。") + _raw_markdown_panel(report_content)

    submission_payload = submission.to_dict()
    materials = [store.materials[item_id].to_dict() for item_id in submission.material_ids if item_id in store.materials]
    type_counter = Counter(str(item.get("material_type", "unknown")) for item in materials)
    issue_total = sum(len(item.get("issues", []) or []) for item in materials)
    rows = [
        [
            escape_html(item.get("original_filename", "") or item.get("id", "material")),
            pill(type_label(item.get("material_type", "unknown")), "info"),
            escape_html(item.get("detected_software_name", "") or "-"),
            escape_html(str(len(item.get("issues", []) or []))),
        ]
        for item in materials
    ]
    type_pairs = [(type_label(key), str(value)) for key, value in sorted(type_counter.items())]

    metrics = "".join(
        [
            metric_card("批次文件数", str(len(materials)), "当前批次材料总数", "info", icon_name="layers"),
            metric_card("问题总数", str(issue_total), "批次内所有材料问题总数", "warning" if issue_total else "success", icon_name="alert"),
            metric_card("项目数", str(len(submission_payload.get("case_ids", []) or [])), "批次识别出的项目数量", "success", icon_name="lock"),
        ]
    )

    body = f"""
    <div class="report-rich">
      {_report_toolbar(report)}
      <div class="report-section-stack">
        {panel('审查结果', list_pairs(type_pairs or [('材料类型', '0')], css_class='dossier-list dossier-list-single'), kicker='类型分布', extra_class='span-12', icon_name='bar', description='', panel_id='report-overview')}
        {panel('文件结果', table(['文件名', '材料类型', '软件名称', '问题数'], rows) if rows else empty_state('当前批次没有文件', '暂无可展示的批次文件结果。'), kicker='文件清单', extra_class='span-12', icon_name='cluster', description='', panel_id='report-items')}
        {panel('原始 Markdown', _raw_markdown_panel(report_content), kicker='按需展开', extra_class='span-12', icon_name='file', description='', panel_id='report-source')}
      </div>
    </div>
    """
    return metrics, body


def _report_toolbar(report: dict) -> str:
    report_id = str(report.get("id", "") or "")
    chips = ""
    if report_id:
        chips += download_chip(f"/downloads/reports/{report_id}", "保存为 MD")
        chips += download_chip(f"/downloads/reports/{report_id}/json", "保存为 JSON")
    return (
        '<div class="report-toolbar print-hidden">'
        f"{chips}"
        '<button class="button-secondary button-compact" type="button" data-print-page>打印 / 另存 PDF</button>'
        "</div>"
    )


def render_report_page(report: dict) -> str:
    report_content = report.get("content", "") or read_text_file(report.get("storage_path", ""))
    report_id = str(report.get("id", "") or "")
    line_count = len([line for line in report_content.splitlines() if line.strip()])
    character_count = len(report_content)
    storage_name = Path(str(report.get("storage_path", "") or "")).name or "-"

    report_type = str(report.get("report_type", "") or "")
    if report_type == "case_markdown":
        report_metrics, report_body = _render_case_report(report, report_content)
        page_links = [
            ("#report-reader", "结果", "report"),
        ]
    elif report_type == "material_markdown":
        report_metrics, report_body = _render_material_report(report, report_content)
        page_links = [
            ("#report-reader", "结果", "report"),
        ]
    elif report_type == "batch_markdown":
        report_metrics, report_body = _render_batch_report(report, report_content)
        page_links = [
            ("#report-reader", "结果", "report"),
        ]
    else:
        report_metrics = ""
        report_body = _report_toolbar(report) + _raw_markdown_panel(report_content)
        page_links = [
            ("#report-reader", "结果", "report"),
        ]

    # Simplified context - only essential metadata
    context_pairs = [
        ("类型", escape_html(report_label(report_type))),
        ("生成", escape_html(report.get("created_at", "") or "-")),
    ]

    content = f"""
    {contract_markers("报告上下文")}
    <section class="kpi-grid">
      {report_metrics}
      {metric_card('行数', str(line_count), '', 'neutral', icon_name='bar')}
      {metric_card('字符', str(character_count), '', 'neutral', icon_name='search')}
    </section>
    <section class="dashboard-grid">
      {panel('审查结果', report_body, kicker='', extra_class='span-12', icon_name='report', description='', panel_id='report-reader')}
      {panel('元数据', list_pairs(context_pairs, css_class='dossier-list dossier-list-single'), kicker='', extra_class='span-6', icon_name='layers', description='', panel_id='report-context')}
    </section>
    """
    return layout(
        title=report.get("id", "报告"),
        active_nav="submissions",
        header_tag="报告详情",
        header_title="审查结果",
        header_subtitle="查看项目审查结论",
        header_meta="".join(
            [
                pill(report_label(report_type), "info"),
            ]
        ),
        content=content,
        header_note="",
        page_links=page_links,
    )
