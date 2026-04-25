from __future__ import annotations

from app.core.services.online_filing import normalize_online_filing, online_filing_summary
from app.core.services.review_dimensions import build_case_review_dimensions
from app.core.services.review_profile import normalize_review_profile, review_profile_summary
from app.core.utils.text import escape_html
from app.web.prompt_views import render_prompt_snapshot
from app.web.view_helpers import (
    download_chip,
    empty_state,
    issue_tone,
    layout,
    link,
    list_pairs,
    metric_card,
    panel,
    pill,
    report_label,
    severity_label,
    status_label,
    status_tone,
    table,
    type_label,
)


def _dimension_rule_link(submission_id: str, case_id: str, item: dict) -> str:
    key = str(item.get("key", "") or "")
    title = str(item.get("title", "") or key or "-")
    if not submission_id or not case_id or not key:
        return escape_html(title)
    return link(f"/submissions/{submission_id}/review-rules/{key}?case_id={case_id}", title)


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


def render_case_detail(case: dict, materials: list[dict], report: dict | None, review_result: dict | None) -> str:
    review_payload = review_result or {}
    issues = list(review_payload.get("issues_json", []) or [])
    severity_summary = dict(review_payload.get("severity_summary_json", {}) or {})
    review_profile = normalize_review_profile(review_payload.get("review_profile_snapshot", {}))
    prompt_snapshot = dict(review_payload.get("prompt_snapshot_json", {}) or {})
    review_dimensions = build_case_review_dimensions(
        case,
        materials,
        cross_material_issues=issues,
        ai_resolution=str(review_payload.get("ai_resolution", "") or ""),
        review_profile=review_profile,
    )

    source_submission_id = str(case.get("source_submission_id", "") or "")
    case_id = str(case.get("id", "") or "")

    issue_rows = [
        [
            pill(severity_label(str(issue.get("severity", "") or "")), status_tone(str(issue.get("severity", "") or ""))),
            escape_html(issue.get("title", "") or issue.get("rule", "") or issue.get("category", "") or "-"),
            escape_html(issue.get("message", "") or issue.get("detail", "") or issue.get("desc", "") or "-"),
        ]
        for issue in issues
    ]

    dimension_rows = [
        [
            _dimension_rule_link(source_submission_id, case_id, item),
            pill(str(item.get("status", "") or "-"), str(item.get("tone", "neutral") or "neutral")),
            escape_html(item.get("summary", "") or "-"),
        ]
        for item in review_dimensions
    ]

    material_rows = [
        [
            escape_html(item.get("original_filename", "") or item.get("id", "material")),
            pill(type_label(item.get("material_type", "unknown")), status_tone(item.get("review_status", "unknown"))),
            pill(status_label(item.get("review_status", "unknown")), status_tone(item.get("review_status", "unknown"))),
        ]
        for item in materials
    ]
    filing = normalize_online_filing(case.get("online_filing", {}) or {})
    online_pairs = online_filing_summary(filing)

    overview_pairs = [
        ("软件名称", escape_html(str(case.get("software_name", "") or "-"))),
        ("版本", escape_html(str(case.get("version", "") or "-"))),
        ("项目状态", escape_html(status_label(str(case.get("status", "unknown"))))),
        ("材料数量", escape_html(str(len(materials)))),
        ("严重问题", escape_html(str(severity_summary.get("severe", 0)))),
        ("中等问题", escape_html(str(severity_summary.get("moderate", 0)))),
        ("较轻问题", escape_html(str(severity_summary.get("minor", 0)))),
    ]
    ai_pairs = [
        ("AI 通道", escape_html(str(review_payload.get("ai_provider", "mock") or "mock"))),
        ("处理结果", escape_html(status_label(str(review_payload.get("ai_resolution", "not_run") or "not_run")))),
        ("评分", escape_html(str(review_payload.get("score", "-") or "-"))),
        ("规则结论", escape_html(str(review_payload.get("rule_conclusion", "") or review_payload.get("conclusion", "") or "-"))),
        ("AI 补充摘要", escape_html(str(review_payload.get("ai_summary", "") or "当前没有可用的 AI 补充意见。"))),
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

    if report:
        report_id = str(report.get("id", "") or "")
        report_body = (
            '<div class="inline-actions">'
            f'<a class="button-secondary button-compact" href="/reports/{escape_html(report_id)}">打开报告</a>'
            f"{download_chip(f'/downloads/reports/{report_id}', '下载报告') if report_id else ''}"
            "</div>"
            + list_pairs(
                [
                    ("报告类型", escape_html(report_label(report.get("report_type", "")))),
                    ("格式", escape_html(str(report.get("file_format", "md") or "md"))),
                    ("生成时间", escape_html(report.get("created_at", "") or "-")),
                ],
                css_class="dossier-list dossier-list-single",
            )
        )
    else:
        report_body = empty_state("暂无项目报告", "这个项目还没有生成可查看的报告。")

    advanced_groups = '<div class="operator-group-grid">'
    advanced_groups += _fold_group(
        1,
        "维度明细",
        "逐项查看每个审查重点的当前结论。",
        table(["审查维度", "当前结论", "摘要"], dimension_rows) if dimension_rows else empty_state("暂无维度结果", "当前没有可显示的审查维度。"),
        open_by_default=False,
    )
    advanced_groups += _fold_group(
        2,
        "审查配置",
        "查看当前维度、模式和规则入口。",
        list_pairs(profile_pairs, css_class="dossier-list dossier-list-single") + rule_links,
        open_by_default=False,
    )
    advanced_groups += _fold_group(
        3,
        "材料矩阵",
        "按需核对参与审查的材料。",
        table(["文件名", "类型", "状态"], material_rows) if material_rows else empty_state("暂无材料", "当前项目下没有材料。"),
        open_by_default=False,
    )
    advanced_groups += _fold_group(
        4,
        "LLM 审查提示词",
        "需要排查模型判断时再展开。",
        render_prompt_snapshot(prompt_snapshot) if prompt_snapshot else empty_state("暂无提示词快照", "当前审查结果没有保存提示词快照。"),
        open_by_default=False,
    )
    advanced_groups += "</div>"

    content = f"""
    <section class="kpi-grid">
      {metric_card('问题数', str(len(issues)), '当前项目需要关注的问题', issue_tone(len(issues)), icon_name='alert')}
      {metric_card('项目状态', status_label(case.get('status', 'unknown')), '当前处理状态', status_tone(case.get('status', 'unknown')), icon_name='lock')}
      {metric_card('评分', str(review_payload.get('score', '-')), '综合审查得分', 'neutral', icon_name='trend')}
    </section>
    <section class="dashboard-grid">
      {panel('审查结果', list_pairs(overview_pairs, css_class='dossier-list dossier-list-single'), kicker='概览', extra_class='span-8', icon_name='layers', description='', panel_id='case-summary')}
      {panel('AI 辅助研判', list_pairs(ai_pairs, css_class='dossier-list dossier-list-single'), kicker='AI 信号', extra_class='span-4', icon_name='spark', description='', panel_id='ai-supplement')}
      {panel('风险队列', table(['严重级别', '问题', '说明'], issue_rows) if issue_rows else empty_state('当前无跨材料问题', '没有发现需要优先处理的冲突。'), kicker='优先处理', extra_class='span-8', icon_name='alert', description='', panel_id='risk-queue')}
      {panel('审查维度', table(['维度', '结论', '摘要'], dimension_rows) if dimension_rows else empty_state('暂无审查维度', '当前没有可显示的维度结论。'), kicker='当前结论', extra_class='span-4 panel-soft', icon_name='shield', description='', panel_id='review-dimensions')}
      {panel('在线填报', list_pairs(online_pairs, css_class='dossier-list dossier-list-single') if filing.get('has_data') else empty_state('尚未录入在线填报信息', '可在批次详情页的人工干预台录入在线填报字段后重新审查。'), kicker='录入状态', extra_class='span-12', icon_name='file', description='', panel_id='online-filing')}
      {panel('报告查看', report_body, kicker='结果出口', extra_class='span-12', icon_name='report', description='', panel_id='report-reader')}
      {panel('更多信息', advanced_groups, kicker='按需展开', extra_class='span-12', icon_name='search', description='', panel_id='dimension-details')}
    </section>
    """
    return layout(
        title=case.get("case_name", "项目详情"),
        active_nav="submissions",
        header_tag="项目详情",
        header_title=case.get("case_name", "项目详情"),
        header_subtitle="先看结论和问题，其他内容按需展开。",
        header_meta="".join(
            [
                pill(status_label(case.get("status", "unknown")), status_tone(case.get("status", "unknown"))),
                pill(case.get("version", "") or "版本未定", "neutral"),
                link("/submissions", "返回批次总览", css_class="button-secondary button-compact"),
            ]
        ),
        content=content,
        header_note="默认只保留核心结果，配置和提示词放到折叠区。",
        page_links=[
            ("#case-summary", "审查结果", "layers"),
            ("#risk-queue", "风险队列", "alert"),
            ("#review-dimensions", "审查维度", "shield"),
            ("#online-filing", "在线填报", "file"),
            ("#report-reader", "报告查看", "report"),
            ("#dimension-details", "更多信息", "search"),
        ],
    )
