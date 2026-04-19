from __future__ import annotations

from collections import Counter
from pathlib import Path

from app.core.services.ops_status import (
    format_signed_delta,
    latest_metrics_baseline_status,
    latest_runtime_backup_status,
    list_metrics_baseline_history,
)
from app.core.services.runtime_store import store
from app.core.utils.text import escape_html


MODE_LABELS = {
    "single_case_package": "同一个软著，多个材料",
    "batch_same_material": "不同软著，同一类材料",
}

TYPE_LABELS = {
    "agreement": "合作协议",
    "source_code": "源代码",
    "info_form": "信息采集表",
    "software_doc": "软著文档",
    "unknown": "未识别",
}

REPORT_LABELS = {
    "material_markdown": "材料审查报告",
    "case_markdown": "项目综合报告",
    "batch_markdown": "批次汇总报告",
}

SEVERITY_LABELS = {
    "severe": "涓ラ噸",
    "moderate": "涓瓑",
    "minor": "杞诲井",
}


def _icon(name: str, class_name: str = "icon") -> str:
    icons = {
        "brand": '<path d="M12 3 4 7v6c0 4.8 3.1 8.6 8 10 4.9-1.4 8-5.2 8-10V7l-8-4Z"/><path d="m9.8 12.2 1.7 1.7 3.4-3.9"/>',
        "dashboard": '<rect x="4" y="4" width="7" height="7" rx="2"/><rect x="13" y="4" width="7" height="4" rx="2"/><rect x="13" y="10" width="7" height="10" rx="2"/><rect x="4" y="13" width="7" height="7" rx="2"/>',
        "upload": '<path d="M12 16V6"/><path d="m8 10 4-4 4 4"/><path d="M5 19h14"/>',
        "submissions": '<path d="m12 4 8 4-8 4-8-4 8-4Z"/><path d="m4 12 8 4 8-4"/><path d="m4 16 8 4 8-4"/>',
        "workflow": '<circle cx="6" cy="6" r="2"/><circle cx="18" cy="12" r="2"/><circle cx="8" cy="18" r="2"/><path d="M8 6h5c2 0 3 1 3 3v1"/><path d="M16 14c0 2-1 3-3 3h-3"/>',
        "shield": '<path d="M12 3 5 6v6c0 4.3 2.8 7.8 7 9.2 4.2-1.4 7-4.9 7-9.2V6l-7-3Z"/><path d="m9.8 12.2 1.7 1.7 3.7-4.2"/>',
        "report": '<path d="M7 4h10a2 2 0 0 1 2 2v12l-3-2-4 2-4-2-3 2V6a2 2 0 0 1 2-2Z"/><path d="M9 9h6"/><path d="M9 12h6"/>',
        "case": '<rect x="4" y="7" width="16" height="11" rx="2.5"/><path d="M9 7V5a3 3 0 0 1 6 0v2"/>',
        "file": '<path d="M8 3h7l4 4v12a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z"/><path d="M15 3v4h4"/>',
        "info_form": '<rect x="5" y="4" width="14" height="16" rx="2"/><path d="M8 8h8"/><path d="M8 12h8"/><path d="M8 16h5"/>',
        "source_code": '<path d="m9 8-4 4 4 4"/><path d="m15 8 4 4-4 4"/><path d="M13 6 11 18"/>',
        "software_doc": '<path d="M8 3h7l4 4v12a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z"/><path d="M15 3v4h4"/><path d="M9 11h6"/><path d="M9 15h4"/>',
        "agreement": '<path d="M8 4h8l4 4v10a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Z"/><path d="M14 4v4h4"/><path d="M9 10h6"/><path d="M9 14h6"/>',
        "chart": '<path d="M5 19V9"/><path d="M12 19V5"/><path d="M19 19v-7"/>',
        "risk": '<path d="M12 4 3.5 19h17L12 4Z"/><path d="M12 10v4"/><circle cx="12" cy="17" r="1"/>',
        "check": '<circle cx="12" cy="12" r="9"/><path d="m9.5 12.5 1.8 1.8 3.7-4.2"/>',
        "history": '<path d="M12 8v5l3 2"/><path d="M4.5 9A8 8 0 1 1 8 18"/><path d="M4 4v5h5"/>',
        "server": '<rect x="4" y="5" width="16" height="5" rx="2"/><rect x="4" y="14" width="16" height="5" rx="2"/><path d="M8 7.5h.01"/><path d="M8 16.5h.01"/>',
        "target": '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r="1"/>',
        "trend": '<path d="M4 16 9 11l3 3 7-7"/><path d="M15 7h4v4"/>',
        "filter": '<path d="M4 6h16"/><path d="M7 12h10"/><path d="M10 18h4"/>',
    }
    payload = icons.get(name, icons["file"])
    return (
        f'<svg class="{class_name}" viewBox="0 0 24 24" fill="none" '
        f'xmlns="http://www.w3.org/2000/svg" aria-hidden="true" stroke="currentColor" '
        f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{payload}</svg>'
    )


def _mode_label(mode: str) -> str:
    return MODE_LABELS.get(mode, mode)


def _type_label(material_type: str) -> str:
    return TYPE_LABELS.get(material_type, material_type)


def _report_label(report_type: str) -> str:
    return REPORT_LABELS.get(report_type, report_type)


def _status_tone(status: str) -> str:
    mapping = {
        "completed": "success",
        "grouped": "info",
        "processing": "warning",
        "running": "warning",
        "failed": "danger",
    }
    return mapping.get(status, "neutral")


def _material_tone(material_type: str) -> str:
    mapping = {
        "agreement": "warning",
        "source_code": "info",
        "info_form": "success",
        "software_doc": "purple",
    }
    return mapping.get(material_type, "neutral")


def _issue_tone(issue_count: int) -> str:
    if issue_count >= 3:
        return "danger"
    if issue_count >= 1:
        return "warning"
    return "success"


def _material_icon(material_type: str) -> str:
    mapping = {
        "agreement": "agreement",
        "source_code": "source_code",
        "info_form": "info_form",
        "software_doc": "software_doc",
    }
    return _icon(mapping.get(material_type, "file"), "icon icon-sm")


def _pill(text: str, tone: str = "neutral") -> str:
    return f'<span class="pill pill-{tone}">{escape_html(text)}</span>'


def _delta_pill(label: str, value: int | None) -> str:
    normalized = label.lower()
    if value is None:
        return _pill(f"{label} -", "neutral")
    if "review" in normalized or "quality" in normalized:
        tone = "success" if value < 0 else "danger" if value > 0 else "info"
    elif "redaction" in normalized:
        tone = "info" if value >= 0 else "warning"
    else:
        tone = "info" if value > 0 else "warning" if value < 0 else "neutral"
    return _pill(f"{label} {format_signed_delta(value)}", tone)


def _nav_link(path: str, label: str, icon: str, active: bool) -> str:
    active_class = " nav-link-active" if active else ""
    return (
        f'<a class="nav-link{active_class}" href="{path}">'
        f'{_icon(icon, "icon")}<span>{escape_html(label)}</span></a>'
    )


def _kpi_card(label: str, value: str, note: str, icon: str, tone: str = "neutral") -> str:
    return f"""
    <article class="kpi-card kpi-card-{tone}">
      <div class="kpi-icon">{_icon(icon, "icon icon-md")}</div>
      <div class="kpi-copy">
        <span class="kpi-label">{escape_html(label)}</span>
        <strong>{escape_html(value)}</strong>
        <small>{escape_html(note)}</small>
      </div>
    </article>
    """


def _progress_row(label: str, value: int, total: int, tone: str = "info", prefix_icon: str = "chart") -> str:
    total = max(total, 1)
    width = max(8, int((value / total) * 100)) if value else 8
    return f"""
    <div class="metric-row">
      <div class="metric-label">
        {_icon(prefix_icon, "icon icon-sm")}
        <span>{escape_html(label)}</span>
      </div>
      <div class="metric-track">
        <span class="metric-fill metric-fill-{tone}" style="width: {width}%"></span>
      </div>
      <strong>{value}</strong>
    </div>
    """


def _ops_status_card(
    kicker: str,
    title: str,
    note: str,
    icon: str,
    tone: str,
    rows: list[tuple[str, str]],
    badges: list[str] | None = None,
) -> str:
    row_html = "".join(
        f"<div><span>{escape_html(label)}</span><strong>{escape_html(value)}</strong></div>"
        for label, value in rows
        if str(value or "").strip()
    )
    badge_html = "".join(badges or [])
    return f"""
    <article class="ops-status-card">
      <div class="ops-status-top">
        <div class="ops-status-copy">
          <span class="panel-kicker">{escape_html(kicker)}</span>
          <strong>{escape_html(title)}</strong>
          <small>{escape_html(note)}</small>
        </div>
        <div class="panel-head-icon">{_icon(icon, "icon icon-lg")}</div>
      </div>
      <div class="ops-status-badges">{badge_html}</div>
      <div class="ops-mini-list">{row_html}</div>
    </article>
    """


def _table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return '<div class="empty-state"><strong>鏆傛棤鏁版嵁</strong><span>褰撳墠瑙嗗浘涓嬭繕娌℃湁鍙睍绀虹殑璁板綍銆?/span></div>'
    head = "".join(f"<th>{escape_html(item)}</th>" for item in headers)
    body_rows = []
    for row in rows:
        body_rows.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>")
    return f"""
    <div class="table-wrap">
      <table class="data-table">
        <thead><tr>{head}</tr></thead>
        <tbody>{''.join(body_rows)}</tbody>
      </table>
    </div>
    """


def _type_breakdown(materials: list[dict]) -> Counter:
    return Counter(item.get("material_type", "unknown") for item in materials)


def _runtime_snapshot() -> dict:
    materials = [item.to_dict() for item in store.materials.values()]
    parse_results = [item.to_dict() for item in store.parse_results.values()]
    return {
        "submission_count": len(store.submissions),
        "material_count": len(materials),
        "case_count": len(store.cases),
        "report_count": len(store.report_artifacts),
        "unknown_count": sum(1 for item in materials if item.get("material_type") == "unknown"),
        "needs_review_count": sum(
            1 for item in parse_results if item.get("metadata_json", {}).get("triage", {}).get("needs_manual_review")
        ),
        "low_quality_count": sum(
            1 for item in parse_results if item.get("metadata_json", {}).get("parse_quality", {}).get("quality_level") == "low"
        ),
        "redaction_total": sum(
            int(item.get("metadata_json", {}).get("privacy", {}).get("total_replacements", 0) or 0)
            for item in parse_results
        ),
    }


def _issue_total(materials: list[dict]) -> int:
    return sum(len(item.get("issues", [])) for item in materials)


def _severity_summary(issues: list[dict]) -> dict[str, int]:
    summary = {"severe": 0, "moderate": 0, "minor": 0}
    for issue in issues:
        severity = str(issue.get("severity", "minor")).lower()
        if severity in summary:
            summary[severity] += 1
        else:
            summary["minor"] += 1
    return summary


def _privacy_category_label(category: str) -> str:
    mapping = {
        "labeled_field": "鏍囩瀛楁",
        "contact": "鑱旂郴鏂瑰紡",
        "identity": "韬唤淇℃伅",
        "organization": "涓讳綋缂栫爜",
        "financial": "閲戣瀺淇℃伅",
        "network": "缃戠粶鏍囪瘑",
        "explicit_value": "鏄惧紡瀛楁",
    }
    return mapping.get(category, category)


def _privacy_overview(materials: list[dict], parse_results: list[dict]) -> dict:
    material_names = {item.get("id"): item.get("original_filename", "") for item in materials}
    category_counter: Counter = Counter()
    rows: list[list[str]] = []
    total_replacements = 0
    files_with_redaction = 0
    policy = "local_manual_redaction_v1"

    for item in parse_results:
        metadata = item.get("metadata_json", {})
        privacy = metadata.get("privacy", {})
        policy = str(privacy.get("policy", policy))
        replacement_total = int(privacy.get("total_replacements", 0) or 0)
        total_replacements += replacement_total
        if replacement_total:
            files_with_redaction += 1
        category_counts = privacy.get("category_counts", {})
        for category, count in category_counts.items():
            category_counter[str(category)] += int(count)
        category_text = ", ".join(
            f"{_privacy_category_label(str(category))}:{int(count)}"
            for category, count in sorted(category_counts.items())
        ) or "鏃犲懡涓?
        rows.append(
            [
                escape_html(material_names.get(item.get("material_id"), item.get("material_id", "鏈煡鏉愭枡"))),
                str(replacement_total),
                escape_html(category_text),
                _pill("宸茶劚鏁?, "success" if privacy.get("llm_safe") else "warning"),
            ]
        )

    category_summary = ", ".join(
        f"{_privacy_category_label(category)} {count}"
        for category, count in sorted(category_counter.items())
    ) or "鏈壒娆℃湭鍛戒腑棰勭疆鏁忔劅瑙勫垯"

    return {
        "policy": policy,
        "total_replacements": total_replacements,
        "files_with_redaction": files_with_redaction,
        "category_summary": category_summary,
        "rows": rows,
    }


def _quality_tone(level: str) -> str:
    mapping = {
        "high": "success",
        "medium": "warning",
        "low": "danger",
    }
    return mapping.get(level, "neutral")


def _legacy_doc_bucket_tone(bucket: str) -> str:
    mapping = {
        "usable_text": "success",
        "partial_fragments": "warning",
        "binary_noise": "danger",
    }
    return mapping.get(bucket, "neutral")


def _self_check_tone(status: str) -> str:
    mapping = {
        "ok": "success",
        "warning": "warning",
        "failed": "danger",
    }
    return mapping.get(status, "neutral")


def _provider_phase_tone(phase: str) -> str:
    mapping = {
        "mock_mode": "info",
        "provider_no_probe_required": "info",
        "disabled": "warning",
        "configured_disabled": "warning",
        "not_configured": "warning",
        "partially_configured": "warning",
        "ready_for_probe": "success",
        "probe_skipped": "warning",
        "probe_passed": "success",
        "probe_failed": "danger",
        "not_run": "neutral",
    }
    return mapping.get(str(phase or "").strip().lower(), "neutral")


def _gate_tone(status: str) -> str:
    mapping = {
        "pass": "success",
        "warning": "warning",
        "blocked": "danger",
    }
    return mapping.get(str(status or "").strip().lower(), "neutral")


def _first_nonempty(values: list[str], fallback: str = "") -> str:
    for value in values:
        if str(value or "").strip():
            return str(value).strip()
    return fallback


def _suggested_case_defaults(submission: dict, materials: list[dict], parse_results: list[dict], cases: list[dict]) -> dict:
    parse_map = {item.get("material_id"): item for item in parse_results}
    suggested_material_ids = [
        item["id"]
        for item in materials
        if parse_map.get(item["id"], {}).get("metadata_json", {}).get("triage", {}).get("needs_manual_review")
    ]
    inferred_name = _first_nonempty(
        [
            *(item.get("detected_software_name", "") for item in materials),
            *(item.get("metadata", {}).get("software_name", "") for item in materials),
            *(item.get("case_name", "") for item in cases),
            Path(submission.get("filename", "")).stem,
        ],
        "浜哄伐鏂板缓椤圭洰",
    )
    inferred_version = _first_nonempty(
        [
            *(item.get("detected_version", "") for item in materials),
            *(item.get("metadata", {}).get("version", "") for item in materials),
            *(item.get("version", "") for item in cases),
        ]
    )
    inferred_company = _first_nonempty(
        [
            *(item.get("metadata", {}).get("company_name", "") for item in materials),
            *(item.get("company_name", "") for item in cases),
        ]
    )
    return {
        "case_name": inferred_name,
        "version": inferred_version,
        "company_name": inferred_company,
        "material_ids": ",".join(suggested_material_ids or [item["id"] for item in materials[:2]]),
    }


def _review_queue(materials: list[dict], parse_results: list[dict]) -> dict:
    parse_map = {item.get("material_id"): item for item in parse_results}
    rows: list[list[str]] = []
    needs_review = 0
    low_quality = 0
    unknown_count = 0

    for material in materials:
        parse_result = parse_map.get(material.get("id"), {})
        metadata = parse_result.get("metadata_json", {})
        quality = metadata.get("parse_quality", {})
        triage = metadata.get("triage", {})
        classification = metadata.get("classification", {})

        if quality.get("quality_level") == "low":
            low_quality += 1
        if material.get("material_type") == "unknown":
            unknown_count += 1

        if not triage.get("needs_manual_review"):
            continue

        needs_review += 1
        reason = (
            triage.get("unknown_reason")
            or triage.get("quality_review_reason_label")
            or quality.get("review_reason_label")
            or quality.get("quality_reason")
            or classification.get("reason")
            or "manual_triage"
        )
        quality_flags = ", ".join(str(item) for item in quality.get("quality_flags", [])) or "鏃犻澶栦俊鍙?
        bucket = triage.get("legacy_doc_bucket") or quality.get("legacy_doc_bucket") or ""
        bucket_text = triage.get("legacy_doc_bucket_label") or quality.get("legacy_doc_bucket_label") or "闈?legacy doc"
        action = "鍏堟敼绫诲瀷" if material.get("material_type") == "unknown" else "澶嶆牳鏂囨湰鍚庡啀褰掓。"
        rows.append(
            [
                f'<div class="table-title-cell">{_material_icon(material["material_type"])}<span>{escape_html(material["original_filename"])}</span></div>',
                _pill(_type_label(material["material_type"]), _material_tone(material["material_type"])),
                _pill(str(quality.get("quality_level", "unknown")), _quality_tone(str(quality.get("quality_level", "unknown")))),
                _pill(bucket_text, _legacy_doc_bucket_tone(bucket)) if bucket else escape_html(bucket_text),
                escape_html(quality_flags),
                escape_html(str(reason)),
                _pill(action, "warning"),
            ]
        )

    return {
        "needs_review": needs_review,
        "low_quality": low_quality,
        "unknown_count": unknown_count,
        "rows": rows,
    }


def _correction_history(submission: dict) -> dict:
    rows: list[list[str]] = []
    correction_ids = submission.get("correction_ids", [])
    corrections = [store.corrections[item_id] for item_id in correction_ids if item_id in store.corrections]

    for correction in corrections:
        target = correction.material_id or correction.case_id or submission.get("id", "")
        rows.append(
            [
                escape_html(correction.corrected_at or "-"),
                escape_html(correction.correction_type),
                escape_html(target),
                escape_html(correction.corrected_by or "local"),
                escape_html(correction.note or "-"),
            ]
        )

    return {"count": len(corrections), "rows": rows}


def _download_chip(path: str, label: str) -> str:
    return f'<a class="button-secondary button-compact" href="{path}">{escape_html(label)}</a>'


def _read_preview(path: str, limit: int = 180) -> str:
    if not path:
        return ""
    target = Path(path)
    if not target.exists():
        return ""
    text = target.read_text(encoding="utf-8", errors="ignore")
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[:limit].rstrip() + "..."


def _sidebar(active_nav: str) -> str:
    snapshot = _runtime_snapshot()
    return f"""
    <aside class="sidebar">
      <a class="sidebar-brand" href="/">
        <span class="sidebar-brand-mark">{_icon("dashboard", "icon icon-md")}</span>
        <span class="sidebar-brand-copy">
          <strong>杞憲瀹℃煡鍙?/strong>
          <small>Admin Analysis Console</small>
        </span>
      </a>

      <section class="sidebar-section">
        <span class="sidebar-label">瀵艰埅</span>
        <nav class="sidebar-nav" aria-label="涓诲鑸?>
          {_nav_link("/", "鎺у埗鍙?, "dashboard", active_nav == "home")}
          {_nav_link("/submissions", "鎵规涓績", "submissions", active_nav == "submissions")}
          {_nav_link("/ops", "Support / Ops", "server", active_nav == "ops")}
        </nav>
      </section>

      <section class="sidebar-section">
        <span class="sidebar-label">宸ヤ綔娴?/span>
        <div class="sidebar-list">
          <div class="sidebar-item">{_icon("upload", "icon icon-sm")}<span>ZIP 瀵煎叆</span></div>
          <div class="sidebar-item">{_icon("workflow", "icon icon-sm")}<span>鑷姩鍒嗙被</span></div>
          <div class="sidebar-item">{_icon("shield", "icon icon-sm")}<span>瑙勫垯瀹℃煡</span></div>
          <div class="sidebar-item">{_icon("report", "icon icon-sm")}<span>鎶ュ憡鍥炵湅</span></div>
        </div>
      </section>

      <section class="sidebar-section sidebar-signal">
        <span class="sidebar-label">绯荤粺鍩虹嚎</span>
        <div class="sidebar-mini-kpi">
          <div><strong>2</strong><span>瀵煎叆妯″紡</span></div>
          <div><strong>{snapshot['submission_count']}</strong><span>杩愯鎵规</span></div>
          <div><strong>{snapshot['needs_review_count']}</strong><span>寰呭鏍?/span></div>
        </div>
      </section>
    </aside>
    """


def _layout(
    title: str,
    active_nav: str,
    header_tag: str,
    header_title: str,
    header_subtitle: str,
    header_meta: str,
    content: str,
) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>{escape_html(title)}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
  <div class="admin-shell">
    {_sidebar(active_nav)}
    <div class="workspace">
      <header class="workspace-header">
        <div class="workspace-header-main">
          <span class="workspace-tag">{escape_html(header_tag)}</span>
          <h1>{escape_html(header_title)}</h1>
          <p>{escape_html(header_subtitle)}</p>
        </div>
        <div class="workspace-header-meta">{header_meta}</div>
      </header>
      <main class="workspace-content">
        {content}
      </main>
    </div>
  </div>
</body>
</html>"""


def render_home_page() -> str:
    snapshot = _runtime_snapshot()
    kpis = "".join(
        [
            _kpi_card("瀵煎叆妯″紡", "2", "鍗曢」鐩?/ 鍚岀被鎵规", "workflow", "info"),
            _kpi_card("鏉愭枡绫诲瀷", "4", "淇℃伅琛?/ 浠ｇ爜 / 鏂囨。 / 鍗忚", "file", "success"),
            _kpi_card("瀹℃煡绛栫暐", "瑙勫垯浼樺厛", "AI 璐熻矗瑙ｉ噴涓庢眹鎬?, "shield", "warning"),
            _kpi_card("杩愯鎽樿", str(snapshot["submission_count"]), "宸茶繘鍏ョ郴缁熺殑瀵煎叆鎵规", "report", "purple"),
        ]
    )
    upload_panel = f"""
    <section class="panel panel-primary span-7">
      <div class="panel-head">
        <div>
          <span class="panel-kicker">Import Console</span>
          <h2>涓婁紶 ZIP</h2>
          <p>浠庤繖閲岃繘鍏ヤ富澶勭悊閾捐矾銆傚綋鍓嶇郴缁熶細鎶?ZIP 杞垚鍙垎鏋愩€佸彲杩借釜銆佸彲鍥炵湅鐨勭粨鏋勫寲缁撴灉銆?/p>
        </div>
        <div class="panel-head-icon">{_icon("upload", "icon icon-lg")}</div>
      </div>
      <form class="admin-form" action="/upload" method="post" enctype="multipart/form-data">
        <label class="field">
          <span>瀵煎叆妯″紡</span>
          <select name="mode">
            <option value="single_case_package">鍚屼竴涓蒋钁楋紝澶氫釜鏉愭枡</option>
            <option value="batch_same_material">涓嶅悓杞憲锛屽悓涓€绫绘潗鏂?/option>
          </select>
          <small class="field-hint">妯″紡 A 鐢ㄤ簬鈥滀竴涓」鐩浠芥潗鏂欌€濓紝妯″紡 B 鐢ㄤ簬鈥滃涓」鐩殑鍚岀被鏉愭枡鎵瑰鐞嗏€濄€?/small>
        </label>
        <label class="field">
          <span>ZIP 鏂囦欢</span>
          <input type="file" name="file" accept=".zip" required>
          <small class="field-hint">寤鸿濮嬬粓鍏堟墦鎴?ZIP 鍐嶄笂浼狅紝鑳芥樉钁楅檷浣庢祻瑙堝櫒宸紓涓庣洰褰曠粨鏋勪涪澶遍棶棰樸€?/small>
        </label>
        <div class="empty-state">
          <strong>Privacy Shield</strong>
          <span>绯荤粺浼氬厛鍦ㄦ湰鍦版墽琛岃鍒欒劚鏁忥紝鍘熸枃涓庤劚鏁忔枃鏈垎绂讳繚瀛橈紱鍚庣画澶栭儴妯″瀷鍙厑璁镐娇鐢ㄨ劚鏁忕粨鏋溿€?/span>
        </div>
        <button class="button-primary" type="submit">{_icon("upload", "icon icon-sm")}寮€濮嬪鍏?/button>
      </form>
    </section>
    """
    health_panel = f"""
    <section class="panel span-5">
      <div class="panel-head">
        <div>
          <span class="panel-kicker">System Health</span>
          <h2>绯荤粺淇″彿</h2>
        </div>
        <div class="panel-head-icon">{_icon("server", "icon icon-lg")}</div>
      </div>
      <div class="status-stack">
        <div class="status-card">{_pill('瑙勫垯寮曟搸鍦ㄧ嚎', 'success')}<span>纭畾鎬ц鍒欐鏌ュ凡鎺ュ叆涓婚摼璺€?/span></div>
        <div class="status-card">{_pill('ZIP 瀹夊叏闃叉姢', 'info')}<span>鍖呭惈 Zip Slip 闃叉姢鍜屽彲鎵ц鏂囦欢鎷︽埅銆?/span></div>
        <div class="status-card">{_pill('鍙拷婧緭鍑?, 'warning')}<span>Submission銆丆ase銆丷eport 涓夊眰缁撴灉閮藉彲鍥炵湅銆?/span></div>
      </div>
    </section>
    """
    workflow_panel = f"""
    <section class="panel span-7">
      <div class="panel-head">
        <div>
          <span class="panel-kicker">Pipeline Analysis</span>
          <h2>瀹℃煡娴佺▼鍒嗘瀽</h2>
          <p>杩欎笉鏄畼缃戦椤碉紝鑰屾槸涓€涓伐浣滃彴鍏ュ彛銆傛祦绋嬨€佺姸鎬佸拰缁撴灉鍏ュ彛搴旇姣旇惀閿€鏂囨鏇存樉鐪笺€?/p>
        </div>
        <div class="panel-head-icon">{_icon("chart", "icon icon-lg")}</div>
      </div>
      <div class="process-board">
        <article class="process-step">
          <span class="step-icon">{_icon("upload", "icon icon-sm")}</span>
          <strong>涓婁紶涓庤В鍘?/strong>
          <p>鏍￠獙 ZIP銆佸睍寮€鐩綍缁撴瀯銆佽繃婊ゅ嵄闄╂枃浠躲€?/p>
        </article>
        <article class="process-step">
          <span class="step-icon">{_icon("filter", "icon icon-sm")}</span>
          <strong>鑷姩鍒嗙被</strong>
          <p>鎸夋枃浠跺悕銆佺洰褰曞拰鍐呭鐗瑰緛璇嗗埆鏉愭枡绫诲埆銆?/p>
        </article>
        <article class="process-step">
          <span class="step-icon">{_icon("shield", "icon icon-sm")}</span>
          <strong>瑙勫垯瀹℃煡</strong>
          <p>璇嗗埆鐗堟湰銆佷竴鑷存€с€侀敊璇嶃€佷贡鐮佷笌瀹夊叏闂銆?/p>
        </article>
        <article class="process-step">
          <span class="step-icon">{_icon("report", "icon icon-sm")}</span>
          <strong>杈撳嚭鎶ュ憡</strong>
          <p>鐢熸垚鏉愭枡绾с€侀」鐩骇鍜屾壒娆＄骇缁撴灉瑙嗗浘銆?/p>
        </article>
      </div>
    </section>
    """
    runtime_panel = f"""
    <section class="panel span-5">
      <div class="panel-head">
        <div>
          <span class="panel-kicker">Runtime Snapshot</span>
          <h2>褰撳墠杩愯鎽樿</h2>
          <p>鎶婃渶杩戝鍏ュ悗鐨勬壒娆¤妯°€佸緟澶嶆牳鏁伴噺鍜岃劚鏁忓懡涓噺鏀惧湪棣栭〉锛岄伩鍏嶈繍钀ュ悓瀛﹀彧鑳借繘璇︽儏椤垫墠鐪嬪埌缁撴灉銆?/p>
        </div>
        <div class="panel-head-icon">{_icon("trend", "icon icon-lg")}</div>
      </div>
      <div class="dossier-list">
        <div><span>杩愯鎵规</span><strong>{snapshot['submission_count']}</strong></div>
        <div><span>鏉愭枡鎬婚噺</span><strong>{snapshot['material_count']}</strong></div>
        <div><span>寰呭鏍?/span><strong>{snapshot['needs_review_count']}</strong></div>
        <div><span>鑴辨晱鏇挎崲</span><strong>{snapshot['redaction_total']}</strong></div>
      </div>
      <p class="highlight-note">鐪熷疄鏍锋湰鍩虹嚎宸茬粡杩涘叆鈥滈浂 unknown 涓荤洰鏍団€濓紝褰撳墠鏇村叧娉ㄤ綆璐ㄩ噺 legacy `.doc` 鐨勭户缁敹鏁涘拰寰呭鏍稿帇缂┿€?/p>
    </section>
    """
    mode_panel = f"""
    <section class="panel span-5">
      <div class="panel-head">
        <div>
          <span class="panel-kicker">Mode Matrix</span>
          <h2>瀵煎叆妯″紡鐭╅樀</h2>
        </div>
        <div class="panel-head-icon">{_icon("target", "icon icon-lg")}</div>
      </div>
      <div class="mode-grid">
        <article class="mode-tile">
          <span class="mode-icon">{_icon("case", "icon icon-sm")}</span>
          <strong>妯″紡 A</strong>
          <p>鍚屼竴涓蒋钁楋紝澶氫釜鏉愭枡銆傜洰鏍囨槸褰㈡垚瀹屾暣 Case 鍜岀患鍚堟姤鍛娿€?/p>
        </article>
        <article class="mode-tile">
          <span class="mode-icon">{_icon("submissions", "icon icon-sm")}</span>
          <strong>妯″紡 B</strong>
          <p>涓嶅悓杞憲锛屽悓涓€绉嶆潗鏂欍€傜洰鏍囨槸鍏堟壒閲忓綊妗ｏ紝鍐嶇瓑寰呭悎骞躲€?/p>
        </article>
      </div>
    </section>
    """
    batch_guidance_panel = f"""
    <section class="panel span-7">
      <div class="panel-head">
        <div>
          <span class="panel-kicker">Mode B Guidance</span>
          <h2>鎵归噺瀵煎叆鎿嶄綔寤鸿</h2>
          <p>妯″紡 B 鐨勯噸鐐逛笉鏄珛鍒诲嚭缁煎悎鎶ュ憡锛岃€屾槸鍏堟妸鍚岀被鏉愭枡绋冲畾褰掓。锛屽啀绛夊緟琛ュ叏鍏朵粬鏉愭枡鎴栦汉宸ュ悎骞躲€?/p>
        </div>
        <div class="panel-head-icon">{_icon("submissions", "icon icon-lg")}</div>
      </div>
      <div class="dossier-list">
        <div><span>鎺ㄨ崘 ZIP 缁撴瀯</span><strong>涓嶅悓杞憲 + 鍚屼竴绫绘潗鏂?/strong></div>
        <div><span>褰掔粍閿?/span><strong>杞欢鍚?+ 鐗堟湰鍙?/strong></div>
        <div><span>澶辫触鍥為€€</span><strong>鏃犳硶璇嗗埆鏃跺厛鐣欏湪寰呭鏍搁槦鍒?/strong></div>
        <div><span>鍚庣画鍔ㄤ綔</span><strong>鎵嬪伐寤?Case / 鍚堝苟 Case / 閲嶈窇瀹℃煡</strong></div>
      </div>
      <p class="highlight-note">濡傛灉鍚屽悕鏉愭枡閲岀己杞欢鍚嶆垨鐗堟湰鍙凤紝涓嶈寮鸿鑷姩鍚堝苟锛屽厛璁╃郴缁熶繚鐣欏垎鏁ｅ綊妗ｏ紝鍐嶇敤鎿嶄綔鍙扮籂鍋忋€?/p>
    </section>
    """
    intake_guidance_panel = f"""
    <section class="panel span-12">
      <div class="panel-head">
        <div>
          <span class="panel-kicker">Browser Intake Policy</span>
          <h2>娴忚鍣ㄧ瀵煎叆璇存槑</h2>
          <p>褰撳墠娴忚鍣ㄥ伐浣滄祦浠?ZIP 涓轰富銆傛ā寮?B 宸叉敮鎸佸悓绫绘潗鏂欐壒閲?ZIP 瀵煎叆锛涚洰褰曠洿浼犱粛寤鸿鍏堝湪鏈湴鎵撳寘锛屽啀涓婁紶浠ヤ繚鎸佽В鏋愮ǔ瀹氭€у拰璺ㄦ祻瑙堝櫒涓€鑷存€с€?/p>
        </div>
        <div class="panel-head-icon">{_icon("workflow", "icon icon-lg")}</div>
      </div>
      <div class="dossier-list">
        <div><span>妯″紡 A</span><strong>涓€涓?ZIP锛屽寘鍚悓涓€杞憲鐨勫浠芥潗鏂?/strong></div>
        <div><span>妯″紡 B</span><strong>涓€涓?ZIP锛屽寘鍚笉鍚岃蒋钁楃殑鍚岀被鏉愭枡</strong></div>
        <div><span>鎺ㄨ崘褰㈡€?/span><strong>ZIP first</strong></div>
        <div><span>娴忚鍣ㄩ檺鍒?/span><strong>鐩綍鐩翠紶鏆備笉浣滀负涓昏矾寰?/strong></div>
      </div>
      <p class="highlight-note">濡傛灉闇€瑕佺洰褰曠骇鎵瑰鐞嗭紝寤鸿璧版湰鍦?runner 鎴栧厛鎵撴垚 ZIP 鍐嶈繘鍏ユ祻瑙堝櫒绠＄悊鍙般€?/p>
    </section>
    """

    content = f"""
    <section class="kpi-grid">{kpis}</section>
    <section class="dashboard-grid">
      {upload_panel}
      {health_panel}
      {runtime_panel}
      {workflow_panel}
      {batch_guidance_panel}
      {mode_panel}
      {intake_guidance_panel}
    </section>
    """
    return _layout(
        title="杞憲瀹℃煡鍙?,
        active_nav="home",
        header_tag="Control Center",
        header_title="杞憲棰勫鍒嗘瀽绯荤粺",
        header_subtitle="浠ュ悗鍙板伐浣滃彴鏂瑰紡缁勭粐瀵煎叆銆佸綊妗ｃ€佸鏌ュ拰鎶ュ憡锛岃€屼笉鏄畼缃戝紡灞曠ず椤甸潰銆?,
        header_meta="".join(
            [
                _pill("绠＄悊绯荤粺瑙嗗浘", "info"),
                _pill("涓婁紶 ZIP", "neutral"),
            ]
        ),
        content=content,
    )


def render_submissions_index() -> str:
    submissions = list(store.submissions.values())
    material_total = 0
    case_total = 0
    status_counter = Counter()
    rows = []
    for submission in submissions:
        material_count = len(submission.material_ids)
        case_count = len(submission.case_ids)
        report_count = len(submission.report_ids)
        material_total += material_count
        case_total += case_count
        status_counter[submission.status] += 1
        rows.append(
            [
                f'<div class="table-title-cell">{_icon("submissions", "icon icon-sm")}<span>{escape_html(submission.filename)}</span></div>',
                escape_html(_mode_label(submission.mode)),
                str(material_count),
                str(case_count),
                str(report_count),
                _pill(submission.status, _status_tone(submission.status)),
                f'<a class="table-link" href="/submissions/{escape_html(submission.id)}">杩涘叆鎵规</a>',
            ]
        )
    status_panel = "".join(
        [
            _progress_row("宸插畬鎴?, status_counter.get("completed", 0), max(len(submissions), 1), "success", "check"),
            _progress_row("澶勭悊涓?, status_counter.get("processing", 0), max(len(submissions), 1), "warning", "workflow"),
            _progress_row("澶辫触", status_counter.get("failed", 0), max(len(submissions), 1), "danger", "risk"),
        ]
    )
    content = f"""
    <section class="kpi-grid">
      {_kpi_card('鎵规鏁?, str(len(submissions)), '褰撳墠杩愯鏃跺凡璁板綍鐨勫鍏ユ壒娆?, 'submissions', 'info')}
      {_kpi_card('鏉愭枡鎬婚噺', str(material_total), '璺ㄦ墍鏈夋壒娆＄疮璁¤瘑鍒潗鏂欐暟', 'file', 'success')}
      {_kpi_card('椤圭洰褰掓。', str(case_total), '宸茶仛鍚堝舰鎴愮殑 Case 鏁伴噺', 'case', 'warning')}
      {_kpi_card('鏈€杩戠姸鎬?, 'Completed' if status_counter.get('completed') else 'Idle', '鎵规鐘舵€佸垎甯冭鍙充晶闈㈡澘', 'trend', 'purple')}
    </section>
    <section class="dashboard-grid">
      <section class="panel span-8">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">Batch Registry</span>
            <h2>鎵规涓績</h2>
            <p>浠ユ暟鎹〃鏂瑰紡鍥炵湅姣忎釜 Submission 鐨勬ā寮忋€佺姸鎬併€佹潗鏂欐暟鍜屾姤鍛婂叆鍙ｃ€?/p>
          </div>
          <div class="panel-head-icon">{_icon("submissions", "icon icon-lg")}</div>
        </div>
        {_table(['鎵规', '妯″紡', '鏉愭枡', '椤圭洰', '鎶ュ憡', '鐘舵€?, '鎿嶄綔'], rows)}
      </section>
      <section class="panel span-4">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">Status Distribution</span>
            <h2>鐘舵€佸垎甯?/h2>
          </div>
          <div class="panel-head-icon">{_icon("chart", "icon icon-lg")}</div>
        </div>
        <div class="metric-stack">
          {status_panel or _progress_row('鏆傛棤鎵规', 0, 1)}
        </div>
      </section>
    </section>
    """
    return _layout(
        title="瀵煎叆鎵规",
        active_nav="submissions",
        header_tag="Submission Center",
        header_title="瀵煎叆鎵规鍒嗘瀽",
        header_subtitle="鎵归噺鏌ョ湅姣忎竴娆″鍏ョ殑瑙勬ā銆佺姸鎬佸拰褰掓。缁撴灉锛岀鍚堝悗鍙板垎鏋愮郴缁熺殑浣跨敤鏂瑰紡銆?,
        header_meta=_pill("鎵规瑙嗗浘", "info"),
        content=content,
    )


def render_submission_detail(
    submission: dict,
    materials: list[dict],
    cases: list[dict],
    reports: list[dict],
    parse_results: list[dict],
) -> str:
    material_count = len(materials)
    case_count = len(cases)
    report_count = len(reports)
    issue_count = _issue_total(materials)
    type_breakdown = _type_breakdown(materials)
    privacy = _privacy_overview(materials, parse_results)
    review_queue = _review_queue(materials, parse_results)
    correction_history = _correction_history(submission)
    parse_map = {item.get("material_id"): item for item in parse_results}
    privacy_table = _table(['鏉愭枡', '鏇挎崲鏁?, '鍛戒腑鍒嗙被', '鐘舵€?], privacy["rows"])
    distribution = "".join(
        _progress_row(_type_label(material_type), count, max(material_count, 1), _material_tone(material_type), "file")
        for material_type, count in type_breakdown.items()
    )

    material_rows = []
    for item in materials:
        issues = len(item.get("issues", []))
        material_rows.append(
            [
                f'<div class="table-title-cell">{_material_icon(item["material_type"])}<span>{escape_html(item["original_filename"])}</span></div>',
                _pill(_type_label(item["material_type"]), _material_tone(item["material_type"])),
                escape_html(item.get("detected_software_name") or "鏈瘑鍒?),
                escape_html(item.get("detected_version") or "鏈瘑鍒?),
                _pill(f"{issues} 涓棶棰?, _issue_tone(issues)),
            ]
        )

    material_options = "".join(
        f'<option value="{escape_html(item["id"])}">{escape_html(item["original_filename"])} | {escape_html(_type_label(item["material_type"]))}</option>'
        for item in materials
    ) or '<option value="">鏆傛棤鏉愭枡</option>'
    case_options = "".join(
        f'<option value="{escape_html(item["id"])}">{escape_html(item["case_name"])} | {escape_html(item.get("version") or "鏃犵増鏈?)}</option>'
        for item in cases
    ) or '<option value="">鏆傛棤 Case</option>'
    material_reference = "".join(
        f'<span class="helper-chip">{escape_html(item["id"])} 路 {escape_html(item["original_filename"])}</span>'
        for item in materials
    ) or '<span class="helper-chip">鏆傛棤鏉愭枡</span>'
    suggested_defaults = _suggested_case_defaults(submission, materials, parse_results, cases)
    mode_guidance = (
        "妯″紡 A 浼氬皾璇曠洿鎺ョ敓鎴愬畬鏁?Case锛岄€傚悎涓€涓蒋钁楃殑鎴愬鏉愭枡銆?
        if submission.get("mode") == "single_case_package"
        else "妯″紡 B 鍏堝仛鍚岀被鏉愭枡褰掓。锛岃嫢杞欢鍚嶆垨鐗堟湰淇℃伅涓嶈冻锛屽缓璁繚鐣欏垎鏁ｇ粨鏋滃苟鍦ㄦ搷浣滃彴鎵嬪伐褰掔粍銆?
    )
    import_digest = f"""
    <section class="panel span-12 summary-band">
      <div class="panel-head">
        <div>
          <span class="panel-kicker">Import Digest</span>
          <h2>瀵煎叆鎽樿鍗?/h2>
          <p>鎶婅繖娆″鍏ョ殑缁撴瀯鍖栫粨鏋滃厛鍘嬫垚涓€涓憳瑕侀潰鏉匡紝杩愯惀鍚屽涓嶇敤缈诲涓尯鍧楁墠鑳藉垽鏂槸鍚﹀彲缁х画涓嬫父鎿嶄綔銆?/p>
        </div>
        <div class="panel-head-icon">{_icon("dashboard", "icon icon-lg")}</div>
      </div>
      <div class="summary-grid">
        <article class="summary-tile">
          <span>鏉愭枡鏁?/span>
          <strong>{material_count}</strong>
          <small>宸茶瘑鍒苟钀界洏</small>
        </article>
        <article class="summary-tile">
          <span>Case 鏁?/span>
          <strong>{case_count}</strong>
          <small>褰撳墠褰掓。缁撴灉</small>
        </article>
        <article class="summary-tile">
          <span>寰呭鏍?/span>
          <strong>{review_queue['needs_review']}</strong>
          <small>unknown / low quality / 浣庣疆淇″害</small>
        </article>
        <article class="summary-tile">
          <span>鑴辨晱鏇挎崲</span>
          <strong>{privacy['total_replacements']}</strong>
          <small>浠呰劚鏁忔枃鏈彲杩涘叆 AI</small>
        </article>
      </div>
      <p class="highlight-note">{escape_html(mode_guidance)}</p>
    </section>
    """

    case_rows = []
    for case in cases:
        case_rows.append(
            [
                f'<div class="table-title-cell">{_icon("case", "icon icon-sm")}<span>{escape_html(case["case_name"])}</span></div>',
                escape_html(case.get("version") or "鏃犵増鏈?),
                _pill(case.get("status") or "unknown", _status_tone(case.get("status") or "")),
                f'<a class="table-link" href="/cases/{escape_html(case["id"])}">鏌ョ湅椤圭洰</a>',
            ]
        )

    export_rows = []
    for report in reports:
        export_rows.append(
            [
                escape_html(_report_label(report["report_type"])),
                escape_html(report["scope_type"]),
                _download_chip(f'/reports/{escape_html(report["id"])}', "鏌ョ湅")
                + _download_chip(f'/downloads/reports/{escape_html(report["id"])}', "涓嬭浇"),
            ]
        )
    export_table = _table(['浜х墿', '鑼冨洿', '鎿嶄綔'], export_rows)

    artifact_rows = []
    preview_count = 0
    available_artifact_count = 0
    for item in materials:
        parse_result = parse_map.get(item["id"], {})
        links: list[str] = []
        for artifact_kind, label in (
            ("raw", "raw"),
            ("clean", "clean"),
            ("desensitized", "desensitized"),
            ("privacy", "privacy"),
        ):
            artifact_key = {
                "raw": "raw_text_path",
                "clean": "clean_text_path",
                "desensitized": "desensitized_text_path",
                "privacy": "privacy_manifest_path",
            }[artifact_kind]
            if parse_result.get(artifact_key):
                available_artifact_count += 1
                links.append(_download_chip(f'/downloads/materials/{escape_html(item["id"])}/{artifact_kind}', label))
        if item.get("report_id"):
            links.append(_download_chip(f'/downloads/reports/{escape_html(item["report_id"])}', "鏉愭枡鎶ュ憡"))
        preview = _read_preview(parse_result.get("desensitized_text_path", ""))
        if preview:
            preview_count += 1
        artifact_rows.append(
            [
                f'<div class="table-title-cell">{_material_icon(item["material_type"])}<span>{escape_html(item["original_filename"])}</span></div>',
                "".join(links) or '<span class="helper-chip">鏆傛棤浜х墿</span>',
                f'<div class="preview-block">{escape_html(preview or "鏆傛棤鑴辨晱棰勮")}</div>',
            ]
        )
    artifact_table = _table(['鏉愭枡', '浜х墿涓嬭浇', '鑴辨晱棰勮'], artifact_rows)

    report_cards = "".join(
        f"""
        <div class="report-card">
          <div class="report-card-head">{_icon('report', 'icon icon-sm')}<strong>{escape_html(_report_label(report['report_type']))}</strong></div>
          <span>{escape_html(report['file_format'].upper())} 路 {escape_html(report['scope_type'])}</span>
          <div class="inline-actions">
            {_download_chip(f"/reports/{escape_html(report['id'])}", "鏌ョ湅")}
            {_download_chip(f"/downloads/reports/{escape_html(report['id'])}", "涓嬭浇")}
          </div>
        </div>
        """
        for report in reports
    ) or '<div class="empty-state"><strong>鏆傛棤鎶ュ憡</strong><span>褰撳墠鎵规杩樻病鏈夌敓鎴愬彲鏌ョ湅鐨勬姤鍛婁骇鐗┿€?/span></div>'

    content = f"""
    <section class="kpi-grid">
      {_kpi_card('鏉愭枡鏁?, str(material_count), '褰撳墠鎵规宸茶瘑鍒潗鏂?, 'file', 'info')}
      {_kpi_card('椤圭洰鏁?, str(case_count), '鑷姩鑱氬悎鍚庣殑 Case 鏁伴噺', 'case', 'success')}
      {_kpi_card('鎶ュ憡鏁?, str(report_count), '鍙洿鎺ヨ繘鍏ョ殑瀹℃煡鎶ュ憡', 'report', 'warning')}
      {_kpi_card('闂鎬婚噺', str(issue_count), '鏉愭枡绾ч棶棰樼疮璁?, 'risk', 'danger' if issue_count else 'success')}
      {_kpi_card('寰呭鏍?, str(review_queue['needs_review']), '鍖呭惈 unknown 涓庝綆璐ㄩ噺瑙ｆ瀽鏉愭枡', 'history', 'warning' if review_queue['needs_review'] else 'success')}
    </section>
    <section class="dashboard-grid">
      {import_digest}
      <section class="panel span-8">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">Material Matrix</span>
            <h2>鏉愭枡鎬昏琛?/h2>
            <p>鎸夊悗鍙板垎鏋愮郴缁熺殑鏂瑰紡鐩存帴鏌ョ湅鏂囦欢銆佹潗鏂欑被鍨嬨€佽瘑鍒悕绉般€佺増鏈拰闂鏁伴噺銆?/p>
          </div>
          <div class="panel-head-icon">{_icon("file", "icon icon-lg")}</div>
        </div>
        {_table(['鏂囦欢', '绫诲瀷', '璇嗗埆鍚嶇О', '璇嗗埆鐗堟湰', '闂鏁?], material_rows)}
      </section>
      <section class="panel span-4">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">Distribution</span>
            <h2>鏉愭枡鍒嗗竷</h2>
          </div>
          <div class="panel-head-icon">{_icon("chart", "icon icon-lg")}</div>
        </div>
        <div class="metric-stack">
          {distribution or _progress_row('鏆傛棤鏉愭枡', 0, 1)}
        </div>
      </section>
      <section class="panel span-5">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">Case Mapping</span>
            <h2>椤圭洰鑱氬悎</h2>
          </div>
          <div class="panel-head-icon">{_icon("case", "icon icon-lg")}</div>
        </div>
        {_table(['椤圭洰', '鐗堟湰', '鐘舵€?, '鎿嶄綔'], case_rows)}
      </section>
      <section class="panel span-7">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">Reports</span>
            <h2>鎶ュ憡涓績</h2>
          </div>
          <div class="panel-head-icon">{_icon("report", "icon icon-lg")}</div>
        </div>
        <div class="report-card-grid">{report_cards}</div>
      </section>
      <section class="panel span-12">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">Operator Console</span>
            <h2>浜哄伐绾犻敊鎿嶄綔鍙?/h2>
            <p>鎶婂悗绔?correction 鑳藉姏鐩存帴鎼埌娴忚鍣ㄧ銆傝繖閲屼紭鍏堟敮鎸佸垎绫讳慨姝ｃ€丆ase 褰掔粍銆丆ase 鍚堝苟鍜岄噸璺戝鏌ワ紝鏂逛究杩愯惀鍚屽閫愪釜娓呯悊寰呭鏍搁槦鍒椼€?/p>
          </div>
          <div class="panel-head-icon">{_icon("workflow", "icon icon-lg")}</div>
        </div>
        <div class="helper-chip-row">{material_reference}</div>
        <div class="operator-note">
          <strong>棰勫～寤鸿</strong>
          <span>绯荤粺宸茬粡鏍规嵁褰撳墠鎵规鎺ㄦ柇浜嗗缓璁殑 Case 鍚嶇О銆佺増鏈彿鍜屽叕鍙稿悕锛涘鏋滃緟澶嶆牳闃熷垪閲屾湁鏉愭枡锛屼細浼樺厛鎶婅繖浜涙潗鏂?ID 鏀捐繘鏂板缓 Case 琛ㄥ崟銆?/span>
        </div>
        <div class="control-grid">
          <form class="operator-form" action="/submissions/{escape_html(submission['id'])}/actions/change-type" method="post">
            <span class="panel-kicker">Type Fix</span>
            <label class="field"><span>鏉愭枡</span><select name="material_id">{material_options}</select></label>
            <label class="field">
              <span>鐩爣绫诲瀷</span>
              <select name="material_type">
                <option value="info_form">淇℃伅閲囬泦琛?/option>
                <option value="source_code">婧愪唬鐮?/option>
                <option value="software_doc">杞憲鏂囨。</option>
                <option value="agreement">鍚堜綔鍗忚</option>
                <option value="unknown">鏈瘑鍒?/option>
              </select>
              <small class="field-hint">浼樺厛鐢ㄤ簬 unknown 淇锛屾垨 legacy `.doc` 琚鍒嗗瀷鍚庣殑浜哄伐鍏滃簳銆?/small>
            </label>
            <label class="field"><span>澶囨敞</span><input type="text" name="note" placeholder="渚嬪锛氭枃浠跺悕鍜屾鏂囬兘琛ㄦ槑杩欐槸鍚堜綔鍗忚"></label>
            <input type="hidden" name="corrected_by" value="operator_ui">
            <button class="button-primary" type="submit">{_icon("filter", "icon icon-sm")}鎻愪氦绫诲瀷淇</button>
          </form>

          <form class="operator-form" action="/submissions/{escape_html(submission['id'])}/actions/assign-case" method="post">
            <span class="panel-kicker">Case Assign</span>
            <label class="field"><span>鏉愭枡</span><select name="material_id">{material_options}</select></label>
            <label class="field"><span>鐩爣 Case</span><select name="case_id">{case_options}</select><small class="field-hint">鐢ㄤ簬鎶婃暎钀芥潗鏂欏苟鍥炲凡鏈夐」鐩紝閫傚悎妯″紡 B 鐨勫悗缁ˉ妗ｃ€?/small></label>
            <label class="field"><span>澶囨敞</span><input type="text" name="note" placeholder="渚嬪锛氳蒋浠跺悕鍜岀増鏈彿涓庣洰鏍?Case 涓€鑷?></label>
            <input type="hidden" name="corrected_by" value="operator_ui">
            <button class="button-primary" type="submit">{_icon("case", "icon icon-sm")}鍒嗛厤鍒?Case</button>
          </form>

          <form class="operator-form" action="/submissions/{escape_html(submission['id'])}/actions/create-case" method="post">
            <span class="panel-kicker">Create Case</span>
            <label class="field"><span>鏉愭枡 ID 鍒楄〃</span><input type="text" name="material_ids" value="{escape_html(suggested_defaults['material_ids'])}" placeholder="mat_xxx, mat_yyy"><small class="field-hint">榛樿浼樺厛濉叆寰呭鏍告潗鏂欙紝鍑忓皯澶嶅埗绮樿创銆?/small></label>
            <label class="field"><span>Case 鍚嶇О</span><input type="text" name="case_name" value="{escape_html(suggested_defaults['case_name'])}" placeholder="浜哄伐 Case 鍚嶇О"></label>
            <label class="field"><span>鐗堟湰</span><input type="text" name="version" value="{escape_html(suggested_defaults['version'])}" placeholder="鍙€?></label>
            <label class="field"><span>鍏徃鍚?/span><input type="text" name="company_name" value="{escape_html(suggested_defaults['company_name'])}" placeholder="鍙€?></label>
            <label class="field"><span>澶囨敞</span><input type="text" name="note" placeholder="渚嬪锛氬悓涓€椤圭洰鏉愭枡琚媶鏁ｏ紝闇€瑕佷汉宸ラ噸鏂板缓妗?></label>
            <input type="hidden" name="corrected_by" value="operator_ui">
            <button class="button-primary" type="submit">{_icon("submissions", "icon icon-sm")}鏂板缓浜哄伐 Case</button>
          </form>

          <form class="operator-form" action="/submissions/{escape_html(submission['id'])}/actions/merge-cases" method="post">
            <span class="panel-kicker">Merge Cases</span>
            <label class="field"><span>婧?Case</span><select name="source_case_id">{case_options}</select></label>
            <label class="field"><span>鐩爣 Case</span><select name="target_case_id">{case_options}</select></label>
            <label class="field"><span>澶囨敞</span><input type="text" name="note" placeholder="渚嬪锛氫袱涓?Case 瀹為檯鏄悓涓€杞憲鐨勪笉鍚屾潗鏂欓泦鍚?></label>
            <input type="hidden" name="corrected_by" value="operator_ui">
            <button class="button-primary" type="submit">{_icon("workflow", "icon icon-sm")}鍚堝苟 Case</button>
          </form>

          <form class="operator-form" action="/submissions/{escape_html(submission['id'])}/actions/rerun-review" method="post">
            <span class="panel-kicker">Rerun Review</span>
            <label class="field"><span>Case</span><select name="case_id">{case_options}</select></label>
            <label class="field"><span>澶囨敞</span><input type="text" name="note" placeholder="渚嬪锛氬凡瀹屾垚绾犲亸锛岄噸鏂扮敓鎴愮患鍚堢粨璁轰笌鎶ュ憡"></label>
            <input type="hidden" name="corrected_by" value="operator_ui">
            <button class="button-primary" type="submit">{_icon("check", "icon icon-sm")}閲嶆柊瀹℃煡</button>
          </form>
        </div>
      </section>
      <section class="panel span-12">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">Needs Review</span>
            <h2>寰呭鏍搁槦鍒?/h2>
            <p>浣庤川閲忚В鏋愩€乽nknown 鍒嗙被鎴栦綆缃俊搴︽潗鏂欎細杩涘叆璇ラ槦鍒楋紝渚涘悗缁汉宸ョ籂閿欏伐浣滄祦澶勭悊銆?/p>
          </div>
          <div class="panel-head-icon">{_icon("history", "icon icon-lg")}</div>
        </div>
        <div class="dossier-list">
          <div><span>寰呭鏍告€绘暟</span><strong>{review_queue['needs_review']}</strong></div>
          <div><span>浣庤川閲忚В鏋?/span><strong>{review_queue['low_quality']}</strong></div>
          <div><span>Unknown 鏉愭枡</span><strong>{review_queue['unknown_count']}</strong></div>
          <div><span>褰撳墠绛栫暐</span><strong>manual_triage</strong></div>
        </div>
        <p class="highlight-note">寰呭鏍歌〃鐜板湪浼氱洿鎺ュ睍绀?legacy `.doc` 鍒嗘《銆乣quality_flags` 鍜屾洿缁嗙殑澶嶆牳鍘熷洜锛屼究浜庡尯鍒嗏€滄枃鏈繃鐭?/ 鍣煶杩囧 / OLE 鍙娈典笉瓒斥€濄€?/p>
        {_table(['鏂囦欢', '绫诲瀷', '瑙ｆ瀽璐ㄩ噺', 'legacy doc 鍒嗘《', '璐ㄩ噺淇″彿', '澶嶆牳鍘熷洜', '寤鸿鍔ㄤ綔'], review_queue["rows"])}
      </section>
      <section class="panel span-12">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">Export Center</span>
            <h2>瀵煎嚭涓庢敮鎸佷腑蹇?/h2>
            <p>瀵煎嚭鎵规鍏ㄩ噺浜х墿銆佸崟浠芥姤鍛婂拰杩愯鏃ュ織锛屾柟渚挎彁浜ゅ綊妗ｃ€侀棶棰樺鐩樺拰澶栭儴娴佽浆銆?/p>
          </div>
          <div class="panel-head-icon">{_icon("report", "icon icon-lg")}</div>
        </div>
        <div class="dossier-list">
          <div><span>鎵规鎵撳寘</span><strong>bundle.zip</strong></div>
          <div><span>鎶ュ憡鏁伴噺</span><strong>{report_count}</strong></div>
          <div><span>杩愯鏃ュ織</span><strong>app.jsonl</strong></div>
          <div><span>鎸佷箙鍖栫姸鎬?/span><strong>sqlite + runtime</strong></div>
        </div>
        <div class="inline-actions">
          {_download_chip(f"/downloads/submissions/{escape_html(submission['id'])}/bundle", "涓嬭浇鎵规鍖?)}
          {_download_chip("/downloads/logs/app", "涓嬭浇杩愯鏃ュ織")}
        </div>
        {export_table}
      </section>
      <section class="panel span-12">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">Correction Audit</span>
            <h2>绾犻敊鍘嗗彶</h2>
            <p>璁板綍浜哄伐绾犻敊鐨勫姩浣滅被鍨嬨€佺洰鏍囧璞°€佹搷浣滀汉鍜屽娉紝涓哄悗缁棶棰樿拷婧笌缁忛獙澶嶇敤鎻愪緵鍩虹銆?/p>
          </div>
          <div class="panel-head-icon">{_icon("history", "icon icon-lg")}</div>
        </div>
        <div class="dossier-list">
          <div><span>绾犻敊娆℃暟</span><strong>{correction_history['count']}</strong></div>
          <div><span>瀹¤鑼冨洿</span><strong>submission</strong></div>
          <div><span>瀛樺偍鐘舵€?/span><strong>runtime</strong></div>
          <div><span>涓嬩竴闃舵</span><strong>sqlite</strong></div>
        </div>
        {_table(['鏃堕棿', '鍔ㄤ綔', '鐩爣', '鎿嶄綔浜?, '澶囨敞'], correction_history["rows"])}
      </section>
      <section class="panel span-12">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">Artifact Browser</span>
            <h2>闅愮涓庢枃鏈骇鐗?/h2>
            <p>閫愪唤鏉愭枡鏌ョ湅 raw銆乧lean銆乨esensitized銆乸rivacy manifest 鐨勪笅杞藉叆鍙ｏ紝骞剁洿鎺ラ瑙堣劚鏁忓悗鐨勬枃鏈墖娈点€?/p>
          </div>
          <div class="panel-head-icon">{_icon("file", "icon icon-lg")}</div>
        </div>
        <div class="dossier-list">
          <div><span>鍙笅杞戒骇鐗?/span><strong>{available_artifact_count}</strong></div>
          <div><span>鍙瑙堣劚鏁忔枃鏈?/span><strong>{preview_count}</strong></div>
          <div><span>闅愮娓呭崟</span><strong>{material_count} 浠?/strong></div>
          <div><span>褰撳墠妯″紡</span><strong>artifact first</strong></div>
        </div>
        {artifact_table}
      </section>
      <section class="panel span-12">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">Privacy Shield</span>
            <h2>鏈湴鑴辨晱瀹¤</h2>
            <p>鏁忔劅瀛楁宸插湪鏈湴瑙勫垯灞傝劚鏁忥紝鍘熸枃銆佹竻娲楁枃鏈€佽劚鏁忔枃鏈笌闅愮娓呭崟鍒嗙淇濆瓨銆?/p>
          </div>
          <div class="panel-head-icon">{_icon("shield", "icon icon-lg")}</div>
        </div>
        <div class="dossier-list">
          <div><span>鑴辨晱鍛戒腑鏂囦欢</span><strong>{privacy['files_with_redaction']} / {material_count}</strong></div>
          <div><span>鏇挎崲鎬绘暟</span><strong>{privacy['total_replacements']}</strong></div>
          <div><span>绛栫暐鐗堟湰</span><strong>{escape_html(privacy['policy'])}</strong></div>
          <div><span>AI 杈撳叆杈圭晫</span><strong>浠呰劚鏁忔枃鏈?/strong></div>
        </div>
        <p class="highlight-note">{escape_html(privacy['category_summary'])}</p>
        {privacy_table}
      </section>
    </section>
    """
    return _layout(
        title=f"Submission {submission['id']}",
        active_nav="submissions",
        header_tag="Submission Analytics",
        header_title=submission["filename"],
        header_subtitle="浠ヨ繍钀ュ悗鍙版柟寮忔煡鐪嬭鎵规鐨勬潗鏂欑粨鏋勩€侀」鐩仛鍚堝拰鎶ュ憡杈撳嚭銆?,
        header_meta="".join(
            [
                _pill(_mode_label(submission["mode"]), "info"),
                _pill("Local Redaction", "success"),
                _pill("SQLite Recovery", "neutral"),
                _pill(submission["status"], _status_tone(submission["status"])),
            ]
        ),
        content=content,
    )


def render_case_detail(case: dict, materials: list[dict], report: dict | None, review_result: dict | None) -> str:
    issues = (review_result or {}).get("issues_json", [])
    severity = _severity_summary(issues)
    coverage = _type_breakdown(materials)
    rule_conclusion = (review_result or {}).get("rule_conclusion") or (review_result or {}).get("conclusion", "鏆傛棤瑙勫垯缁撹")
    ai_summary = (review_result or {}).get("ai_summary") or "褰撳墠娌℃湁棰濆 AI 琛ュ厖璇存槑"
    ai_provider = (review_result or {}).get("ai_provider", "mock")
    ai_resolution = (review_result or {}).get("ai_resolution", "explicit_mock")

    issue_rows = []
    for issue in issues:
        tone = str(issue.get("severity", "minor")).lower()
        issue_rows.append(
            [
                f'<div class="table-title-cell">{_icon("risk", "icon icon-sm")}<span>{escape_html(issue.get("category", "闂"))}</span></div>',
                _pill(SEVERITY_LABELS.get(tone, "杞诲井"), "danger" if tone == "severe" else "warning" if tone == "moderate" else "info"),
                escape_html(issue.get("desc", "")),
            ]
        )

    material_rows = []
    for item in materials:
        material_rows.append(
            [
                f'<div class="table-title-cell">{_material_icon(item["material_type"])}<span>{escape_html(item["original_filename"])}</span></div>',
                _pill(_type_label(item["material_type"]), _material_tone(item["material_type"])),
                escape_html(item.get("detected_software_name") or "鏈瘑鍒?),
                escape_html(item.get("detected_version") or "鏈瘑鍒?),
            ]
        )

    coverage_block = "".join(
        _progress_row(_type_label(material_type), count, 1 if count else 1, _material_tone(material_type), "target")
        for material_type, count in coverage.items()
    )

    dossier = f"""
    <div class="dossier-list">
      <div><span>杞欢鍚嶇О</span><strong>{escape_html(case.get('software_name') or '鏈瘑鍒?)}</strong></div>
      <div><span>鐗堟湰鍙?/span><strong>{escape_html(case.get('version') or '鏈瘑鍒?)}</strong></div>
      <div><span>钁椾綔鏉冧汉</span><strong>{escape_html(case.get('company_name') or '鏈瘑鍒?)}</strong></div>
      <div><span>缁煎悎鎶ュ憡</span><strong>{'宸茬敓鎴? if report else '鏆傛棤'}</strong></div>
    </div>
    """

    report_action = (
        f'<a class="button-secondary" href="/reports/{escape_html(report["id"])}">{_icon("report", "icon icon-sm")}鏌ョ湅瀹屾暣鎶ュ憡</a>'
        if report
        else ""
    )

    content = f"""
    <section class="kpi-grid">
      {_kpi_card('鏉愭枡鏋勬垚', str(len(materials)), 'Case 鍏宠仈鏉愭枡鎬婚噺', 'file', 'info')}
      {_kpi_card('璺ㄦ潗鏂欓棶棰?, str(len(issues)), '涓€鑷存€т笌缁煎悎椋庨櫓', 'risk', 'danger' if issues else 'success')}
      {_kpi_card('涓ラ噸闂', str(severity['severe']), '闇€瑕佷紭鍏堝鐞?, 'shield', 'danger' if severity['severe'] else 'success')}
      {_kpi_card('鎶ュ憡鐘舵€?, 'Ready' if report else 'Pending', '椤圭洰缁煎悎鎶ュ憡杈撳嚭鎯呭喌', 'report', 'warning')}
    </section>
    <section class="dashboard-grid">
      <section class="panel span-7">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">Risk Queue</span>
            <h2>缁煎悎缁撹</h2>
            <p>璺ㄦ潗鏂欓棶棰樻寜鍒嗘瀽闃熷垪鏂瑰紡鍒楀嚭锛屼究浜庝紭鍏堝鐞嗗拰鍥炵湅銆?/p>
          </div>
          <div class="panel-head-icon">{_icon("risk", "icon icon-lg")}</div>
        </div>
        <p class="highlight-note">{escape_html(rule_conclusion)}</p>
        <div class="summary-grid">
          <article class="summary-tile">
            <span>AI Provider</span>
            <strong>{escape_html(ai_provider)}</strong>
            <small>{escape_html(ai_resolution)}</small>
          </article>
          <article class="summary-tile">
            <span>AI Supplement</span>
            <strong>宸插垎绂诲睍绀?/strong>
            <small>瑙勫垯缁撹鍜?AI 璇存槑涓嶅啀娣峰湪涓€璧?/small>
          </article>
        </div>
        <div class="operator-note">
          <strong>AI 琛ュ厖璇存槑</strong>
          <span>{escape_html(ai_summary)}</span>
        </div>
        {_table(['闂', '绛夌骇', '璇存槑'], issue_rows)}
      </section>
      <section class="panel span-5">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">Case Dossier</span>
            <h2>椤圭洰妗ｆ</h2>
          </div>
          <div class="panel-head-icon">{_icon("case", "icon icon-lg")}</div>
        </div>
        {dossier}
        <div class="metric-stack">
          {coverage_block or _progress_row('鏆傛棤鏉愭枡', 0, 1)}
        </div>
        {report_action}
      </section>
      <section class="panel span-12">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">Material Matrix</span>
            <h2>鏉愭枡鐭╅樀</h2>
          </div>
          <div class="panel-head-icon">{_icon("workflow", "icon icon-lg")}</div>
        </div>
        {_table(['鏂囦欢', '绫诲瀷', '璇嗗埆鍚嶇О', '璇嗗埆鐗堟湰'], material_rows)}
      </section>
    </section>
    """
    return _layout(
        title=f"Case {case['case_name']}",
        active_nav="submissions",
        header_tag="Case Analytics",
        header_title=case["case_name"],
        header_subtitle="鎸夐」鐩悗鍙拌瑙掓煡鐪嬬患鍚堢粨璁恒€佹潗鏂欑煩闃靛拰褰撳墠褰掓。鐘舵€併€?,
        header_meta="".join(
            [
                _pill(case.get("status") or "unknown", _status_tone(case.get("status") or "")),
                _pill(case.get("version") or "鏈瘑鍒増鏈?, "neutral"),
                _pill(ai_provider, "info"),
            ]
        ),
        content=content,
    )


def render_report_page(report: dict) -> str:
    content = escape_html(report.get("content", ""))
    line_count = len([line for line in report.get("content", "").splitlines() if line.strip()])
    content_length = len(report.get("content", ""))
    content = f"""
    <section class="dashboard-grid">
      <section class="panel span-4">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">Report Summary</span>
            <h2>鎶ュ憡鎽樿</h2>
          </div>
          <div class="panel-head-icon">{_icon("report", "icon icon-lg")}</div>
        </div>
        <div class="dossier-list">
          <div><span>鎶ュ憡绫诲瀷</span><strong>{escape_html(_report_label(report.get('report_type', '鎶ュ憡')))}</strong></div>
          <div><span>浣滅敤鑼冨洿</span><strong>{escape_html(report.get('scope_type', 'report'))}</strong></div>
          <div><span>鏂囦欢鏍煎紡</span><strong>{escape_html(report.get('file_format', 'md').upper())}</strong></div>
          <div><span>闈炵┖琛屾暟</span><strong>{line_count}</strong></div>
          <div><span>瀛楃鏁?/span><strong>{content_length}</strong></div>
        </div>
      </section>
      <section class="panel span-8 report-panel">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">Report Reader</span>
            <h2>鎶ュ憡姝ｆ枃</h2>
          </div>
          <div class="panel-head-icon">{_icon("file", "icon icon-lg")}</div>
        </div>
        <div class="report-toolbar">
          {_pill(report.get('scope_type', 'report'), 'info')}
          {_pill('Local Redaction', 'success')}
          {_pill(report.get('file_format', 'md').upper(), 'neutral')}
          {_download_chip(f"/downloads/reports/{escape_html(report['id'])}", "涓嬭浇鎶ュ憡")}
        </div>
        <pre>{content}</pre>
      </section>
    </section>
    """
    return _layout(
        title="鎶ュ憡",
        active_nav="submissions",
        header_tag="Report Reader",
        header_title=_report_label(report.get("report_type", "鎶ュ憡")),
        header_subtitle="鐢ㄥ悗鍙伴槄璇诲櫒瑙嗗浘鏌ョ湅鎶ュ憡姝ｆ枃锛岃€屼笉鏄櫘閫氶〉闈㈠紡灞曠ず銆?,
        header_meta=_pill(report.get("scope_type", "report"), "info"),
        content=content,
    )


def _render_ops_page_legacy(config: dict, self_check: dict) -> str:
    snapshot = _runtime_snapshot()
    provider_readiness = self_check.get("provider_readiness", {})
    backup_status = latest_runtime_backup_status()
    baseline_status = latest_metrics_baseline_status()
    check_rows = [
        [
            escape_html(item.get("label", item.get("name", "check"))),
            _pill(str(item.get("status", "unknown")), _self_check_tone(str(item.get("status", "unknown")))),
            escape_html(item.get("path", "")),
            escape_html(item.get("detail", "")),
        ]
        for item in self_check.get("checks", [])
    ]
    config_rows = [
        [escape_html("host"), escape_html(str(config.get("host", "")))],
        [escape_html("port"), escape_html(str(config.get("port", "")))],
        [escape_html("data_root"), escape_html(str(config.get("data_root", "")))],
        [escape_html("sqlite_path"), escape_html(str(config.get("sqlite_path", "")))],
        [escape_html("log_path"), escape_html(str(config.get("log_path", "")))],
        [escape_html("ai_provider"), escape_html(str(config.get("ai_provider", "")))],
        [escape_html("ai_enabled"), escape_html(str(config.get("ai_enabled", "")))],
        [escape_html("ai_timeout_seconds"), escape_html(str(config.get("ai_timeout_seconds", "")))],
        [escape_html("ai_endpoint"), escape_html(str(config.get("ai_endpoint", "")))],
        [escape_html("ai_model"), escape_html(str(config.get("ai_model", "")))],
        [escape_html("ai_api_key_env"), escape_html(str(config.get("ai_api_key_env", "")))],
        [escape_html("ai_require_desensitized"), escape_html(str(config.get("ai_require_desensitized", "")))],
        [escape_html("ai_fallback_to_mock"), escape_html(str(config.get("ai_fallback_to_mock", "")))],
        [escape_html("retention_days"), escape_html(str(config.get("retention_days", "")))],
    ]
    provider_rows = [
        ("Provider", str(provider_readiness.get("provider", config.get("ai_provider", "mock")) or "mock")),
        ("Endpoint", str(provider_readiness.get("endpoint", "") or "not configured")),
        ("Model", str(provider_readiness.get("model", "") or "not configured")),
        (
            "API Key",
            str(provider_readiness.get("api_key_env", "") or "not configured")
            if provider_readiness.get("api_key_present")
            else (f"{provider_readiness.get('api_key_env', '')} (missing)" if provider_readiness.get("api_key_env") else "optional / not configured"),
        ),
        ("Boundary", "desensitized only" if config.get("ai_require_desensitized", True) else "boundary disabled"),
    ]
    backup_rows = [
        ("Archive", str(backup_status.get("file_name", "") or "not created")),
        ("Size", str(backup_status.get("size_label", "0 B"))),
        ("Entries", str(backup_status.get("entry_count", 0))),
        ("Created", str(backup_status.get("created_at", "") or backup_status.get("updated_at", "") or "n/a")),
        ("SQLite", str(backup_status.get("sqlite_snapshot_mode", "") or "n/a")),
    ]
    baseline_totals = baseline_status.get("totals", {})
    baseline_rows = [
        ("Artifact", str(baseline_status.get("file_name", "") or "not generated")),
        ("Targets", str(baseline_status.get("target_count", 0))),
        ("Needs Review", str(baseline_totals.get("needs_review", 0))),
        ("Low Quality", str(baseline_totals.get("low_quality", 0))),
        ("Redactions", str(baseline_totals.get("redactions", 0))),
    ]
    baseline_badges = []
    for target in baseline_status.get("targets", [])[:3]:
        aggregate = target.get("aggregate", {})
        baseline_badges.append(
            _pill(
                f"{target.get('label', 'target')} N{aggregate.get('needs_review', 0)} / L{aggregate.get('low_quality', 0)}",
                "info",
            )
        )
    content = f"""
    <section class="kpi-grid">
      {_kpi_card('鑷鐘舵€?, self_check.get('status', 'unknown').upper(), '鍚姩闃舵杩愯鐜妫€鏌?, 'server', _self_check_tone(self_check.get('status', 'unknown')))}
      {_kpi_card('杩愯鎵规', str(snapshot['submission_count']), '褰撳墠 runtime store 涓殑 submission 鏁伴噺', 'submissions', 'info')}
      {_kpi_card('寰呭鏍?, str(snapshot['needs_review_count']), '浠嶉渶浜哄伐澶勭悊鐨勬潗鏂?, 'history', 'warning' if snapshot['needs_review_count'] else 'success')}
      {_kpi_card('鑴辨晱鏇挎崲', str(snapshot['redaction_total']), '宸插懡涓殑鏈湴鑴辨晱鏇挎崲鏁?, 'shield', 'success')}
    </section>
    <section class="ops-status-grid">
      {_ops_status_card(
          'Provider Readiness',
          str(provider_readiness.get('provider', config.get('ai_provider', 'mock')) or 'mock').upper(),
          str(provider_readiness.get('summary', 'No provider readiness summary available.')),
          'server',
          _self_check_tone(str(provider_readiness.get('status', 'unknown'))),
          provider_rows,
          [
              _pill(str(provider_readiness.get('status', 'unknown')), _self_check_tone(str(provider_readiness.get('status', 'unknown')))),
              _pill('desensitized boundary', 'success' if config.get('ai_require_desensitized', True) else 'warning'),
          ],
      )}
      {_ops_status_card(
          'Latest Backup',
          str(backup_status.get('file_name', '') or 'No Backup Yet'),
          str(backup_status.get('summary', 'Run runtime_backup create to generate the first archive.')),
          'history',
          _self_check_tone(str(backup_status.get('status', 'warning'))),
          backup_rows,
          [
              _pill(str(backup_status.get('status', 'warning')), _self_check_tone(str(backup_status.get('status', 'warning')))),
              _pill(str(backup_status.get('size_label', '0 B')), 'info'),
          ],
      )}
      {_ops_status_card(
          'Latest Baseline',
          str(baseline_status.get('file_name', '') or 'No Baseline Yet'),
          str(baseline_status.get('summary', 'Run metrics_baseline to capture a real-sample trend snapshot.')),
          'trend',
          _self_check_tone(str(baseline_status.get('status', 'warning'))),
          baseline_rows,
          [_pill(str(baseline_status.get('status', 'warning')), _self_check_tone(str(baseline_status.get('status', 'warning'))))] + baseline_badges,
      )}
    </section>
    <section class="dashboard-grid">
      <section class="panel span-7">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">Startup Self Check</span>
            <h2>鍚姩鑷</h2>
            <p>瑕嗙洊杩愯鐩綍銆佷笂浼犵洰褰曘€丼QLite 鐩綍銆佹棩蹇楃洰褰曚笌閰嶇疆妯℃澘銆傝繖閲屽睍绀虹殑鏄〉闈㈣闂椂閲嶆柊璇诲彇鐨勬渶鏂扮粨鏋溿€?/p>
          </div>
          <div class="panel-head-icon">{_icon("server", "icon icon-lg")}</div>
        </div>
        {_table(['妫€鏌ラ」', '鐘舵€?, '璺緞', '璇存槑'], check_rows)}
      </section>
      <section class="panel span-5">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">Support Actions</span>
            <h2>鏀寔鍏ュ彛</h2>
            <p>鎶婃渶甯哥敤鐨勬帓鏌ュ姩浣滅洿鎺ユ斁杩涗竴涓繍缁撮〉锛岄檷浣庘€滅煡閬撻棶棰樹絾涓嶇煡閬撳幓鍝噷鐪嬧€濈殑鎽╂摝銆?/p>
          </div>
          <div class="panel-head-icon">{_icon("history", "icon icon-lg")}</div>
        </div>
        <div class="dossier-list">
          <div><span>鏃ュ織涓嬭浇</span><strong><a class="table-link" href="/downloads/logs/app">app.jsonl</a></strong></div>
          <div><span>閰嶇疆妯℃澘</span><strong>{escape_html(self_check.get('paths', {}).get('config_template_path', 'config/local.example.json'))}</strong></div>
          <div><span>淇濈暀绛栫暐</span><strong>{escape_html(str(self_check.get('retention_days', config.get('retention_days', 14))))} 澶?/strong></div>
          <div><span>AI 杈圭晫</span><strong>浠呰劚鏁?payload</strong></div>
        </div>
        <div class="command-list">
          <div class="command-block"><strong>妯″紡 A 鐑熸祴</strong><code>py -m app.tools.input_runner --path input\\杞憲鏉愭枡 --mode single_case_package</code></div>
          <div class="command-block"><strong>妯″紡 B 鐑熸祴</strong><code>py -m app.tools.input_runner --path input\\鍚堜綔鍗忚 --mode batch_same_material</code></div>
          <div class="command-block"><strong>Runtime Cleanup</strong><code>py -m app.tools.runtime_cleanup</code></div>
          <div class="command-block"><strong>Runtime Backup</strong><code>py -m app.tools.runtime_backup create</code></div>
          <div class="command-block"><strong>Provider Sandbox</strong><code>py -m app.tools.provider_sandbox --port 8010</code></div>
          <div class="command-block"><strong>Provider Probe</strong><code>py -m app.tools.provider_probe --provider external_http --endpoint http://127.0.0.1:8010/review --model sandbox-model --probe</code></div>
          <div class="command-block"><strong>Metrics Baseline</strong><code>py -m app.tools.metrics_baseline --markdown-path docs\\dev\\54-real-sample-baseline.md --json-path docs\\dev\\55-real-sample-baseline.json</code></div>
          <div class="command-block"><strong>Baseline Compare</strong><code>py -m app.tools.metrics_baseline --compare docs\\dev\\55-real-sample-baseline.json --markdown-path docs\\dev\\56-real-sample-baseline-compare.md --json-path docs\\dev\\57-real-sample-baseline-compare.json</code></div>
          <div class="command-block"><strong>鍚姩 Web</strong><code>py -m app.api.main</code></div>
        </div>
      </section>
      <section class="panel span-6">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">Active Config</span>
            <h2>褰撳墠閰嶇疆</h2>
          </div>
          <div class="panel-head-icon">{_icon("filter", "icon icon-lg")}</div>
        </div>
        {_table(['閰嶇疆椤?, '鍊?], config_rows)}
      </section>
      <section class="panel span-6">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">Retention Policy</span>
            <h2>杩愯鏃朵繚鐣欑瓥鐣?/h2>
            <p>褰撳墠绯荤粺鎶婂師鏂囥€乧lean銆乨esensitized銆乸rivacy manifest 鍒嗗紑淇濆瓨鍦?`data/runtime/`锛屼究浜庤拷婧紝浣嗕篃蹇呴』鏄惧紡绠＄悊淇濈暀鍛ㄦ湡銆?/p>
          </div>
          <div class="panel-head-icon">{_icon("shield", "icon icon-lg")}</div>
        </div>
        <div class="dossier-list">
          <div><span>鏁版嵁鏍圭洰褰?/span><strong>{escape_html(self_check.get('paths', {}).get('data_root', config.get('data_root', 'data/runtime')))}</strong></div>
          <div><span>SQLite</span><strong>{escape_html(self_check.get('paths', {}).get('sqlite_path', config.get('sqlite_path', 'data/runtime/soft_review.db')))}</strong></div>
          <div><span>鏃ュ織</span><strong>{escape_html(self_check.get('paths', {}).get('log_path', config.get('log_path', 'data/runtime/logs/app.jsonl')))}</strong></div>
          <div><span>寤鸿鑺傚</span><strong>姣忓畬鎴愬涓樁娈靛悗鍋氬洖褰掑苟褰掓。</strong></div>
        </div>
        <p class="highlight-note">寤鸿鑷冲皯鎸夆€滆嚜鍔ㄥ洖褰掗€氳繃 + 鐪熷疄鏍锋湰鐑熸祴閫氳繃 + 鏂囨。钀界洏瀹屾垚鈥濅笁涓潯浠跺啀鎺ㄨ繘鍒颁笅涓€闃舵锛岄伩鍏嶉棶棰樺湪澶氫釜闃舵閲屽彔鍔犮€?/p>
      </section>
    </section>
    """
    return _layout(
        title="Support / Ops",
        active_nav="ops",
        header_tag="Support / Ops",
        header_title="杩愮淮涓庢敮鎸佷腑蹇?,
        header_subtitle="闆嗕腑鏌ョ湅鍚姩鑷銆侀厤缃€佹棩蹇楀叆鍙ｅ拰杩愯鏃朵繚鐣欑瓥鐣ャ€?,
        header_meta="".join(
            [
                _pill(self_check.get("status", "unknown"), _self_check_tone(self_check.get("status", "unknown"))),
                _pill("Local Redaction", "success"),
                _pill(str(config.get("ai_provider", "mock")), "info"),
            ]
        ),
        content=content,
    )


def _render_ops_page_round6_legacy(config: dict, self_check: dict) -> str:
    snapshot = _runtime_snapshot()
    provider_readiness = self_check.get("provider_readiness", {})
    backup_status = latest_runtime_backup_status()
    baseline_status = latest_metrics_baseline_status()
    baseline_history = list_metrics_baseline_history(limit=5)
    provider_check_counts = Counter(str(item.get("status", "unknown")) for item in provider_readiness.get("checks", []))

    check_rows = [
        [
            escape_html(item.get("label", item.get("name", "check"))),
            _pill(str(item.get("status", "unknown")), _self_check_tone(str(item.get("status", "unknown")))),
            escape_html(item.get("path", "")),
            escape_html(item.get("detail", "")),
        ]
        for item in self_check.get("checks", [])
    ]
    config_rows = [
        [escape_html("host"), escape_html(str(config.get("host", "")))],
        [escape_html("port"), escape_html(str(config.get("port", "")))],
        [escape_html("data_root"), escape_html(str(config.get("data_root", "")))],
        [escape_html("sqlite_path"), escape_html(str(config.get("sqlite_path", "")))],
        [escape_html("log_path"), escape_html(str(config.get("log_path", "")))],
        [escape_html("ai_provider"), escape_html(str(config.get("ai_provider", "")))],
        [escape_html("ai_enabled"), escape_html(str(config.get("ai_enabled", "")))],
        [escape_html("ai_timeout_seconds"), escape_html(str(config.get("ai_timeout_seconds", "")))],
        [escape_html("ai_endpoint"), escape_html(str(config.get("ai_endpoint", "")))],
        [escape_html("ai_model"), escape_html(str(config.get("ai_model", "")))],
        [escape_html("ai_api_key_env"), escape_html(str(config.get("ai_api_key_env", "")))],
        [escape_html("ai_require_desensitized"), escape_html(str(config.get("ai_require_desensitized", "")))],
        [escape_html("ai_fallback_to_mock"), escape_html(str(config.get("ai_fallback_to_mock", "")))],
        [escape_html("retention_days"), escape_html(str(config.get("retention_days", "")))],
    ]
    provider_check_rows = [
        [
            escape_html(item.get("label", item.get("name", "check"))),
            _pill(str(item.get("status", "unknown")), _self_check_tone(str(item.get("status", "unknown")))),
            escape_html(str(item.get("value", "") or "-")),
            escape_html(item.get("detail", "")),
        ]
        for item in provider_readiness.get("checks", [])
    ]
    provider_rows = [
        ("Provider", str(provider_readiness.get("provider", config.get("ai_provider", "mock")) or "mock")),
        ("Endpoint", str(provider_readiness.get("endpoint", "") or "not configured")),
        ("Model", str(provider_readiness.get("model", "") or "not configured")),
        (
            "API Key",
            str(provider_readiness.get("api_key_env", "") or "not configured")
            if provider_readiness.get("api_key_present")
            else (
                f"{provider_readiness.get('api_key_env', '')} (missing)"
                if provider_readiness.get("api_key_env")
                else "optional / not configured"
            ),
        ),
        ("Boundary", "desensitized only" if config.get("ai_require_desensitized", True) else "boundary disabled"),
    ]
    backup_rows = [
        ("Archive", str(backup_status.get("file_name", "") or "not created")),
        ("Size", str(backup_status.get("size_label", "0 B"))),
        ("Entries", str(backup_status.get("entry_count", 0))),
        ("Created", str(backup_status.get("created_at", "") or backup_status.get("updated_at", "") or "n/a")),
        ("SQLite", str(backup_status.get("sqlite_snapshot_mode", "") or "n/a")),
    ]

    baseline_totals = baseline_status.get("totals", {})
    baseline_deltas = baseline_status.get("delta_totals", {})
    baseline_rows = [
        ("Artifact", str(baseline_status.get("file_name", "") or "not generated")),
        ("Generated", str(baseline_status.get("generated_at", "") or baseline_status.get("updated_at", "") or "n/a")),
        ("Targets", str(baseline_status.get("target_count", 0))),
        ("Needs Review", str(baseline_totals.get("needs_review", 0))),
        ("Low Quality", str(baseline_totals.get("low_quality", 0))),
        ("Redactions", str(baseline_totals.get("redactions", 0))),
    ]
    baseline_badges = [
        _pill(str(baseline_status.get("status", "warning")), _self_check_tone(str(baseline_status.get("status", "warning")))),
        _pill(
            "comparison ready" if baseline_status.get("comparison_available") else "no compare",
            "info" if baseline_status.get("comparison_available") else "neutral",
        ),
        _delta_pill("Review 螖", baseline_deltas.get("needs_review")),
        _delta_pill("Quality 螖", baseline_deltas.get("low_quality")),
        _delta_pill("Redactions 螖", baseline_deltas.get("redactions")),
    ]
    for target in baseline_status.get("targets", [])[:3]:
        aggregate = target.get("aggregate", {})
        baseline_badges.append(
            _pill(
                f"{target.get('label', 'target')} N{aggregate.get('needs_review', 0)} / L{aggregate.get('low_quality', 0)}",
                "info",
            )
        )

    baseline_history_rows = []
    for item in baseline_history:
        delta_badges = "".join(
            [
                _delta_pill("Review 螖", item.get("delta_totals", {}).get("needs_review")),
                _delta_pill("Quality 螖", item.get("delta_totals", {}).get("low_quality")),
                _delta_pill("Redactions 螖", item.get("delta_totals", {}).get("redactions")),
            ]
        )
        baseline_history_rows.append(
            [
                escape_html(item.get("file_name", "-")),
                _pill(str(item.get("status", "unknown")), _self_check_tone(str(item.get("status", "unknown")))),
                escape_html(str(item.get("generated_at", "") or item.get("updated_at", "") or "n/a")),
                escape_html(str(item.get("target_count", 0))),
                escape_html(str(item.get("totals", {}).get("needs_review", 0))),
                escape_html(str(item.get("totals", {}).get("low_quality", 0))),
                delta_badges,
            ]
        )

    content = f"""
    <section class="kpi-grid">
      {_kpi_card('Release Gate', release_gate_status.upper(), str(release_gate.get('summary', 'Release gate status is unavailable.')), 'target', _gate_tone(release_gate_status))}
      {_kpi_card('Self Check', self_check.get('status', 'unknown').upper(), 'Startup environment and writable-path validation.', 'server', _self_check_tone(self_check.get('status', 'unknown')))}
      {_kpi_card('Needs Review', str(snapshot['needs_review_count']), 'Materials still waiting for manual review or correction.', 'history', 'warning' if snapshot['needs_review_count'] else 'success')}
      {_kpi_card('Redactions', str(snapshot['redaction_total']), 'Local desensitization replacements completed before any AI boundary.', 'shield', 'success')}
    </section>
    <section class="ops-status-grid">
      {_ops_status_card(
          'Provider Readiness',
          str(provider_readiness.get('provider', config.get('ai_provider', 'mock')) or 'mock').upper(),
          str(provider_readiness.get('summary', 'No provider readiness summary available.')),
          'server',
          _self_check_tone(str(provider_readiness.get('status', 'unknown'))),
          provider_rows,
          [
              _pill(str(provider_readiness.get('status', 'unknown')), _self_check_tone(str(provider_readiness.get('status', 'unknown')))),
              _pill('desensitized boundary', 'success' if config.get('ai_require_desensitized', True) else 'warning'),
          ],
      )}
      {_ops_status_card(
          'Latest Backup',
          str(backup_status.get('file_name', '') or 'No Backup Yet'),
          str(backup_status.get('summary', 'Run runtime_backup create to generate the first archive.')),
          'history',
          _self_check_tone(str(backup_status.get('status', 'warning'))),
          backup_rows,
          [
              _pill(str(backup_status.get('status', 'warning')), _self_check_tone(str(backup_status.get('status', 'warning')))),
              _pill(str(backup_status.get('size_label', '0 B')), 'info'),
          ],
      )}
      {_ops_status_card(
          'Latest Baseline',
          str(baseline_status.get('file_name', '') or 'No Baseline Yet'),
          str(baseline_status.get('summary', 'Run metrics_baseline to capture a real-sample trend snapshot.')),
          'trend',
          _self_check_tone(str(baseline_status.get('status', 'warning'))),
          baseline_rows,
          baseline_badges,
      )}
    </section>
    <section class="dashboard-grid">
      <section class="panel span-7">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">Startup Self Check</span>
            <h2>Startup Environment Checks</h2>
            <p>Re-check writable runtime directories, SQLite parent, log path, config template, and the privacy boundary on every page load.</p>
          </div>
          <div class="panel-head-icon">{_icon("server", "icon icon-lg")}</div>
        </div>
        {_table(['Check', 'Status', 'Path', 'Detail'], check_rows)}
      </section>
      <section class="panel span-5">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">Support Actions</span>
            <h2>Operator Commands</h2>
            <p>Keep the most common smoke, backup, probe, release-gate, and baseline actions visible in one place for faster triage.</p>
          </div>
          <div class="panel-head-icon">{_icon("history", "icon icon-lg")}</div>
        </div>
        <div class="dossier-list">
          <div><span>Log Download</span><strong><a class="table-link" href="/downloads/logs/app">app.jsonl</a></strong></div>
          <div><span>Config Template</span><strong>{escape_html(self_check.get('paths', {}).get('config_template_path', 'config/local.example.json'))}</strong></div>
          <div><span>Retention</span><strong>{escape_html(str(self_check.get('retention_days', config.get('retention_days', 14))))} days</strong></div>
          <div><span>AI Boundary</span><strong>desensitized payload only</strong></div>
        </div>
        <div class="command-list">
          <div class="command-block"><strong>Mode A Smoke</strong><code>py -m app.tools.input_runner --path input\\杞憲鏉愭枡 --mode single_case_package</code></div>
          <div class="command-block"><strong>Mode B Smoke</strong><code>py -m app.tools.input_runner --path input\\鍚堜綔鍗忚 --mode batch_same_material</code></div>
          <div class="command-block"><strong>Runtime Cleanup</strong><code>py -m app.tools.runtime_cleanup</code></div>
          <div class="command-block"><strong>Runtime Backup</strong><code>py -m app.tools.runtime_backup create</code></div>
          <div class="command-block"><strong>Provider Sandbox</strong><code>py -m app.tools.provider_sandbox --port 8010</code></div>
          <div class="command-block"><strong>Provider Probe</strong><code>py -m app.tools.provider_probe --provider external_http --endpoint http://127.0.0.1:8010/review --model sandbox-model --probe</code></div>
          <div class="command-block"><strong>Metrics Baseline</strong><code>py -m app.tools.metrics_baseline --markdown-path docs\\dev\\54-real-sample-baseline.md --json-path docs\\dev\\55-real-sample-baseline.json</code></div>
          <div class="command-block"><strong>Baseline Compare</strong><code>py -m app.tools.metrics_baseline --compare docs\\dev\\55-real-sample-baseline.json --markdown-path docs\\dev\\56-real-sample-baseline-compare.md --json-path docs\\dev\\57-real-sample-baseline-compare.json</code></div>
          <div class="command-block"><strong>Rolling Baseline</strong><code>py -m app.tools.metrics_baseline --compare-latest-in-dir docs\\dev --archive-dir docs\\dev\\history --archive-stem real-sample-baseline</code></div>
          <div class="command-block"><strong>Start Web</strong><code>py -m app.api.main</code></div>
        </div>
      </section>
      <section class="panel span-7">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">Trend Watch</span>
            <h2>Baseline History</h2>
            <p>Track the latest sample baseline, compare against the previous snapshot automatically, and keep a rolling archive for regression visibility.</p>
          </div>
          <div class="panel-head-icon">{_icon("trend", "icon icon-lg")}</div>
        </div>
        <div class="summary-grid">
          <article class="summary-tile">
            <span>Latest Snapshot</span>
            <strong>{escape_html(str(baseline_status.get('generated_at', '') or baseline_status.get('updated_at', '') or 'n/a'))}</strong>
            <small>Latest baseline generation time.</small>
          </article>
          <article class="summary-tile">
            <span>History Depth</span>
            <strong>{len(baseline_history)}</strong>
            <small>Visible baseline artifacts scanned from docs/dev.</small>
          </article>
          <article class="summary-tile">
            <span>Needs Review 螖</span>
            <strong>{escape_html(format_signed_delta(baseline_deltas.get('needs_review')))}</strong>
            <small>Signed change versus the previous baseline snapshot.</small>
          </article>
          <article class="summary-tile">
            <span>Low Quality 螖</span>
            <strong>{escape_html(format_signed_delta(baseline_deltas.get('low_quality')))}</strong>
            <small>Keep this trending downward before the next release slice.</small>
          </article>
        </div>
        <p class="highlight-note">Rolling Baseline writes timestamped JSON and Markdown artifacts into <code>docs/dev/history</code> while auto-comparing with the newest baseline under <code>docs/dev</code>.</p>
        {_table(['Artifact', 'Status', 'Generated', 'Targets', 'Needs Review', 'Low Quality', 'Delta'], baseline_history_rows)}
      </section>
      <section class="panel span-5">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">Provider Checklist</span>
            <h2>External Provider Gate</h2>
            <p>Keep the provider boundary explicit so only desensitized payloads can cross the non-mock edge when the local config is ready.</p>
          </div>
          <div class="panel-head-icon">{_icon("check", "icon icon-lg")}</div>
        </div>
        <div class="dossier-list">
          <div><span>Ready Status</span><strong>{escape_html(str(provider_readiness.get('status', 'unknown')).upper())}</strong></div>
          <div><span>Checks OK</span><strong>{provider_check_counts.get('ok', 0)}</strong></div>
          <div><span>Warnings</span><strong>{provider_check_counts.get('warning', 0)}</strong></div>
          <div><span>Failures</span><strong>{provider_check_counts.get('failed', 0)}</strong></div>
        </div>
        {_table(['Check', 'Status', 'Value', 'Detail'], provider_check_rows)}
      </section>
      <section class="panel span-6">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">Active Config</span>
            <h2>Runtime Config</h2>
          </div>
          <div class="panel-head-icon">{_icon("filter", "icon icon-lg")}</div>
        </div>
        {_table(['Config', 'Value'], config_rows)}
      </section>
      <section class="panel span-6">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">Retention Policy</span>
            <h2>Runtime Retention</h2>
            <p>The system keeps original, clean, desensitized, and privacy-manifest artifacts separated under <code>data/runtime</code> so traceability stays intact without weakening the privacy boundary.</p>
          </div>
          <div class="panel-head-icon">{_icon("shield", "icon icon-lg")}</div>
        </div>
        <div class="dossier-list">
          <div><span>Data Root</span><strong>{escape_html(self_check.get('paths', {}).get('data_root', config.get('data_root', 'data/runtime')))}</strong></div>
          <div><span>SQLite</span><strong>{escape_html(self_check.get('paths', {}).get('sqlite_path', config.get('sqlite_path', 'data/runtime/soft_review.db')))}</strong></div>
          <div><span>Logs</span><strong>{escape_html(self_check.get('paths', {}).get('log_path', config.get('log_path', 'data/runtime/logs/app.jsonl')))}</strong></div>
          <div><span>Suggested Cadence</span><strong>Run regression after each completed slice before moving on.</strong></div>
        </div>
        <p class="highlight-note">Promote the next phase only after automated regression passes, real-sample smoke passes, and the <code>docs/dev</code> artifacts for that slice are written completely.</p>
      </section>
    </section>
    """
    return _layout(
        title="Support / Ops",
        active_nav="ops",
        header_tag="Support / Ops",
        header_title="Operations Console",
        header_subtitle="Centralize self-checks, provider readiness, rolling baseline history, support commands, and retention controls in one admin view.",
        header_meta="".join(
            [
                _pill(self_check.get("status", "unknown"), _self_check_tone(self_check.get("status", "unknown"))),
                _pill("Local Redaction", "success"),
                _pill(str(config.get("ai_provider", "mock")), "info"),
            ]
        ),
        content=content,
    )


def render_ops_page(config: dict, self_check: dict) -> str:
    snapshot = _runtime_snapshot()
    provider_readiness = self_check.get("provider_readiness", {})
    provider_probe_status = self_check.get("provider_probe_status", {})
    provider_probe_history = self_check.get("provider_probe_history", [])
    provider_probe_last_success = self_check.get("provider_probe_last_success", {})
    provider_probe_last_failure = self_check.get("provider_probe_last_failure", {})
    release_gate = self_check.get("release_gate", {})
    local_config = self_check.get("local_config", {})
    backup_status = latest_runtime_backup_status()
    baseline_status = latest_metrics_baseline_status()
    baseline_history = list_metrics_baseline_history(limit=5)

    provider_check_items = list(provider_readiness.get("checks", [])) + [
        {
            "name": "local_config",
            "label": "Local Config",
            "status": local_config.get("status", "warning"),
            "detail": local_config.get("detail", "local config status is unavailable"),
            "value": local_config.get("path", ""),
        },
        {
            "name": "latest_probe_artifact",
            "label": "Latest Probe Artifact",
            "status": provider_probe_status.get("status", "warning"),
            "detail": provider_probe_status.get("summary", "latest provider probe status is unavailable"),
            "value": provider_probe_status.get("file_name", "") or "not recorded",
        },
    ]
    provider_check_counts = Counter(str(item.get("status", "unknown")) for item in provider_check_items)
    probe_state = str(provider_probe_status.get("probe_status", "not_run") or "not_run")
    probe_state_tone = (
        "success"
        if probe_state == "ok"
        else "danger"
        if probe_state == "failed"
        else "warning"
        if probe_state == "skipped"
        else "neutral"
    )
    release_gate_status = str(release_gate.get("status", "warning") or "warning")
    latest_success_value = str(provider_probe_last_success.get("generated_at", "") or provider_probe_last_success.get("file_name", "") or "not recorded")
    latest_failure_value = str(
        provider_probe_last_failure.get("error_code", "")
        or provider_probe_last_failure.get("generated_at", "")
        or provider_probe_last_failure.get("file_name", "")
        or "none recorded"
    )

    check_rows = [
        [
            escape_html(item.get("label", item.get("name", "check"))),
            _pill(str(item.get("status", "unknown")), _self_check_tone(str(item.get("status", "unknown")))),
            escape_html(item.get("path", "")),
            escape_html(item.get("detail", "")),
        ]
        for item in self_check.get("checks", [])
    ]
    config_rows = [
        [escape_html("host"), escape_html(str(config.get("host", "")))],
        [escape_html("port"), escape_html(str(config.get("port", "")))],
        [escape_html("data_root"), escape_html(str(config.get("data_root", "")))],
        [escape_html("sqlite_path"), escape_html(str(config.get("sqlite_path", "")))],
        [escape_html("log_path"), escape_html(str(config.get("log_path", "")))],
        [escape_html("ai_provider"), escape_html(str(config.get("ai_provider", "")))],
        [escape_html("ai_enabled"), escape_html(str(config.get("ai_enabled", "")))],
        [escape_html("ai_timeout_seconds"), escape_html(str(config.get("ai_timeout_seconds", "")))],
        [escape_html("ai_endpoint"), escape_html(str(config.get("ai_endpoint", "")))],
        [escape_html("ai_model"), escape_html(str(config.get("ai_model", "")))],
        [escape_html("ai_api_key_env"), escape_html(str(config.get("ai_api_key_env", "")))],
        [escape_html("ai_require_desensitized"), escape_html(str(config.get("ai_require_desensitized", "")))],
        [escape_html("ai_fallback_to_mock"), escape_html(str(config.get("ai_fallback_to_mock", "")))],
        [escape_html("retention_days"), escape_html(str(config.get("retention_days", "")))],
        [escape_html("config_local_path"), escape_html(str(self_check.get("paths", {}).get("config_local_path", "config/local.json")))],
    ]
    provider_check_rows = [
        [
            escape_html(item.get("label", item.get("name", "check"))),
            _pill(str(item.get("status", "unknown")), _self_check_tone(str(item.get("status", "unknown")))),
            escape_html(str(item.get("value", "") or "-")),
            escape_html(item.get("detail", "")),
        ]
        for item in provider_check_items
    ]
    provider_rows = [
        ("Provider", str(provider_readiness.get("provider", config.get("ai_provider", "mock")) or "mock")),
        ("Phase", str(provider_readiness.get("phase", "not_configured")).replace("_", " ")),
        ("Endpoint", str(provider_readiness.get("endpoint", "") or "not configured")),
        ("Model", str(provider_readiness.get("model", "") or "not configured")),
        (
            "API Key",
            str(provider_readiness.get("api_key_env", "") or "not configured")
            if provider_readiness.get("api_key_present")
            else (
                f"{provider_readiness.get('api_key_env', '')} (missing)"
                if provider_readiness.get("api_key_env")
                else "optional / not configured"
            ),
        ),
        ("Boundary", "desensitized only" if config.get("ai_require_desensitized", True) else "boundary disabled"),
    ]
    probe_rows = [
        ("Probe", probe_state),
        ("Generated", str(provider_probe_status.get("generated_at", "") or "not recorded")),
        ("Endpoint", str(provider_probe_status.get("endpoint", "") or provider_readiness.get("endpoint", "") or "not configured")),
        ("HTTP", str(provider_probe_status.get("http_status", 0) or "n/a") if provider_probe_status.get("attempted") else "n/a"),
        ("Error", str(provider_probe_status.get("error_code", "") or "none")),
    ]
    if str(provider_probe_status.get("provider_request_id", "")).strip():
        probe_rows.append(("Request ID", str(provider_probe_status.get("provider_request_id", ""))))
    backup_rows = [
        ("Archive", str(backup_status.get("file_name", "") or "not created")),
        ("Size", str(backup_status.get("size_label", "0 B"))),
        ("Entries", str(backup_status.get("entry_count", 0))),
        ("Created", str(backup_status.get("created_at", "") or backup_status.get("updated_at", "") or "n/a")),
        ("SQLite", str(backup_status.get("sqlite_snapshot_mode", "") or "n/a")),
    ]

    baseline_totals = baseline_status.get("totals", {})
    baseline_deltas = baseline_status.get("delta_totals", {})
    baseline_rows = [
        ("Artifact", str(baseline_status.get("file_name", "") or "not generated")),
        ("Generated", str(baseline_status.get("generated_at", "") or baseline_status.get("updated_at", "") or "n/a")),
        ("Targets", str(baseline_status.get("target_count", 0))),
        ("Needs Review", str(baseline_totals.get("needs_review", 0))),
        ("Low Quality", str(baseline_totals.get("low_quality", 0))),
        ("Redactions", str(baseline_totals.get("redactions", 0))),
    ]
    baseline_badges = [
        _pill(str(baseline_status.get("status", "warning")), _self_check_tone(str(baseline_status.get("status", "warning")))),
        _pill(
            "comparison ready" if baseline_status.get("comparison_available") else "no compare",
            "info" if baseline_status.get("comparison_available") else "neutral",
        ),
        _delta_pill("Review Delta", baseline_deltas.get("needs_review")),
        _delta_pill("Quality Delta", baseline_deltas.get("low_quality")),
        _delta_pill("Redactions Delta", baseline_deltas.get("redactions")),
    ]
    for target in baseline_status.get("targets", [])[:3]:
        aggregate = target.get("aggregate", {})
        baseline_badges.append(
            _pill(
                f"{target.get('label', 'target')} N{aggregate.get('needs_review', 0)} / L{aggregate.get('low_quality', 0)}",
                "info",
            )
        )

    baseline_history_rows = []
    for item in baseline_history:
        delta_badges = "".join(
            [
                _delta_pill("Review Delta", item.get("delta_totals", {}).get("needs_review")),
                _delta_pill("Quality Delta", item.get("delta_totals", {}).get("low_quality")),
                _delta_pill("Redactions Delta", item.get("delta_totals", {}).get("redactions")),
            ]
        )
        baseline_history_rows.append(
            [
                escape_html(item.get("file_name", "-")),
                _pill(str(item.get("status", "unknown")), _self_check_tone(str(item.get("status", "unknown")))),
                escape_html(str(item.get("generated_at", "") or item.get("updated_at", "") or "n/a")),
                escape_html(str(item.get("target_count", 0))),
                escape_html(str(item.get("totals", {}).get("needs_review", 0))),
                escape_html(str(item.get("totals", {}).get("low_quality", 0))),
                delta_badges,
            ]
        )

    probe_badges = [
        _pill(str(provider_probe_status.get("status", "warning")), _self_check_tone(str(provider_probe_status.get("status", "warning")))),
        _pill(str(provider_probe_status.get("phase", "not_run")).replace("_", " "), _provider_phase_tone(str(provider_probe_status.get("phase", "not_run")))),
        _pill(probe_state, probe_state_tone),
    ]
    if str(provider_probe_status.get("provider_status", "")).strip():
        probe_badges.append(_pill(str(provider_probe_status.get("provider_status", "")), "info"))
    elif str(provider_probe_status.get("error_code", "")).strip():
        probe_badges.append(_pill(str(provider_probe_status.get("error_code", "")), "danger"))

    probe_detail_rows = [
        [escape_html("Provider"), escape_html(str(provider_probe_status.get("provider", "") or provider_readiness.get("provider", config.get("ai_provider", "mock")) or "mock"))],
        [escape_html("Readiness Phase"), escape_html(str(provider_readiness.get("phase", "not_configured")).replace("_", " "))],
        [escape_html("Probe Phase"), escape_html(str(provider_probe_status.get("phase", "not_run")).replace("_", " "))],
        [escape_html("Probe Status"), _pill(probe_state, probe_state_tone)],
        [escape_html("Generated"), escape_html(str(provider_probe_status.get("generated_at", "") or "not recorded"))],
        [escape_html("Endpoint"), escape_html(str(provider_probe_status.get("endpoint", "") or provider_readiness.get("endpoint", "") or "not configured"))],
        [escape_html("Model"), escape_html(str(provider_probe_status.get("model", "") or provider_readiness.get("model", "") or "not configured"))],
        [escape_html("HTTP Status"), escape_html(str(provider_probe_status.get("http_status", 0) or "n/a") if provider_probe_status.get("attempted") else "n/a")],
        [escape_html("Error Code"), escape_html(str(provider_probe_status.get("error_code", "") or "none"))],
        [escape_html("Request ID"), escape_html(str(provider_probe_status.get("provider_request_id", "") or "n/a"))],
        [
            escape_html("Artifact"),
            _download_chip("/downloads/ops/provider-probe/latest", "Latest JSON")
            if provider_probe_status.get("exists")
            else escape_html("not recorded"),
        ],
        [
            escape_html("Request Audit"),
            escape_html(
                "llm_safe={0} | raw_user_material={1} | issue_count={2}".format(
                    bool((provider_probe_status.get("request_summary") or {}).get("llm_safe", False)),
                    bool((provider_probe_status.get("request_summary") or {}).get("contains_raw_user_material", False)),
                    int((provider_probe_status.get("request_summary") or {}).get("rule_issue_count", 0) or 0),
                )
            ),
        ],
    ]
    release_gate_check_rows = [
        [
            escape_html(item.get("label", item.get("name", "check"))),
            _pill(str(item.get("status", "warning")), _gate_tone(str(item.get("status", "warning")))),
            escape_html(str(item.get("value", "") or "-")),
            escape_html(str(item.get("detail", "") or "")),
        ]
        for item in release_gate.get("checks", [])
    ]
    release_gate_command_blocks = "".join(
        f'<div class="command-block"><strong>{escape_html(item.get("label", "Command"))}</strong><code>{escape_html(item.get("command", ""))}</code></div>'
        for item in release_gate.get("commands", [])
    )
    probe_history_rows = []
    for item in provider_probe_history:
        download_cell = (
            _download_chip(f"/downloads/ops/provider-probe/history/{item.get('file_name', '')}", "JSON")
            if item.get("file_name")
            else escape_html("n/a")
        )
        probe_history_rows.append(
            [
                escape_html(str(item.get("file_name", "-"))),
                _pill(str(item.get("probe_status", "not_run")), _provider_phase_tone(str(item.get("phase", "not_run")))),
                escape_html(str(item.get("generated_at", "") or item.get("updated_at", "") or "n/a")),
                escape_html(str(item.get("http_status", 0) or "n/a") if item.get("attempted") else "n/a"),
                escape_html(str(item.get("error_code", "") or item.get("provider_status", "") or item.get("summary", ""))),
                download_cell,
            ]
        )

    content = f"""
    <section class="kpi-grid">
      {_kpi_card('Release Gate', release_gate_status.upper(), str(release_gate.get('summary', 'Release gate status is unavailable.')), 'target', _gate_tone(release_gate_status))}
      {_kpi_card('Self Check', self_check.get('status', 'unknown').upper(), 'Startup environment and writable-path validation.', 'server', _self_check_tone(self_check.get('status', 'unknown')))}
      {_kpi_card('Needs Review', str(snapshot['needs_review_count']), 'Materials still waiting for manual review or correction.', 'history', 'warning' if snapshot['needs_review_count'] else 'success')}
      {_kpi_card('Redactions', str(snapshot['redaction_total']), 'Local desensitization replacements completed before any AI boundary.', 'shield', 'success')}
    </section>
    <section class="ops-status-grid">
      {_ops_status_card(
          'Provider Readiness',
          str(provider_readiness.get('provider', config.get('ai_provider', 'mock')) or 'mock').upper(),
          str(provider_readiness.get('summary', 'No provider readiness summary available.')),
          'server',
          _self_check_tone(str(provider_readiness.get('status', 'unknown'))),
          provider_rows,
          [
              _pill(str(provider_readiness.get('status', 'unknown')), _self_check_tone(str(provider_readiness.get('status', 'unknown')))),
              _pill(str(provider_readiness.get('phase', 'not_configured')).replace('_', ' '), _provider_phase_tone(str(provider_readiness.get('phase', 'not_configured')))),
              _pill('desensitized boundary', 'success' if config.get('ai_require_desensitized', True) else 'warning'),
          ],
      )}
      {_ops_status_card(
          'Latest Probe',
          str(provider_probe_status.get('probe_status', 'not_run')).upper(),
          str(provider_probe_status.get('summary', 'No persisted provider probe result is available yet.')),
          'check',
          _self_check_tone(str(provider_probe_status.get('status', 'warning'))),
          probe_rows,
          probe_badges,
      )}
      {_ops_status_card(
          'Latest Backup',
          str(backup_status.get('file_name', '') or 'No Backup Yet'),
          str(backup_status.get('summary', 'Run runtime_backup create to generate the first archive.')),
          'history',
          _self_check_tone(str(backup_status.get('status', 'warning'))),
          backup_rows,
          [
              _pill(str(backup_status.get('status', 'warning')), _self_check_tone(str(backup_status.get('status', 'warning')))),
              _pill(str(backup_status.get('size_label', '0 B')), 'info'),
          ],
      )}
      {_ops_status_card(
          'Latest Baseline',
          str(baseline_status.get('file_name', '') or 'No Baseline Yet'),
          str(baseline_status.get('summary', 'Run metrics_baseline to capture a real-sample trend snapshot.')),
          'trend',
          _self_check_tone(str(baseline_status.get('status', 'warning'))),
          baseline_rows,
          baseline_badges,
      )}
    </section>
    <section class="dashboard-grid">
      <section class="panel span-7">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">Startup Self Check</span>
            <h2>Startup Environment Checks</h2>
            <p>Re-check writable runtime directories, SQLite parent, log path, config files, and the privacy boundary on every page load.</p>
          </div>
          <div class="panel-head-icon">{_icon("server", "icon icon-lg")}</div>
        </div>
        {_table(['Check', 'Status', 'Path', 'Detail'], check_rows)}
      </section>
      <section class="panel span-5">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">Support Actions</span>
            <h2>Operator Commands</h2>
            <p>Keep the most common smoke, backup, probe, release-gate, and baseline actions visible in one place for faster triage.</p>
          </div>
          <div class="panel-head-icon">{_icon("history", "icon icon-lg")}</div>
        </div>
        <div class="dossier-list">
          <div><span>Log Download</span><strong><a class="table-link" href="/downloads/logs/app">app.jsonl</a></strong></div>
          <div><span>Local Config</span><strong>{escape_html(str(self_check.get('paths', {}).get('config_local_path', 'config/local.json')))}</strong></div>
          <div><span>Latest Probe</span><strong>{_download_chip('/downloads/ops/provider-probe/latest', 'Latest JSON') if provider_probe_status.get('exists') else 'not recorded'}</strong></div>
          <div><span>AI Boundary</span><strong>desensitized payload only</strong></div>
        </div>
        <div class="command-list command-grid">
          <div class="command-block"><strong>Mode A Smoke</strong><code>py -m app.tools.input_runner --path input\\软著材料 --mode single_case_package</code></div>
          <div class="command-block"><strong>Mode B Smoke</strong><code>py -m app.tools.input_runner --path input\\合作协议 --mode batch_same_material</code></div>
          <div class="command-block"><strong>Runtime Cleanup</strong><code>py -m app.tools.runtime_cleanup</code></div>
          <div class="command-block"><strong>Runtime Backup</strong><code>py -m app.tools.runtime_backup create</code></div>
          <div class="command-block"><strong>Sandbox First</strong><code>py -m app.tools.provider_sandbox --port 8010
py -m app.tools.provider_probe --provider external_http --endpoint http://127.0.0.1:8010/review --model sandbox-model --probe</code></div>
          <div class="command-block"><strong>Real Provider Smoke</strong><code>py -m app.tools.provider_probe --config config\\local.json --probe</code></div>
          <div class="command-block"><strong>Release Gate</strong><code>py -m app.tools.release_gate --config config\\local.json</code></div>
          <div class="command-block"><strong>Rolling Baseline</strong><code>py -m app.tools.metrics_baseline --compare-latest-in-dir docs\\dev --archive-dir docs\\dev\\history --archive-stem real-sample-baseline</code></div>
          <div class="command-block"><strong>Full Regression</strong><code>py -m pytest</code></div>
          <div class="command-block"><strong>Start Web</strong><code>py -m app.api.main</code></div>
        </div>
      </section>
      <section class="panel span-5">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">Release Gate</span>
            <h2>Promote Or Hold</h2>
            <p>Use one gate to combine startup checks, provider smoke status, and rolling-baseline health before the next phase or release step.</p>
          </div>
          <div class="panel-head-icon">{_icon("target", "icon icon-lg")}</div>
        </div>
        <div class="summary-grid">
          <article class="summary-tile">
            <span>Status</span>
            <strong>{escape_html(release_gate_status.upper())}</strong>
            <small>Overall promote-or-hold status for the current environment.</small>
          </article>
          <article class="summary-tile">
            <span>Mode</span>
            <strong>{escape_html(str(release_gate.get('mode', 'unknown')).replace('_', ' '))}</strong>
            <small>Current provider operating mode seen by the gate.</small>
          </article>
          <article class="summary-tile">
            <span>Latest Success</span>
            <strong>{escape_html(latest_success_value)}</strong>
            <small>Most recent successful provider probe in history.</small>
          </article>
          <article class="summary-tile">
            <span>Latest Failure</span>
            <strong>{escape_html(latest_failure_value)}</strong>
            <small>Most recent failed provider probe or none recorded.</small>
          </article>
        </div>
        <p class="highlight-note">{escape_html(str(release_gate.get('recommended_action', '') or release_gate.get('summary', 'Release gate guidance is unavailable.')))}</p>
        {_table(['Check', 'Status', 'Value', 'Detail'], release_gate_check_rows)}
        <div class="command-list command-grid">{release_gate_command_blocks}</div>
      </section>
      <section class="panel span-7">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">Probe Observatory</span>
            <h2>Latest Provider Probe</h2>
            <p>Persist the newest safe provider probe so operators can see what happened, what was sent, and what to fix next.</p>
          </div>
          <div class="panel-head-icon">{_icon("check", "icon icon-lg")}</div>
        </div>
        <div class="summary-grid">
          <article class="summary-tile">
            <span>Gate Phase</span>
            <strong>{escape_html(str(provider_readiness.get('phase', 'not_configured')).replace('_', ' '))}</strong>
            <small>Current external provider readiness phase.</small>
          </article>
          <article class="summary-tile">
            <span>Last Probe</span>
            <strong>{escape_html(str(provider_probe_status.get('generated_at', '') or 'not recorded'))}</strong>
            <small>Persisted time of the newest probe summary.</small>
          </article>
          <article class="summary-tile">
            <span>Latest Success</span>
            <strong>{escape_html(latest_success_value)}</strong>
            <small>Most recent successful probe across latest and history.</small>
          </article>
          <article class="summary-tile">
            <span>Latest Failure</span>
            <strong>{escape_html(latest_failure_value)}</strong>
            <small>Keep the last failure visible until a newer success supersedes it.</small>
          </article>
        </div>
        <p class="highlight-note">{escape_html(str(provider_probe_status.get('recommended_action', '') or provider_readiness.get('recommended_action', 'Provider remediation is not available.')))}</p>
        {_table(['Field', 'Value'], probe_detail_rows)}
      </section>
      <section class="panel span-6">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">Probe History</span>
            <h2>Recent Probe Artifacts</h2>
            <p>Keep timestamped safe probe artifacts so operators can compare the newest result with the recent success/failure trail.</p>
          </div>
          <div class="panel-head-icon">{_icon("history", "icon icon-lg")}</div>
        </div>
        {_table(['Artifact', 'Probe', 'Generated', 'HTTP', 'Detail', 'Download'], probe_history_rows)}
      </section>
      <section class="panel span-6">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">Trend Watch</span>
            <h2>Baseline History</h2>
            <p>Track the latest sample baseline, compare against the previous snapshot automatically, and keep a rolling archive for regression visibility.</p>
          </div>
          <div class="panel-head-icon">{_icon("trend", "icon icon-lg")}</div>
        </div>
        <div class="summary-grid">
          <article class="summary-tile">
            <span>Latest Snapshot</span>
            <strong>{escape_html(str(baseline_status.get('generated_at', '') or baseline_status.get('updated_at', '') or 'n/a'))}</strong>
            <small>Latest baseline generation time.</small>
          </article>
          <article class="summary-tile">
            <span>History Depth</span>
            <strong>{len(baseline_history)}</strong>
            <small>Visible baseline artifacts scanned from docs/dev.</small>
          </article>
          <article class="summary-tile">
            <span>Needs Review Delta</span>
            <strong>{escape_html(format_signed_delta(baseline_deltas.get('needs_review')))}</strong>
            <small>Signed change versus the previous baseline snapshot.</small>
          </article>
          <article class="summary-tile">
            <span>Low Quality Delta</span>
            <strong>{escape_html(format_signed_delta(baseline_deltas.get('low_quality')))}</strong>
            <small>Keep this trending downward before the next release slice.</small>
          </article>
        </div>
        <p class="highlight-note">Rolling Baseline writes timestamped JSON and Markdown artifacts into <code>docs/dev/history</code> while auto-comparing with the newest baseline under <code>docs/dev</code>.</p>
        {_table(['Artifact', 'Status', 'Generated', 'Targets', 'Needs Review', 'Low Quality', 'Delta'], baseline_history_rows)}
      </section>
      <section class="panel span-6">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">Provider Checklist</span>
            <h2>External Provider Gate</h2>
            <p>Keep the provider boundary explicit so only desensitized payloads can cross the non-mock edge when local config or env overrides are ready.</p>
          </div>
          <div class="panel-head-icon">{_icon("check", "icon icon-lg")}</div>
        </div>
        <div class="dossier-list">
          <div><span>Ready Status</span><strong>{escape_html(str(provider_readiness.get('status', 'unknown')).upper())}</strong></div>
          <div><span>Phase</span><strong>{escape_html(str(provider_readiness.get('phase', 'not_configured')).replace('_', ' '))}</strong></div>
          <div><span>Checks OK</span><strong>{provider_check_counts.get('ok', 0)}</strong></div>
          <div><span>Warnings</span><strong>{provider_check_counts.get('warning', 0)}</strong></div>
        </div>
        <p class="highlight-note">{escape_html(str(provider_readiness.get('recommended_action', 'Provider remediation is not available.')))}</p>
        {_table(['Check', 'Status', 'Value', 'Detail'], provider_check_rows)}
      </section>
      <section class="panel span-6">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">Active Config</span>
            <h2>Runtime Config</h2>
          </div>
          <div class="panel-head-icon">{_icon("filter", "icon icon-lg")}</div>
        </div>
        {_table(['Config', 'Value'], config_rows)}
      </section>
      <section class="panel span-12">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">Retention Policy</span>
            <h2>Runtime Retention</h2>
            <p>The system keeps original, clean, desensitized, and privacy-manifest artifacts separated under <code>data/runtime</code> so traceability stays intact without weakening the privacy boundary.</p>
          </div>
          <div class="panel-head-icon">{_icon("shield", "icon icon-lg")}</div>
        </div>
        <div class="dossier-list">
          <div><span>Data Root</span><strong>{escape_html(self_check.get('paths', {}).get('data_root', config.get('data_root', 'data/runtime')))}</strong></div>
          <div><span>SQLite</span><strong>{escape_html(self_check.get('paths', {}).get('sqlite_path', config.get('sqlite_path', 'data/runtime/soft_review.db')))}</strong></div>
          <div><span>Logs</span><strong>{escape_html(self_check.get('paths', {}).get('log_path', config.get('log_path', 'data/runtime/logs/app.jsonl')))}</strong></div>
          <div><span>Suggested Cadence</span><strong>Run regression after each completed slice before moving on.</strong></div>
        </div>
        <p class="highlight-note">Promote the next phase only after automated regression passes, real-sample smoke passes, and the <code>docs/dev</code> artifacts for that slice are written completely.</p>
      </section>
    </section>
    """
    return _layout(
        title="Support / Ops",
        active_nav="ops",
        header_tag="Support / Ops",
        header_title="Operations Console",
        header_subtitle="Centralize self-checks, provider readiness, probe observability, rolling baseline history, and retention controls in one admin view.",
        header_meta="".join(
            [
                _pill(self_check.get("status", "unknown"), _self_check_tone(self_check.get("status", "unknown"))),
                _pill("Local Redaction", "success"),
                _pill(str(config.get("ai_provider", "mock")), "info"),
                _pill(str(provider_probe_status.get("phase", "not_run")).replace("_", " "), _provider_phase_tone(str(provider_probe_status.get("phase", "not_run")))),
            ]
        ),
        content=content,
    )


def render_stylesheet() -> str:
    css_path = Path(__file__).with_name("static").joinpath("styles.css")
    return css_path.read_text(encoding="utf-8")
