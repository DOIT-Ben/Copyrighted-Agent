from __future__ import annotations

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
    del note
    return (
        f'<article class="kpi-card kpi-card-{tone}">'
        f'<div class="kpi-icon">{icon(icon_name, "icon icon-md")}</div>'
        '<div class="kpi-copy">'
        f'<span class="kpi-label">{escape_html(label)}</span>'
        f"<strong>{escape_html(value)}</strong>"
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
    del meta
    return (
        f'<section class="notice-banner notice-banner-{escape_html(tone)}">'
        f'<div class="notice-banner-icon">{icon(icon_name, "icon icon-md")}</div>'
        '<div class="notice-banner-copy">'
        f"<strong>{escape_html(title)}</strong>"
        f"<p>{escape_html(message)}</p>"
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
    return (
        f'<section{id_attr} class="{class_name}"><div class="panel-head"><div class="panel-head-copy">'
        f"<h2>{escape_html(title)}</h2></div>"
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
    del header_note
    home_label = SECTION_LINKS["home"][1]
    submissions_label = SECTION_LINKS["submissions"][1]
    ops_label = SECTION_LINKS["ops"][1]
    mode_count = len(MODE_LABELS)
    type_count = max(len(TYPE_LABELS) - 1, 0)
    page_link_strip = _page_link_strip(page_links)

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
  <a class="skip-link" href="#main-content">跳到主内容</a>
  <div class="admin-shell">
    <aside class="sidebar">
      <a class="sidebar-brand" href="/">
        <span class="sidebar-brand-mark">{icon("dashboard", "icon icon-md")}</span>
        <span class="sidebar-brand-copy">
          <strong>软著分析平台</strong>
          <small>中文管理台</small>
        </span>
      </a>

      <section class="sidebar-section">
        <span class="sidebar-label">导航</span>
        <nav class="sidebar-nav" aria-label="Main navigation">
          {nav_link("/", home_label, active_nav == "home", icon_name="dashboard")}
          {nav_link("/submissions", submissions_label, active_nav == "submissions", icon_name="layers")}
          {nav_link("/ops", ops_label, active_nav == "ops", icon_name="terminal")}
        </nav>
      </section>

      <section class="sidebar-section">
        <span class="sidebar-label">处理流程</span>
        <div class="sidebar-list">
          <div class="sidebar-item">{icon("upload", "icon icon-sm")}<span>ZIP 导入</span></div>
          <div class="sidebar-item">{icon("cluster", "icon icon-sm")}<span>自动归类</span></div>
          <div class="sidebar-item">{icon("shield", "icon icon-sm")}<span>规则审查</span></div>
          <div class="sidebar-item">{icon("report", "icon icon-sm")}<span>报告交付</span></div>
        </div>
      </section>

      <section class="sidebar-section sidebar-signal">
        <span class="sidebar-label">运行基线</span>
        <div class="sidebar-mini-kpi">
          <div><strong>{mode_count}</strong><span>导入模式</span></div>
          <div><strong>{type_count}</strong><span>核心材料</span></div>
          <div><strong>safe</strong><span>安全边界</span></div>
        </div>
      </section>
    </aside>

    <main id="main-content" class="workspace">
      <header class="workspace-header">
        <div class="workspace-header-main">
          <span class="workspace-tag">{escape_html(header_tag)}</span>
          <h1>{escape_html(header_title)}</h1>
          <p>{escape_html(header_subtitle)}</p>
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
        <div class="submit-feedback-step" id="submit-feedback-step">文件已提交</div>
        <strong id="submit-feedback-title">正在处理，请稍候</strong>
        <p id="submit-feedback-detail">系统正在提交你的请求。</p>
        <div class="inline-actions submit-feedback-actions" id="submit-feedback-actions" hidden></div>
      </div>
    </div>
  </div>
  <script>
    (() => {{
      const feedback = document.getElementById("submit-feedback");
      const feedbackTitle = document.getElementById("submit-feedback-title");
      const feedbackDetail = document.getElementById("submit-feedback-detail");
      const feedbackProgressFill = document.getElementById("submit-feedback-progress-fill");
      const feedbackStep = document.getElementById("submit-feedback-step");
      const feedbackActions = document.getElementById("submit-feedback-actions");
      if (!feedback || !feedbackTitle || !feedbackDetail || !feedbackProgressFill || !feedbackStep || !feedbackActions) {{
        return;
      }}

      let stageTimer = null;
      const defaultSteps = ["文件已提交", "正在解析材料", "正在执行脱敏与审查", "正在整理结果页"];
      const wait = (milliseconds) => new Promise((resolve) => window.setTimeout(resolve, milliseconds));
      const dimensionKeys = ["identity", "completeness", "consistency", "source_code", "software_doc", "agreement", "ai"];

      const stopStageTimer = () => {{
        if (stageTimer !== null) {{
          window.clearInterval(stageTimer);
          stageTimer = null;
        }}
      }};

      const runStageSequence = (steps, inlineStep) => {{
        const activeSteps = steps.length ? steps : defaultSteps;
        let activeIndex = 0;

        const renderStep = () => {{
          const progress = activeSteps.length <= 1 ? 100 : 18 + Math.round((activeIndex / (activeSteps.length - 1)) * 82);
          feedbackStep.textContent = activeSteps[activeIndex];
          feedbackProgressFill.style.width = progress + "%";
          if (inlineStep) {{
            inlineStep.textContent = activeSteps.slice(0, activeIndex + 1).join(" -> ");
          }}
        }};

        stopStageTimer();
        renderStep();
        if (activeSteps.length <= 1) {{
          return;
        }}

        stageTimer = window.setInterval(() => {{
          if (activeIndex >= activeSteps.length - 1) {{
            stopStageTimer();
            return;
          }}
          activeIndex += 1;
          renderStep();
        }}, 1200);
      }};

      const setFeedbackState = (state) => {{
        feedback.classList.toggle("is-error", state === "error");
      }};

      const clearFeedbackActions = () => {{
        feedbackActions.innerHTML = "";
        feedbackActions.hidden = true;
      }};

      const setFeedbackActions = (actions) => {{
        if (!Array.isArray(actions) || !actions.length) {{
          clearFeedbackActions();
          return;
        }}
        feedbackActions.innerHTML = "";
        for (const item of actions) {{
          if (!item || !item.label) {{
            continue;
          }}
          if (item.kind === "button") {{
            const button = document.createElement("button");
            button.type = "button";
            button.className = item.primary ? "button-primary button-compact" : "button-secondary button-compact";
            button.textContent = String(item.label);
            button.addEventListener("click", () => item.onClick && item.onClick());
            feedbackActions.appendChild(button);
            continue;
          }}
          const link = document.createElement("a");
          link.className = item.primary ? "button-primary button-compact" : "button-secondary button-compact";
          link.href = String(item.href || "#");
          link.textContent = String(item.label);
          feedbackActions.appendChild(link);
        }}
        feedbackActions.hidden = feedbackActions.childElementCount === 0;
      }};

      const jobFailureHint = (payload) => {{
        const errorCode = String(payload.error_code || "").trim();
        const fallback = String(payload.error_message || payload.detail || "").trim();
        const hintMap = {{
          worker_interrupted_during_runtime: "任务在处理过程中中断，可以重新发起导入。",
          filesystem_io_error: "文件读写阶段失败，稍后重试通常可以恢复。",
          source_file_missing: "原始上传文件已经不存在，建议重新上传 ZIP。",
          invalid_zip_archive: "ZIP 文件本身不可用，建议重新打包后再上传。",
          unsupported_submission_mode: "导入模式异常，请重新选择正确模式后提交。",
          unsupported_review_strategy: "审查策略异常，请刷新页面后重新提交。",
          invalid_submission_request: "这次提交参数不完整，建议返回首页重新提交。",
          unexpected_runtime_error: "系统处理过程中出现未预期错误，可以先重试一次。",
        }};
        return hintMap[errorCode] || fallback || "处理失败，请稍后重试。";
      }};

      const pollAsyncJob = async (statusUrl, redirectUrl, inlineStep, pendingDetail) => {{
        for (;;) {{
          const jobResponse = await window.fetch(statusUrl, {{ headers: {{ Accept: "application/json" }} }});
          if (!jobResponse.ok) {{
            throw new Error(await readErrorMessage(jobResponse));
          }}
          const jobPayload = await jobResponse.json();
          applyJobFeedback(jobPayload, inlineStep, pendingDetail);
          if (jobPayload.status === "completed") {{
            clearFeedbackActions();
            feedbackTitle.textContent = "分析完成，正在跳转";
            feedbackDetail.textContent = jobPayload.detail || "批次结果已生成，即将进入详情页。";
            feedbackStep.textContent = jobPayload.stage || "结果已生成";
            feedbackProgressFill.style.width = "100%";
            if (inlineStep) {{
              inlineStep.textContent = jobPayload.stage || "结果已生成";
            }}
            window.setTimeout(() => {{
              window.location.href = redirectUrl;
            }}, 380);
            return;
          }}
          if (jobPayload.status === "failed" || jobPayload.status === "interrupted") {{
            const hint = jobFailureHint(jobPayload);
            throw Object.assign(new Error(hint), {{ jobPayload, redirectUrl }});
          }}
          await wait(900);
        }}
      }};

      const restoreForm = (form) => {{
        form.dataset.submitting = "false";
        form.classList.remove("is-submitting");
        const submitButtons = Array.from(form.querySelectorAll('button[type="submit"], input[type="submit"]'));
        for (const button of submitButtons) {{
          button.disabled = false;
          button.classList.remove("is-loading");
          if (button.tagName === "BUTTON" && button.dataset.originalHtml) {{
            button.innerHTML = button.dataset.originalHtml;
          }}
        }}
      }};

      const applyJobFeedback = (payload, inlineStep, fallbackDetail) => {{
        const jobStage = String(payload.stage || "").trim();
        const jobDetail = String(payload.detail || "").trim();
        const jobProgress = Number(payload.progress || 0);
        feedbackStep.textContent = jobStage || defaultSteps[defaultSteps.length - 1];
        feedbackDetail.textContent = jobDetail || fallbackDetail;
        feedbackProgressFill.style.width = Math.max(8, Math.min(100, jobProgress || 8)) + "%";
        if (inlineStep) {{
          inlineStep.textContent = jobStage || jobDetail || fallbackDetail;
        }}
      }};

      const readErrorMessage = async (response) => {{
        try {{
          const payload = await response.json();
          return payload.detail || payload.message || "提交失败，请稍后重试。";
        }} catch (_error) {{
          return "提交失败，请稍后重试。";
        }}
      }};

      const applyReviewPreset = (button) => {{
        const form = button.closest("form");
        if (!form) {{
          return;
        }}
        const presetKey = String(button.dataset.reviewPreset || "").trim();
        const hiddenPreset = form.querySelector('input[name="review_profile_preset"]');
        if (hiddenPreset) {{
          hiddenPreset.value = presetKey;
        }}
        let profile = null;
        try {{
          profile = JSON.parse(String(button.dataset.reviewProfile || "{{}}"));
        }} catch (_error) {{
          profile = null;
        }}
        if (!profile) {{
          return;
        }}

        const focusMode = form.querySelector('select[name="focus_mode"]');
        const strictness = form.querySelector('select[name="strictness"]');
        const llmInstruction = form.querySelector('textarea[name="llm_instruction"]');
        if (focusMode && profile.focus_mode) {{
          focusMode.value = profile.focus_mode;
        }}
        if (strictness && profile.strictness) {{
          strictness.value = profile.strictness;
        }}
        if (llmInstruction) {{
          llmInstruction.value = String(profile.llm_instruction || "");
        }}
        const enabledDimensions = new Set(Array.isArray(profile.enabled_dimensions) ? profile.enabled_dimensions : []);
        for (const key of dimensionKeys) {{
          const checkbox = form.querySelector('input[name="dimension_' + key + '"]');
          if (checkbox) {{
            checkbox.checked = enabledDimensions.has(key);
          }}
        }}
        const siblingButtons = Array.from(form.querySelectorAll("[data-review-preset]"));
        for (const item of siblingButtons) {{
          item.classList.toggle("is-active", item === button);
        }}
      }};

      const presetButtons = Array.from(document.querySelectorAll("[data-review-preset]"));
      for (const button of presetButtons) {{
        button.addEventListener("click", () => applyReviewPreset(button));
      }}

      const forms = Array.from(document.querySelectorAll("form[data-pending-text]"));
      for (const form of forms) {{
        form.addEventListener("submit", async (event) => {{
          if (form.dataset.submitting === "true") {{
            event.preventDefault();
            return;
          }}

          if (typeof form.reportValidity === "function" && !form.reportValidity()) {{
            return;
          }}

          form.dataset.submitting = "true";
          form.classList.add("is-submitting");
          document.body.classList.add("has-submit-feedback");

          const pendingText = form.dataset.pendingText || "正在处理，请稍候";
          const pendingDetail = form.dataset.pendingDetail || "系统正在提交你的请求。";
          const steps = (form.dataset.pendingSteps || "")
            .split("|")
            .map((item) => item.trim())
            .filter(Boolean);
          const inlineNote = form.querySelector("[data-inline-pending]");
          const inlineStep = form.querySelector("[data-inline-step]");
          if (inlineNote) {{
            inlineNote.classList.remove("is-error");
            inlineNote.hidden = false;
          }}
          clearFeedbackActions();
          feedbackTitle.textContent = pendingText;
          feedbackDetail.textContent = pendingDetail;
          feedback.hidden = false;
          setFeedbackState("running");
          runStageSequence(steps, inlineStep);

          const submitButtons = Array.from(form.querySelectorAll('button[type="submit"], input[type="submit"]'));
          for (const button of submitButtons) {{
            button.disabled = true;
            button.classList.add("is-loading");
            if (button.tagName === "BUTTON") {{
              if (!button.dataset.originalHtml) {{
                button.dataset.originalHtml = button.innerHTML;
              }}
              const pendingLabel = button.dataset.pendingLabel || pendingText;
              button.innerHTML = '<span class="button-spinner" aria-hidden="true"></span><span>' + pendingLabel + "</span>";
            }}
          }}

          const asyncUrl = form.dataset.asyncUploadUrl;
          if (!asyncUrl || !window.fetch || !window.FormData) {{
            return;
          }}

          event.preventDefault();
          try {{
            const submitResponse = await window.fetch(asyncUrl, {{
              method: (form.method || "POST").toUpperCase(),
              body: new window.FormData(form),
              headers: {{ Accept: "application/json" }},
            }});
            if (!submitResponse.ok) {{
              throw new Error(await readErrorMessage(submitResponse));
            }}

            const submitPayload = await submitResponse.json();
            const statusUrl = submitPayload.status_url || (submitPayload.job_id ? "/api/jobs/" + submitPayload.job_id : "");
            const redirectUrl = submitPayload.redirect_url || (submitPayload.submission_id ? "/submissions/" + submitPayload.submission_id : "/submissions");
            stopStageTimer();

            if (!statusUrl) {{
              window.location.href = redirectUrl;
              return;
            }}

            await pollAsyncJob(statusUrl, redirectUrl, inlineStep, pendingDetail);
          }} catch (error) {{
            stopStageTimer();
            setFeedbackState("error");
            feedbackTitle.textContent = "分析失败，请重试";
            const jobPayload = error && typeof error === "object" && "jobPayload" in error ? error.jobPayload : null;
            const redirectUrl = error && typeof error === "object" && "redirectUrl" in error ? error.redirectUrl : "";
            feedbackDetail.textContent = error instanceof Error ? error.message : "系统处理失败，请稍后重试。";
            feedbackStep.textContent = "本次提交未完成";
            feedbackProgressFill.style.width = "100%";
            if (inlineNote) {{
              inlineNote.classList.add("is-error");
            }}
            if (inlineStep) {{
              inlineStep.textContent = error instanceof Error ? error.message : "系统处理失败，请稍后重试。";
            }}
            const actions = [];
            if (redirectUrl) {{
              actions.push({{ kind: "link", label: "查看批次详情", href: redirectUrl, primary: false }});
            }}
            if (jobPayload && jobPayload.can_retry && jobPayload.retry_url) {{
              actions.unshift({{
                kind: "button",
                label: "立即重试",
                primary: true,
                onClick: async () => {{
                  clearFeedbackActions();
                  setFeedbackState("running");
                  feedbackTitle.textContent = "正在重新发起任务";
                  feedbackDetail.textContent = "系统正在根据原始上传文件重试导入。";
                  feedbackStep.textContent = "重新进入处理队列";
                  feedbackProgressFill.style.width = "18%";
                  try {{
                    const retryResponse = await window.fetch(String(jobPayload.retry_url), {{ method: "POST", headers: {{ Accept: "application/json" }} }});
                    if (!retryResponse.ok) {{
                      throw new Error(await readErrorMessage(retryResponse));
                    }}
                    const retryPayload = await retryResponse.json();
                    await pollAsyncJob(String(retryPayload.status_url || ""), String(retryPayload.redirect_url || redirectUrl || "/submissions"), inlineStep, pendingDetail);
                  }} catch (retryError) {{
                    setFeedbackState("error");
                    feedbackTitle.textContent = "重试失败";
                    feedbackDetail.textContent = retryError instanceof Error ? retryError.message : "任务重试失败，请稍后再试。";
                    feedbackStep.textContent = "重试未完成";
                    setFeedbackActions(actions);
                  }}
                }},
              }});
            }}
            setFeedbackActions(actions);
            restoreForm(form);
          }}
        }});
      }}
    }})();
  </script>
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
    "review_stage_label",
    "review_strategy_label",
    "severity_label",
    "status_label",
    "status_tone",
    "table",
    "type_label",
]
