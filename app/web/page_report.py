from __future__ import annotations

from pathlib import Path

from app.core.utils.text import escape_html

from app.web.view_helpers import download_chip, layout, list_pairs, metric_card, panel, pill, read_text_file, report_label


def render_report_page(report: dict) -> str:
    report_content = report.get("content", "") or read_text_file(report.get("storage_path", ""))
    report_id = str(report.get("id", "") or "")
    line_count = len([line for line in report_content.splitlines() if line.strip()])
    character_count = len(report_content)
    storage_name = Path(str(report.get("storage_path", "") or "")).name or "-"

    reader_body = (
        '<div class="report-toolbar">'
        f'<span class="helper-chip">{escape_html(report_label(report.get("report_type", "")))}</span>'
        f'<span class="helper-chip">{escape_html(report.get("file_format", "md"))}</span>'
        f"{download_chip(f'/downloads/reports/{report_id}', 'Download report') if report_id else ''}"
        "</div>"
        '<p class="highlight-note">Report Reader keeps the generated artifact visible inside the admin workspace so operators can verify output before export.</p>'
        f'<div class="report-panel"><pre>{escape_html(report_content or "No report content available.")}</pre></div>'
    )

    context_pairs = [
        ("Report ID", escape_html(report_id or "-")),
        ("Type", escape_html(report_label(report.get("report_type", "")))),
        ("Format", escape_html(report.get("file_format", "md"))),
        ("Created", escape_html(report.get("created_at", "") or "-")),
        ("Storage File", escape_html(storage_name)),
        ("Storage Path", escape_html(report.get("storage_path", "") or "-")),
    ]

    content = f"""
    <section class="kpi-grid">
      {metric_card('Report Type', report_label(report.get('report_type', 'report')), 'Generated artifact category', 'info', icon_name='report')}
      {metric_card('Format', str(report.get('file_format', 'md')).upper(), 'Stored export format', 'success', icon_name='file')}
      {metric_card('Lines', str(line_count), 'Non-empty lines in the artifact', 'neutral', icon_name='bar')}
      {metric_card('Chars', str(character_count), 'Character count for quick sanity checks', 'warning', icon_name='search')}
    </section>
    <section class="dashboard-grid">
      {panel('Report Reader', reader_body, kicker='Report Reader', extra_class='span-8', icon_name='report', description='Read the stored report body directly from the operator console.')}
      {panel('Report Context', list_pairs(context_pairs), kicker='Artifact Context', extra_class='span-4', icon_name='layers', description='Report metadata stays visible beside the reader for traceability.')}
    </section>
    """
    return layout(
        title=report.get("id", "Report"),
        active_nav="submissions",
        header_tag="Report",
        header_title="Report Reader",
        header_subtitle="Read the stored report body, confirm artifact metadata, and export the generated report from the same admin view.",
        header_meta="".join(
            [
                pill(report.get("report_type", "report"), "info"),
                pill(report.get("file_format", "md"), "neutral"),
                pill("Traceable Artifact", "success"),
            ]
        ),
        content=content,
    )
