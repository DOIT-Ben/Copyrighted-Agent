from __future__ import annotations

from app.core.utils.text import escape_html

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
    status_tone,
    table,
    type_label,
)


def _summary_tile(label: str, value: str, note: str) -> str:
    return (
        '<div class="summary-tile">'
        f"<span>{escape_html(label)}</span>"
        f"<strong>{escape_html(value)}</strong>"
        f"<small>{escape_html(note)}</small>"
        "</div>"
    )


def render_case_detail(case: dict, materials: list[dict], report: dict | None, review_result: dict | None) -> str:
    review_payload = review_result or {}
    issues = list(review_payload.get("issues_json", []) or [])
    severity_summary = dict(review_payload.get("severity_summary_json", {}) or {})

    issue_rows: list[list[str]] = []
    for issue in issues:
        severity = str(issue.get("severity", "") or "")
        issue_rows.append(
            [
                pill(severity_label(severity), status_tone(severity)),
                escape_html(issue.get("title", "") or issue.get("rule", "") or "-"),
                escape_html(issue.get("message", "") or issue.get("detail", "") or "-"),
            ]
        )

    material_rows = [
        [
            escape_html(item.get("original_filename", "") or item.get("id", "material")),
            pill(type_label(item.get("material_type", "unknown")), status_tone(item.get("review_status", "unknown"))),
            escape_html(item.get("detected_software_name", "") or case.get("software_name", "") or "-"),
            escape_html(item.get("detected_version", "") or case.get("version", "") or "-"),
            pill(item.get("review_status", "unknown"), status_tone(item.get("review_status", "unknown"))),
        ]
        for item in materials
    ]

    summary_grid = "".join(
        [
            _summary_tile("Case", str(case.get("case_name", "") or case.get("id", "case")), "Current grouped project view"),
            _summary_tile("Software", str(case.get("software_name", "") or "-"), "Detected or operator-adjusted name"),
            _summary_tile("Version", str(case.get("version", "") or "-"), "Resolved version signal"),
            _summary_tile("Status", str(case.get("status", "unknown")), "Current case state"),
            _summary_tile("Severe", str(severity_summary.get("severe", 0)), "Highest-risk findings"),
            _summary_tile("Moderate", str(severity_summary.get("moderate", 0)), "Needs operator follow-up"),
            _summary_tile("Minor", str(severity_summary.get("minor", 0)), "Lower-priority findings"),
            _summary_tile("Materials", str(len(materials)), "Evidence inside this case"),
        ]
    )

    ai_pairs = [
        ("Provider", escape_html(review_payload.get("ai_provider", "mock"))),
        ("Resolution", escape_html(review_payload.get("ai_resolution", "-"))),
        ("Score", escape_html(str(review_payload.get("score", "-")))),
        ("Conclusion", escape_html(review_payload.get("conclusion", "") or review_payload.get("rule_conclusion", "") or "-")),
        ("Summary", escape_html(review_payload.get("ai_summary", "") or "No AI supplement available.")),
    ]

    if report:
        report_id = str(report.get("id", "") or "")
        report_toolbar = (
            '<div class="report-toolbar">'
            f'<a class="button-secondary button-compact" href="/reports/{escape_html(report_id)}">Open Report Reader</a>'
            f"{download_chip(f'/downloads/reports/{report_id}', 'Download report') if report_id else ''}"
            "</div>"
        )
        report_body = (
            report_toolbar
            + list_pairs(
                [
                    ("Report Type", escape_html(report_label(report.get("report_type", "")))),
                    ("Format", escape_html(report.get("file_format", "md"))),
                    ("Created", escape_html(report.get("created_at", "") or "-")),
                    ("Storage", escape_html(report.get("storage_path", "") or "-")),
                ]
            )
        )
    else:
        report_body = empty_state("Report Reader", "No case report has been generated yet for this grouped view.")

    signal_rows = [
        [
            "Issue Count",
            pill(str(len(issues)), issue_tone(len(issues))),
            "Combined rule and cross-material findings",
        ],
        [
            "Report Artifact",
            pill("ready" if report else "missing", "success" if report else "warning"),
            "Reader and downloadable artifact status",
        ],
        [
            "AI Path",
            pill(review_payload.get("ai_resolution", "not_run"), status_tone(review_payload.get("ai_resolution", "not_run"))),
            "Outcome of the AI supplement stage",
        ],
    ]

    content = f"""
    <section class="kpi-grid">
      {metric_card('Materials', str(len(materials)), 'Current case material count', 'info', icon_name='file')}
      {metric_card('Issues', str(len(issues)), 'Rule and cross-material issues', issue_tone(len(issues)), icon_name='alert')}
      {metric_card('Status', case.get('status', 'unknown'), 'Current case status', status_tone(case.get('status', 'unknown')), icon_name='lock')}
      {metric_card('Score', str(review_payload.get('score', '-')), 'Hybrid review score', 'neutral', icon_name='trend')}
    </section>
    <section class="dashboard-grid">
      {panel('Case Summary', f'<div class="summary-grid">{summary_grid}</div>', kicker='Case Summary', extra_class='span-12', icon_name='layers', description='Keep the case overview dense, scannable, and ready for risk triage.', panel_id='case-summary')}
      {panel('Risk Queue', table(['Severity', 'Issue', 'Detail'], issue_rows), kicker='Risk Queue', extra_class='span-7', icon_name='alert', description='The primary surface for cross-material issues that need action.', panel_id='risk-queue') if issue_rows else panel('Risk Queue', empty_state('Risk Queue', 'No issues were found for this case.'), kicker='Risk Queue', extra_class='span-7', icon_name='check', description='The case is currently clear of detected review issues.', panel_id='risk-queue')}
      {panel('AI Supplement', list_pairs(ai_pairs), kicker='AI Supplement', extra_class='span-5', icon_name='spark', description='AI notes are shown alongside the deterministic review outcome, never instead of it.', panel_id='ai-supplement')}
      {panel('Material Matrix', table(['Filename', 'Type', 'Software', 'Version', 'Review'], material_rows), kicker='Material Matrix', extra_class='span-7', icon_name='cluster', description='Inspect every piece of evidence grouped into this case.', panel_id='material-matrix')}
      {panel('Case Signals', table(['Signal', 'Status', 'Detail'], signal_rows), kicker='Review Signals', extra_class='span-5', icon_name='bar', description='A compact operational read before you open the full report.', panel_id='case-signals')}
      {panel('Report Reader', report_body, kicker='Report Reader', extra_class='span-12', icon_name='report', description='Open or download the current case report from the same analytical workspace.', panel_id='report-reader')}
    </section>
    """
    return layout(
        title=case.get("case_name", "Case"),
        active_nav="submissions",
        header_tag="Case",
        header_title=case.get("case_name", "Case"),
        header_subtitle="Inspect the risk queue, AI supplement, evidence matrix, and report handoff for the current grouped case.",
        header_meta="".join(
            [
                pill(case.get("status", "unknown"), status_tone(case.get("status", "unknown"))),
                pill(case.get("version", "") or "unknown version", "neutral"),
                link("/submissions", "Back to Batch Registry", css_class="button-secondary button-compact"),
            ]
        ),
        content=content,
        header_note="Triage the risk queue first, compare it with the AI supplement, then verify the report handoff before you leave the case.",
        page_links=[
            ("#risk-queue", "Risk Queue", "alert"),
            ("#ai-supplement", "AI Supplement", "spark"),
            ("#material-matrix", "Material Matrix", "cluster"),
            ("#report-reader", "Report Reader", "report"),
        ],
    )
