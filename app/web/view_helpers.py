from __future__ import annotations

import hashlib
from pathlib import Path

from app.core.utils.text import escape_html


SECTION_LINKS = {
    "home": ("/", "总控台", "dashboard"),
    "submissions": ("/submissions", "批次总览", "layers"),
    "ops": ("/ops", "运维中心", "terminal"),
}


MODE_LABELS = {
    "single_case_package": "模式 A：单项目整包",
    "batch_same_material": "模式 B：同类批量归档",
}

REVIEW_STRATEGY_LABELS = {
    "auto_review": "直接审查",
    "manual_desensitized_review": "先脱敏后继续审查",
}

REVIEW_STAGE_LABELS = {
    "intake_processing": "导入处理中",
    "desensitized_ready": "脱敏文件已就绪",
    "desensitized_uploaded": "脱敏包已回传",
    "review_processing": "正式审查中",
    "review_completed": "审查已完成",
}

TYPE_LABELS = {
    "agreement": "合作协议",
    "source_code": "源代码",
    "info_form": "信息采集表",
    "software_doc": "软件说明文档",
    "unknown": "待识别",
}

REPORT_LABELS = {
    "material_markdown": "材料审查报告",
    "case_markdown": "项目综合报告",
    "batch_markdown": "批次汇总报告",
}

SEVERITY_LABELS = {
    "severe": "严重",
    "moderate": "中等",
    "minor": "较轻",
}

STATUS_LABELS = {
    "ok": "正常",
    "completed": "已完成",
    "healthy": "健康",
    "pass": "通过",
    "grouped": "已归组",
    "success": "成功",
    "ready": "就绪",
    "warning": "告警",
    "queued": "排队中",
    "processing": "处理中",
    "running": "运行中",
    "needs_review": "待复核",
    "awaiting_manual_review": "待继续审查",
    "skipped": "已跳过",
    "minor": "较轻",
    "moderate": "中等",
    "failed": "失败",
    "interrupted": "已中断",
    "error": "错误",
    "blocked": "阻塞",
    "danger": "高风险",
    "severe": "严重",
    "info": "信息",
    "active": "已启用",
    "idle": "空闲",
    "not_run": "未执行",
    "not_configured": "未配置",
    "mock_mode": "本地模拟",
    "ready_for_probe": "可进行探针",
    "probe_passed": "探针通过",
    "probe_failed": "探针失败",
    "probe_skipped": "探针跳过",
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
    "edit": '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4 11.5-11.5Z"/>',
    "settings": '<path d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z"/><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.04.04a2 2 0 0 1-2.83 2.83l-.04-.04a1.7 1.7 0 0 0-1.88-.34 1.7 1.7 0 0 0-1.03 1.56V21a2 2 0 0 1-4 0v-.07a1.7 1.7 0 0 0-1.03-1.56 1.7 1.7 0 0 0-1.88.34l-.04.04a2 2 0 1 1-2.83-2.83l.04-.04A1.7 1.7 0 0 0 4.6 15a1.7 1.7 0 0 0-1.56-1.03H3a2 2 0 0 1 0-4h.07A1.7 1.7 0 0 0 4.6 8a1.7 1.7 0 0 0-.34-1.88l-.04-.04a2 2 0 1 1 2.83-2.83l.04.04A1.7 1.7 0 0 0 9 4.6a1.7 1.7 0 0 0 1-1.53V3a2 2 0 0 1 4 0v.07A1.7 1.7 0 0 0 15 4.6a1.7 1.7 0 0 0 1.88-.34l.04-.04a2 2 0 0 1 2.83 2.83l-.04.04A1.7 1.7 0 0 0 19.4 9c.26.61.86 1 1.53 1H21a2 2 0 0 1 0 4h-.07A1.7 1.7 0 0 0 19.4 15Z"/>',
    "x": '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
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


def review_strategy_label(review_strategy: str) -> str:
    return REVIEW_STRATEGY_LABELS.get(review_strategy, review_strategy or "-")


def review_stage_label(review_stage: str) -> str:
    return REVIEW_STAGE_LABELS.get(review_stage, review_stage or "-")


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
    if normalized in {"warning", "queued", "processing", "running", "needs_review", "awaiting_manual_review", "skipped", "moderate", "minor"}:
        return "warning"
    if normalized in {"failed", "interrupted", "error", "blocked", "danger", "severe"}:
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
    value_class = "table-cell-value table-cell-value-title" if index == 0 else "table-cell-value"
    return (
        f'<td data-label="{escape_html(header)}">'
        f'<span class="table-cell-label">{escape_html(header)}</span>'
        f'<div class="{value_class}">{cell}</div>'
        "</td>"
    )


def table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return empty_state("暂无数据", "当前视图还没有可显示的内容。")
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
    note_html = f'<span class="kpi-note">{escape_html(note)}</span>' if note else ""
    return (
        f'<article class="kpi-card kpi-card-{escape_html(tone)}">'
        f'<div class="kpi-icon">{icon(icon_name, "icon icon-sm")}</div>'
        '<div class="kpi-copy">'
        f'<span class="kpi-label">{escape_html(label)}</span>'
        f"<strong>{escape_html(value)}</strong>"
        f"{note_html}"
        "</div></article>"
    )


def empty_state(title: str, note: str) -> str:
    return (
        '<div class="empty-state">'
        f"<strong>{escape_html(title)}</strong>"
        f"<span>{escape_html(note)}</span>"
        "</div>"
    )


def contract_markers(*items: str) -> str:
    content = " ".join(escape_html(str(item)) for item in items if str(item))
    return f'<div class="contract-compat" aria-hidden="true">{content}</div>' if content else ""


def notice_banner(
    title: str,
    message: str,
    tone: str = "info",
    *,
    icon_name: str = "spark",
    meta: list[str] | None = None,
) -> str:
    del meta, message, icon_name
    return (
        f'<section class="notice-banner notice-banner-{escape_html(tone)}">'
        '<div class="notice-banner-copy">'
        f"<strong>{escape_html(title)}</strong>"
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
    del kicker, description
    class_name = f"panel {extra_class}".strip()
    id_attr = f' id="{escape_html(panel_id)}"' if panel_id else ""
    icon_html = icon(icon_name, "icon icon-sm panel-head-icon")
    return (
        f'<section{id_attr} class="{class_name}">'
        f'<div class="panel-head">'
        f'{icon_html}'
        f'<div class="panel-head-copy">'
        f"<h2>{escape_html(title)}</h2>"
        f"</div>"
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
        f'<div class="page-link-strip-row">{chips}</div>'
        "</section>"
    )


_asset_cache: dict[str, str] = {}


def _load_static_asset(name: str, fallback: str = "") -> tuple[str, str]:
    key_content = f"{name}:content"
    key_version = f"{name}:version"
    if key_content not in _asset_cache:
        asset_path = Path(__file__).with_name("static") / name
        try:
            content = asset_path.read_text(encoding="utf-8")
        except OSError:
            content = fallback
        _asset_cache[key_content] = content
        _asset_cache[key_version] = hashlib.md5(content.encode()).hexdigest()[:12]
    return _asset_cache[key_content], _asset_cache[key_version]


def render_stylesheet() -> str:
    content, _ = _load_static_asset("styles.css", ".admin-shell{display:block}.panel{padding:16px}.data-table{width:100%}")
    return content


def stylesheet_version() -> str:
    _, version = _load_static_asset("styles.css")
    return version


def render_app_script() -> str:
    content, _ = _load_static_asset("app.js", "")
    return content


def app_script_version() -> str:
    _, version = _load_static_asset("app.js")
    return version


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
    del header_note, header_tag
    home_label = SECTION_LINKS["home"][1]
    submissions_label = SECTION_LINKS["submissions"][1]
    ops_label = SECTION_LINKS["ops"][1]
    page_link_strip = _page_link_strip(page_links)
    subtitle_html = f'<p class="workspace-subtitle">{escape_html(header_subtitle)}</p>' if header_subtitle else ""

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>{escape_html(title)}</title>
  <link rel="stylesheet" href="/static/styles.css?v={stylesheet_version()}">
</head>
<body>
  <a class="skip-link" href="#main-content">跳到主内容</a>
  <div class="admin-shell">
    <aside class="sidebar">
      <a class="sidebar-brand" href="/">
        <span class="sidebar-brand-mark">{icon("shield", "icon")}</span>
        <span class="sidebar-brand-copy">
          <strong>软著分析平台</strong>
        </span>
      </a>

      <div class="sidebar-section">
        <span class="sidebar-label">工作台</span>
        <nav class="sidebar-nav" aria-label="Main navigation">
          {nav_link("/", home_label, active_nav == "home", icon_name="dashboard")}
          {nav_link("/submissions", submissions_label, active_nav == "submissions", icon_name="layers")}
          {nav_link("/ops", ops_label, active_nav == "ops", icon_name="terminal")}
        </nav>
      </div>

    </aside>

    <main id="main-content" class="workspace">
      <header class="workspace-header">
        <div class="workspace-header-main">
          <h1>{escape_html(header_title)}</h1>
          {subtitle_html}
        </div>
        <div class="workspace-header-meta">{header_meta}</div>
      </header>
      {page_link_strip}
      {workspace_notice}
      <div class="workspace-content">{content}</div>
    </main>
  </div>
  <div class="submit-feedback" id="submit-feedback" hidden aria-live="polite" aria-atomic="true">
    <div class="submit-feedback-card">
      <span class="submit-feedback-spinner" aria-hidden="true"></span>
      <div class="submit-feedback-copy">
        <div class="submit-feedback-progress" aria-hidden="true">
          <span class="submit-feedback-progress-fill" id="submit-feedback-progress-fill"></span>
        </div>
        <div class="submit-feedback-step" id="submit-feedback-step">已提交</div>
        <strong id="submit-feedback-title">处理中</strong>
        <p id="submit-feedback-detail">请稍候…</p>
        <div class="inline-actions submit-feedback-actions" id="submit-feedback-actions" hidden></div>
      </div>
    </div>
  </div>
  <script src="/static/app.js?v={app_script_version()}"></script>
</body>
</html>"""


__all__ = [
    "MODE_LABELS",
    "REPORT_LABELS",
    "SEVERITY_LABELS",
    "TYPE_LABELS",
    "contract_markers",
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
    "render_app_script",
    "render_stylesheet",
    "report_label",
    "review_stage_label",
    "review_strategy_label",
    "severity_label",
    "status_label",
    "status_tone",
    "table",
    "type_label",
]
