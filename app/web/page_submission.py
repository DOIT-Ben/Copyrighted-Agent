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


def _summary_tile(label: str, value: str, note: str) -> str:
    return (
        '<div class="summary-tile">'
        f"<span>{escape_html(label)}</span>"
        f"<strong>{escape_html(value)}</strong>"
        f"<small>{escape_html(note)}</small>"
        "</div>"
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


def _correction_label(value: str) -> str:
    return CORRECTION_LABELS.get(str(value or "").strip(), value or "-")


def _quality_bucket_label(value: str) -> str:
    return QUALITY_BUCKET_LABELS.get(str(value or "").strip(), value or "待判断")


def _build_parse_lookup(parse_results: list[dict]) -> dict[str, dict]:
    lookup: dict[str, dict] = {}
    for item in parse_results:
        material_id = str(item.get("material_id", "") or item.get("id", "") or "").strip()
        if material_id:
            lookup[material_id] = item
    return lookup


def _submission_corrections(submission_id: str) -> list[dict]:
    submission = store.submissions.get(submission_id)
    if not submission:
        return []
    result = [
        store.corrections[item_id].to_dict()
        for item_id in submission.correction_ids
        if item_id in store.corrections
    ]
    return sorted(result, key=lambda item: item.get("corrected_at", ""), reverse=True)


def _submission_header_meta(submission: dict, cases: list[dict]) -> str:
    return "".join(
        [
            pill(status_label(submission.get("status", "unknown")), status_tone(submission.get("status", "unknown"))),
            pill(mode_label(submission.get("mode", "")), "info"),
            pill(f"{len(cases)} 个项目", "neutral"),
        ]
    )


def _submission_view_data(
    submission: dict,
    materials: list[dict],
    cases: list[dict],
    reports: list[dict],
    parse_results: list[dict],
) -> dict:
    parse_lookup = _build_parse_lookup(parse_results)
    corrections = _submission_corrections(str(submission.get("id", "")))

    needs_review_items: list[tuple[str, str]] = []
    material_rows: list[list[str]] = []
    artifact_rows: list[list[str]] = []
    case_rows: list[list[str]] = []

    for material in materials:
        parse_result = parse_lookup.get(str(material.get("id", "")), {})
        metadata = dict(parse_result.get("metadata_json", {}) or {})
        triage = dict(metadata.get("triage", {}) or {})
        parse_quality = dict(metadata.get("parse_quality", {}) or metadata.get("quality", {}) or {})
        issue_count = len(material.get("issues", []) or [])
        needs_manual_review = bool(triage.get("needs_manual_review", False)) or material.get("material_type") == "unknown"

        if needs_manual_review:
            needs_review_items.append(
                (
                    str(material.get("original_filename", "") or material.get("id", "material")),
                    str(triage.get("review_recommendation", "") or "建议人工复核"),
                )
            )

        quality_bucket = str(parse_quality.get("legacy_doc_bucket", "") or parse_quality.get("bucket", "") or "unknown")
        material_rows.append(
            [
                escape_html(material.get("original_filename", "") or "-"),
                pill(type_label(material.get("material_type", "unknown")), status_tone(material.get("review_status", "unknown"))),
                escape_html(material.get("detected_software_name", "") or "-"),
                escape_html(material.get("detected_version", "") or "-"),
                pill(str(issue_count), issue_tone(issue_count)),
                escape_html(_quality_bucket_label(quality_bucket)),
                pill("待复核" if needs_manual_review else "可继续", "warning" if needs_manual_review else "success"),
            ]
        )
        artifact_rows.append(
            [
                escape_html(material.get("original_filename", "") or "-"),
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
    )

    return {
        "needs_review_items": needs_review_items,
        "material_rows": material_rows,
        "artifact_rows": artifact_rows,
        "case_rows": case_rows,
        "correction_rows": correction_rows,
        "report_cards": report_cards,
    }


def render_submissions_index() -> str:
    submissions = sorted(store.submissions.values(), key=lambda item: item.created_at, reverse=True)
    total = len(submissions)
    materials_total = sum(len(item.material_ids) for item in submissions)
    cases_total = sum(len(item.case_ids) for item in submissions)
    reports_total = sum(len(item.report_ids) for item in submissions)
    latest_status = submissions[0].status if submissions else "idle"
    status_counts = Counter(str(item.status or "unknown") for item in submissions)

    rows = [
        [
            link(f"/submissions/{submission.id}", submission.filename),
            escape_html(mode_label(submission.mode)),
            pill(status_label(submission.status), status_tone(submission.status)),
            escape_html(str(len(submission.material_ids))),
            escape_html(str(len(submission.case_ids))),
            escape_html(str(len(submission.report_ids))),
            escape_html(submission.created_at),
        ]
        for submission in submissions
    ]

    distribution_body = "".join(
        [
            _metric_row("已完成", status_counts.get("completed", 0), total, "success", "check"),
            _metric_row("处理中", status_counts.get("processing", 0), total, "warning", "cluster"),
            _metric_row("失败", status_counts.get("failed", 0), total, "danger", "alert"),
        ]
    )

    action_body = (
        '<div class="summary-grid">'
        f'{_summary_tile("先看状态", "快速排查", "先定位失败、处理中和需要重点关注的批次。")}'
        f'{_summary_tile("再进详情", "按批处理", "进入批次页后再看导入摘要、产物浏览、人工干预台和导出中心。")}'
        f'{_summary_tile("保持简洁", "不堆说明", "总览页只负责发现批次和进入下一步。")}'
        "</div>"
        '<div class="inline-actions">'
        f'<a class="button-secondary button-compact" href="/">{icon("dashboard", "icon icon-sm")}返回总控台</a>'
        '<a class="button-secondary button-compact" href="#batch-registry">'
        f'{icon("layers", "icon icon-sm")}查看批次台账</a>'
        "</div>"
    )

    content = f"""
    <section class="kpi-grid">
      {metric_card('批次数', str(total), '当前已导入的批次总量', 'info', icon_name='layers')}
      {metric_card('材料数', str(materials_total), '全部批次识别出的材料总量', 'success', icon_name='file')}
      {metric_card('项目数', str(cases_total), '全部批次形成的项目数量', 'warning', icon_name='lock')}
      {metric_card('报告数', str(reports_total), '当前可交付的报告数量', 'neutral', icon_name='report')}
    </section>
    <section class="dashboard-grid">
      {panel('批次台账', table(['压缩包', '导入模式', '状态', '材料数', '项目数', '报告数', '创建时间'], rows), kicker='批次总览', extra_class='span-8', icon_name='layers', description='只保留列表和入口，避免总览页继续堆叠复杂操作。', panel_id='batch-registry')}
      {panel('状态分布', distribution_body, kicker='运行状态', extra_class='span-4', icon_name='bar', description='快速判断当前批次池是否稳定。', panel_id='status-distribution')}
      {panel('查看方式', action_body, kicker='处理顺序', extra_class='span-12 panel-soft', icon_name='search', description='先在这里找到目标批次，再进入批次页做细节处理。', panel_id='registry-actions')}
    </section>
    """

    return layout(
        title="批次总览",
        active_nav="submissions",
        header_tag="批次总览",
        header_title="批次总览台账",
        header_subtitle="先定位目标批次，再进入批次详情页处理具体审查工作。",
        header_meta="".join(
            [
                pill(f"{len(submissions)} 个批次", "info"),
                pill(status_label(latest_status), status_tone(latest_status)),
            ]
        ),
        content=content,
        header_note="总览页只负责发现问题和进入详情，不承担材料纠偏、导出和大表浏览。",
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
    data = _submission_view_data(submission, materials, cases, reports, parse_results)
    submission_id = escape_html(submission.get("id", ""))

    import_digest = "".join(
        [
            _summary_tile("导入文件", str(submission.get("filename", "") or "-"), "当前导入的 ZIP 包"),
            _summary_tile("导入模式", mode_label(str(submission.get("mode", ""))), "本批次采用的整理策略"),
            _summary_tile("材料数", str(len(materials)), "本批次识别出的材料数量"),
            _summary_tile("项目数", str(len(cases)), "当前已形成的项目分组"),
            _summary_tile("报告数", str(len(reports)), "当前已生成的报告数量"),
            _summary_tile("导入时间", str(submission.get("created_at", "") or "-"), "批次记录创建时间"),
        ]
    )

    needs_review_body = (
        '<div class="summary-grid">'
        + "".join(_summary_tile(name, "待复核", note) for name, note in data["needs_review_items"][:6])
        + "</div>"
        if data["needs_review_items"]
        else empty_state("暂无待复核材料", "当前这个批次没有需要人工优先确认的材料。")
    )

    if len(data["needs_review_items"]) > 6:
        needs_review_body += (
            f'<div class="operator-note"><strong>还有 {len(data["needs_review_items"]) - 6} 项</strong>'
            "<span>其余材料请进入产物浏览页继续核查。</span></div>"
        )

    nav_body = f"""
    <div class="summary-grid">
      {_summary_tile("导入摘要", "先看这里", "确认这个批次导入了什么、规模多大。")}
      {_summary_tile("产物浏览", "独立页面", "材料矩阵、项目分组和下载产物单独查看。")}
      {_summary_tile("人工干预台", "独立页面", "所有纠偏表单集中到一个页面。")}
      {_summary_tile("导出中心", "独立页面", "报告、批次包和日志统一收口。")}
    </div>
    <div class="inline-actions">
      <a class="button-secondary" href="/submissions/{submission_id}/materials">{icon('cluster', 'icon icon-sm')}进入产物浏览</a>
      <a class="button-secondary" href="/submissions/{submission_id}/operator">{icon('wrench', 'icon icon-sm')}进入人工干预台</a>
      <a class="button-secondary" href="/submissions/{submission_id}/exports">{icon('download', 'icon icon-sm')}进入导出中心</a>
    </div>
    """

    audit_body = (
        table(["操作类型", "对象", "备注", "时间"], data["correction_rows"])
        if data["correction_rows"]
        else empty_state("暂无更正记录", "人工纠偏发生后，这里会保留完整留痕。")
    )

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
    <section class="kpi-grid">
      {metric_card('材料数', str(len(materials)), '当前批次识别出的材料数量', 'info', icon_name='file')}
      {metric_card('项目数', str(len(cases)), '当前批次形成的项目数量', 'success', icon_name='lock')}
      {metric_card('报告数', str(len(reports)), '当前可查看的报告数量', 'neutral', icon_name='report')}
      {metric_card('待复核', str(len(data['needs_review_items'])), '需要人工优先关注的材料数量', 'warning' if data['needs_review_items'] else 'success', icon_name='alert')}
    </section>
    <section class="dashboard-grid">
      {panel('导入摘要', f'<div class="summary-grid">{import_digest}</div>', kicker='批次摘要', extra_class='span-12 panel-soft', icon_name='file', description='主页面只保留这个批次的核心概览。', panel_id='import-digest')}
      {panel('待复核队列', needs_review_body, kicker='优先处理', extra_class='span-12', icon_name='alert', description='先确认这些材料，再进入下级页面处理细节。', panel_id='needs-review')}
      {panel('页面导航', nav_body, kicker='拆页处理', extra_class='span-12', icon_name='search', description='把高密度内容拆出去，避免继续堆在一个页面。', panel_id='page-navigation')}
      {panel('更正审计', audit_body, kicker='留痕记录', extra_class='span-12', icon_name='clock', description='人工动作统一留痕，便于回溯。', panel_id='correction-audit')}
    </section>
    """

    return layout(
        title=submission.get("filename", "批次详情"),
        active_nav="submissions",
        header_tag="批次详情",
        header_title=submission.get("filename", "批次详情"),
        header_subtitle="这个页面只保留概览、待复核队列和进入各子页面的入口。",
        header_meta=_submission_header_meta(submission, cases),
        content=content,
        header_note="导入摘要、产物浏览、人工干预台、导出中心已经拆开，主页面不再承载所有内容。",
        page_links=[
            ("#import-digest", "导入摘要", "file"),
            ("#needs-review", "待复核队列", "alert"),
            (f"/submissions/{submission.get('id', '')}/materials", "产物浏览", "cluster"),
            (f"/submissions/{submission.get('id', '')}/operator", "人工干预台", "wrench"),
            (f"/submissions/{submission.get('id', '')}/exports", "导出中心", "download"),
            ("#correction-audit", "更正审计", "clock"),
        ],
        workspace_notice=workspace_notice,
    )


def render_submission_materials_page(
    submission: dict,
    materials: list[dict],
    cases: list[dict],
    reports: list[dict],
    parse_results: list[dict],
) -> str:
    data = _submission_view_data(submission, materials, cases, reports, parse_results)

    queue_body = (
        '<div class="summary-grid">'
        + "".join(_summary_tile(name, "待复核", note) for name, note in data["needs_review_items"][:4])
        + "</div>"
        if data["needs_review_items"]
        else empty_state("暂无待复核项", "材料解析结果当前没有需要优先人工处理的内容。")
    )

    content = f"""
    <section class="kpi-grid">
      {metric_card('材料数', str(len(materials)), '当前批次材料总数', 'info', icon_name='file')}
      {metric_card('待复核', str(len(data['needs_review_items'])), '需要人工判断的材料数', 'warning' if data['needs_review_items'] else 'success', icon_name='alert')}
    </section>
    <section class="dashboard-grid">
      {panel('待复核队列', queue_body, kicker='优先处理', extra_class='span-12 panel-soft', icon_name='alert', description='先看需要人工判断的材料。', panel_id='needs-review')}
      {panel('材料矩阵', table(['文件名', '类型', '软件名', '版本', '问题数', '解析质量', '状态'], data['material_rows']), kicker='材料诊断', extra_class='span-12', icon_name='cluster', description='空间不足时宁可向下排，也不再横向压缩。', panel_id='material-matrix')}
      {panel('项目分组', table(['项目', '软件名', '版本', '状态', '报告'], data['case_rows']), kicker='分组结果', extra_class='span-12', icon_name='lock', description='查看系统如何把材料聚合成项目。', panel_id='case-registry')}
      {panel('产物浏览', table(['文件名', '原件', '清洗版', '脱敏版', '隐私说明'], data['artifact_rows']), kicker='材料产物', extra_class='span-12', icon_name='download', description='原件、清洗版和脱敏版都集中在这里。', panel_id='artifact-browser')}
    </section>
    """

    return layout(
        title=f"{submission.get('filename', '批次详情')} - 产物浏览",
        active_nav="submissions",
        header_tag="产物浏览",
        header_title="产物浏览",
        header_subtitle="把材料矩阵、项目分组和材料产物集中到一个独立页面。",
        header_meta=_submission_header_meta(submission, cases),
        content=content,
        header_note="如果需要纠偏，请进入人工干预台；如果要交付结果，请进入导出中心。",
        page_links=[
            (f"/submissions/{submission.get('id', '')}", "批次总览", "file"),
            ("#needs-review", "待复核队列", "alert"),
            ("#material-matrix", "材料矩阵", "cluster"),
            ("#case-registry", "项目分组", "lock"),
            ("#artifact-browser", "产物浏览", "download"),
        ],
    )


def render_submission_operator_page(
    submission: dict,
    materials: list[dict],
    cases: list[dict],
    reports: list[dict],
    parse_results: list[dict],
) -> str:
    data = _submission_view_data(submission, materials, cases, reports, parse_results)
    submission_id = escape_html(submission.get("id", ""))

    case_options = (
        "".join(
            f'<option value="{escape_html(case.get("id", ""))}">{escape_html(case.get("case_name", "") or case.get("id", ""))}</option>'
            for case in cases
        )
        or '<option value="">暂无项目</option>'
    )
    material_options = (
        "".join(
            f'<option value="{escape_html(material.get("id", ""))}">{escape_html(material.get("original_filename", "") or material.get("id", ""))}</option>'
            for material in materials
        )
        or '<option value="">暂无材料</option>'
    )
    default_material_ids = ",".join(str(item.get("id", "")) for item in materials[:1])

    operator_intro = (
        '<div class="summary-grid">'
        f'{_summary_tile("顺序", "先改材料再调分组", "先修正材料，再处理项目，最后重跑审查。")}'
        f'{_summary_tile("影响", "动作会留痕", "所有操作都会写入更正审计。")}'
        f'{_summary_tile("建议", "只做必要动作", "避免无差别重跑，减少噪音。")}'
        "</div>"
    )

    operator_body = f"""
    {operator_intro}
    <div class="operator-group-grid">
      <details class="operator-group" open>
        <summary>
          <span class="operator-group-index">1</span>
          <div>
            <strong>材料纠偏</strong>
            <small>先修正识别错误的材料类型和归属。</small>
          </div>
        </summary>
        <div class="control-grid">
          <form class="operator-form" action="/submissions/{submission_id}/actions/change-type" method="post">
            <strong>更正材料类型</strong>
            <label class="field"><span>材料</span><select name="material_id">{material_options}</select></label>
            <label class="field"><span>类型</span><select name="material_type">
              <option value="agreement">合作协议</option>
              <option value="source_code">源代码</option>
              <option value="info_form">信息采集表</option>
              <option value="software_doc">软件说明文档</option>
            </select></label>
            <label class="field"><span>备注</span><input type="text" name="note" placeholder="说明为什么要修改"></label>
            <button class="button-secondary button-compact" type="submit">{icon('wrench', 'icon icon-sm')}保存并刷新</button>
          </form>
          <form class="operator-form" action="/submissions/{submission_id}/actions/assign-case" method="post">
            <strong>指派到项目</strong>
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
            <small>创建新项目，或把拆散的项目重新合并。</small>
          </div>
        </summary>
        <div class="control-grid">
          <form class="operator-form" action="/submissions/{submission_id}/actions/create-case" method="post">
            <strong>创建项目</strong>
            <label class="field"><span>材料 ID</span><input type="text" name="material_ids" value="{escape_html(default_material_ids)}"></label>
            <label class="field"><span>项目名称</span><input type="text" name="case_name" value="{escape_html(submission.get('filename', '新项目'))}"></label>
            <label class="field"><span>版本号</span><input type="text" name="version"></label>
            <label class="field"><span>公司名称</span><input type="text" name="company_name"></label>
            <label class="field"><span>备注</span><input type="text" name="note" placeholder="记录创建原因"></label>
            <button class="button-secondary button-compact" type="submit">{icon('lock', 'icon icon-sm')}创建并刷新</button>
          </form>
          <form class="operator-form" action="/submissions/{submission_id}/actions/merge-cases" method="post">
            <strong>合并项目</strong>
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
            <small>确认项目整理完成后，再统一重跑审查。</small>
          </div>
        </summary>
        <div class="control-grid">
          <form class="operator-form" action="/submissions/{submission_id}/actions/rerun-review" method="post">
            <strong>重新审查项目</strong>
            <label class="field"><span>项目</span><select name="case_id">{case_options}</select></label>
            <label class="field"><span>备注</span><input type="text" name="note" placeholder="说明为什么重跑"></label>
            <button class="button-secondary button-compact" type="submit">{icon('refresh', 'icon icon-sm')}重跑并刷新</button>
          </form>
        </div>
      </details>
    </div>
    """

    content = f"""
    <section class="dashboard-grid">
      {panel('人工干预台', operator_body, kicker='纠偏操作', extra_class='span-12', icon_name='wrench', description='所有纠偏动作集中在这里，不再挤在批次总览页。', panel_id='operator-console')}
      {panel('更正审计', table(['操作类型', '对象', '备注', '时间'], data['correction_rows']), kicker='留痕记录', extra_class='span-12', icon_name='clock', description='每一次人工动作都会留痕，方便回溯。', panel_id='correction-audit')}
    </section>
    """

    return layout(
        title=f"{submission.get('filename', '批次详情')} - 人工干预台",
        active_nav="submissions",
        header_tag="人工干预台",
        header_title="人工干预台",
        header_subtitle="纠偏表单单独承载，主页面不再被长表单压垮。",
        header_meta=_submission_header_meta(submission, cases),
        content=content,
        header_note="先在产物浏览页确认问题，再回到这里执行必要的人工修正。",
        page_links=[
            (f"/submissions/{submission.get('id', '')}", "批次总览", "file"),
            ("#operator-console", "人工干预台", "wrench"),
            ("#correction-audit", "更正审计", "clock"),
        ],
    )


def render_submission_exports_page(
    submission: dict,
    materials: list[dict],
    cases: list[dict],
    reports: list[dict],
    parse_results: list[dict],
) -> str:
    data = _submission_view_data(submission, materials, cases, reports, parse_results)
    submission_id = escape_html(submission.get("id", ""))

    export_body = (
        '<div class="summary-grid">'
        f'{_summary_tile("报告数", str(len(reports)), "当前批次可下载的报告数量")}'
        f'{_summary_tile("批次包", "可直接下载", "适合整体交付或归档")}'
        f'{_summary_tile("应用日志", "可直接下载", "需要追踪处理过程时再使用")}'
        "</div>"
        '<div class="inline-actions">'
        f'<a class="button-secondary" href="/downloads/submissions/{submission_id}/bundle">{icon("download", "icon icon-sm")}下载批次包</a>'
        f'<a class="button-secondary" href="/downloads/logs/app">{icon("terminal", "icon icon-sm")}下载日志</a>'
        "</div>"
        + (
            f'<div class="report-card-grid">{data["report_cards"]}</div>'
            if data["report_cards"]
            else empty_state("暂无报告", "批次审查完成后，这里会出现可查看和可下载的报告。")
        )
    )

    content = f"""
    <section class="dashboard-grid">
      {panel('导出中心', export_body, kicker='产物交付', extra_class='span-12', icon_name='download', description='报告、批次包和日志统一集中到这里。', panel_id='export-center')}
    </section>
    """

    return layout(
        title=f"{submission.get('filename', '批次详情')} - 导出中心",
        active_nav="submissions",
        header_tag="导出中心",
        header_title="导出中心",
        header_subtitle="把交付动作集中收口，避免和材料处理页面混在一起。",
        header_meta=_submission_header_meta(submission, cases),
        content=content,
        header_note="如果要查看材料原件、清洗版和脱敏版，请进入产物浏览页。",
        page_links=[
            (f"/submissions/{submission.get('id', '')}", "批次总览", "file"),
            ("#export-center", "导出中心", "download"),
        ],
    )


__all__ = [
    "render_submission_detail",
    "render_submission_exports_page",
    "render_submission_materials_page",
    "render_submission_operator_page",
    "render_submissions_index",
]
