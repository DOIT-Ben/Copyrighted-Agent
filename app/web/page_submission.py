from __future__ import annotations

from collections import Counter
from urllib.parse import urlencode

from app.core.services.online_filing import normalize_online_filing, online_filing_summary
from app.core.services.review_profile import dimension_title, normalize_review_profile, review_profile_summary
from app.core.services.review_rulebook import dimension_rulebook_from_profile
from app.core.services.sqlite_repository import list_submission_registry
from app.core.services.submission_insights import parse_diagnostic_snapshot
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


CORRECTION_LABELS["update_case_online_filing"] = "补录在线填报信息"
CORRECTION_LABELS["update_internal_state"] = "更新内部处理状态"


QUALITY_BUCKET_LABELS = {
    "usable_text": "文本可用",
    "partial_fragments": "片段可用",
    "binary_noise": "疑似二进制噪声",
    "unknown": "待判断",
}

INTERNAL_STATUS_LABELS = {
    "unassigned": "待认领",
    "in_review": "审查中",
    "waiting_materials": "待补材料",
    "fixing": "修正中",
    "ready_to_deliver": "可交付",
    "delivered": "已交付",
    "blocked": "已阻塞",
}


def _summary_tile(label: str, value: str, note: str) -> str:
    del note
    return (
        '<div class="summary-tile">'
        f"<span>{escape_html(label)}</span>"
        f"<strong>{escape_html(value)}</strong>"
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


GLOBAL_REVIEW_STATUS_LABELS = {
    "ready": "整包可继续",
    "needs_review": "需要复核",
    "blocked": "存在阻断",
}

GLOBAL_REVIEW_STATUS_TONES = {
    "ready": "success",
    "needs_review": "warning",
    "blocked": "danger",
}


def _global_review_status_label(value: str) -> str:
    return GLOBAL_REVIEW_STATUS_LABELS.get(str(value or "").strip(), "待生成")


def _global_review_status_tone(value: str) -> str:
    return GLOBAL_REVIEW_STATUS_TONES.get(str(value or "").strip(), "neutral")


def _global_review_next_action(submission_id: str, global_review: dict) -> dict[str, str]:
    status = str(global_review.get("status", "") or "").strip()
    inventory = dict(global_review.get("material_inventory", {}) or {})
    report_id = str(global_review.get("report_id", "") or "").strip()
    if status == "blocked":
        return {
            "title": "下一步建议：先处理阻断项",
            "note": "优先确认未知材料、低质解析、核心材料缺失或批量未分组问题，避免带着结构性风险进入交付。",
            "href": f"/submissions/{submission_id}/materials#needs-review",
            "label": "查看待复核材料",
        }
    if status == "needs_review" or int(inventory.get("manual_review_count", 0) or 0) > 0:
        return {
            "title": "下一步建议：完成人工复核",
            "note": "当前整包基本可审，但仍建议先确认待复核材料和分组，再查看项目报告。",
            "href": f"/submissions/{submission_id}/operator",
            "label": "进入人工干预台",
        }
    if report_id:
        return {
            "title": "下一步建议：查看整包报告",
            "note": "整包结构稳定，可以打开全局报告确认结论，随后进入导出中心生成交付包。",
            "href": f"/reports/{report_id}",
            "label": "查看整包报告",
        }
    return {
        "title": "下一步建议：继续查看结果",
        "note": "整包结构稳定，可以继续查看项目报告或进入导出中心。",
        "href": f"/submissions/{submission_id}/exports",
        "label": "进入导出中心",
    }


def _render_global_review_board(submission: dict) -> str:
    review_profile = dict(submission.get("review_profile", {}) or {})
    global_review = dict(review_profile.get("submission_global_review", {}) or {})
    if not global_review:
        return empty_state("整包全局审查待生成", "完成导入后，系统会把材料完整性、分组和跨项目风险统一汇总到这里。")

    status = str(global_review.get("status", "") or "").strip()
    severity_counts = dict(global_review.get("severity_counts", {}) or {})
    inventory = dict(global_review.get("material_inventory", {}) or {})
    case_inventory = dict(global_review.get("case_inventory", {}) or {})
    issues = list(global_review.get("issues", []) or [])
    top_issues = sorted(
        issues,
        key=lambda item: {"severe": 0, "moderate": 1, "minor": 2}.get(str(item.get("severity", "minor")), 3),
    )[:5]
    report_id = str(global_review.get("report_id", "") or "").strip()
    report_link = (
        f'<a class="button-secondary button-compact" href="/reports/{escape_html(report_id)}">{icon("report", "icon icon-sm")}查看整包报告</a>'
        if report_id
        else ""
    )
    next_action = _global_review_next_action(str(submission.get("id", "") or ""), global_review)
    next_action_body = (
        '<div class="operator-note global-review-next-step">'
        f"<strong>{escape_html(next_action['title'])}</strong>"
        f"<span>{escape_html(next_action['note'])}</span>"
        '<div class="inline-actions">'
        f'<a class="button-primary button-compact" href="{escape_html(next_action["href"])}">{icon("spark", "icon icon-sm")}{escape_html(next_action["label"])}</a>'
        "</div>"
        "</div>"
    )
    issue_body = (
        '<div class="rule-checkpoint-list"><ul>'
        + "".join(
            "<li>"
            f"<strong>{escape_html(str(item.get('category', '全局审查') or '全局审查'))}</strong>"
            f"：{escape_html(str(item.get('desc', '') or ''))}"
            "</li>"
            for item in top_issues
        )
        + "</ul></div>"
        if top_issues
        else empty_state("未发现整包级阻断", "当前整包结构稳定，可继续查看项目报告或进入导出中心。")
    )
    return (
        '<div class="global-review-board">'
        + notice_banner(
            f"整包结论：{_global_review_status_label(status)}",
            str(global_review.get("summary", "") or "系统已完成整包级材料审查。"),
            tone=_global_review_status_tone(status),
            icon_name="shield",
            meta=[
                f"材料 {inventory.get('total', 0)}",
                f"项目 {case_inventory.get('total', 0)}",
                f"严重 {severity_counts.get('severe', 0)}",
                f"复核 {severity_counts.get('moderate', 0)}",
            ],
        )
        + '<div class="summary-grid">'
        + _summary_tile("全局得分", str(global_review.get("score", "-")), "整包级确定性规则评分")
        + _summary_tile("未知材料", str(inventory.get("unknown_count", 0)), "未稳定识别类型的材料数量")
        + _summary_tile("低质解析", str(inventory.get("low_quality_count", 0)), "解析质量不足的材料数量")
        + _summary_tile("人工复核", str(inventory.get("manual_review_count", 0)), "建议人工确认的材料数量")
        + "</div>"
        + next_action_body
        + issue_body
        + (f'<div class="inline-actions">{report_link}</div>' if report_link else "")
        + "</div>"
    )


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


def _review_profile_meta_badges(review_profile: dict) -> str:
    meta = dict(review_profile.get("rulebook_meta", {}) or {})
    if not meta:
        return ""
    parts = [pill(f"r{int(meta.get('revision', 1) or 1)}", "info")]
    last_dimension_key = str(meta.get("last_dimension_key", "") or "").strip()
    if last_dimension_key:
        parts.append(pill(dimension_title(last_dimension_key), "neutral"))
    updated_by = str(meta.get("updated_by", "") or "").strip()
    if updated_by:
        parts.append(pill(updated_by, "neutral"))
    return "".join(parts)


def _submission_jobs(submission_id: str) -> list[dict]:
    rows = []
    for item in store.jobs.values():
        if str(getattr(item, "scope_id", "") or "").strip() != str(submission_id or "").strip():
            continue
        payload = item.to_dict()
        payload["can_retry"] = bool(
            payload.get("retryable")
            and payload.get("job_type") == "ingest_submission"
            and str(payload.get("status", "") or "").strip().lower() in {"failed", "interrupted"}
            and str((payload.get("metadata") or {}).get("source_path", "")).strip()
        )
        rows.append(payload)
    return sorted(rows, key=lambda item: (item.get("started_at", "") or "", item.get("id", "") or ""), reverse=True)


def _job_error_label(job: dict) -> str:
    return str(job.get("error_code", "") or job.get("error_message", "") or job.get("detail", "") or "-").strip() or "-"


def _job_retry_action(submission_id: str, job: dict) -> str:
    if not bool(job.get("can_retry")):
        return "-"
    job_id = escape_html(str(job.get("id", "") or ""))
    return_to = escape_html(f"/submissions/{submission_id}")
    return (
        f'<form class="inline-form" action="/submissions/{escape_html(submission_id)}/actions/retry-job" method="post">'
        f'<input type="hidden" name="job_id" value="{job_id}">'
        f'<input type="hidden" name="return_to" value="{return_to}">'
        f'<button class="button-secondary button-compact" type="submit">{icon("refresh", "icon icon-sm")}重试导入</button>'
        "</form>"
    )


def _job_history_board(submission_id: str) -> str:
    jobs = _submission_jobs(submission_id)
    if not jobs:
        return empty_state("暂无处理任务记录", "当前批次还没有可展示的异步任务链路。")

    rows: list[list[str]] = []
    for item in jobs[:6]:
        metadata = dict(item.get("metadata", {}) or {})
        rows.append(
            [
                escape_html(str(item.get("started_at", "") or "-")),
                pill(status_label(item.get("status", "unknown")), status_tone(item.get("status", "unknown"))),
                escape_html(str(metadata.get("retry_count", 0) or 0)),
                escape_html(_job_error_label(item)),
                _job_retry_action(submission_id, item),
            ]
        )
    return table(["开始时间", "状态", "重试次数", "失败原因", "操作"], rows)


def _parse_diagnostics_board(materials: list[dict], parse_results: list[dict]) -> str:
    parse_lookup = _build_parse_lookup(parse_results)
    rows: list[list[str]] = []
    for material in materials[:8]:
        parse_result = parse_lookup.get(str(material.get("id", "") or ""), {})
        diagnostic = parse_diagnostic_snapshot(material, parse_result)
        rows.append(
            [
                escape_html(str(material.get("original_filename", "") or material.get("id", "") or "-")),
                escape_html(str(diagnostic.get("quality_level", "") or "-")),
                escape_html(str(diagnostic.get("parse_reason_label", "") or "-")),
                escape_html(str(diagnostic.get("manual_review_reason_label", "") or diagnostic.get("unknown_reason_label", "") or "-")),
                pill("待复核" if diagnostic.get("needs_manual_review") else "可继续", "warning" if diagnostic.get("needs_manual_review") else "success"),
            ]
        )
    return table(["材料", "质量", "解析原因", "人工原因", "建议"], rows) if rows else empty_state("暂无解析诊断", "当前没有可展示的解析诊断。")


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
            escape_html(
                " / ".join(
                    part
                    for part in [
                        str(item.get("reason_label", "") or item.get("reason_code", "") or "").strip(),
                        str(item.get("outcome_label", "") or item.get("outcome_code", "") or "").strip(),
                        str(item.get("note", "") or "").strip(),
                    ]
                    if part
                )
                or "-"
            ),
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


def render_submissions_index(filters: dict | None = None) -> str:
    filters = dict(filters or {})
    all_submissions = list_submission_registry()

    def _submission_todo_flags(submission) -> set[str]:
        flags: set[str] = set()
        if any(
            case_id in store.cases and getattr(store.cases[case_id], "status", "") == "awaiting_manual_review"
            for case_id in submission.case_ids
        ):
            flags.add("pending_review")
        if any(
            material_id in store.materials and len(getattr(store.materials[material_id], "issues", []) or []) > 0
            for material_id in submission.material_ids
        ):
            flags.add("has_issues")
        if not submission.report_ids:
            flags.add("missing_report")
        if flags:
            flags.add("has_todo")
        else:
            flags.add("no_todo")
        return flags

    internal_status_filter = str(filters.get("internal_status", "") or "").strip()
    system_status_filter = str(filters.get("status", "") or "").strip()
    todo_filter = str(filters.get("todo", "") or "").strip()
    filtered_by_registry = list_submission_registry(filters)
    submissions = []
    for submission in filtered_by_registry:
        if todo_filter and todo_filter not in _submission_todo_flags(submission):
            continue
        submissions.append(submission)

    total_all = len(all_submissions)
    total = len(submissions)
    materials_total = sum(len(item.material_ids) for item in submissions)
    cases_total = sum(len(item.case_ids) for item in submissions)
    reports_total = sum(len(item.report_ids) for item in submissions)
    latest_status = submissions[0].status if submissions else "idle"
    status_counts = Counter(str(item.status or "unknown") for item in submissions)
    internal_status_counts = Counter(str(getattr(item, "internal_status", "unassigned") or "unassigned") for item in submissions)
    unassigned_count = internal_status_counts.get("unassigned", 0)
    blocked_count = internal_status_counts.get("blocked", 0)
    waiting_materials_count = internal_status_counts.get("waiting_materials", 0)
    ready_to_deliver_count = internal_status_counts.get("ready_to_deliver", 0) + internal_status_counts.get("delivered", 0)

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

    def _internal_status_tone(value: str) -> str:
        normalized = str(value or "unassigned").strip()
        if normalized in {"ready_to_deliver", "delivered"}:
            return "success"
        if normalized in {"waiting_materials", "fixing", "blocked"}:
            return "warning" if normalized != "blocked" else "danger"
        if normalized == "in_review":
            return "info"
        return "neutral"

    def _batch_internal_cell(submission) -> str:
        internal_status = str(getattr(submission, "internal_status", "unassigned") or "unassigned")
        owner = str(getattr(submission, "internal_owner", "") or "").strip() or "未认领"
        next_step = str(getattr(submission, "internal_next_step", "") or "").strip()
        updated_at = str(getattr(submission, "internal_updated_at", "") or "").strip()
        detail = next_step or (f"更新于 {updated_at}" if updated_at else "等待内部认领")
        return (
            '<div class="batch-internal-cell">'
            f'{pill(_internal_status_label(internal_status), _internal_status_tone(internal_status))}'
            f'<strong>{escape_html(owner)}</strong>'
            f'<small>{escape_html(detail)}</small>'
            "</div>"
        )

    def _batch_todo_cell(submission) -> str:
        pending_case_count = sum(
            1
            for case_id in submission.case_ids
            if case_id in store.cases and getattr(store.cases[case_id], "status", "") == "awaiting_manual_review"
        )
        issue_count = sum(
            len(getattr(store.materials[material_id], "issues", []) or [])
            for material_id in submission.material_ids
            if material_id in store.materials
        )
        items = []
        if pending_case_count:
            items.append((f"{pending_case_count} 待继续", "warning"))
        if issue_count:
            items.append((f"{issue_count} 问题", "warning"))
        if not submission.report_ids:
            items.append(("缺报告", "danger"))
        if not items:
            items.append(("可跟进", "success"))
        return '<div class="batch-todo-cell">' + "".join(pill(label, tone) for label, tone in items[:3]) + "</div>"

    def _select_options(options: list[tuple[str, str]], selected: str) -> str:
        normalized = str(selected or "").strip()
        return "".join(
            f'<option value="{escape_html(value)}"{ " selected" if value == normalized else ""}>{escape_html(label)}</option>'
            for value, label in options
        )

    return_query = urlencode(
        {
            key: value
            for key, value in {
                "internal_status": internal_status_filter,
                "owner": str(filters.get("owner", "") or "").strip(),
                "status": system_status_filter,
                "todo": todo_filter,
            }.items()
            if value
        }
    )
    return_to = f"/submissions?{return_query}#batch-registry" if return_query else "/submissions#batch-registry"

    def _batch_action_cell(submission) -> str:
        submission_id = escape_html(str(submission.id))
        owner = escape_html(str(getattr(submission, "internal_owner", "") or ""))
        next_step = escape_html(str(getattr(submission, "internal_next_step", "") or ""))
        note = escape_html(str(getattr(submission, "internal_note", "") or ""))
        current_status = str(getattr(submission, "internal_status", "unassigned") or "unassigned")
        quick_options = _select_options(
            [
                ("unassigned", "待认领"),
                ("in_review", "审查中"),
                ("waiting_materials", "待补材料"),
                ("ready_to_deliver", "可交付"),
                ("blocked", "已阻塞"),
            ],
            current_status,
        )
        return (
            '<div class="batch-actions-cell">'
            f'<a class="button-secondary button-compact" href="/submissions/{submission_id}">{icon("search", "icon icon-sm")}详情</a>'
            f'<form class="quick-internal-state-form" action="/submissions/{submission_id}/actions/update-internal-state" method="post">'
            f'<input type="hidden" name="internal_owner" value="{owner}">'
            f'<input type="hidden" name="internal_next_step" value="{next_step}">'
            f'<input type="hidden" name="internal_note" value="{note}">'
            '<input type="hidden" name="updated_by" value="batch_registry">'
            f'<input type="hidden" name="return_to" value="{escape_html(return_to)}">'
            f'<select name="internal_status" aria-label="快捷更新内部状态">{quick_options}</select>'
            '<button class="button-secondary button-compact" type="submit">更新</button>'
            "</form>"
            "</div>"
        )

    rows = [
        [
            _batch_name_cell(submission),
            _batch_internal_cell(submission),
            _batch_todo_cell(submission),
            pill(status_label(submission.status), status_tone(submission.status)),
            escape_html(review_stage_label(getattr(submission, "review_stage", "review_completed"))),
            _batch_count_cell(submission),
            escape_html(submission.created_at),
            _batch_action_cell(submission),
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

    internal_board_body = "".join(
        [
            _summary_tile("待认领", str(unassigned_count), "还没有负责人，需要内部团队分配"),
            _summary_tile("已阻塞", str(blocked_count), "需要先解除阻塞再继续交付"),
            _summary_tile("待补材料", str(waiting_materials_count), "等待客户或内部补齐材料"),
            _summary_tile("可交付", str(ready_to_deliver_count), "已准备交付或已经交付的批次"),
        ]
    )
    filter_form = f"""
    <form class="submission-filter-bar" action="/submissions" method="get">
      <label class="field">
        <span>内部状态</span>
        <select name="internal_status">
          {_select_options([("", "全部内部状态"), *list(INTERNAL_STATUS_LABELS.items())], internal_status_filter)}
        </select>
      </label>
      <label class="field">
        <span>负责人</span>
        <input type="search" name="owner" value="{escape_html(str(filters.get('owner', '') or ''))}" placeholder="输入负责人关键字">
      </label>
      <label class="field">
        <span>系统状态</span>
        <select name="status">
          {_select_options([("", "全部系统状态"), ("completed", "已完成"), ("processing", "处理中"), ("awaiting_manual_review", "待继续审查"), ("failed", "失败")], system_status_filter)}
        </select>
      </label>
      <label class="field">
        <span>待办</span>
        <select name="todo">
          {_select_options([("", "全部待办"), ("has_todo", "有待办"), ("pending_review", "待继续审查"), ("has_issues", "有审查问题"), ("missing_report", "缺报告"), ("no_todo", "无待办")], todo_filter)}
        </select>
      </label>
      <div class="inline-actions submission-filter-actions">
        <button class="button-primary button-compact" type="submit">{icon("search", "icon icon-sm")}筛选</button>
        <a class="button-secondary button-compact" href="/submissions">清空</a>
        <span class="form-helper-text">当前显示 {total} / {total_all} 个批次</span>
      </div>
    </form>
    """

    has_active_filters = any([internal_status_filter, str(filters.get("owner", "") or "").strip().lower(), system_status_filter, todo_filter])
    empty_title = "没有匹配批次" if has_active_filters else "暂无批次"
    empty_note = "调整筛选条件后再试，或清空筛选回到完整台账。" if has_active_filters else "导入 ZIP 后，这里会出现批次记录。"
    registry_body = filter_form + (table(['批次', '内部状态', '待办', '系统状态', '阶段', '数量', '创建时间', '操作'], rows) if rows else empty_state(empty_title, empty_note))

    content = f"""
    <section class="kpi-grid">
      {metric_card('批次数', str(total), '当前筛选条件下的批次数量', 'info', icon_name='layers')}
      {metric_card('材料数', str(materials_total), '当前筛选结果识别出的材料总量', 'success', icon_name='file')}
      {metric_card('项目数', str(cases_total), '当前筛选结果形成的项目总量', 'warning', icon_name='lock')}
      {metric_card('报告数', str(reports_total), '当前筛选结果已生成的项目级报告数量', 'neutral', icon_name='report')}
    </section>
    <section class="dashboard-grid">
      {panel('内部跟进看板', internal_board_body, kicker='团队协作', extra_class='span-12 panel-internal-board panel-soft', icon_name='wrench', description='用于内部早会和日常巡检，先看待认领、阻塞、待补材料和可交付批次。', panel_id='internal-board')}
      {panel('批次台账', registry_body, kicker='批次总览', extra_class='span-12 panel-batch-registry', icon_name='layers', description='按内部状态、负责人、系统状态和待办快速定位目标批次。', panel_id='batch-registry')}
      {panel('状态分布', distribution_body, kicker='运行状态', extra_class='span-12 panel-soft', icon_name='bar', description='快速判断当前筛选结果是否稳定。', panel_id='status-distribution')}
    </section>
    """

    notice_code = str(filters.get("notice", "") or "").strip()
    workspace_notice = ""
    if notice_code:
        notice_map = {
            "internal_state_updated": ("内部处理状态已更新", "负责人、内部状态和下一步备注已经保存，台账已刷新。", "success", "wrench"),
        }
        notice_info = notice_map.get(notice_code)
        if notice_info:
            workspace_notice = notice_banner(notice_info[0], notice_info[1], tone=notice_info[2], icon_name=notice_info[3])

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
            ("#internal-board", "内部看板", "wrench"),
            ("#batch-registry", "批次台账", "layers"),
            ("#status-distribution", "状态分布", "bar"),
        ],
        workspace_notice=workspace_notice,
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
    global_review = dict((submission.get("review_profile", {}) or {}).get("submission_global_review", {}) or {})
    global_status = str(global_review.get("status", "") or "").strip()

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
    review_profile_body = _review_profile_meta_badges(review_profile) + list_pairs(review_profile_summary(review_profile), css_class="dossier-list dossier-list-single")
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


def _delivery_history_timeline(submission_id: str) -> str:
    delivery_events = []
    for item in _submission_corrections(submission_id):
        if item.get("correction_type") != "update_internal_state":
            continue
        corrected_value = dict(item.get("corrected_value", {}) or {})
        status = str(corrected_value.get("internal_status", "") or "").strip()
        if status not in {"ready_to_deliver", "delivered"}:
            continue
        delivery_events.append(
            {
                "status": status,
                "next_step": str(corrected_value.get("internal_next_step", "") or "").strip(),
                "note": str(item.get("note", "") or corrected_value.get("internal_note", "") or "").strip(),
                "updated_by": str(item.get("corrected_by", "") or corrected_value.get("internal_updated_by", "") or "-").strip(),
                "updated_at": str(item.get("corrected_at", "") or corrected_value.get("internal_updated_at", "") or "-").strip(),
            }
        )

    if not delivery_events:
        return empty_state("暂无交付历史", "在导出中心标记可交付或已交付后，这里会形成内部交付时间线。")

    rows = []
    for event in delivery_events:
        status = event["status"]
        tone = "success" if status == "delivered" else "info"
        rows.append(
            '<article class="delivery-history-item">'
            '<div class="delivery-history-marker"></div>'
            '<div class="delivery-history-copy">'
            '<div class="delivery-history-head">'
            f'{pill(_internal_status_label(status), tone)}'
            f'<strong>{escape_html(event["next_step"] or _internal_status_label(status))}</strong>'
            '</div>'
            f'<p>{escape_html(event["note"] or "已记录交付状态更新。")}</p>'
            f'<small>{escape_html(event["updated_at"])} / {escape_html(event["updated_by"] or "-")}</small>'
            '</div>'
            '</article>'
        )
    return '<div class="delivery-history-list">' + "".join(rows) + '</div>'


def render_submission_exports_page(
    submission: dict,
    materials: list[dict],
    cases: list[dict],
    reports: list[dict],
    parse_results: list[dict],
) -> str:
    del parse_results
    submission_id = escape_html(submission.get("id", ""))
    internal_status = str(submission.get("internal_status", "unassigned") or "unassigned")
    review_stage = str(submission.get("review_stage", "review_completed") or "review_completed")
    pending_case_count = sum(1 for case in cases if str(case.get("status", "") or "") == "awaiting_manual_review")
    issue_count = sum(len(material.get("issues", []) or []) for material in materials)
    has_reports = bool(reports)
    has_blocking_internal_status = internal_status in {"blocked", "waiting_materials", "fixing"}
    is_review_finished = review_stage in {"review_completed", "desensitized_review_completed"}

    delivery_checks = [
        ("项目报告", has_reports, f"已生成 {len(reports)} 份报告" if has_reports else "尚未生成项目级报告"),
        ("正式审查", is_review_finished, review_stage_label(review_stage)),
        ("待继续审查", pending_case_count == 0, "无待继续项目" if pending_case_count == 0 else f"{pending_case_count} 个项目待继续审查"),
        ("审查问题", issue_count == 0, "暂无材料问题" if issue_count == 0 else f"{issue_count} 个问题待确认"),
        ("内部状态", not has_blocking_internal_status, _internal_status_label(internal_status)),
    ]
    blocking_checks = [item for item in delivery_checks if not item[1]]
    delivery_ready = not blocking_checks
    delivery_tone = "success" if delivery_ready else "warning"
    delivery_title = "可以准备交付" if delivery_ready else "交付前仍需处理"
    delivery_note = "报告、审查阶段和内部状态均已满足交付前检查。" if delivery_ready else "先处理未通过项，再下载报告和批次包。"
    delivery_check_rows = "".join(
        '<div class="delivery-check-item">'
        f'{pill("通过" if passed else "待处理", "success" if passed else "warning")}'
        f'<strong>{escape_html(label)}</strong>'
        f'<span>{escape_html(detail)}</span>'
        "</div>"
        for label, passed, detail in delivery_checks
    )
    delivery_check_body = (
        notice_banner(delivery_title, delivery_note, tone=delivery_tone, icon_name="check", meta=[f"报告 {len(reports)}", f"待继续 {pending_case_count}", f"问题 {issue_count}"])
        + f'<div class="delivery-check-list">{delivery_check_rows}</div>'
    )
    delivery_return_to = f"/submissions/{submission_id}/exports#delivery-check"
    delivery_owner = escape_html(str(submission.get("internal_owner", "") or ""))
    delivery_note_value = "已完成交付前检查，准备内部交付。" if delivery_ready else "交付前检查仍有未通过项，需处理后再确认交付。"
    delivery_confirm_body = (
        '<div class="delivery-confirm-actions">'
        '<form class="delivery-confirm-form" action="/submissions/'
        + submission_id
        + '/actions/update-internal-state" method="post">'
        + f'<input type="hidden" name="internal_owner" value="{delivery_owner}">'
        + '<input type="hidden" name="internal_status" value="ready_to_deliver">'
        + '<input type="hidden" name="internal_next_step" value="已生成内部交付包，待负责人复核后发送。">'
        + f'<input type="hidden" name="internal_note" value="{escape_html(delivery_note_value)}">'
        + '<input type="hidden" name="updated_by" value="delivery_center">'
        + f'<input type="hidden" name="return_to" value="{escape_html(delivery_return_to)}">'
        + f'<button class="button-secondary" type="submit">{icon("check", "icon icon-sm")}标记为可交付</button>'
        + '</form>'
        '<form class="delivery-confirm-form" action="/submissions/'
        + submission_id
        + '/actions/update-internal-state" method="post">'
        + f'<input type="hidden" name="internal_owner" value="{delivery_owner}">'
        + '<input type="hidden" name="internal_status" value="delivered">'
        + '<input type="hidden" name="internal_next_step" value="本批次已交付并完成内部归档。">'
        + '<input type="hidden" name="internal_note" value="导出中心确认已交付，交付结果已进入内部归档。">'
        + '<input type="hidden" name="updated_by" value="delivery_center">'
        + f'<input type="hidden" name="return_to" value="{escape_html(delivery_return_to)}">'
        + f'<button class="button-primary" type="submit">{icon("download", "icon icon-sm")}标记为已交付</button>'
        + '</form>'
        '</div>'
        '<p class="delivery-confirm-note">确认动作会写入内部状态和更正审计；如检查仍有未通过项，建议先处理再标记已交付。</p>'
    )

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

    handoff_body = (
        '<div class="summary-grid">'
        + _summary_tile("报告数", str(len(reports)), "当前批次可带走的项目级报告数量")
        + _summary_tile("批次包", "可直接下载", "适合整体交付、回传或归档")
        + _summary_tile("当前阶段", review_stage_label(submission.get("review_stage", "review_completed")), "导出前可快速确认是否已经完成正式审查")
        + _summary_tile("交付动作", "先下报告和批次包", "日志和排障信息放到下方按需查看")
        + "</div>"
        + '<div class="inline-actions">'
        + f'<a class="button-secondary" href="/downloads/submissions/{submission_id}/bundle">{icon("download", "icon icon-sm")}下载批次包</a>'
        + "</div>"
        + (
            f'<div class="report-card-grid">{report_cards}</div>'
            if report_cards
            else empty_state("暂无报告", "批次审查完成后，这里会出现可查看和可下载的报告。")
        )
    )

    support_body = (
        '<div class="summary-grid">'
        + _summary_tile("应用日志", "可直接下载", "只有在追踪处理过程或排查异常时才需要")
        + _summary_tile("使用场景", "排障附件", "不建议把日志和交付结果混在一起发给业务侧")
        + "</div>"
        + '<div class="inline-actions">'
        + f'<a class="button-secondary" href="/downloads/logs/app">{icon("terminal", "icon icon-sm")}下载日志</a>'
        + "</div>"
    )

    delivery_history_body = _delivery_history_timeline(str(submission.get("id", "") or ""))

    content = f"""
    <section class="dashboard-grid">
      {panel('交付前收口检查', delivery_check_body, kicker='内部交付', extra_class='span-12 panel-delivery-check panel-soft', icon_name='check', description='交付前先确认报告、审查阶段、待继续项目、问题和内部状态。', panel_id='delivery-check')}
      {panel('交付确认', delivery_confirm_body, kicker='状态收口', extra_class='span-12 panel-delivery-confirm panel-soft', icon_name='wrench', description='确认后会更新内部状态并写入更正审计，方便团队追踪可交付和已交付批次。', panel_id='delivery-confirm')}
      {panel('交付历史', delivery_history_body, kicker='交付留痕', extra_class='span-12 panel-delivery-history panel-soft', icon_name='clock', description='只展示可交付和已交付确认事件，帮助内部团队回看交付状态变化。', panel_id='delivery-history')}
      {panel('导出中心', handoff_body, kicker='产物交付', extra_class='span-12', icon_name='download', description='先处理真正要交付的报告和批次包。', panel_id='export-center')}
      {panel('排障附件', support_body, kicker='按需查看', extra_class='span-12', icon_name='terminal', description='日志单独放在这里，避免和交付动作混在一起。', panel_id='export-support')}
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
            ("#delivery-check", "收口检查", "check"),
            ("#delivery-confirm", "交付确认", "wrench"),
            ("#delivery-history", "交付历史", "clock"),
            ("#export-center", "导出中心", "download"),
            ("#export-support", "排障附件", "terminal"),
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
        + _summary_tile("当前阶段", review_stage_label(submission.get("review_stage", "review_completed")), "先判断是不是还卡在脱敏或待继续审查")
        + _summary_tile("操作顺序", "继续审查 -> 整理材料 -> 重跑", "把常见动作压成一条顺手路径")
        + _summary_tile("留痕方式", "自动记录", "所有人工动作都会写入更正审计")
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
            <strong>材料与项目整理</strong>
            <small>先修正材料类型、归属，再决定是否新建或合并项目。</small>
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
          <span class="operator-group-index">3</span>
          <div>
            <strong>在线填报信息</strong>
            <small>按项目录入在线系统字段，保存后会立即重跑审查。</small>
          </div>
        </summary>
        {_render_online_filing_operator_forms(submission.get("id", ""), cases)}
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


def _internal_status_label(value: str) -> str:
    return INTERNAL_STATUS_LABELS.get(str(value or "unassigned").strip(), "待认领")


def _internal_status_options(selected: str) -> str:
    normalized = str(selected or "unassigned").strip() or "unassigned"
    return "".join(
        f'<option value="{escape_html(value)}"{ " selected" if value == normalized else ""}>{escape_html(label)}</option>'
        for value, label in INTERNAL_STATUS_LABELS.items()
    )


def _internal_issue_counts(materials: list[dict], cases: list[dict]) -> dict[str, int]:
    material_issue_count = sum(len(material.get("issues", []) or []) for material in materials)
    case_issue_count = 0
    for case in cases:
        review_result_id = str(case.get("review_result_id", "") or "").strip()
        if review_result_id and review_result_id in store.review_results:
            case_issue_count += len(store.review_results[review_result_id].issues_json or [])
    total = max(material_issue_count, case_issue_count)
    return {
        "material": material_issue_count,
        "case": case_issue_count,
        "total": total,
    }


def _internal_work_status(submission: dict, pending_cases: list[dict], needs_review_count: int, issue_count: int) -> tuple[str, str, str]:
    status = str(submission.get("status", "") or "")
    if status == "failed":
        return "处理异常", "danger", "先查看处理失败原因，必要时重新上传或拆分材料包。"
    if status == "processing":
        return "处理中", "warning", "等待系统处理完成后再做人工判断。"
    if pending_cases:
        return "待继续审查", "warning", "先确认脱敏件，再到人工干预台继续审查。"
    if needs_review_count:
        return "待人工复核", "warning", "先处理待复核材料，确认类型、归属和解析质量。"
    if issue_count:
        return "待修复问题", "warning", "进入报告页查看问题清单，先处理退回级和一致性问题。"
    if status == "completed":
        return "可交付", "success", "当前没有优先阻塞项，可以进入导出中心生成内部交付包。"
    return "待判断", "neutral", "先确认材料、项目和报告是否已经生成完整。"


def _internal_next_actions(
    submission_id: str,
    *,
    pending_cases_count: int,
    needs_review_count: int,
    issue_count: int,
    reports: list[dict],
) -> str:
    actions: list[str] = []
    if pending_cases_count:
        actions.append(
            f'<a class="button-primary button-compact" href="/submissions/{submission_id}/operator">'
            f'{icon("refresh", "icon icon-sm")}继续审查</a>'
        )
    if needs_review_count:
        actions.append(
            f'<a class="button-secondary button-compact" href="/submissions/{submission_id}/materials#needs-review">'
            f'{icon("alert", "icon icon-sm")}处理待复核</a>'
        )
    if issue_count and reports:
        first_report_id = escape_html(str(reports[0].get("id", "")))
        actions.append(
            f'<a class="button-secondary button-compact" href="/reports/{first_report_id}">'
            f'{icon("report", "icon icon-sm")}查看修复清单</a>'
        )
    actions.append(
        f'<a class="button-secondary button-compact" href="/submissions/{submission_id}/exports">'
        f'{icon("download", "icon icon-sm")}导出内部包</a>'
    )
    actions.append(
        f'<a class="button-secondary button-compact" href="/submissions/{submission_id}/operator">'
        f'{icon("wrench", "icon icon-sm")}记录人工动作</a>'
    )
    return '<div class="inline-actions internal-action-row">' + "".join(actions[:5]) + "</div>"


def _render_internal_workbench(
    submission: dict,
    materials: list[dict],
    cases: list[dict],
    reports: list[dict],
    data: dict,
    pending_cases: list[dict],
) -> str:
    submission_id = escape_html(str(submission.get("id", "") or ""))
    needs_review_count = len(data.get("needs_review_items", []) or [])
    correction_count = len(data.get("correction_rows", []) or [])
    issue_counts = _internal_issue_counts(materials, cases)
    work_status, tone, next_step = _internal_work_status(
        submission,
        pending_cases,
        needs_review_count,
        issue_counts["total"],
    )
    saved_owner = str(submission.get("internal_owner", "") or "").strip()
    saved_status = str(submission.get("internal_status", "unassigned") or "unassigned").strip() or "unassigned"
    saved_next_step = str(submission.get("internal_next_step", "") or "").strip()
    saved_note = str(submission.get("internal_note", "") or "").strip()
    saved_updated_by = str(submission.get("internal_updated_by", "") or "").strip()
    saved_updated_at = str(submission.get("internal_updated_at", "") or "").strip()
    owner = saved_owner or "内部待认领"
    if correction_count and not saved_owner:
        owner = "已有人工处理"

    blockers: list[str] = []
    if pending_cases:
        blockers.append(f"{len(pending_cases)} 个项目等待脱敏后继续审查")
    if needs_review_count:
        blockers.append(f"{needs_review_count} 份材料需要人工复核")
    if issue_counts["total"]:
        blockers.append(f"{issue_counts['total']} 个审查问题需要确认")
    if not reports:
        blockers.append("尚未生成可交付报告")
    blocker_body = (
        '<div class="rule-checkpoint-list"><ul>'
        + "".join(f"<li>{escape_html(item)}</li>" for item in blockers[:5])
        + "</ul></div>"
        if blockers
        else empty_state("暂无内部阻塞项", "这个批次可以进入导出中心准备内部交付。")
    )

    display_next_step = saved_next_step or next_step
    updated_meta = ""
    if saved_updated_at or saved_updated_by:
        updated_meta = f"最近更新：{saved_updated_at or '-'} / {saved_updated_by or '-'}"

    def _template_options(items: list[str]) -> str:
        return '<option value="">选择常用模板</option>' + "".join(
            f'<option value="{escape_html(item)}">{escape_html(item)}</option>'
            for item in items
        )

    next_step_templates = [
        "等客户补协议签署页",
        "等客户补源码后 30 页",
        "等客户确认软件名称",
        "已发客户补材料清单",
        "已生成内部交付包",
        "已交付归档",
    ]
    note_templates = [
        "已通知客户补齐缺失材料，等待回传。",
        "材料命名或项目归属需要内部复核后再继续。",
        "审查问题已记录，待修正后重新生成报告。",
        "脱敏件已准备，等待确认后继续正式审查。",
        "交付包已生成，待负责人复核后发送。",
        "本批次已交付并完成内部归档。",
    ]
    internal_template_picker = f"""
      <div class="internal-template-grid">
        <label class="field">
          <span>下一步模板</span>
          <select data-template-target="internal_next_step" onchange="if (this.value) this.form.elements[this.dataset.templateTarget].value = this.value; this.selectedIndex = 0;">
            {_template_options(next_step_templates)}
          </select>
        </label>
        <label class="field">
          <span>备注模板</span>
          <select data-template-target="internal_note" onchange="if (this.value) this.form.elements[this.dataset.templateTarget].value = this.value; this.selectedIndex = 0;">
            {_template_options(note_templates)}
          </select>
        </label>
      </div>
    """
    internal_form = f"""
    <form class="internal-state-form" action="/submissions/{submission_id}/actions/update-internal-state" method="post">
      <div class="control-grid internal-state-grid">
        <label class="field">
          <span>负责人</span>
          <input type="text" name="internal_owner" value="{escape_html(saved_owner)}" placeholder="例如：张三 / 交付组A">
        </label>
        <label class="field">
          <span>内部状态</span>
          <select name="internal_status">{_internal_status_options(saved_status)}</select>
        </label>
        <label class="field">
          <span>下一步动作</span>
          <input type="text" name="internal_next_step" value="{escape_html(saved_next_step)}" placeholder="例如：等客户补协议签署页">
        </label>
        <label class="field">
          <span>更新人</span>
          <input type="text" name="updated_by" value="{escape_html(saved_updated_by or 'operator_ui')}" placeholder="记录操作人">
        </label>
      </div>
      {internal_template_picker}
      <label class="field">
        <span>内部备注</span>
        <textarea name="internal_note" rows="3" placeholder="只给内部团队看的处理备注">{escape_html(saved_note)}</textarea>
      </label>
      <div class="inline-actions internal-action-row">
        <button class="button-primary button-compact" type="submit">{icon("wrench", "icon icon-sm")}保存内部状态</button>
        <span class="form-helper-text">{escape_html(updated_meta or "保存后会写入更正审计。")}</span>
      </div>
    </form>
    """

    return (
        '<div class="internal-workbench">'
        '<div class="summary-grid internal-workbench-grid">'
        + _summary_tile("内部状态", _internal_status_label(saved_status), display_next_step)
        + _summary_tile("负责人", owner, "内部团队当前责任人")
        + _summary_tile("必须关注", str(len(blockers)), "待继续、待复核、审查问题和报告产物")
        + _summary_tile("人工留痕", str(correction_count), "材料纠偏、继续审查和规则调整都会记录")
        + "</div>"
        + notice_banner(
            f"内部处理建议：{work_status}",
            next_step,
            tone=tone,
            icon_name="wrench",
            meta=[
                f"材料 {len(materials)}",
                f"项目 {len(cases)}",
                f"报告 {len(reports)}",
                f"问题 {issue_counts['total']}",
            ],
        )
        + blocker_body
        + internal_form
        + _internal_next_actions(
            submission_id,
            pending_cases_count=len(pending_cases),
            needs_review_count=needs_review_count,
            issue_count=issue_counts["total"],
            reports=reports,
        )
        + "</div>"
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
    global_review = dict((submission.get("review_profile", {}) or {}).get("submission_global_review", {}) or {})
    global_status = str(global_review.get("status", "") or "").strip()

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
            _summary_tile("导入模式", mode_label(str(submission.get("mode", ""))), "这次材料按什么方式整理"),
            _summary_tile("审查策略", review_strategy_label(str(submission.get("review_strategy", "auto_review"))), "决定直接审查还是先脱敏后继续"),
            _summary_tile("当前阶段", review_stage_label(str(submission.get("review_stage", "review_completed"))), "先看这里，就知道当前卡在哪一步"),
        ]
    )

    destination_body = (
        '<div class="summary-grid">'
        + _summary_tile("当前状态", status_label(submission.get("status", "unknown")), "先确认批次是否已完成、处理中，或仍待人工推进")
        + _summary_tile("待继续审查", str(len(pending_cases)), "只有先脱敏后继续模式下才会出现")
        + _summary_tile("结果去向", "三个子页面", "材料、人工处理、导出入口都放到独立页面")
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

    review_profile_body = list_pairs(review_profile_summary(review_profile), css_class="dossier-list dossier-list-single")
    review_rule_links = _review_rule_links(str(submission.get("id", "")), review_profile)
    compact_notes = []
    if pending_cases:
        compact_notes.append(f"有 {len(pending_cases)} 个项目还在等待继续审查。")
    if data["needs_review_items"]:
        compact_notes.append(f"有 {len(data['needs_review_items'])} 份材料建议优先人工复核。")
    if data["correction_rows"]:
        compact_notes.append(f"当前批次已有 {len(data['correction_rows'])} 条人工处理留痕。")
    compact_note_body = (
        '<div class="rule-checkpoint-list"><ul>'
        + "".join(f"<li>{escape_html(item)}</li>" for item in compact_notes[:4])
        + "</ul></div>"
        if compact_notes
        else empty_state("当前没有额外提醒", "这个批次已经具备继续查看结果或导出的基本条件。")
    )
    job_history_body = _job_history_board(str(submission.get("id", "") or ""))
    parse_diagnostics_body = _parse_diagnostics_board(materials, parse_results)
    advanced_groups = '<div class="operator-group-grid">'
    advanced_groups += _fold_group(0, "整包全局审查", "先看整个材料包是否完整、是否串项或需要复核。", _render_global_review_board(submission), open_by_default=True)
    advanced_groups += _fold_group(1, "审查配置", "查看当前维度和规则入口。", review_profile_body + review_rule_links, open_by_default=False)
    advanced_groups += _fold_group(2, "批次提醒", "只保留当前还值得你注意的补充说明。", compact_note_body, open_by_default=False)
    advanced_groups += _fold_group(3, "任务链路", "查看导入任务状态、失败原因和重试入口。", job_history_body, open_by_default=False)
    advanced_groups += _fold_group(9, "解析诊断", "统一查看解析质量、人工复核原因和当前建议。", parse_diagnostics_body, open_by_default=False)
    advanced_groups += "</div>"

    content = f"""
    <section class="kpi-grid">
      {metric_card('整包审查', _global_review_status_label(global_status), '先判断整个压缩包是否完整、串项或需要复核', _global_review_status_tone(global_status), icon_name='shield')}
      {metric_card('材料数', str(len(materials)), '当前批次识别出的材料数量', 'info', icon_name='file')}
      {metric_card('项目数', str(len(cases)), '当前批次形成的项目数量', 'success', icon_name='lock')}
      {metric_card('报告数', str(len(reports)), '当前可查看的项目级报告数量', 'neutral', icon_name='report')}
      {metric_card('待复核队列', str(len(data['needs_review_items'])), '需要优先人工确认的材料数量', 'warning' if data['needs_review_items'] else 'success', icon_name='alert')}
    </section>
    <section class="dashboard-grid">
      {panel('导入摘要', f'<div class="summary-grid">{import_digest}</div>', kicker='批次摘要', extra_class='span-12 panel-soft', icon_name='file', description='主页面只保留这个批次的关键概览。', panel_id='import-digest')}
      {panel('内部处理面板', _render_internal_workbench(submission, materials, cases, reports, data, pending_cases), kicker='团队协作', extra_class='span-12 panel-internal-workbench', icon_name='wrench', description='按内部团队使用场景聚合状态、阻塞项和下一步动作。', panel_id='internal-workbench')}
      {panel('结果去向', destination_body, kicker='下一步', extra_class='span-12', icon_name='spark', description='首页只保留去往材料、人工处理和导出的入口，不再堆太多解释。', panel_id='review-workflow')}
      {panel('待复核队列', needs_review_body, kicker='优先处理', extra_class='span-12', icon_name='alert', description='优先确认这些材料，再决定是否进入人工处理或继续审查。', panel_id='needs-review')}
      {panel('更多信息', advanced_groups, kicker='按需展开', extra_class='span-12', icon_name='search', description='这里只保留少量补充信息，不再展示冗长列表。', panel_id='submission-more')}
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
            ("#internal-workbench", "内部处理", "wrench"),
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
