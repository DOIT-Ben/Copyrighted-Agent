from __future__ import annotations

from app.core.services.online_filing import normalize_online_filing, online_filing_summary
from app.core.services.review_dimensions import build_case_review_dimensions
from app.core.services.review_profile import normalize_review_profile, review_profile_summary
from app.core.utils.text import escape_html
from app.web.prompt_views import render_prompt_snapshot
from app.web.view_helpers import (
    contract_markers,
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


def _top_issue_actions(case: dict, issues: list[dict], review_dimensions: list[dict]) -> str:
    submission_id = str(case.get("source_submission_id", "") or "")
    case_id = str(case.get("id", "") or "")
    if not issues:
        actions = []
        if submission_id:
            actions.append(f'<a class="button-secondary button-compact" href="/submissions/{escape_html(submission_id)}/materials">查看材料</a>')
        if submission_id and case_id:
            actions.append(f'<a class="button-secondary button-compact" href="/submissions/{escape_html(submission_id)}/operator">人工处理台</a>')
        return (
            '<div class="rule-checkpoint-list">'
            "<p>当前没有需要优先处理的问题，可以直接去看完整报告或继续导出。</p>"
            f'<div class="inline-actions">{"".join(actions)}</div>'
            "</div>"
        )

    lines = []
    for issue in issues[:3]:
        lines.append(
            "<li>"
            f"<strong>{escape_html(issue.get('title', '') or issue.get('rule', '') or issue.get('category', '') or '问题')}</strong>"
            f"<span class=\"table-subtext\">{escape_html(issue.get('message', '') or issue.get('detail', '') or issue.get('desc', '') or '-')}</span>"
            "</li>"
        )

    actions = []
    if submission_id:
        actions.append(f'<a class="button-secondary button-compact" href="/submissions/{escape_html(submission_id)}/materials">查看材料</a>')
    if submission_id and case_id and review_dimensions:
        first_dimension = str(review_dimensions[0].get("key", "") or "")
        if first_dimension:
            actions.append(
                f'<a class="button-secondary button-compact" href="/submissions/{escape_html(submission_id)}/review-rules/{escape_html(first_dimension)}?case_id={escape_html(case_id)}">调整规则</a>'
            )
    if case_id:
        report_id = str(case.get("report_id", "") or "")
        if report_id:
            actions.append(f'<a class="button-secondary button-compact" href="/reports/{escape_html(report_id)}">打开报告</a>')

    return (
        '<div class="rule-checkpoint-list">'
        f"<ul>{''.join(lines)}</ul>"
        f'<div class="inline-actions">{"".join(actions)}</div>'
        "</div>"
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

    # Simplified overview - only essential info
    online_filing = normalize_online_filing(case.get("online_filing", {}) or {})
    overview_pairs = [
        ("软件", escape_html(str(case.get("software_name", "") or "-"))),
        ("版本", escape_html(str(case.get("version", "") or "-"))),
        ("状态", escape_html(status_label(str(case.get("status", "unknown"))))),
        ("问题", escape_html(str(len(issues)))),
    ]

    # Simplified report section
    if report:
        report_id = str(report.get("id", "") or "")
        report_body = (
            '<div class="inline-actions">'
            f'<a class="button-primary" href="/reports/{escape_html(report_id)}">查看报告</a>'
            "</div>"
        )
    else:
        report_body = empty_state("无报告", "")

    # Simplified dimension table
    dimension_body = (
        table(["维度", "结论"], dimension_rows)
        if dimension_rows
        else empty_state("无维度", "")
    )

    # Simplified issue table
    issue_body = (
        table(["级别", "问题"], issue_rows)
        if issue_rows
        else empty_state("无问题", "")
    )

    content = f"""
    {contract_markers("修复入口", "AI 辅助研判")}
    <section class="kpi-grid">
      {metric_card('问题', str(len(issues)), '', issue_tone(len(issues)), icon_name='alert')}
      {metric_card('状态', status_label(case.get('status', 'unknown')), '', status_tone(case.get('status', 'unknown')), icon_name='lock')}
      {metric_card('评分', str(review_payload.get('score', '-')), '', 'neutral', icon_name='trend')}
    </section>
    <section class="dashboard-grid">
      {panel('项目信息', list_pairs(overview_pairs, css_class='dossier-list dossier-list-single'), kicker='', extra_class='span-6 panel-soft', icon_name='info', description='', panel_id='case-summary')}
      {panel('报告', report_body, kicker='', extra_class='span-6', icon_name='report', description='', panel_id='report-reader')}
      {panel('风险队列', issue_body, kicker='', extra_class='span-6', icon_name='alert', description='', panel_id='risk-queue')}
      {panel('审查维度', dimension_body, kicker='', extra_class='span-6', icon_name='shield', description='', panel_id='review-dimensions')}
      {panel('更多信息', list_pairs(online_filing_summary(online_filing), css_class='dossier-list dossier-list-single'), kicker='', extra_class='span-12', icon_name='search', description='', panel_id='case-more')}
    </section>
    """
    return layout(
        title=case.get("case_name", "项目详情"),
        active_nav="submissions",
        header_tag="项目详情",
        header_title=case.get("case_name", "项目详情"),
        header_subtitle=case.get("software_name", ""),
        header_meta="".join(
            [
                pill(status_label(case.get("status", "unknown")), status_tone(case.get("status", "unknown"))),
                pill(case.get("version", "") or "-", "neutral"),
            ]
        ),
        content=content,
        header_note="",
        page_links=[
            ("/submissions", "返回", "layers"),
        ],
    )
