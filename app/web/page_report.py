from __future__ import annotations

from collections import Counter
from pathlib import Path

from app.core.services.review_dimensions import build_case_review_dimensions
from app.core.services.review_profile import normalize_review_profile, review_profile_summary
from app.core.services.runtime_store import store
from app.core.utils.text import escape_html
from app.web.prompt_views import render_prompt_snapshot
from app.web.view_helpers import (
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


def _dimension_rule_link(submission_id: str, case_id: str, item: dict) -> str:
    key = str(item.get("key", "") or "")
    title = str(item.get("title", "") or key or "-")
    if not submission_id or not case_id or not key:
        return escape_html(title)
    return f'<a href="/submissions/{escape_html(submission_id)}/review-rules/{escape_html(key)}?case_id={escape_html(case_id)}">{escape_html(title)}</a>'


def _report_toolbar(report: dict) -> str:
    report_id = str(report.get("id", "") or "")
    return (
        '<div class="report-toolbar print-hidden">'
        f"{download_chip(f'/downloads/reports/{report_id}', '保存为 MD') if report_id else ''}"
        '<button class="button-secondary button-compact" type="button" onclick="window.print()">保存为 PDF</button>'
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
    severity_summary = dict(review_payload.get("severity_summary_json", {}) or {})
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
        ("严重问题", escape_html(str(severity_summary.get("severe", 0)))),
        ("中等问题", escape_html(str(severity_summary.get("moderate", 0)))),
        ("较轻问题", escape_html(str(severity_summary.get("minor", 0)))),
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
        "审查配置",
        "查看本次报告对应的规则和模式。",
        list_pairs(profile_pairs, css_class="dossier-list dossier-list-single") + rule_links,
        open_by_default=False,
    )
    advanced_groups += _fold_group(
        2,
        "LLM 审查提示词",
        "需要追查模型判断时再展开。",
        render_prompt_snapshot(prompt_snapshot) if prompt_snapshot else empty_state("暂无提示词快照", "当前报告没有保存提示词快照。"),
        open_by_default=False,
    )
    advanced_groups += _fold_group(
        3,
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
        {panel('审查维度', table(['审查维度', '当前状态', '摘要'], dimension_rows) if dimension_rows else empty_state('暂无审查维度', '当前没有可展示的维度结果。'), kicker='当前结论', extra_class='span-6', icon_name='shield', description='', panel_id='report-dimensions')}
        {panel('发现的问题', table(['严重级别', '问题', '说明'], issue_rows) if issue_rows else empty_state('当前未发现跨材料问题', '本次项目没有发现明显冲突。'), kicker='优先处理', extra_class='span-6', icon_name='alert', description='', panel_id='report-issues')}
        {panel('审查材料', table(['文件名', '材料类型', '软件名称'], material_rows) if material_rows else empty_state('暂无材料', '当前项目下没有可展示的材料。'), kicker='证据来源', extra_class='span-12', icon_name='cluster', description='', panel_id='report-materials')}
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
            ("#report-reader", "审查结果", "report"),
            ("#report-dimensions", "审查维度", "shield"),
            ("#report-profile", "更多信息", "search"),
            ("#report-context", "报告上下文", "layers"),
        ]
    elif report_type == "material_markdown":
        report_metrics, report_body = _render_material_report(report, report_content)
        page_links = [
            ("#report-reader", "审查结果", "report"),
            ("#report-context", "报告上下文", "layers"),
        ]
    elif report_type == "batch_markdown":
        report_metrics, report_body = _render_batch_report(report, report_content)
        page_links = [
            ("#report-reader", "审查结果", "report"),
            ("#report-context", "报告上下文", "layers"),
        ]
    else:
        report_metrics = ""
        report_body = _report_toolbar(report) + _raw_markdown_panel(report_content)
        page_links = [
            ("#report-reader", "审查结果", "report"),
            ("#report-context", "报告上下文", "layers"),
        ]

    context_pairs = [
        ("报告 ID", escape_html(report_id or "-")),
        ("报告类型", escape_html(report_label(report_type))),
        ("文件格式", escape_html(str(report.get("file_format", "md") or "md").upper())),
        ("生成时间", escape_html(report.get("created_at", "") or "-")),
        ("存储文件", escape_html(storage_name)),
        ("存储路径", escape_html(report.get("storage_path", "") or "-")),
    ]

    content = f"""
    <section class="kpi-grid">
      {report_metrics}
      {metric_card('有效行数', str(line_count), '非空内容行数', 'neutral', icon_name='bar')}
      {metric_card('字符数', str(character_count), '用于判断报告体量', 'neutral', icon_name='search')}
    </section>
    <section class="dashboard-grid">
      {panel('审查结果', report_body, kicker='结果视图', extra_class='span-12', icon_name='report', description='', panel_id='report-reader')}
      {panel('报告上下文', list_pairs(context_pairs, css_class='dossier-list dossier-list-single'), kicker='元数据', extra_class='span-12', icon_name='layers', description='', panel_id='report-context')}
    </section>
    """
    return layout(
        title=report.get("id", "报告"),
        active_nav="submissions",
        header_tag="报告详情",
        header_title="审查结果",
        header_subtitle="先看结果，再按需展开配置、提示词和原始内容。",
        header_meta="".join(
            [
                pill(report_label(report_type), "info"),
                pill(str(report.get("file_format", "md") or "md").upper(), "neutral"),
                pill("可在线查看", "success"),
            ]
        ),
        content=content,
        header_note="默认收起次要信息，结果页只保留主结论和导出动作。",
        page_links=page_links,
    )
