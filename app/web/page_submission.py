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
    notice_banner,
    panel,
    pill,
    report_label,
    status_label,
    status_tone,
    table,
    type_label,
)


CORRECTION_LABELS = {
    "change_material_type": "更正材料类型",
    "assign_material_to_case": "指派到项目",
    "create_case_from_materials": "从材料创建项目",
    "merge_cases": "合并项目",
    "rerun_case_review": "重新审查项目",
}

QUALITY_BUCKET_LABELS = {
    "usable_text": "文本可用",
    "partial_fragments": "内容片段化",
    "binary_noise": "疑似二进制噪声",
    "unknown": "待判断",
}


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


def _correction_label(value: str) -> str:
    normalized = str(value or "").strip()
    return CORRECTION_LABELS.get(normalized, normalized or "-")


def _quality_bucket_label(value: str) -> str:
    normalized = str(value or "").strip().lower()
    return QUALITY_BUCKET_LABELS.get(normalized, value or "-")


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
                pill(status_label(submission.status), status_tone(submission.status)),
                escape_html(str(len(submission.material_ids))),
                escape_html(str(len(submission.case_ids))),
                escape_html(str(len(submission.report_ids))),
                escape_html(submission.created_at),
            ]
        )

    distribution_body = "".join(
        [
            _metric_row("已完成", status_counts.get("completed", 0), total, "success", "check"),
            _metric_row("处理中", status_counts.get("processing", 0), total, "warning", "cluster"),
            _metric_row("失败", status_counts.get("failed", 0), total, "danger", "alert"),
        ]
    )

    action_body = """
    <div class="helper-chip-row">
      <span class="helper-chip">台账视图</span>
      <span class="helper-chip">一键下钻</span>
      <span class="helper-chip">适合复核</span>
    </div>
    <div class="status-stack">
      <article class="status-card">
        %s
        <span>批次页优先暴露状态、规模和入口，方便你先判断哪里异常，再进入详情深查。</span>
      </article>
      <article class="status-card">
        %s
        <span>从这里可以直接进入批次详情、项目详情和报告查看页，保持分析链路连续。</span>
      </article>
      <article class="status-card">
        %s
        <span>导入入口继续留在总控台，批次总览只承担“观察”和“下钻”，避免首页按钮过多。</span>
      </article>
    </div>
    <div class="inline-actions">
      <a class="button-secondary" href="/">%s返回总控台</a>
    </div>
    """ % (
        pill("先看状态", "info"),
        pill("再看详情", "success"),
        pill("最后导出", "warning"),
        icon("dashboard", "icon icon-sm"),
    )

    content = f"""
    <section class="kpi-grid">
      {metric_card('批次数', str(total), '当前运行时已导入的批次总量', 'info', icon_name='layers')}
      {metric_card('材料数', str(materials_total), '各批次识别出的材料总数', 'success', icon_name='file')}
      {metric_card('项目数', str(cases_total), '已形成的项目分组数量', 'warning', icon_name='lock')}
      {metric_card('最新状态', status_label(latest_status), '最近一个批次的处理状态', status_tone(latest_status), icon_name='trend')}
    </section>
    <section class="dashboard-grid">
      {panel('批次台账', table(['压缩包', '导入模式', '状态', '材料数', '项目数', '报告数', '创建时间'], rows), kicker='批次总览', extra_class='span-8', icon_name='layers', description='查看所有导入批次的规模、状态和详情入口。', panel_id='batch-registry')}
      {panel('状态分布', distribution_body, kicker='运行状态', extra_class='span-4', icon_name='bar', description='快速判断当前批次池是稳定、拥堵还是有失败堆积。', panel_id='status-distribution')}
      {panel('查看方式', action_body, kicker='分析路径', extra_class='span-12', icon_name='search', description='先看台账，再下钻到批次、项目和报告详情。', panel_id='registry-actions')}
    </section>
    """

    return layout(
        title="批次总览",
        active_nav="submissions",
        header_tag="批次总览",
        header_title="批次总览台账",
        header_subtitle="集中查看所有导入批次的状态、规模和入口，适合先做批次级排查，再进入详情页面。",
        header_meta=pill(f"{len(submissions)} 个批次", "info"),
        content=content,
        header_note="先在台账里定位异常批次，再进入批次详情核对材料矩阵、人工干预和导出产物。",
        page_links=[
            ("#batch-registry", "批次台账", "layers"),
            ("#status-distribution", "状态分布", "bar"),
            ("#registry-actions", "查看方式", "search"),
        ],
    )


def render_submission_detail(
    submission: dict,
    materials: list[dict],
    cases: list[dict],
    reports: list[dict],
    parse_results: list[dict],
    notice: dict | None = None,
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
                    str(triage.get("review_recommendation", "建议人工复核")),
                )
            )

        quality_bucket = parse_quality.get("legacy_doc_bucket", parse_quality.get("bucket", "unknown"))
        material_rows.append(
            [
                escape_html(material.get("original_filename", "")),
                pill(type_label(material.get("material_type", "unknown")), status_tone(material.get("review_status", "unknown"))),
                escape_html(material.get("detected_software_name", "") or "-"),
                escape_html(material.get("detected_version", "") or "-"),
                pill(str(issue_count), issue_tone(issue_count)),
                escape_html(_quality_bucket_label(str(quality_bucket))),
                pill("待复核" if needs_manual_review else "可继续", "warning" if needs_manual_review else "success"),
            ]
        )
        artifact_rows.append(
            [
                escape_html(material.get("original_filename", "")),
                download_chip(f"/downloads/materials/{material.get('id', '')}/raw", "原件"),
                download_chip(f"/downloads/materials/{material.get('id', '')}/clean", "清洗版"),
                download_chip(f"/downloads/materials/{material.get('id', '')}/desensitized", "脱敏版"),
                download_chip(f"/downloads/materials/{material.get('id', '')}/privacy", "隐私说明"),
            ]
        )

    for case in cases:
        case_rows.append(
            [
                link(f"/cases/{case.get('id', '')}", case.get("case_name", "") or case.get("id", "case")),
                escape_html(case.get("software_name", "") or "-"),
                escape_html(case.get("version", "") or "-"),
                pill(status_label(case.get("status", "unknown")), status_tone(case.get("status", "unknown"))),
                link(f"/reports/{case.get('report_id', '')}", "查看报告") if case.get("report_id") else "-",
            ]
        )

    correction_rows = [
        [
            escape_html(_correction_label(item.get("correction_type", ""))),
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
                f'<div class="inline-actions"><a class="button-secondary button-compact" href="/reports/{escape_html(report_id)}">查看报告</a>'
                f"{download_chip(f'/downloads/reports/{report_id}', '下载')}</div>"
                "</article>"
            )
            for report in reports
            for report_id in [str(report.get("id", "") or "")]
        ]
    )

    case_options = (
        "".join(
            f'<option value="{escape_html(case.get("id", ""))}">{escape_html(case.get("case_name", "") or case.get("id", ""))}</option>'
            for case in cases
        )
        or '<option value="">暂无项目</option>'
    )
    material_options = (
        "".join(
            f'<option value="{escape_html(material.get("id", ""))}">{escape_html(material.get("original_filename", ""))}</option>'
            for material in materials
        )
        or '<option value="">暂无材料</option>'
    )
    default_material_ids = ",".join(item.get("id", "") for item in materials[:1])

    import_digest = "".join(
        [
            _summary_tile("压缩包", str(submission.get("filename", "")), "当前导入的 ZIP 包"),
            _summary_tile("导入模式", mode_label(str(submission.get("mode", ""))), "本批次采用的整理策略"),
            _summary_tile("材料数", str(len(materials)), "识别到的材料条目"),
            _summary_tile("项目数", str(len(cases)), "已形成的项目分组"),
            _summary_tile("报告数", str(len(reports)), "已产出的报告数量"),
            _summary_tile("导入时间", str(submission.get("created_at", "")), "批次记录创建时间"),
        ]
    )

    triage_body = """
    <div class="sequence-board">
      <article class="sequence-step">
        <span class="sequence-index">1</span>
        <div>
          <strong>先看待复核队列</strong>
          <p>把需要人工判断的材料先挑出来，避免后面在项目和报告里反复返工。</p>
        </div>
      </article>
      <article class="sequence-step">
        <span class="sequence-index">2</span>
        <div>
          <strong>再核对材料矩阵</strong>
          <p>确认材料类型、版本、软件名和解析质量是否可信，再决定是否需要纠偏。</p>
        </div>
      </article>
      <article class="sequence-step">
        <span class="sequence-index">3</span>
        <div>
          <strong>最后人工干预与重跑</strong>
          <p>先改材料，再调分组，最后重跑审查并进入导出中心。</p>
        </div>
      </article>
    </div>
    <div class="inline-actions">
      <a class="button-secondary button-compact" href="#needs-review">{icon('alert', 'icon icon-sm')}看待复核</a>
      <a class="button-secondary button-compact" href="#material-matrix">{icon('cluster', 'icon icon-sm')}看材料矩阵</a>
      <a class="button-secondary button-compact" href="#operator-console">{icon('wrench', 'icon icon-sm')}去人工干预</a>
      <a class="button-secondary button-compact" href="#export-center">{icon('download', 'icon icon-sm')}去导出中心</a>
    </div>
    """

    needs_review_body = (
        '<div class="status-stack">'
        + "".join(
            '<article class="status-card">'
            f'{pill("待复核", "warning")}'
            f'<span><strong>{escape_html(name)}</strong><br>{escape_html(note)}</span>'
            "</article>"
            for name, note in needs_review_items
        )
        + "</div>"
        if needs_review_items
        else empty_state("暂无待复核材料", "这个批次当前没有需要人工介入的材料。")
    )

    export_body = (
        f'<div class="report-card-grid">{report_cards}</div>'
        if report_cards
        else empty_state("暂无报告", "批次审查完成后，这里会出现可查看和可下载的报告。")
    )
    export_body += (
        '<div class="inline-actions">'
        f'<a class="button-secondary" href="/downloads/submissions/{escape_html(submission.get("id", ""))}/bundle">{icon("download", "icon icon-sm")}下载批次包</a>'
        f'<a class="button-secondary" href="/downloads/logs/app">{icon("terminal", "icon icon-sm")}下载日志</a>'
        "</div>"
    )

    operator_body = f"""
    <div class="operator-note">
      <strong>人工干预台</strong>
      <span>所有人工操作都会回到当前批次，并在更正审计中留下可追溯记录，不会悄悄改状态。</span>
    </div>
    <div class="operator-note">
      <strong>操作建议</strong>
      <span>先处理待复核材料，再决定是否创建项目、重新分组或重新审查。真实模型开启后，重新审查耗时会增加。</span>
    </div>
    <div class="helper-chip-row">
      <span class="helper-chip">先改材料</span>
      <span class="helper-chip">再调分组</span>
      <span class="helper-chip">最后重跑审查</span>
    </div>
    <div class="operator-group-grid">
      <details class="operator-group" open>
        <summary>
          <span class="operator-group-index">1</span>
          <div>
            <strong>材料纠偏</strong>
            <small>先把识别错的材料类型和归属修正掉。</small>
          </div>
        </summary>
        <div class="control-grid">
          <form class="operator-form" action="/submissions/{escape_html(submission.get('id', ''))}/actions/change-type" method="post">
            <strong>更正材料类型</strong>
            <span class="field-hint">当系统识别错材料类型时使用。保存后会自动回到“更正审计”。</span>
            <label class="field"><span>材料</span><select name="material_id">{material_options}</select></label>
            <label class="field"><span>类型</span><select name="material_type">
              <option value="agreement">合作协议</option>
              <option value="source_code">源代码</option>
              <option value="info_form">信息采集表</option>
              <option value="software_doc">软件说明文档</option>
            </select></label>
            <label class="field"><span>备注</span><input type="text" name="note" placeholder="说明为什么要改类型"></label>
            <button class="button-secondary button-compact" type="submit">{icon('wrench', 'icon icon-sm')}保存并刷新</button>
          </form>

          <form class="operator-form" action="/submissions/{escape_html(submission.get('id', ''))}/actions/assign-case" method="post">
            <strong>指派到项目</strong>
            <span class="field-hint">把某份材料归入已有项目。如果项目列表为空，先创建项目。</span>
            <label class="field"><span>材料</span><select name="material_id">{material_options}</select></label>
            <label class="field"><span>目标项目</span><select name="case_id">{case_options}</select></label>
            <label class="field"><span>备注</span><input type="text" name="note" placeholder="记录这次归组原因"></label>
            <button class="button-secondary button-compact" type="submit">{icon('merge', 'icon icon-sm')}提交并刷新</button>
          </form>
        </div>
      </details>

      <details class="operator-group">
        <summary>
          <span class="operator-group-index">2</span>
          <div>
            <strong>项目编排</strong>
            <small>创建新项目，或者把拆散的项目重新合并。</small>
          </div>
        </summary>
        <div class="control-grid">
          <form class="operator-form" action="/submissions/{escape_html(submission.get('id', ''))}/actions/create-case" method="post">
            <strong>创建项目</strong>
            <span class="field-hint">从一份或多份材料创建新项目。若想一次带入多份材料，可填写逗号分隔的材料 ID。</span>
            <label class="field"><span>材料 ID</span><input type="text" name="material_ids" value="{escape_html(default_material_ids)}"></label>
            <label class="field"><span>项目名称</span><input type="text" name="case_name" value="{escape_html(submission.get('filename', '新项目'))}"></label>
            <label class="field"><span>版本号</span><input type="text" name="version"></label>
            <label class="field"><span>公司名称</span><input type="text" name="company_name"></label>
            <label class="field"><span>备注</span><input type="text" name="note" placeholder="记录创建原因"></label>
            <button class="button-secondary button-compact" type="submit">{icon('lock', 'icon icon-sm')}创建并刷新</button>
          </form>

          <form class="operator-form" action="/submissions/{escape_html(submission.get('id', ''))}/actions/merge-cases" method="post">
            <strong>合并项目</strong>
            <span class="field-hint">保留目标项目，把源项目并入目标项目，适用于同一软著被拆散的情况。</span>
            <label class="field"><span>源项目</span><select name="source_case_id">{case_options}</select></label>
            <label class="field"><span>目标项目</span><select name="target_case_id">{case_options}</select></label>
            <label class="field"><span>备注</span><input type="text" name="note" placeholder="记录合并原因"></label>
            <button class="button-secondary button-compact" type="submit">{icon('merge', 'icon icon-sm')}合并并刷新</button>
          </form>
        </div>
      </details>

      <details class="operator-group">
        <summary>
          <span class="operator-group-index">3</span>
          <div>
            <strong>复核重跑</strong>
            <small>在项目更正之后，统一重新生成结果。</small>
          </div>
        </summary>
        <div class="control-grid">
          <form class="operator-form" action="/submissions/{escape_html(submission.get('id', ''))}/actions/rerun-review" method="post">
            <strong>重新审查项目</strong>
            <span class="field-hint">完成更正或重组后使用，让风险结果、报告和 AI 补充意见都重新生成。</span>
            <label class="field"><span>项目</span><select name="case_id">{case_options}</select></label>
            <label class="field"><span>备注</span><input type="text" name="note" placeholder="说明为什么重跑"></label>
            <button class="button-secondary button-compact" type="submit">{icon('refresh', 'icon icon-sm')}重跑并刷新</button>
          </form>
        </div>
      </details>
    </div>
    """

    workspace_notice = ""
    if notice:
        workspace_notice = notice_banner(
            notice.get("title", "已更新"),
            notice.get("message", "当前批次页面已刷新。"),
            tone=notice.get("tone", "info"),
            icon_name=notice.get("icon_name", "check"),
            meta=notice.get("meta"),
        )

    content = f"""
    {panel('这个批次先怎么处理', triage_body, kicker='推荐顺序', extra_class='span-12 panel-soft', icon_name='spark', description='先把复核和纠偏顺序走对，再看项目与导出，整体会更稳。', panel_id='triage-flow')}
    <section class="kpi-grid">
      {metric_card('材料数', str(len(materials)), '当前批次已识别的材料数量', 'info', icon_name='file')}
      {metric_card('项目数', str(len(cases)), '当前批次已形成的项目数量', 'success', icon_name='lock')}
      {metric_card('报告数', str(len(reports)), '当前可查看的报告数量', 'neutral', icon_name='report')}
      {metric_card('待复核', str(len(needs_review_items)), '需要人工处理的材料数量', 'warning' if needs_review_items else 'success', icon_name='alert')}
    </section>
    <section class="dashboard-grid">
      {panel('导入摘要', f'<div class="summary-grid">{import_digest}</div>', kicker='批次摘要', extra_class='span-4', icon_name='file', description='先确认这个批次导入了什么，再决定后续操作。', panel_id='import-digest')}
      {panel('待复核队列', needs_review_body, kicker='人工复核', extra_class='span-4', icon_name='alert', description='需要人介入的材料会优先集中在这里。', panel_id='needs-review')}
      {panel('导出中心', export_body, kicker='产物交付', extra_class='span-4', icon_name='download', description='报告、批次包和日志都可以从这里直接拿走。', panel_id='export-center')}
      {panel('材料矩阵', table(['文件名', '类型', '软件名', '版本', '问题数', '解析质量', '状态'], material_rows), kicker='材料诊断', extra_class='span-8', icon_name='cluster', description='这是当前批次最核心的诊断表，适合逐行排查。', panel_id='material-matrix')}
      {panel('项目分组', table(['项目', '软件名', '版本', '状态', '报告'], case_rows), kicker='分组结果', extra_class='span-4', icon_name='lock', description='查看系统如何把材料聚合为项目，并进入单项目详情。', panel_id='case-registry')}
      {panel('产物浏览', table(['文件名', '原件', '清洗版', '脱敏版', '隐私说明'], artifact_rows), kicker='材料产物', extra_class='span-4', icon_name='download', description='原件、清洗版和脱敏版都保持可见，便于核查。', panel_id='artifact-browser')}
      {panel('人工干预台', operator_body, kicker='纠偏操作', extra_class='span-8', icon_name='wrench', description='所有纠偏动作都显式可见、可回溯、可通过重跑刷新结果。', panel_id='operator-console')}
      {panel('更正审计', table(['操作类型', '对象', '备注', '时间'], correction_rows), kicker='操作留痕', extra_class='span-12', icon_name='clock', description='每一次人工动作都会记录下来，便于事后回溯。', panel_id='correction-audit')}
    </section>
    """

    return layout(
        title=submission.get("filename", "批次详情"),
        active_nav="submissions",
        header_tag="批次详情",
        header_title=submission.get("filename", "批次详情"),
        header_subtitle="集中查看这个批次的材料矩阵、待复核队列、人工干预台和导出产物。",
        header_meta="".join(
            [
                pill(status_label(submission.get("status", "unknown")), status_tone(submission.get("status", "unknown"))),
                pill(mode_label(submission.get("mode", "")), "info"),
                pill(f"{len(cases)} 个项目", "neutral"),
            ]
        ),
        content=content,
        header_note="先看导入摘要和待复核队列，再核对材料矩阵，最后使用人工干预台与导出中心。",
        page_links=[
            ("#needs-review", "待复核队列", "alert"),
            ("#material-matrix", "材料矩阵", "cluster"),
            ("#operator-console", "人工干预台", "wrench"),
            ("#export-center", "导出中心", "download"),
        ],
        workspace_notice=workspace_notice,
    )
