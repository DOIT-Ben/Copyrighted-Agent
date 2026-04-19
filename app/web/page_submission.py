from __future__ import annotations

from collections import Counter

from app.core.services.runtime_store import store
from app.core.utils.text import escape_html

from app.web.view_helpers import (
    download_chip,
    empty_state,
    icon,
    issue_tone,
    layout,
    link,
    metric_card,
    mode_label,
    panel,
    pill,
    report_label,
    status_tone,
    table,
    type_label,
)


def _metric_row(label: str, value: int, total: int, tone: str, icon_name: str) -> str:
    percent = 8 if total <= 0 else max(8, min(100, round((value / total) * 100)))
    return (
        '<div class="metric-row">'
        '<div class="metric-label">'
        f'{icon(icon_name, "icon icon-sm")}'
        f"<span>{escape_html(label)}</span>"
        "</div>"
        '<div class="metric-track">'
        f'<span class="metric-fill metric-fill-{tone}" style="width: {percent}%"></span>'
        "</div>"
        f"<strong>{value}</strong>"
        "</div>"
    )


def _summary_tile(label: str, value: str, note: str) -> str:
    return (
        '<div class="summary-tile">'
        f"<span>{escape_html(label)}</span>"
        f"<strong>{escape_html(value)}</strong>"
        f"<small>{escape_html(note)}</small>"
        "</div>"
    )


def _submission_corrections(submission_id: str) -> list[dict]:
    return [
        correction.to_dict()
        for correction in store.corrections.values()
        if getattr(correction, "submission_id", "") == submission_id
    ]


def _build_parse_lookup(parse_results: list[dict]) -> dict[str, dict]:
    return {item.get("material_id", ""): item for item in parse_results}


def render_submissions_index() -> str:
    submissions = sorted(store.submissions.values(), key=lambda item: item.created_at, reverse=True)
    materials_total = sum(len(item.material_ids) for item in submissions)
    cases_total = sum(len(item.case_ids) for item in submissions)
    reports_total = sum(len(item.report_ids) for item in submissions)
    latest_status = submissions[0].status if submissions else "idle"
    status_counts = Counter(str(item.status or "unknown") for item in submissions)
    total = len(submissions)

    rows: list[list[str]] = []
    for submission in submissions:
        rows.append(
            [
                link(f"/submissions/{submission.id}", submission.filename),
                escape_html(mode_label(submission.mode)),
                pill(submission.status, status_tone(submission.status)),
                escape_html(str(len(submission.material_ids))),
                escape_html(str(len(submission.case_ids))),
                escape_html(str(len(submission.report_ids))),
                escape_html(submission.created_at),
            ]
        )

    distribution_body = "".join(
        [
            _metric_row("Completed", status_counts.get("completed", 0), total, "success", "check"),
            _metric_row("Processing", status_counts.get("processing", 0), total, "warning", "cluster"),
            _metric_row("Failed", status_counts.get("failed", 0), total, "danger", "alert"),
        ]
    )

    action_body = """
    <div class="helper-chip-row">
      <span class="helper-chip">Data-dense registry</span>
      <span class="helper-chip">Direct drill-down</span>
      <span class="helper-chip">Operator-ready</span>
    </div>
    <div class="status-stack">
      <article class="status-card">
        %s
        <span>批次列表应该优先暴露规模、状态和入口，而不是空白占位。</span>
      </article>
      <article class="status-card">
        %s
        <span>从这里进入 Submission 详情、Case 风险面板和 Report Reader。</span>
      </article>
      <article class="status-card">
        %s
        <span>新的导入入口保持在控制台首页，避免列表页承担过多首屏动作。</span>
      </article>
    </div>
    <div class="inline-actions">
      <a class="button-secondary" href="/">%sBack To Control Center</a>
    </div>
    """ % (
        pill("Batch-first", "info"),
        pill("Drill-down", "success"),
        pill("Focused intake", "warning"),
        icon("dashboard", "icon icon-sm"),
    )

    content = f"""
    <section class="kpi-grid">
      {metric_card('Batches', str(total), 'Imported submissions in runtime', 'info', icon_name='layers')}
      {metric_card('Materials', str(materials_total), 'Recognized materials across batches', 'success', icon_name='file')}
      {metric_card('Cases', str(cases_total), 'Grouped project views', 'warning', icon_name='lock')}
      {metric_card('Latest Status', latest_status.upper(), 'Most recent submission status', status_tone(latest_status), icon_name='trend')}
    </section>
    <section class="dashboard-grid">
      {panel('Batch Registry', table(['Filename', 'Mode', 'Status', 'Materials', 'Cases', 'Reports', 'Created'], rows), kicker='Batch Registry', extra_class='span-8', icon_name='layers', description='Inspect imported batches, grouping volume, and direct entry points into submission detail views.')}
      {panel('Status Distribution', distribution_body, kicker='Status Distribution', extra_class='span-4', icon_name='bar', description='A quick operational read on how the registry is moving.')}
      {panel('Registry Actions', action_body, kicker='Review Lens', extra_class='span-12', icon_name='search', description='Keep the batch list analytical: dense, scannable, and ready for drill-down.')}
    </section>
    """

    return layout(
        title="Batch Registry",
        active_nav="submissions",
        header_tag="Batch Registry",
        header_title="Batch Registry",
        header_subtitle="Inspect imported batches, grouping volume, and direct entry points into submission detail views.",
        header_meta=pill(f"{len(submissions)} batches", "info"),
        content=content,
    )


def render_submission_detail(
    submission: dict,
    materials: list[dict],
    cases: list[dict],
    reports: list[dict],
    parse_results: list[dict],
) -> str:
    parse_lookup = _build_parse_lookup(parse_results)
    corrections = _submission_corrections(submission.get("id", ""))

    needs_review_items: list[tuple[str, str]] = []
    material_rows: list[list[str]] = []
    artifact_rows: list[list[str]] = []
    case_rows: list[list[str]] = []

    for material in materials:
        parse_result = parse_lookup.get(material.get("id", ""), {})
        metadata = dict(parse_result.get("metadata_json", {}) or {})
        triage = dict(metadata.get("triage", {}) or {})
        parse_quality = dict(metadata.get("parse_quality", {}) or metadata.get("quality", {}) or {})
        issue_count = len(material.get("issues", []))
        needs_manual_review = bool(triage.get("needs_manual_review", False)) or material.get("material_type") == "unknown"

        if needs_manual_review:
            needs_review_items.append(
                (
                    str(material.get("original_filename", material.get("id", "material"))),
                    str(triage.get("review_recommendation", "needs manual review")),
                )
            )

        material_rows.append(
            [
                escape_html(material.get("original_filename", "")),
                pill(type_label(material.get("material_type", "unknown")), status_tone(material.get("review_status", "unknown"))),
                escape_html(material.get("detected_software_name", "") or "-"),
                escape_html(material.get("detected_version", "") or "-"),
                pill(str(issue_count), issue_tone(issue_count)),
                escape_html(str(parse_quality.get("legacy_doc_bucket", parse_quality.get("bucket", "-")))),
                pill("Needs Review" if needs_manual_review else "Ready", "warning" if needs_manual_review else "success"),
            ]
        )
        artifact_rows.append(
            [
                escape_html(material.get("original_filename", "")),
                download_chip(f"/downloads/materials/{material.get('id', '')}/raw", "raw"),
                download_chip(f"/downloads/materials/{material.get('id', '')}/clean", "clean"),
                download_chip(f"/downloads/materials/{material.get('id', '')}/desensitized", "desensitized"),
                download_chip(f"/downloads/materials/{material.get('id', '')}/privacy", "privacy"),
            ]
        )

    for case in cases:
        case_rows.append(
            [
                link(f"/cases/{case.get('id', '')}", case.get("case_name", "") or case.get("id", "case")),
                escape_html(case.get("software_name", "") or "-"),
                escape_html(case.get("version", "") or "-"),
                pill(case.get("status", "unknown"), status_tone(case.get("status", "unknown"))),
                link(f"/reports/{case.get('report_id', '')}", "Open Report") if case.get("report_id") else "-",
            ]
        )

    correction_rows = [
        [
            escape_html(item.get("correction_type", "")),
            escape_html(item.get("material_id", "") or item.get("case_id", "") or "-"),
            escape_html(item.get("note", "") or "-"),
            escape_html(item.get("corrected_at", "") or "-"),
        ]
        for item in corrections
    ]

    report_cards = "".join(
        [
            (
                '<article class="report-card">'
                f'<div class="report-card-head">{icon("report", "icon icon-sm")}<strong>{escape_html(report_label(report.get("report_type", "")))}</strong></div>'
                f'<span>{escape_html(report.get("file_format", "md"))}</span>'
                f'<div class="inline-actions"><a class="button-secondary button-compact" href="/reports/{escape_html(report_id)}">Open Reader</a>'
                f"{download_chip(f'/downloads/reports/{report_id}', 'Download')}</div>"
                "</article>"
            )
            for report in reports
            for report_id in [str(report.get("id", "") or "")]
        ]
    )

    case_options = "".join(
        f'<option value="{escape_html(case.get("id", ""))}">{escape_html(case.get("case_name", ""))}</option>' for case in cases
    )
    material_options = "".join(
        f'<option value="{escape_html(material.get("id", ""))}">{escape_html(material.get("original_filename", ""))}</option>'
        for material in materials
    )
    default_material_ids = ",".join(item.get("id", "") for item in materials[:1])

    import_digest = "".join(
        [
            _summary_tile("Filename", str(submission.get("filename", "")), "Current uploaded archive"),
            _summary_tile("Mode", mode_label(str(submission.get("mode", ""))), "Intake grouping strategy"),
            _summary_tile("Materials", str(len(materials)), "Recognized material entries"),
            _summary_tile("Cases", str(len(cases)), "Grouped project views"),
            _summary_tile("Reports", str(len(reports)), "Generated report artifacts"),
            _summary_tile("Created", str(submission.get("created_at", "")), "Submission record time"),
        ]
    )

    needs_review_body = (
        '<div class="status-stack">'
        + "".join(
            '<article class="status-card">'
            f'{pill("Needs Review", "warning")}'
            f'<span><strong>{escape_html(name)}</strong><br>{escape_html(note)}</span>'
            "</article>"
            for name, note in needs_review_items
        )
        + "</div>"
        if needs_review_items
        else empty_state("Needs Review", "No materials are waiting for manual review in this submission.")
    )

    export_body = (
        f'<div class="report-card-grid">{report_cards}</div>' if report_cards else empty_state("No Reports Yet", "Reports will appear here after the submission finishes review.")
    )
    export_body += (
        '<div class="inline-actions">'
        f'<a class="button-secondary" href="/downloads/submissions/{escape_html(submission.get("id", ""))}/bundle">{icon("download", "icon icon-sm")}submission bundle</a>'
        f'<a class="button-secondary" href="/downloads/logs/app">{icon("terminal", "icon icon-sm")}app.jsonl</a>'
        "</div>"
    )

    operator_body = f"""
    <div class="operator-note">
      <strong>Operator Console</strong>
      <span>Manual actions stay auditable and are designed to re-run review rather than mutate hidden state.</span>
    </div>
    <div class="helper-chip-row">
      <span class="helper-chip">change_material_type</span>
      <span class="helper-chip">assign_case</span>
      <span class="helper-chip">create_case_from_materials</span>
      <span class="helper-chip">merge_cases</span>
      <span class="helper-chip">rerun-review</span>
    </div>
    <div class="control-grid">
      <form class="operator-form" action="/submissions/{escape_html(submission.get('id', ''))}/actions/change-type" method="post">
        <strong>change_material_type</strong>
        <label class="field"><span>Material</span><select name="material_id">{material_options}</select></label>
        <label class="field"><span>Type</span><select name="material_type">
          <option value="agreement">agreement</option>
          <option value="source_code">source_code</option>
          <option value="info_form">info_form</option>
          <option value="software_doc">software_doc</option>
        </select></label>
        <label class="field"><span>Note</span><input type="text" name="note" placeholder="why this material type changed"></label>
        <button class="button-secondary button-compact" type="submit">{icon('wrench', 'icon icon-sm')}Apply Type Change</button>
      </form>

      <form class="operator-form" action="/submissions/{escape_html(submission.get('id', ''))}/actions/assign-case" method="post">
        <strong>assign_case</strong>
        <label class="field"><span>Material</span><select name="material_id">{material_options}</select></label>
        <label class="field"><span>Case</span><select name="case_id">{case_options}</select></label>
        <label class="field"><span>Note</span><input type="text" name="note" placeholder="assignment reason"></label>
        <button class="button-secondary button-compact" type="submit">{icon('merge', 'icon icon-sm')}Assign To Case</button>
      </form>

      <form class="operator-form" action="/submissions/{escape_html(submission.get('id', ''))}/actions/create-case" method="post">
        <strong>create_case_from_materials</strong>
        <label class="field"><span>Material IDs</span><input type="text" name="material_ids" value="{escape_html(default_material_ids)}"></label>
        <label class="field"><span>Case Name</span><input type="text" name="case_name" value="{escape_html(submission.get('filename', 'New Case'))}"></label>
        <label class="field"><span>Version</span><input type="text" name="version"></label>
        <label class="field"><span>Company</span><input type="text" name="company_name"></label>
        <label class="field"><span>Note</span><input type="text" name="note" placeholder="new case rationale"></label>
        <button class="button-secondary button-compact" type="submit">{icon('lock', 'icon icon-sm')}Create Case</button>
      </form>

      <form class="operator-form" action="/submissions/{escape_html(submission.get('id', ''))}/actions/merge-cases" method="post">
        <strong>merge_cases</strong>
        <label class="field"><span>Source</span><select name="source_case_id">{case_options}</select></label>
        <label class="field"><span>Target</span><select name="target_case_id">{case_options}</select></label>
        <label class="field"><span>Note</span><input type="text" name="note" placeholder="merge reason"></label>
        <button class="button-secondary button-compact" type="submit">{icon('merge', 'icon icon-sm')}Merge Cases</button>
      </form>

      <form class="operator-form" action="/submissions/{escape_html(submission.get('id', ''))}/actions/rerun-review" method="post">
        <strong>rerun-review</strong>
        <label class="field"><span>Case</span><select name="case_id">{case_options}</select></label>
        <label class="field"><span>Note</span><input type="text" name="note" placeholder="why review needs rerun"></label>
        <button class="button-secondary button-compact" type="submit">{icon('refresh', 'icon icon-sm')}Rerun Review</button>
      </form>
    </div>
    """

    content = f"""
    <section class="kpi-grid">
      {metric_card('Materials', str(len(materials)), 'Current submission material count', 'info', icon_name='file')}
      {metric_card('Cases', str(len(cases)), 'Grouped case count', 'success', icon_name='lock')}
      {metric_card('Reports', str(len(reports)), 'Available reports', 'neutral', icon_name='report')}
      {metric_card('Needs Review', str(len(needs_review_items)), 'Manual-review queue size', 'warning' if needs_review_items else 'success', icon_name='alert')}
    </section>
    <section class="dashboard-grid">
      {panel('Import Digest', f'<div class="summary-grid">{import_digest}</div>', kicker='Import Digest', extra_class='span-4', icon_name='file', description='Understand what entered this submission before you change anything.')}
      {panel('Needs Review', needs_review_body, kicker='Review Queue', extra_class='span-4', icon_name='alert', description='Operators should see unresolved items immediately.')}
      {panel('Export Center', export_body, kicker='Export Center', extra_class='span-4', icon_name='download', description='Reports, bundles and logs are part of the working surface, not an afterthought.')}
      {panel('Material Matrix', table(['Filename', 'Type', 'Software', 'Version', 'Issues', 'Quality', 'Status'], material_rows), kicker='Material Matrix', extra_class='span-8', icon_name='cluster', description='The central diagnostic table for this submission.')}
      {panel('Case Registry', table(['Case', 'Software', 'Version', 'Status', 'Report'], case_rows), kicker='Case Registry', extra_class='span-4', icon_name='lock', description='Each case can be opened, merged, reassigned or rerun from here.')}
      {panel('Artifact Browser', table(['Filename', 'Raw', 'Clean', 'Desensitized', 'Privacy'], artifact_rows), kicker='Artifact Browser', extra_class='span-4', icon_name='download', description='Keep raw, clean and privacy artifacts visible to the operator.')}
      {panel('Operator Console', operator_body, kicker='Operator Console', extra_class='span-8', icon_name='wrench', description='All corrective actions remain explicit, auditable and reversible through rerun.')}
      {panel('Correction Audit', table(['Type', 'Target', 'Note', 'At'], correction_rows), kicker='Correction Audit', extra_class='span-12', icon_name='clock', description='Every manual change is logged for later traceability.')}
    </section>
    """

    return layout(
        title=submission.get("filename", "Submission"),
        active_nav="submissions",
        header_tag="Submission",
        header_title=submission.get("filename", "Submission"),
        header_subtitle="Review the material matrix, manual-correction actions, export center, and operator workstation for this intake batch.",
        header_meta="".join(
            [
                pill(submission.get("status", "unknown"), status_tone(submission.get("status", "unknown"))),
                pill(mode_label(submission.get("mode", "")), "info"),
                pill(f"{len(cases)} cases", "neutral"),
            ]
        ),
        content=content,
    )
