from __future__ import annotations

from pathlib import Path

from app.core.utils.text import escape_html

SECTION_LINKS = {
    "home": ("/", "Control Center", "dashboard"),
    "submissions": ("/submissions", "Batch Registry", "layers"),
    "ops": ("/ops", "Support / Ops", "terminal"),
}


MODE_LABELS = {
    "single_case_package": "single_case_package / 同一软著，多份材料",
    "batch_same_material": "batch_same_material / 不同软著，同类材料",
}

TYPE_LABELS = {
    "agreement": "合作协议",
    "source_code": "源代码",
    "info_form": "信息采集表",
    "software_doc": "软件说明文档",
    "unknown": "未识别",
}

REPORT_LABELS = {
    "material_markdown": "材料审查报告",
    "case_markdown": "项目综合报告",
    "batch_markdown": "批次汇总报告",
}

SEVERITY_LABELS = {
    "severe": "严重",
    "moderate": "中等",
    "minor": "轻微",
}

ICON_PATHS = {
    "dashboard": '<rect x="4" y="4" width="7" height="7" rx="2"/><rect x="13" y="4" width="7" height="4" rx="2"/><rect x="13" y="10" width="7" height="10" rx="2"/><rect x="4" y="13" width="7" height="7" rx="2"/>',
    "layers": '<path d="m12 4 8 4-8 4-8-4 8-4Z"/><path d="m4 12 8 4 8-4"/><path d="m4 16 8 4 8-4"/>',
    "upload": '<path d="M12 16V6"/><path d="m8 10 4-4 4 4"/><path d="M5 19h14"/>',
    "cluster": '<circle cx="6" cy="6" r="2"/><circle cx="18" cy="12" r="2"/><circle cx="8" cy="18" r="2"/><path d="M8 6h5c2 0 3 1 3 3v1"/><path d="M16 14c0 2-1 3-3 3h-3"/>',
    "shield": '<path d="M12 3 5 6v6c0 4.3 2.8 7.8 7 9.2 4.2-1.4 7-4.9 7-9.2V6l-7-3Z"/><path d="m9.8 12.2 1.7 1.7 3.7-4.2"/>',
    "report": '<path d="M7 4h10a2 2 0 0 1 2 2v12l-3-2-4 2-4-2-3 2V6a2 2 0 0 1 2-2Z"/><path d="M9 9h6"/><path d="M9 12h6"/>',
    "bar": '<path d="M5 19V9"/><path d="M12 19V5"/><path d="M19 19v-7"/>',
    "file": '<path d="M8 3h7l4 4v12a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z"/><path d="M15 3v4h4"/>',
    "lock": '<rect x="4" y="7" width="16" height="11" rx="2.5"/><path d="M9 7V5a3 3 0 0 1 6 0v2"/>',
    "trend": '<path d="M4 16 9 11l3 3 7-7"/><path d="M15 7h4v4"/>',
    "alert": '<path d="M12 4 3.5 19h17L12 4Z"/><path d="M12 10v4"/><circle cx="12" cy="17" r="1"/>',
    "check": '<circle cx="12" cy="12" r="9"/><path d="m9.5 12.5 1.8 1.8 3.7-4.2"/>',
    "spark": '<path d="m12 3 1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3Z"/>',
    "download": '<path d="M12 5v9"/><path d="m8.5 11.5 3.5 3.5 3.5-3.5"/><path d="M5 19h14"/>',
    "terminal": '<path d="m8 9 3 3-3 3"/><path d="M13 15h4"/><rect x="3" y="4" width="18" height="16" rx="2"/>',
    "refresh": '<path d="M20 11a8 8 0 1 0 2 5.3"/><path d="M20 4v7h-7"/>',
    "merge": '<path d="M8 6h4a4 4 0 0 1 4 4v1"/><path d="M8 18h4a4 4 0 0 0 4-4v-1"/><circle cx="6" cy="6" r="2"/><circle cx="6" cy="18" r="2"/><circle cx="18" cy="12" r="2"/>',
    "wrench": '<path d="M14 7.5a4 4 0 0 0 5.5 5.5L13 19.5 8.5 15l5.5-6.5Z"/><path d="M6 21 3 18l5.5-5.5L11 15"/>',
    "search": '<circle cx="11" cy="11" r="6"/><path d="m20 20-3.5-3.5"/>',
    "link": '<path d="M10 13a5 5 0 0 0 7.1 0l2.1-2.1a5 5 0 0 0-7.1-7.1L10.9 5"/><path d="M14 11a5 5 0 0 0-7.1 0L4.8 13.1a5 5 0 0 0 7.1 7.1L13.1 19"/>',
    "clock": '<circle cx="12" cy="12" r="8"/><path d="M12 8v4l3 2"/>',
}


def icon(name: str, css_class: str = "icon") -> str:
    body = ICON_PATHS.get(name, ICON_PATHS["dashboard"])
    return (
        f'<svg class="{escape_html(css_class)}" viewBox="0 0 24 24" fill="none" '
        'xmlns="http://www.w3.org/2000/svg" aria-hidden="true" '
        'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</svg>"
    )


def mode_label(mode: str) -> str:
    return MODE_LABELS.get(mode, mode)


def type_label(material_type: str) -> str:
    return TYPE_LABELS.get(material_type, material_type)


def report_label(report_type: str) -> str:
    return REPORT_LABELS.get(report_type, report_type)


def severity_label(severity: str) -> str:
    return SEVERITY_LABELS.get(severity, severity or "-")


def status_tone(status: str) -> str:
    normalized = str(status or "").lower()
    if normalized in {"ok", "completed", "healthy", "pass", "grouped", "success", "ready"}:
        return "success"
    if normalized in {"warning", "processing", "running", "needs_review", "skipped", "moderate", "minor"}:
        return "warning"
    if normalized in {"failed", "error", "blocked", "danger", "severe"}:
        return "danger"
    if normalized in {"info", "active"}:
        return "info"
    return "neutral"


def issue_tone(issue_count: int) -> str:
    if issue_count >= 3:
        return "danger"
    if issue_count >= 1:
        return "warning"
    return "success"


def pill(text: str, tone: str = "neutral") -> str:
    return f'<span class="pill pill-{tone}">{escape_html(str(text))}</span>'


def link(path: str, label: str, *, css_class: str = "table-link") -> str:
    return f'<a class="{css_class}" href="{escape_html(path)}">{escape_html(label)}</a>'


def download_chip(path: str, label: str) -> str:
    return (
        f'<a class="download-chip" href="{escape_html(path)}">'
        f'{icon("download", "icon icon-sm")}'
        f"<span>{escape_html(label)}</span>"
        "</a>"
    )


def nav_link(path: str, label: str, active: bool = False, *, icon_name: str = "dashboard") -> str:
    active_class = " nav-link-active" if active else ""
    return (
        f'<a class="nav-link{active_class}" href="{escape_html(path)}">'
        f'{icon(icon_name, "icon")}'
        f"<span>{escape_html(label)}</span>"
        "</a>"
    )


def table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return empty_state("No Data", "There is nothing to show in this view yet.")
    head = "".join(f"<th>{escape_html(item)}</th>" for item in headers)
    body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
    return (
        '<div class="table-wrap"><table class="data-table">'
        f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"
    )


def metric_card(label: str, value: str, note: str, tone: str = "neutral", *, icon_name: str = "dashboard") -> str:
    return (
        f'<article class="kpi-card kpi-card-{tone}">'
        f'<div class="kpi-icon">{icon(icon_name, "icon icon-md")}</div>'
        '<div class="kpi-copy">'
        f'<span class="kpi-label">{escape_html(label)}</span>'
        f"<strong>{escape_html(value)}</strong>"
        f"<small>{escape_html(note)}</small>"
        "</div></article>"
    )


def empty_state(title: str, note: str) -> str:
    return (
        '<div class="empty-state">'
        f"<strong>{escape_html(title)}</strong>"
        f"<span>{escape_html(note)}</span>"
        "</div>"
    )


def panel(
    title: str,
    body: str,
    *,
    kicker: str = "",
    extra_class: str = "",
    icon_name: str = "dashboard",
    description: str = "",
    panel_id: str = "",
) -> str:
    kicker_html = f'<span class="panel-kicker">{escape_html(kicker)}</span>' if kicker else ""
    description_html = f"<p>{escape_html(description)}</p>" if description else ""
    class_name = f"panel {extra_class}".strip()
    id_attr = f' id="{escape_html(panel_id)}"' if panel_id else ""
    return (
        f'<section{id_attr} class="{class_name}"><div class="panel-head"><div>'
        f"{kicker_html}<h2>{escape_html(title)}</h2>{description_html}</div>"
        f'<div class="panel-head-icon">{icon(icon_name, "icon icon-lg")}</div>'
        f"</div>{body}</section>"
    )


def list_pairs(items: list[tuple[str, str]]) -> str:
    content = "".join(
        f"<div><span>{escape_html(label)}</span><strong>{value}</strong></div>"
        for label, value in items
    )
    return f'<div class="dossier-list">{content}</div>'


def read_text_file(path_value: str) -> str:
    if not path_value:
        return ""
    try:
        return Path(path_value).read_text(encoding="utf-8")
    except OSError:
        return ""


def _breadcrumb(active_nav: str, header_tag: str) -> str:
    current_path, current_label, _ = SECTION_LINKS.get(active_nav, ("/", "Control Center", "dashboard"))
    return (
        '<nav class="workspace-breadcrumbs" aria-label="Breadcrumb">'
        '<a href="/">Console</a>'
        '<span>/</span>'
        f'<a href="{escape_html(current_path)}">{escape_html(current_label)}</a>'
        '<span>/</span>'
        f"<strong>{escape_html(header_tag)}</strong>"
        "</nav>"
    )


def _shortcut_link(path: str, label: str, icon_name: str) -> str:
    return (
        f'<a class="workspace-shortcut" href="{escape_html(path)}">'
        f'{icon(icon_name, "icon icon-sm")}'
        f"<span>{escape_html(label)}</span>"
        "</a>"
    )


def _workspace_shortcuts(active_nav: str, page_links: list[tuple[str, str, str]] | None) -> str:
    items: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str]] = set()

    for key in ("home", "submissions", "ops"):
        path, label, icon_name = SECTION_LINKS[key]
        marker = (path, label)
        if marker in seen:
            continue
        seen.add(marker)
        items.append((path, label, icon_name))

    for path, label, icon_name in page_links or []:
        marker = (path, label)
        if marker in seen:
            continue
        seen.add(marker)
        items.append((path, label, icon_name))

    return '<div class="workspace-shortcuts">' + "".join(
        _shortcut_link(path, label, icon_name) for path, label, icon_name in items
    ) + "</div>"


def _release_card(title: str, note: str, tone: str, icon_name: str) -> str:
    return (
        f'<article class="release-card release-card-{tone}">'
        f'<div class="release-card-icon">{icon(icon_name, "icon icon-sm")}</div>'
        '<div class="release-card-copy">'
        f"<strong>{escape_html(title)}</strong>"
        f"<span>{escape_html(note)}</span>"
        "</div>"
        "</article>"
    )


def render_stylesheet() -> str:
    stylesheet_path = Path(__file__).with_name("static") / "styles.css"
    try:
        return stylesheet_path.read_text(encoding="utf-8")
    except OSError:
        return ".admin-shell{display:block}.panel{padding:16px}.data-table{width:100%}"


def layout(
    *,
    title: str,
    active_nav: str,
    header_tag: str,
    header_title: str,
    header_subtitle: str,
    header_meta: str,
    content: str,
    header_note: str = "",
    page_links: list[tuple[str, str, str]] | None = None,
) -> str:
    mode_count = len(MODE_LABELS)
    type_count = len([key for key in TYPE_LABELS if key != "unknown"])
    release_note = header_note or "Keep intake, review, export, and operator decisions visible from one trusted surface."
    current_section = SECTION_LINKS.get(active_nav, ("/", header_tag, "dashboard"))[1]
    release_cards = "".join(
        [
            _release_card(
                "Local Redaction",
                "AI requests stay behind the desensitization boundary before they leave the workstation.",
                "success",
                "shield",
            ),
            _release_card(
                "Traceable Chain",
                "Submission, case, report, and artifact links remain visible for audit and replay.",
                "info",
                "report",
            ),
            _release_card(
                current_section,
                release_note,
                "warning",
                "bar",
            ),
        ]
    )
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
    <aside class="sidebar">
      <a class="sidebar-brand" href="/">
        <span class="sidebar-brand-mark">{icon("dashboard", "icon icon-md")}</span>
        <span class="sidebar-brand-copy">
          <strong>软著审查台</strong>
          <small>Admin Analysis Console</small>
        </span>
      </a>

      <section class="sidebar-section">
        <span class="sidebar-label">Navigation</span>
        <nav class="sidebar-nav" aria-label="Main navigation">
          {nav_link("/", "Control Center", active_nav == "home", icon_name="dashboard")}
          {nav_link("/submissions", "Batch Registry", active_nav == "submissions", icon_name="layers")}
          {nav_link("/ops", "Support / Ops", active_nav == "ops", icon_name="terminal")}
        </nav>
      </section>

      <section class="sidebar-section">
        <span class="sidebar-label">Workflow</span>
        <div class="sidebar-list">
          <div class="sidebar-item">{icon("upload", "icon icon-sm")}<span>ZIP 导入</span></div>
          <div class="sidebar-item">{icon("cluster", "icon icon-sm")}<span>自动分类</span></div>
          <div class="sidebar-item">{icon("shield", "icon icon-sm")}<span>规则审查</span></div>
          <div class="sidebar-item">{icon("report", "icon icon-sm")}<span>报告回看</span></div>
        </div>
      </section>

      <section class="sidebar-section sidebar-signal">
        <span class="sidebar-label">System Baseline</span>
        <div class="sidebar-mini-kpi">
          <div><strong>{mode_count}</strong><span>导入模式</span></div>
          <div><strong>{type_count}</strong><span>核心材料</span></div>
          <div><strong>safe</strong><span>AI 边界</span></div>
        </div>
      </section>
    </aside>

    <main class="workspace">
      <section class="workspace-rail" aria-label="Release context">
        <div class="workspace-rail-copy">
          {_breadcrumb(active_nav, header_tag)}
          <div class="workspace-rail-summary">
            <strong>Release Readiness</strong>
            <span>{escape_html(release_note)}</span>
          </div>
        </div>
        {_workspace_shortcuts(active_nav, page_links)}
      </section>

      <header class="workspace-header">
        <div class="workspace-header-main">
          <span class="workspace-tag">{escape_html(header_tag)}</span>
          <h1>{escape_html(header_title)}</h1>
          <p>{escape_html(header_subtitle)}</p>
        </div>
        <div class="workspace-header-meta">{header_meta}</div>
      </header>
      <section class="workspace-trust-grid" aria-label="System trust signals">
        {release_cards}
      </section>
      <div class="workspace-content">{content}</div>
    </main>
  </div>
</body>
</html>"""


__all__ = [
    "MODE_LABELS",
    "REPORT_LABELS",
    "SEVERITY_LABELS",
    "TYPE_LABELS",
    "download_chip",
    "empty_state",
    "icon",
    "issue_tone",
    "layout",
    "link",
    "list_pairs",
    "metric_card",
    "mode_label",
    "nav_link",
    "panel",
    "pill",
    "read_text_file",
    "render_stylesheet",
    "report_label",
    "severity_label",
    "status_tone",
    "table",
    "type_label",
]
