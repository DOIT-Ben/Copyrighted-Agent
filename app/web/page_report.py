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
        f"{download_chip(f'/downloads/reports/{report_id}', '下载报告') if report_id else ''}"
        "</div>"
        '<p class="highlight-note">报告页会把生成后的正文留在管理台内，方便先核对内容，再决定是否导出和交付。</p>'
        f'<div class="report-panel"><pre>{escape_html(report_content or "当前没有可显示的报告内容。")}</pre></div>'
    )

    context_pairs = [
        ("报告 ID", escape_html(report_id or "-")),
        ("报告类型", escape_html(report_label(report.get("report_type", "")))),
        ("文件格式", escape_html(report.get("file_format", "md"))),
        ("生成时间", escape_html(report.get("created_at", "") or "-")),
        ("存储文件", escape_html(storage_name)),
        ("存储路径", escape_html(report.get("storage_path", "") or "-")),
    ]

    content = f"""
    <section class="kpi-grid">
      {metric_card('报告类型', report_label(report.get('report_type', 'report')), '当前报告所属的产物类型', 'info', icon_name='report')}
      {metric_card('格式', str(report.get('file_format', 'md')).upper(), '报告当前存储格式', 'success', icon_name='file')}
      {metric_card('有效行数', str(line_count), '非空内容行数，用于快速体量校验', 'neutral', icon_name='bar')}
      {metric_card('字符数', str(character_count), '用于快速判断报告是否异常过短', 'warning', icon_name='search')}
    </section>
    <section class="dashboard-grid">
      {panel('报告阅读器', reader_body, kicker='正文查看', extra_class='span-8', icon_name='report', description='直接在页面内阅读当前报告正文。', panel_id='report-reader')}
      {panel('报告上下文', list_pairs(context_pairs), kicker='产物信息', extra_class='span-4', icon_name='layers', description='把报告元数据固定展示在侧边，便于回溯来源。', panel_id='report-context')}
    </section>
    """
    return layout(
        title=report.get("id", "报告"),
        active_nav="submissions",
        header_tag="报告详情",
        header_title="报告阅读器",
        header_subtitle="在同一个管理台页面中查看报告正文、核对元数据，并决定是否下载交付。",
        header_meta="".join(
            [
                pill(report_label(report.get("report_type", "report")), "info"),
                pill(report.get("file_format", "md"), "neutral"),
                pill("可追溯产物", "success"),
            ]
        ),
        content=content,
        header_note="先在页面内核对正文与元数据，再下载报告，避免把错误内容直接带出系统。",
        page_links=[
            ("#report-reader", "报告阅读器", "report"),
            ("#report-context", "报告上下文", "layers"),
            ("/submissions", "批次总览", "layers"),
        ],
    )
