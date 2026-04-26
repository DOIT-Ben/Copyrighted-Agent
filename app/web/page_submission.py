from __future__ import annotations

from collections import Counter

from app.core.services.online_filing import normalize_online_filing, online_filing_summary
from app.core.services.review_profile import dimension_title, normalize_review_profile, review_profile_summary
from app.core.services.review_rulebook import dimension_rulebook_from_profile
from app.core.services.runtime_store import store
from app.core.utils.text import escape_html

from app.web.review_profile_widgets import render_review_profile_form_fields
from app.web.view_helpers import (
    download_chip,
    empty_state,
    icon,
    issue_tone,
    layout,
    link,
    list_pairs,
    metric_card,
    mode_label,
    notice_banner,
    panel,
    pill,
    report_label,
    review_stage_label,
    review_strategy_label,
    status_label,
    status_tone,
    table,
    type_label,
)


CORRECTION_LABELS = {
    "change_material_type": "更正材料类型",
    "assign_material_to_case": "调整项目归属",
    "create_case_from_materials": "从材料创建项目",
    "merge_cases": "合并项目",
    "rerun_case_review": "重新审查项目",
    "update_review_dimension_rule": "更新审查规则",
    "reset_review_dimension_rule": "恢复默认规则",
    "continue_case_review_from_desensitized": "脱敏后继续审查",
    "upload_desensitized_package": "上传脱敏包",
}


QUALITY_BUCKET_LABELS = {
    "usable_text": "文本可用",
    "partial_fragments": "片段可用",
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
        f'<div class="control-grid">{body}</div>'
        "</details>"
    )


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
    rows = [store.corrections[item_id].to_dict() for item_id in submission.correction_ids if item_id in store.corrections]
    return sorted(rows, key=lambda item: item.get("corrected_at", ""), reverse=True)


def _submission_header_meta(submission: dict, cases: list[dict]) -> str:
    return "".join(
        [
            pill(status_label(submission.get("status", "unknown")), status_tone(submission.get("status", "unknown"))),
            pill(mode_label(submission.get("mode", "")), "info"),
            pill(review_strategy_label(submission.get("review_strategy", "auto_review")), "neutral"),
            pill(review_stage_label(submission.get("review_stage", "review_completed")), "neutral"),
            pill(f"{len(cases)} 个项目", "neutral"),
        ]
    )


def _pending_manual_cases(cases: list[dict]) -> list[dict]:
    return [case for case in cases if case.get("status") == "awaiting_manual_review"]


def _continue_review_forms(submission: dict, cases: list[dict]) -> str:
    pending_cases = _pending_manual_cases(cases)
    if not pending_cases:
        return empty_state("当前没有待继续审查的项目", "如果当前批次是直接审查模式，结果会在导出中心直接查看。")

    forms = []
    submission_id = escape_html(submission.get("id", ""))
    for case in pending_cases:
        case_id = escape_html(case.get("id", ""))
        case_name = escape_html(case.get("case_name", "") or case.get("software_name", "") or case_id)
        forms.append(
            '<form class="operator-form" action="/submissions/'
            + submission_id
            + '/actions/continue-review" method="post">'
            + "<strong>继续审查项目</strong>"
            + f"<p>{case_name}</p>"
            + f'<input type="hidden" name="case_id" value="{case_id}">'
            + '<label class="field"><span>备注</span><input type="text" name="note" placeholder="例如：已确认脱敏件可继续"></label>'
            + '<button class="button-secondary button-compact" type="submit">'
            + icon("refresh", "icon icon-sm")
            + "继续审查</button></form>"
        )
    return '<div class="control-grid">' + "".join(forms) + "</div>"


def _submission_view_data(
    submission: dict,
    materials: list[dict],
    cases: list[dict],
    reports: list[dict],
    parse_results: list[dict],
) -> dict:
    del reports
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
                download_chip(f"/downloads/materials/{material.get('id', '')}/clean", "清洗件"),
                download_chip(f"/downloads/materials/{material.get('id', '')}/desensitized", "脱敏件"),
                download_chip(f"/downloads/materials/{material.get('id', '')}/privacy", "隐私说明"),
            ]
        )

    for case in cases:
        report_cell = "-"
        if case.get("report_id"):
            report_cell = link(f"/reports/{case.get('report_id', '')}", "查看报告")
        case_rows.append(
            [
                link(f"/cases/{case.get('id', '')}", case.get("case_name", "") or case.get("id", "case")),
                escape_html(case.get("software_name", "") or "-"),
                escape_html(case.get("version", "") or "-"),
                pill(status_label(case.get("status", "unknown")), status_tone(case.get("status", "unknown"))),
                escape_html(review_stage_label(case.get("review_stage", "review_completed"))),
                report_cell,
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

    return {
        "needs_review_items": needs_review_items,
        "material_rows": material_rows,
        "artifact_rows": artifact_rows,
        "case_rows": case_rows,
        "correction_rows": correction_rows,
    }


def _review_rule_links(submission_id: str, review_profile: dict, *, case_id: str = "") -> str:
    enabled_dimensions = list(review_profile.get("enabled_dimensions", []) or [])
    rulebook = dimension_rulebook_from_profile(review_profile)
    if not enabled_dimensions:
        return empty_state("暂无规则入口", "当前没有启用的审查重点。")
    chips = []
    suffix = f"?case_id={escape_html(case_id)}" if case_id else ""
    for key in enabled_dimensions:
        entry = rulebook.get(key, {})
        chips.append(
            f'<a class="button-secondary button-compact" href="/submissions/{escape_html(submission_id)}/review-rules/{escape_html(key)}{suffix}">'
            f'{icon("wrench", "icon icon-sm")}编辑规则：{escape_html(entry.get("title", dimension_title(key)))}'
            "</a>"
        )
    return '<div class="inline-actions">' + "".join(chips) + "</div>"


def render_submissions_index() -> str:
    submissions = sorted(store.submissions.values(), key=lambda item: item.created_at, reverse=True)
    total = len(submissions)
    materials_total = sum(len(item.material_ids) for item in submissions)
    cases_total = sum(len(item.case_ids) for item in submissions)
    reports_total = sum(len(item.report_ids) for item in submissions)
    latest_status = submissions[0].status if submissions else "idle"
    status_counts = Counter(str(item.status or "unknown") for item in submissions)

    def _batch_name_cell(submission) -> str:
        filename = escape_html(str(submission.filename or "-"))
        submission_id = escape_html(str(submission.id))
        return (
            '<div class="batch-file-cell">'
            f'<a class="batch-file-name table-link" href="/submissions/{submission_id}" title="{filename}">{filename}</a>'
            '<div class="batch-meta-row">'
            f'<span>{escape_html(mode_label(submission.mode))}</span>'
            f'<span>{escape_html(review_strategy_label(getattr(submission, "review_strategy", "auto_review")))}</span>'
            "</div></div>"
        )

    def _batch_count_cell(submission) -> str:
        return (
            '<div class="batch-counts">'
            f'<span><strong>{escape_html(str(len(submission.material_ids)))}</strong>材料</span>'
            f'<span><strong>{escape_html(str(len(submission.case_ids)))}</strong>项目</span>'
            f'<span><strong>{escape_html(str(len(submission.report_ids)))}</strong>报告</span>'
            "</div>"
        )

    rows = [
        [
            _batch_name_cell(submission),
            pill(status_label(submission.status), status_tone(submission.status)),
            escape_html(review_stage_label(getattr(submission, "review_stage", "review_completed"))),
            _batch_count_cell(submission),
            escape_html(submission.created_at),
            f'<a class="button-secondary button-compact" href="/submissions/{escape_html(str(submission.id))}">{icon("search", "icon icon-sm")}详情</a>',
        ]
        for submission in submissions
    ]

    distribution_body = "".join(
        [
            _metric_row("已完成", status_counts.get("completed", 0), total, "success", "check"),
            _metric_row("处理中", status_counts.get("processing", 0), total, "warning", "cluster"),
            _metric_row("待继续审查", status_counts.get("awaiting_manual_review", 0), total, "warning", "alert"),
            _metric_row("失败", status_counts.get("failed", 0), total, "danger", "alert"),
        ]
    )

    content = f"""
    <section class="kpi-grid">
      {metric_card('批次数', str(total), '当前已导入的批次数量', 'info', icon_name='layers')}
      {metric_card('材料数', str(materials_total), '全部批次识别出的材料总量', 'success', icon_name='file')}
      {metric_card('项目数', str(cases_total), '全部批次形成的项目总量', 'warning', icon_name='lock')}
      {metric_card('报告数', str(reports_total), '当前已生成的项目级报告数量', 'neutral', icon_name='report')}
    </section>
    <section class="dashboard-grid">
      {panel('批次台账', table(['批次', '状态', '阶段', '数量', '创建时间', '操作'], rows) if rows else empty_state('暂无批次', '导入 ZIP 后，这里会出现批次记录。'), kicker='批次总览', extra_class='span-12 panel-batch-registry', icon_name='layers', description='这里只保留列表和入口，避免总览页继续堆复杂操作。', panel_id='batch-registry')}
      {panel('状态分布', distribution_body, kicker='运行状态', extra_class='span-12 panel-soft', icon_name='bar', description='快速判断当前批次池是否稳定。', panel_id='status-distribution')}
    </section>
    """

    return layout(
        title="批次总览",
        active_nav="submissions",
        header_tag="批次总览",
        header_title="批次总览台账",
        header_subtitle="先定位目标批次，再进入批次详情页处理具体审查工作。",
        header_meta="".join([pill(f"{len(submissions)} 个批次", "info"), pill(status_label(latest_status), status_tone(latest_status))]),
        content=content,
        header_note="总览页只负责发现问题和进入详情，不承载材料纠偏、导出和大表浏览。",
        page_links=[
            ("#batch-registry", "批次台账", "layers"),
            ("#status-distribution", "状态分布", "bar"),
        ],
    )


def render_submission_detail_legacy(
    submission: dict,
    materials: list[dict],
    cases: list[dict],
    reports: list[dict],
    parse_results: list[dict],
    notice: dict | None = None,
) -> str:
    data = _submission_view_data(submission, materials, cases, reports, parse_results)
    submission_id = escape_html(submission.get("id", ""))
    pending_cases = _pending_manual_cases(cases)
    review_profile = normalize_review_profile(submission.get("review_profile", {}))

    workspace_notice = ""
    if notice:
        workspace_notice = notice_banner(
            notice.get("title", "已更新"),
            notice.get("message", "当前批次页面已刷新。"),
            tone=notice.get("tone", "info"),
            icon_name=notice.get("icon_name", "check"),
            meta=notice.get("meta"),
        )

    import_digest = "".join(
        [
            _summary_tile("导入文件", str(submission.get("filename", "") or "-"), "当前导入的 ZIP 包"),
            _summary_tile("导入模式", mode_label(str(submission.get("mode", ""))), "本批次采用的整理方式"),
            _summary_tile("审查策略", review_strategy_label(str(submission.get("review_strategy", "auto_review"))), "决定是直接审查还是先脱敏后继续"),
            _summary_tile("当前阶段", review_stage_label(str(submission.get("review_stage", "review_completed"))), "精确显示本批次正在脱敏、待回传或已完成审查"),
            _summary_tile("下一步", "进入产物或导出", "按当前阶段选择产物浏览、人工干预或导出中心"),
            _summary_tile("更多信息", "已收起", "材料、审查配置和留痕在下方分区查看"),
            _summary_tile("材料数", str(len(materials)), "当前批次识别出的材料数量"),
            _summary_tile("项目数", str(len(cases)), "当前已形成的项目分组"),
        ]
    )

    workflow_body = (
        '<div class="summary-grid">'
        + _summary_tile("当前状态", status_label(submission.get("status", "unknown")), "当前批次所处的业务状态")
        + _summary_tile("待继续审查", str(len(pending_cases)), "仅脱敏优先模式下会出现")
        + _summary_tile("产物浏览", "独立页面", "到产物页集中看材料矩阵和脱敏件下载")
        + _summary_tile("人工干预台", "独立页面", "到人工干预台回传脱敏包或继续审查")
        + "</div>"
        + '<div class="inline-actions">'
        + f'<a class="button-secondary" href="/submissions/{submission_id}/materials">{icon("cluster", "icon icon-sm")}进入产物浏览</a>'
        + f'<a class="button-secondary" href="/submissions/{submission_id}/operator">{icon("wrench", "icon icon-sm")}进入人工干预台</a>'
        + f'<a class="button-secondary" href="/submissions/{submission_id}/exports">{icon("download", "icon icon-sm")}进入导出中心</a>'
        + "</div>"
    )

    needs_review_body = (
        '<div class="summary-grid">'
        + "".join(_summary_tile(name, "待复核", note) for name, note in data["needs_review_items"][:6])
        + "</div>"
        if data["needs_review_items"]
        else empty_state("当前没有优先复核材料", "如果需要查看所有材料和脱敏件，请进入产物浏览页面。")
    )

    audit_body = (
        table(["操作类型", "对象", "备注", "时间"], data["correction_rows"])
        if data["correction_rows"]
        else empty_state("暂无更正记录", "人工纠偏和继续审查发生后，这里会保留完整留痕。")
    )
    review_profile_body = list_pairs(review_profile_summary(review_profile), css_class="dossier-list dossier-list-single")
    review_rule_links = _review_rule_links(str(submission.get("id", "")), review_profile)

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
      {metric_card('报告数', str(len(reports)), '当前可查看的项目级报告数量', 'neutral', icon_name='report')}
      {metric_card('待复核队列', str(len(data['needs_review_items'])), '需要优先人工确认的材料数量', 'warning' if data['needs_review_items'] else 'success', icon_name='alert')}
    </section>
    <section class="dashboard-grid">
      {panel('导入摘要', f'<div class="summary-grid">{import_digest}</div>', kicker='批次摘要', extra_class='span-12 panel-soft', icon_name='file', description='主页面只保留这个批次的关键概览。', panel_id='import-digest')}
      {panel('业务流程', workflow_body, kicker='双模式审查', extra_class='span-12', icon_name='spark', description='明确展示本批次当前采用的审查策略、所处阶段和下一步入口。', panel_id='review-workflow')}
      {panel('审查配置', review_profile_body + review_rule_links, kicker='当前配置', extra_class='span-12', icon_name='shield', description='这组配置会影响维度展示与 LLM 补充研判。', panel_id='review-profile')}
      {panel('待复核队列', needs_review_body, kicker='材料提醒', extra_class='span-12', icon_name='alert', description='优先确认这些材料，再决定是否进入人工处理或继续审查。', panel_id='needs-review')}
      {panel('更正审计', audit_body, kicker='留痕记录', extra_class='span-12', icon_name='clock', description='所有人工动作和继续审查都会在这里记录。', panel_id='correction-audit')}
    </section>
    """

    return layout(
        title=submission.get("filename", "批次详情"),
        active_nav="submissions",
        header_tag="批次详情",
        header_title=submission.get("filename", "批次详情"),
        header_subtitle="这个页面只保留概览、业务阶段和进入各子页面的入口。",
        header_meta=_submission_header_meta(submission, cases),
        content=content,
        header_note="如果当前是“先脱敏后继续审查”模式，请先去产物浏览页下载脱敏件，再到人工干预台回传脱敏包或继续审查。",
        page_links=[
            ("#import-digest", "导入摘要", "file"),
            ("#review-workflow", "业务流程", "spark"),
            ("#review-profile", "审查配置", "shield"),
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
    pending_cases = _pending_manual_cases(cases)

    workflow_hint = empty_state("当前是直接审查模式", "产物页主要用于查看原件、清洗件、脱敏件和项目归组。")
    if submission.get("review_strategy") == "manual_desensitized_review":
        workflow_hint = (
            '<div class="summary-grid">'
            + _summary_tile("脱敏优先模式", review_stage_label(submission.get("review_stage", "desensitized_ready")), "先查看脱敏件，再上传脱敏包或继续审查")
            + _summary_tile("待继续项目", str(len(pending_cases)), "待继续项目会在人工干预台出现按钮")
            + "</div>"
            + f'<div class="inline-actions"><a class="button-secondary" href="/submissions/{escape_html(submission.get("id", ""))}/operator">{icon("wrench", "icon icon-sm")}去人工干预台</a></div>'
        )

    queue_body = (
        '<div class="summary-grid">'
        + "".join(_summary_tile(name, "待复核", note) for name, note in data["needs_review_items"][:4])
        + "</div>"
        if data["needs_review_items"]
        else empty_state("暂无待复核项目", "材料解析结果当前没有需要优先人工处理的内容。")
    )

    content = f"""
    <section class="kpi-grid">
      {metric_card('材料数', str(len(materials)), '当前批次材料总量', 'info', icon_name='file')}
      {metric_card('待复核', str(len(data['needs_review_items'])), '需要人工判断的材料数量', 'warning' if data['needs_review_items'] else 'success', icon_name='alert')}
      {metric_card('待继续审查', str(len(pending_cases)), '脱敏优先模式下等待继续的项目数量', 'warning' if pending_cases else 'success', icon_name='spark')}
    </section>
    <section class="dashboard-grid">
      {panel('脱敏工作台', workflow_hint, kicker='业务侧收尾', extra_class='span-12 panel-soft', icon_name='shield', description='先看脱敏件，再决定是否继续进入正式审查。', panel_id='desensitized-workbench')}
      {panel('待复核队列', queue_body, kicker='优先处理', extra_class='span-12', icon_name='alert', description='先看需要人工判断的材料。', panel_id='needs-review')}
      {panel('材料矩阵', table(['文件名', '类型', '软件名', '版本', '问题数', '解析质量', '状态'], data['material_rows']) if data['material_rows'] else empty_state('暂无材料', '当前批次还没有可显示的材料。'), kicker='材料诊断', extra_class='span-12', icon_name='cluster', description='空间不足时宁可向下排，也不再横向挤压。', panel_id='material-matrix')}
      {panel('项目分组', table(['项目', '软件名', '版本', '状态', '阶段', '报告'], data['case_rows']) if data['case_rows'] else empty_state('暂无项目', '当前批次还没有形成项目分组。'), kicker='分组结果', extra_class='span-12', icon_name='lock', description='查看系统如何把材料聚合成项目。', panel_id='case-registry')}
      {panel('产物浏览', table(['文件名', '原件', '清洗件', '脱敏件', '隐私说明'], data['artifact_rows']) if data['artifact_rows'] else empty_state('暂无产物', '当前批次还没有可下载的产物。'), kicker='材料产物', extra_class='span-12', icon_name='download', description='原件、清洗件和脱敏件都集中在这里。', panel_id='artifact-browser')}
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
            ("#desensitized-workbench", "脱敏工作台", "shield"),
            ("#material-matrix", "材料矩阵", "cluster"),
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
    review_profile = normalize_review_profile(submission.get("review_profile", {}))

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
        + _summary_tile("当前阶段", review_stage_label(submission.get("review_stage", "review_completed")), "显示当前是否已完成脱敏、已回传脱敏包或正在正式审查")
        + _summary_tile("顺序", "先脱敏包再继续", "脱敏优先模式建议先下载、再回传、再继续审查")
        + _summary_tile("影响", "动作会留痕", "所有操作都会写入更正审计。")
        + "</div>"
    )

    continue_review_body = _continue_review_forms(submission, cases)
    default_case_id = str(cases[0].get("id", "")) if cases else ""
    review_profile_fields = render_review_profile_form_fields(
        review_profile,
        submit_context="rerun",
        submission_id=str(submission.get("id", "")),
        case_id=default_case_id,
    )
    review_profile_digest = list_pairs(review_profile_summary(review_profile), css_class="dossier-list dossier-list-single")
    review_rule_links = _review_rule_links(str(submission.get("id", "")), review_profile)

    operator_body = f"""
    {operator_intro}
    <div class="operator-group-grid">
      <details class="operator-group" open>
        <summary>
          <span class="operator-group-index">1</span>
          <div>
            <strong>脱敏回传与继续审查</strong>
            <small>支持上传脱敏包，或在确认脱敏件后直接继续项目审查。</small>
          </div>
        </summary>
        <div class="control-grid">
          <form class="operator-form" action="/submissions/{submission_id}/actions/upload-desensitized-package" method="post" enctype="multipart/form-data">
            <strong>上传脱敏包</strong>
            <label class="field"><span>ZIP 文件</span><input type="file" name="file" accept=".zip" required></label>
            <label class="field"><span>备注</span><input type="text" name="note" placeholder="例如：人工确认后重新打包上传"></label>
            <button class="button-secondary button-compact" type="submit">{icon('upload', 'icon icon-sm')}上传并刷新</button>
          </form>
        </div>
        {continue_review_body}
      </details>

      <details class="operator-group">
        <summary>
          <span class="operator-group-index">2</span>
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
          <span class="operator-group-index">3</span>
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

      <details class="operator-group" open>
        <summary>
          <span class="operator-group-index">4</span>
          <div>
            <strong>审查配置与重跑</strong>
            <small>控制审查维度和 LLM 角度，然后按当前配置重新审查。</small>
          </div>
        </summary>
        <div class="control-grid">
          <div class="operator-form operator-form-static">
            <strong>当前配置</strong>
            {review_profile_digest}
            {review_rule_links}
          </div>
          <form class="operator-form" action="/submissions/{submission_id}/actions/rerun-review" method="post">
            <strong>重新审查项目</strong>
            <label class="field"><span>项目</span><select name="case_id">{case_options}</select></label>
            {review_profile_fields}
            <label class="field"><span>备注</span><input type="text" name="note" placeholder="说明为什么重跑"></label>
            <button class="button-secondary button-compact" type="submit">{icon('refresh', 'icon icon-sm')}保存配置并重跑</button>
          </form>
        </div>
      </details>
    </div>
    """

    content = f"""
    <section class="dashboard-grid">
      {panel('人工干预台', operator_body, kicker='纠偏操作', extra_class='span-12', icon_name='wrench', description='所有纠偏动作集中在这里，不再挤在批次总览页。', panel_id='operator-console')}
      {panel('更正审计', table(['操作类型', '对象', '备注', '时间'], data['correction_rows']) if data['correction_rows'] else empty_state('暂无操作记录', '当前还没有人工处理记录。'), kicker='留痕记录', extra_class='span-12', icon_name='clock', description='每一次人工动作都会留痕，方便回溯。', panel_id='correction-audit')}
    </section>
    """

    return layout(
        title=f"{submission.get('filename', '批次详情')} - 人工干预台",
        active_nav="submissions",
        header_tag="人工干预台",
        header_title="人工干预台",
        header_subtitle="纠偏表单单独承载，主页面不再被长表单压缩。",
        header_meta=_submission_header_meta(submission, cases),
        content=content,
        header_note="先在产物浏览页确认问题，再回到这里执行必要的人工修正、上传脱敏包或继续审查。",
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
    del materials, parse_results
    submission_id = escape_html(submission.get("id", ""))

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

    export_body = (
        '<div class="summary-grid">'
        + _summary_tile("报告数", str(len(reports)), "当前批次可下载的项目级报告数量")
        + _summary_tile("批次包", "可直接下载", "适合整体交付或归档")
        + _summary_tile("应用日志", "可直接下载", "需要追踪处理过程时再使用")
        + _summary_tile("当前阶段", review_stage_label(submission.get("review_stage", "review_completed")), "导出前可快速确认当前是否已经完成正式审查")
        + "</div>"
        + '<div class="inline-actions">'
        + f'<a class="button-secondary" href="/downloads/submissions/{submission_id}/bundle">{icon("download", "icon icon-sm")}下载批次包</a>'
        + f'<a class="button-secondary" href="/downloads/logs/app">{icon("terminal", "icon icon-sm")}下载日志</a>'
        + "</div>"
        + (
            f'<div class="report-card-grid">{report_cards}</div>'
            if report_cards
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
        header_note="如果要查看材料原件、清洗件和脱敏件，请进入产物浏览页。",
        page_links=[
            (f"/submissions/{submission.get('id', '')}", "批次总览", "file"),
            ("#export-center", "导出中心", "download"),
        ],
    )


def _render_online_filing_operator_forms(submission_id: str, cases: list[dict]) -> str:
    forms: list[str] = []
    for case in cases:
        filing = normalize_online_filing(case.get("online_filing", {}) or {})
        summary = list_pairs(online_filing_summary(filing), css_class="dossier-list dossier-list-single")
        forms.append(
            '<form class="operator-form" action="/submissions/'
            + escape_html(submission_id)
            + '/actions/update-online-filing" method="post">'
            + f"<strong>{escape_html(case.get('case_name', '') or case.get('id', 'case'))}</strong>"
            + f'<input type="hidden" name="case_id" value="{escape_html(case.get("id", ""))}">'
            + summary
            + f'<label class="field"><span>软件名称</span><input type="text" name="online_software_name" value="{escape_html(filing.get("software_name", ""))}"></label>'
            + f'<label class="field"><span>版本号</span><input type="text" name="online_version" value="{escape_html(filing.get("version", ""))}"></label>'
            + f'<label class="field"><span>软件分类</span><input type="text" name="online_software_category" value="{escape_html(filing.get("software_category", ""))}" placeholder="例如：应用软件"></label>'
            + f'<label class="field"><span>开发方式</span><input type="text" name="online_development_mode" value="{escape_html(filing.get("development_mode", ""))}" placeholder="例如：原创 / 合作开发"></label>'
            + f'<label class="field"><span>主体类型</span><input type="text" name="online_subject_type" value="{escape_html(filing.get("subject_type", ""))}" placeholder="例如：企业法人 / 事业单位"></label>'
            + f'<label class="field"><span>申请日期</span><input type="text" name="online_apply_date" value="{escape_html(filing.get("apply_date", ""))}" placeholder="YYYY-MM-DD"></label>'
            + f'<label class="field"><span>开发完成日期</span><input type="text" name="online_completion_date" value="{escape_html(filing.get("completion_date", ""))}" placeholder="YYYY-MM-DD"></label>'
            + f'<label class="field"><span>申请人顺序</span><textarea name="online_applicants" rows="4" placeholder="每行一位申请人">{escape_html(chr(10).join(filing.get("applicants", [])))}</textarea></label>'
            + f'<label class="field"><span>地址</span><textarea name="online_address" rows="3">{escape_html(filing.get("address", ""))}</textarea></label>'
            + f'<label class="field"><span>电子证书地址</span><textarea name="online_certificate_address" rows="3">{escape_html(filing.get("certificate_address", ""))}</textarea></label>'
            + '<label class="field"><span>备注</span><input type="text" name="note" placeholder="例如：按本次申报口径修正"></label>'
            + '<div class="inline-actions">'
            + f'<a class="button-secondary button-compact" href="/cases/{escape_html(case.get("id", ""))}">查看项目</a>'
            + f'<button class="button-secondary button-compact" type="submit">{icon("refresh", "icon icon-sm")}保存并重跑</button>'
            + "</div></form>"
        )
    if not forms:
        return empty_state("暂无项目", "请先形成项目后再录入在线填报信息。")
    return '<div class="control-grid">' + "".join(forms) + "</div>"


def render_submission_operator_page(
    submission: dict,
    materials: list[dict],
    cases: list[dict],
    reports: list[dict],
    parse_results: list[dict],
) -> str:
    del reports
    data = _submission_view_data(submission, materials, cases, [], parse_results)
    submission_id = escape_html(submission.get("id", ""))
    review_profile = normalize_review_profile(submission.get("review_profile", {}))

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
        + _summary_tile("当前阶段", review_stage_label(submission.get("review_stage", "review_completed")), "显示当前是否已完成脱敏、已回传脱敏包或正在正式审查")
        + _summary_tile("建议顺序", "先整理再重跑", "优先纠偏材料和在线填报，再按最新规则重新审查")
        + _summary_tile("留痕", "自动记录", "所有人工动作都会写入更正审计")
        + "</div>"
    )

    continue_review_body = _continue_review_forms(submission, cases)
    default_case_id = str(cases[0].get("id", "")) if cases else ""
    review_profile_fields = render_review_profile_form_fields(
        review_profile,
        submit_context="rerun",
        submission_id=str(submission.get("id", "")),
        case_id=default_case_id,
    )
    review_profile_digest = list_pairs(review_profile_summary(review_profile), css_class="dossier-list dossier-list-single")
    review_rule_links = _review_rule_links(str(submission.get("id", "")), review_profile)

    operator_body = f"""
    {operator_intro}
    <div class="operator-group-grid">
      <details class="operator-group" open>
        <summary>
          <span class="operator-group-index">1</span>
          <div>
            <strong>脱敏回传与继续审查</strong>
            <small>上传脱敏包，或在确认脱敏件后继续正式审查。</small>
          </div>
        </summary>
        <div class="control-grid">
          <form class="operator-form" action="/submissions/{submission_id}/actions/upload-desensitized-package" method="post" enctype="multipart/form-data">
            <strong>上传脱敏包</strong>
            <label class="field"><span>ZIP 文件</span><input type="file" name="file" accept=".zip" required></label>
            <label class="field"><span>备注</span><input type="text" name="note" placeholder="例如：人工确认后重新打包上传"></label>
            <button class="button-secondary button-compact" type="submit">{icon('upload', 'icon icon-sm')}上传并刷新</button>
          </form>
        </div>
        {continue_review_body}
      </details>

      <details class="operator-group">
        <summary>
          <span class="operator-group-index">2</span>
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
          <span class="operator-group-index">3</span>
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

      <details class="operator-group" open>
        <summary>
          <span class="operator-group-index">4</span>
          <div>
            <strong>在线填报信息</strong>
            <small>按项目录入在线系统字段，保存后会立即重跑审查。</small>
          </div>
        </summary>
        {_render_online_filing_operator_forms(submission.get("id", ""), cases)}
      </details>

      <details class="operator-group" open>
        <summary>
          <span class="operator-group-index">5</span>
          <div>
            <strong>审查配置与重跑</strong>
            <small>控制审查维度和 LLM 角度，然后按当前配置重新审查。</small>
          </div>
        </summary>
        <div class="control-grid">
          <div class="operator-form operator-form-static">
            <strong>当前配置</strong>
            {review_profile_digest}
            {review_rule_links}
          </div>
          <form class="operator-form" action="/submissions/{submission_id}/actions/rerun-review" method="post">
            <strong>重新审查项目</strong>
            <label class="field"><span>项目</span><select name="case_id">{case_options}</select></label>
            {review_profile_fields}
            <label class="field"><span>备注</span><input type="text" name="note" placeholder="说明为什么重跑"></label>
            <button class="button-secondary button-compact" type="submit">{icon('refresh', 'icon icon-sm')}保存配置并重跑</button>
          </form>
        </div>
      </details>
    </div>
    """

    content = f"""
    <section class="dashboard-grid">
      {panel('人工干预台', operator_body, kicker='纠偏操作', extra_class='span-12', icon_name='wrench', description='把人工修正、在线填报和重跑入口集中到这里。', panel_id='operator-console')}
      {panel('更正审计', table(['操作类型', '对象', '备注', '时间'], data['correction_rows']) if data['correction_rows'] else empty_state('暂无操作记录', '当前还没有人工处理记录。'), kicker='留痕记录', extra_class='span-12', icon_name='clock', description='每一次人工动作都会留痕，方便回溯。', panel_id='correction-audit')}
    </section>
    """

    return layout(
        title=f"{submission.get('filename', '批次详情')} - 人工干预台",
        active_nav="submissions",
        header_tag="人工干预台",
        header_title="人工干预台",
        header_subtitle="把纠偏表单单独承载，避免在总览页堆叠长表单。",
        header_meta=_submission_header_meta(submission, cases),
        content=content,
        header_note="先在产品浏览页确认问题，再回到这里执行必要的人工修正、录入在线填报或继续审查。",
        page_links=[
            (f"/submissions/{submission.get('id', '')}", "批次总览", "file"),
            ("#operator-console", "人工干预台", "wrench"),
            ("#correction-audit", "更正审计", "clock"),
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
    pending_cases = _pending_manual_cases(cases)
    review_profile = normalize_review_profile(submission.get("review_profile", {}))

    workspace_notice = ""
    if notice:
        workspace_notice = notice_banner(
            notice.get("title", "已更新"),
            notice.get("message", "当前批次页面已刷新。"),
            tone=notice.get("tone", "info"),
            icon_name=notice.get("icon_name", "check"),
            meta=notice.get("meta"),
        )

    import_digest = "".join(
        [
            _summary_tile("导入文件", str(submission.get("filename", "") or "-"), "当前导入的 ZIP 包"),
            _summary_tile("导入模式", mode_label(str(submission.get("mode", ""))), "当前批次的整理方式"),
            _summary_tile("审查策略", review_strategy_label(str(submission.get("review_strategy", "auto_review"))), "决定直接审查还是先脱敏后继续"),
            _summary_tile("当前阶段", review_stage_label(str(submission.get("review_stage", "review_completed"))), "当前批次所处的业务阶段"),
            _summary_tile("材料数", str(len(materials)), "当前批次识别出的材料数量"),
            _summary_tile("项目数", str(len(cases)), "当前形成的项目分组"),
        ]
    )

    workflow_body = (
        '<div class="summary-grid">'
        + _summary_tile("当前状态", status_label(submission.get("status", "unknown")), "先看批次是否已完成或仍待处理")
        + _summary_tile("待继续审查", str(len(pending_cases)), "仅先脱敏后继续模式下会出现")
        + _summary_tile("下一步", "查看产物或导出", "主页面不再堆叠长表和长表单")
        + "</div>"
        + '<div class="inline-actions">'
        + f'<a class="button-secondary" href="/submissions/{submission_id}/materials">{icon("cluster", "icon icon-sm")}产物浏览</a>'
        + f'<a class="button-secondary" href="/submissions/{submission_id}/operator">{icon("wrench", "icon icon-sm")}人工干预台</a>'
        + f'<a class="button-secondary" href="/submissions/{submission_id}/exports">{icon("download", "icon icon-sm")}导出中心</a>'
        + "</div>"
    )

    needs_review_body = (
        '<div class="summary-grid">'
        + "".join(_summary_tile(name, "待复核", note) for name, note in data["needs_review_items"][:4])
        + "</div>"
        if data["needs_review_items"]
        else empty_state("当前没有优先复核材料", "如需查看全部材料和脱敏件，请进入产物浏览页。")
    )

    audit_body = (
        table(["操作类型", "对象", "备注", "时间"], data["correction_rows"])
        if data["correction_rows"]
        else empty_state("暂无更正记录", "人工纠偏和继续审查发生后，这里会保留完整留痕。")
    )
    review_profile_body = list_pairs(review_profile_summary(review_profile), css_class="dossier-list dossier-list-single")
    review_rule_links = _review_rule_links(str(submission.get("id", "")), review_profile)
    advanced_groups = '<div class="operator-group-grid">'
    advanced_groups += _fold_group(1, "审查配置", "查看当前维度和规则入口。", review_profile_body + review_rule_links, open_by_default=False)
    advanced_groups += _fold_group(2, "更正审计", "人工修正和重跑都会在这里留痕。", audit_body, open_by_default=False)
    advanced_groups += "</div>"

    content = f"""
    <section class="kpi-grid">
      {metric_card('材料数', str(len(materials)), '当前批次识别出的材料数量', 'info', icon_name='file')}
      {metric_card('项目数', str(len(cases)), '当前批次形成的项目数量', 'success', icon_name='lock')}
      {metric_card('报告数', str(len(reports)), '当前可查看的项目级报告数量', 'neutral', icon_name='report')}
      {metric_card('待复核队列', str(len(data['needs_review_items'])), '需要优先人工确认的材料数量', 'warning' if data['needs_review_items'] else 'success', icon_name='alert')}
    </section>
    <section class="dashboard-grid">
      {panel('导入摘要', f'<div class="summary-grid">{import_digest}</div>', kicker='批次摘要', extra_class='span-12 panel-soft', icon_name='file', description='主页面只保留这个批次的关键概览。', panel_id='import-digest')}
      {panel('业务流程', workflow_body, kicker='下一步', extra_class='span-12', icon_name='spark', description='首屏只保留当前阶段和去往子页面的动作入口。', panel_id='review-workflow')}
      {panel('待复核队列', needs_review_body, kicker='优先处理', extra_class='span-12', icon_name='alert', description='优先确认这些材料，再决定是否进入人工处理或继续审查。', panel_id='needs-review')}
      {panel('更多信息', advanced_groups, kicker='按需展开', extra_class='span-12', icon_name='search', description='审查配置和操作留痕都放到这里。', panel_id='submission-more')}
    </section>
    """

    return layout(
        title=submission.get("filename", "批次详情"),
        active_nav="submissions",
        header_tag="批次详情",
        header_title=submission.get("filename", "批次详情"),
        header_subtitle="首页只保留概览、阶段和入口，细项信息按需展开。",
        header_meta=_submission_header_meta(submission, cases),
        content=content,
        header_note="如果当前是“先脱敏后继续审查”模式，请先去产物浏览页下载脱敏件，再到人工干预台回传脱敏包或继续审查。",
        page_links=[
            ("#import-digest", "导入摘要", "file"),
            ("#review-workflow", "业务流程", "spark"),
            ("#needs-review", "待复核队列", "alert"),
            ("#submission-more", "更多信息", "search"),
            (f"/submissions/{submission.get('id', '')}/materials", "产物浏览", "cluster"),
            (f"/submissions/{submission.get('id', '')}/operator", "人工干预台", "wrench"),
            (f"/submissions/{submission.get('id', '')}/exports", "导出中心", "download"),
        ],
        workspace_notice=workspace_notice,
    )


__all__ = [
    "render_submission_detail",
    "render_submission_exports_page",
    "render_submission_materials_page",
    "render_submission_operator_page",
    "render_submissions_index",
]
