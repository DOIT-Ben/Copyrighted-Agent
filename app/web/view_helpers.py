from __future__ import annotations

from pathlib import Path

from app.core.utils.text import escape_html


SECTION_LINKS = {
    "home": ("/", "\u603b\u63a7\u53f0", "dashboard"),
    "submissions": ("/submissions", "\u6279\u6b21\u603b\u89c8", "layers"),
    "ops": ("/ops", "\u8fd0\u7ef4\u4e2d\u5fc3", "terminal"),
}


MODE_LABELS = {
    "single_case_package": "\u6a21\u5f0f A\uff1a\u5355\u9879\u76ee\u6574\u5305",
    "batch_same_material": "\u6a21\u5f0f B\uff1a\u540c\u7c7b\u6279\u91cf\u5f52\u6863",
}

TYPE_LABELS = {
    "agreement": "\u5408\u4f5c\u534f\u8bae",
    "source_code": "\u6e90\u4ee3\u7801",
    "info_form": "\u4fe1\u606f\u91c7\u96c6\u8868",
    "software_doc": "\u8f6f\u4ef6\u8bf4\u660e\u6587\u6863",
    "unknown": "\u5f85\u8bc6\u522b",
}

REPORT_LABELS = {
    "material_markdown": "\u6750\u6599\u5ba1\u67e5\u62a5\u544a",
    "case_markdown": "\u9879\u76ee\u7efc\u5408\u62a5\u544a",
    "batch_markdown": "\u6279\u6b21\u6c47\u603b\u62a5\u544a",
}

SEVERITY_LABELS = {
    "severe": "\u4e25\u91cd",
    "moderate": "\u4e2d\u7b49",
    "minor": "\u8f83\u8f7b",
}

STATUS_LABELS = {
    "ok": "\u6b63\u5e38",
    "completed": "\u5df2\u5b8c\u6210",
    "healthy": "\u5065\u5eb7",
    "pass": "\u901a\u8fc7",
    "grouped": "\u5df2\u5f52\u7ec4",
    "success": "\u6210\u529f",
    "ready": "\u5c31\u7eea",
    "warning": "\u544a\u8b66",
    "processing": "\u5904\u7406\u4e2d",
    "running": "\u8fd0\u884c\u4e2d",
    "needs_review": "\u5f85\u590d\u6838",
    "skipped": "\u5df2\u8df3\u8fc7",
    "minor": "\u8f83\u8f7b",
    "moderate": "\u4e2d\u7b49",
    "failed": "\u5931\u8d25",
    "error": "\u9519\u8bef",
    "blocked": "\u963b\u585e",
    "danger": "\u9ad8\u98ce\u9669",
    "severe": "\u4e25\u91cd",
    "info": "\u4fe1\u606f",
    "active": "\u5df2\u542f\u7528",
    "idle": "\u7a7a\u95f2",
    "not_run": "\u672a\u6267\u884c",
    "not_configured": "\u672a\u914d\u7f6e",
    "mock_mode": "\u672c\u5730\u6a21\u62df",
    "ready_for_probe": "\u53ef\u8fdb\u884c\u63a2\u9488",
    "probe_passed": "\u63a2\u9488\u901a\u8fc7",
    "probe_failed": "\u63a2\u9488\u5931\u8d25",
    "probe_skipped": "\u63a2\u9488\u8df3\u8fc7",
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


def status_label(status: str) -> str:
    normalized = str(status or "").strip().lower()
    if not normalized:
        return "-"
    if normalized in STATUS_LABELS:
        return STATUS_LABELS[normalized]
    return str(status).replace("_", " ")


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
    current_attr = ' aria-current="page"' if active else ""
    return (
        f'<a class="nav-link{active_class}" href="{escape_html(path)}"{current_attr}>'
        f'{icon(icon_name, "icon")}'
        f"<span>{escape_html(label)}</span>"
        "</a>"
    )


def _table_cell(header: str, cell: str, index: int) -> str:
    if index == 0:
        value = f'<div class="table-cell-value table-cell-value-title">{cell}</div>'
    else:
        value = f'<div class="table-cell-value">{cell}</div>'
    return (
        f'<td data-label="{escape_html(header)}">'
        f'<span class="table-cell-label">{escape_html(header)}</span>'
        f"{value}"
        "</td>"
    )


def table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return empty_state("\u6682\u65e0\u6570\u636e", "\u5f53\u524d\u89c6\u56fe\u8fd8\u6ca1\u6709\u53ef\u663e\u793a\u7684\u5185\u5bb9\u3002")
    head = "".join(f'<th scope="col">{escape_html(item)}</th>' for item in headers)
    body = "".join(
        "<tr>"
        + "".join(
            _table_cell(headers[index] if index < len(headers) else f"col_{index + 1}", cell, index)
            for index, cell in enumerate(row)
        )
        + "</tr>"
        for row in rows
    )
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


def notice_banner(
    title: str,
    message: str,
    tone: str = "info",
    *,
    icon_name: str = "spark",
    meta: list[str] | None = None,
) -> str:
    meta_html = ""
    if meta:
        meta_html = '<div class="notice-meta-row">' + "".join(
            f'<span class="helper-chip">{escape_html(item)}</span>' for item in meta
        ) + "</div>"
    return (
        f'<section class="notice-banner notice-banner-{escape_html(tone)}">'
        f'<div class="notice-banner-icon">{icon(icon_name, "icon icon-md")}</div>'
        '<div class="notice-banner-copy">'
        f"<strong>{escape_html(title)}</strong>"
        f"<p>{escape_html(message)}</p>"
        f"{meta_html}"
        "</div></section>"
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
        f'<section{id_attr} class="{class_name}"><div class="panel-head"><div class="panel-head-copy">'
        f"{kicker_html}<h2>{escape_html(title)}</h2>{description_html}</div>"
        f'<div class="panel-head-icon">{icon(icon_name, "icon icon-lg")}</div>'
        f"</div>{body}</section>"
    )


def list_pairs(items: list[tuple[str, str]], *, css_class: str = "dossier-list") -> str:
    content = "".join(
        f"<div><span>{escape_html(label)}</span><strong>{value}</strong></div>"
        for label, value in items
    )
    return f'<div class="{escape_html(css_class)}">{content}</div>'


def read_text_file(path_value: str) -> str:
    if not path_value:
        return ""
    try:
        return Path(path_value).read_text(encoding="utf-8")
    except OSError:
        return ""


def _breadcrumb(active_nav: str, header_tag: str) -> str:
    current_path, current_label, _ = SECTION_LINKS.get(active_nav, ("/", "\u603b\u63a7\u53f0", "dashboard"))
    return (
        '<nav class="workspace-breadcrumbs" aria-label="Breadcrumb">'
        '<a href="/">\u5de5\u4f5c\u53f0</a>'
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

    return '<div class="workspace-shortcuts">' + "".join(
        _shortcut_link(path, label, icon_name) for path, label, icon_name in items
    ) + "</div>"


def _page_link_strip(page_links: list[tuple[str, str, str]] | None) -> str:
    items = page_links or []
    if not items:
        return ""

    chips = "".join(
        (
            f'<a class="page-link-chip" href="{escape_html(path)}">'
            f'{icon(icon_name, "icon icon-sm")}'
            f"<span>{escape_html(label)}</span>"
            "</a>"
        )
        for path, label, icon_name in items
    )
    return (
        '<section class="page-link-strip" aria-label="Page shortcuts">'
        '<strong class="page-link-strip-label">本页导航</strong>'
        f'<div class="page-link-strip-row">{chips}</div>'
        "</section>"
    )


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
    workspace_notice: str = "",
) -> str:
    mode_count = len(MODE_LABELS)
    type_count = len([key for key in TYPE_LABELS if key != "unknown"])
    release_note = header_note or "\u4ece\u540c\u4e00\u4e2a\u53ef\u4fe1\u5de5\u4f5c\u9762\u4e2d\uff0c\u76f4\u63a5\u770b\u5230\u5bfc\u5165\u3001\u5ba1\u67e5\u3001\u5bfc\u51fa\u4e0e\u4eba\u5de5\u51b3\u7b56\u3002"
    current_section = SECTION_LINKS.get(active_nav, ("/", header_tag, "dashboard"))[1]
    home_label = SECTION_LINKS["home"][1]
    submissions_label = SECTION_LINKS["submissions"][1]
    ops_label = SECTION_LINKS["ops"][1]
    release_cards = "".join(
        [
            _release_card(
                "\u672c\u5730\u8131\u654f",
                "\u6240\u6709\u975e mock \u8c03\u7528\u90fd\u5148\u8fc7\u8131\u654f\u8fb9\u754c\uff0c\u518d\u79bb\u5f00\u672c\u673a\u3002",
                "success",
                "shield",
            ),
            _release_card(
                "\u53ef\u8ffd\u6eaf\u94fe\u8def",
                "\u6279\u6b21\u3001\u9879\u76ee\u3001\u62a5\u544a\u4e0e\u4ea7\u7269\u94fe\u8def\u5728\u9875\u9762\u4e0a\u6301\u7eed\u53ef\u89c1\u3002",
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
  <a class="skip-link" href="#main-content">\u8df3\u5230\u4e3b\u5185\u5bb9</a>
  <div class="admin-shell">
    <aside class="sidebar">
      <a class="sidebar-brand" href="/">
        <span class="sidebar-brand-mark">{icon("dashboard", "icon icon-md")}</span>
        <span class="sidebar-brand-copy">
          <strong>\u8f6f\u8457\u5206\u6790\u5e73\u53f0</strong>
          <small>\u4e2d\u6587\u7ba1\u7406\u53f0</small>
        </span>
      </a>

      <section class="sidebar-section">
        <span class="sidebar-label">\u5bfc\u822a</span>
        <nav class="sidebar-nav" aria-label="Main navigation">
          {nav_link("/", home_label, active_nav == "home", icon_name="dashboard")}
          {nav_link("/submissions", submissions_label, active_nav == "submissions", icon_name="layers")}
          {nav_link("/ops", ops_label, active_nav == "ops", icon_name="terminal")}
        </nav>
      </section>

      <section class="sidebar-section">
        <span class="sidebar-label">\u5904\u7406\u6d41\u7a0b</span>
        <div class="sidebar-list">
          <div class="sidebar-item">{icon("upload", "icon icon-sm")}<span>ZIP \u5bfc\u5165</span></div>
          <div class="sidebar-item">{icon("cluster", "icon icon-sm")}<span>\u81ea\u52a8\u5f52\u7c7b</span></div>
          <div class="sidebar-item">{icon("shield", "icon icon-sm")}<span>\u89c4\u5219\u5ba1\u67e5</span></div>
          <div class="sidebar-item">{icon("report", "icon icon-sm")}<span>\u62a5\u544a\u4ea4\u4ed8</span></div>
        </div>
      </section>

      <section class="sidebar-section sidebar-signal">
        <span class="sidebar-label">\u8fd0\u884c\u57fa\u7ebf</span>
        <div class="sidebar-mini-kpi">
          <div><strong>{mode_count}</strong><span>\u5bfc\u5165\u6a21\u5f0f</span></div>
          <div><strong>{type_count}</strong><span>\u6838\u5fc3\u6750\u6599</span></div>
          <div><strong>safe</strong><span>\u5b89\u5168\u8fb9\u754c</span></div>
        </div>
      </section>
    </aside>

    <main id="main-content" class="workspace">
      <section class="workspace-rail" aria-label="Release context">
        <div class="workspace-rail-copy">
          {_breadcrumb(active_nav, header_tag)}
          <div class="workspace-rail-summary">
            <strong>\u53d1\u5e03\u51c6\u5907\u5ea6</strong>
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
      {workspace_notice}
      {_page_link_strip(page_links)}
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
    "notice_banner",
    "panel",
    "pill",
    "read_text_file",
    "render_stylesheet",
    "report_label",
    "severity_label",
    "status_label",
    "status_tone",
    "table",
    "type_label",
]
