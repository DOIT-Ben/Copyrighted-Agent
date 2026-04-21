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
    status_label,
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
            pill(status_label(item.get("review_status", "unknown")), status_tone(item.get("review_status", "unknown"))),
        ]
        for item in materials
    ]

    summary_grid = "".join(
        [
            _summary_tile("项目名称", str(case.get("case_name", "") or case.get("id", "project")), "当前聚合后的项目视图"),
            _summary_tile("软件名", str(case.get("software_name", "") or "-"), "识别结果或人工修正结果"),
            _summary_tile("版本号", str(case.get("version", "") or "-"), "当前项目主版本信号"),
            _summary_tile("状态", status_label(str(case.get("status", "unknown"))), "项目当前处理状态"),
            _summary_tile("严重问题", str(severity_summary.get("severe", 0)), "最高风险项"),
            _summary_tile("中等问题", str(severity_summary.get("moderate", 0)), "建议尽快跟进"),
            _summary_tile("较轻问题", str(severity_summary.get("minor", 0)), "低优先级问题"),
            _summary_tile("材料数", str(len(materials)), "这个项目下的证据材料数"),
        ]
    )

    ai_pairs = [
        ("模型通道", escape_html(review_payload.get("ai_provider", "mock"))),
        ("处理结果", escape_html(status_label(str(review_payload.get("ai_resolution", "-"))))),
        ("评分", escape_html(str(review_payload.get("score", "-")))),
        ("结论", escape_html(review_payload.get("conclusion", "") or review_payload.get("rule_conclusion", "") or "-")),
        ("补充摘要", escape_html(review_payload.get("ai_summary", "") or "当前没有可用的 AI 补充意见。")),
    ]

    if report:
        report_id = str(report.get("id", "") or "")
        report_toolbar = (
            '<div class="report-toolbar">'
            f'<a class="button-secondary button-compact" href="/reports/{escape_html(report_id)}">打开报告</a>'
            f"{download_chip(f'/downloads/reports/{report_id}', '下载报告') if report_id else ''}"
            "</div>"
        )
        report_body = (
            report_toolbar
            + list_pairs(
                [
                    ("报告类型", escape_html(report_label(report.get("report_type", "")))),
                    ("格式", escape_html(report.get("file_format", "md"))),
                    ("生成时间", escape_html(report.get("created_at", "") or "-")),
                    ("存储位置", escape_html(report.get("storage_path", "") or "-")),
                ]
            )
        )
    else:
        report_body = empty_state("暂无项目报告", "这个项目还没有生成可查看的报告。")

    signal_rows = [
        [
            "问题总数",
            pill(str(len(issues)), issue_tone(len(issues))),
            "规则检查与跨材料问题的汇总结果",
        ],
        [
            "报告产物",
            pill("已就绪" if report else "缺失", "success" if report else "warning"),
            "是否已经具备可打开和可下载的报告",
        ],
        [
            "AI 辅助链路",
            pill(status_label(review_payload.get("ai_resolution", "not_run")), status_tone(review_payload.get("ai_resolution", "not_run"))),
            "AI 补充研判阶段的执行结果",
        ],
    ]

    content = f"""
    <section class="kpi-grid">
      {metric_card('材料数', str(len(materials)), '当前项目内的材料总数', 'info', icon_name='file')}
      {metric_card('问题数', str(len(issues)), '规则与跨材料问题总数', issue_tone(len(issues)), icon_name='alert')}
      {metric_card('项目状态', status_label(case.get('status', 'unknown')), '当前项目处理状态', status_tone(case.get('status', 'unknown')), icon_name='lock')}
      {metric_card('评分', str(review_payload.get('score', '-')), '综合审查得分', 'neutral', icon_name='trend')}
    </section>
    <section class="dashboard-grid">
      {panel('项目摘要', f'<div class="summary-grid">{summary_grid}</div>', kicker='项目概览', extra_class='span-12', icon_name='layers', description='把项目关键信息压缩到一屏，便于先做风险判断。', panel_id='case-summary')}
      {panel('风险队列', table(['严重级别', '问题', '说明'], issue_rows), kicker='问题清单', extra_class='span-8', icon_name='alert', description='需要处理的跨材料问题会优先集中展示。', panel_id='risk-queue') if issue_rows else panel('风险队列', empty_state('当前无风险问题', '这个项目暂时没有识别到需要处理的问题。'), kicker='问题清单', extra_class='span-8', icon_name='check', description='当前项目的规则检查结果较为干净。', panel_id='risk-queue')}
      {panel('AI 辅助研判', list_pairs(ai_pairs), kicker='AI 信号', extra_class='span-4', icon_name='spark', description='AI 补充意见始终作为辅助信息展示，不替代规则结论。', panel_id='ai-supplement')}
      {panel('材料矩阵', table(['文件名', '类型', '软件名', '版本', '审查状态'], material_rows), kicker='材料证据', extra_class='span-8', icon_name='cluster', description='逐项核对进入这个项目的每一份材料。', panel_id='material-matrix')}
      {panel('项目信号', table(['信号', '状态', '说明'], signal_rows), kicker='审查信号', extra_class='span-4', icon_name='bar', description='打开完整报告前，可以先看这组压缩后的关键信号。', panel_id='case-signals')}
      {panel('报告查看', report_body, kicker='报告交付', extra_class='span-12', icon_name='report', description='在同一个分析工作台里继续查看或下载项目报告。', panel_id='report-reader')}
    </section>
    """
    return layout(
        title=case.get("case_name", "项目详情"),
        active_nav="submissions",
        header_tag="项目详情",
        header_title=case.get("case_name", "项目详情"),
        header_subtitle="查看项目风险队列、AI 辅助研判、材料矩阵和报告交付信息。",
        header_meta="".join(
            [
                pill(status_label(case.get("status", "unknown")), status_tone(case.get("status", "unknown"))),
                pill(case.get("version", "") or "版本未定", "neutral"),
                link("/submissions", "返回批次总览", css_class="button-secondary button-compact"),
            ]
        ),
        content=content,
        header_note="先看风险队列，再对照 AI 辅助研判与材料矩阵，最后确认报告是否可直接交付。",
        page_links=[
            ("#risk-queue", "风险队列", "alert"),
            ("#ai-supplement", "AI 辅助研判", "spark"),
            ("#material-matrix", "材料矩阵", "cluster"),
            ("#report-reader", "报告查看", "report"),
        ],
    )
