from __future__ import annotations

from app.core.services.review_profile import default_review_profile
from app.core.services.runtime_store import store
from app.core.utils.text import escape_html

from app.web.review_profile_widgets import render_review_profile_form_fields
from app.web.view_helpers import (
    empty_state,
    icon,
    layout,
    link,
    metric_card,
    mode_label,
    panel,
    pill,
    review_stage_label,
    review_strategy_label,
    status_label,
    status_tone,
    table,
)


def _summary_tile(label: str, value: str, note: str) -> str:
    return (
        '<div class="summary-tile">'
        f"<span>{escape_html(label)}</span>"
        f"<strong>{escape_html(value)}</strong>"
        f"<small>{escape_html(note)}</small>"
        "</div>"
    )


def _import_form() -> str:
    review_profile_fields = render_review_profile_form_fields(default_review_profile(), submit_context="import")
    return f"""
    <div class="import-console-grid import-console-grid-wide">
      <form
        class="admin-form import-console-form import-console-form-primary"
        action="/upload"
        method="post"
        enctype="multipart/form-data"
        data-async-upload-url="/api/submissions/async"
        data-pending-text="分析中，请稍候"
        data-pending-detail="系统正在解析 ZIP、识别材料并执行审查。完成后会自动跳转到批次详情页。"
        data-pending-steps="文件已提交|正在解析材料|正在执行脱敏与审查|正在整理结果页"
        onsubmit="this.classList.add('is-submitting'); var note=this.querySelector('[data-inline-pending]'); if(note) note.hidden=false; var step=this.querySelector('[data-inline-step]'); if(step) step.textContent='文件已提交 -> 正在解析材料 -> 正在执行脱敏与审查'; var btn=this.querySelector('button[type=submit]'); if(btn && !btn.disabled){{ btn.disabled=true; btn.classList.add('is-loading'); btn.innerHTML='<span class=&quot;button-spinner&quot; aria-hidden=&quot;true&quot;></span><span>分析中，请稍候</span>'; }} return true;"
      >
        <div class="import-console-copy">
          <strong>浏览器端导入说明</strong>
          <p>提交后自动进入当前批次。</p>
        </div>
        <label class="field">
          <span>导入模式</span>
          <select name="mode">
            <option value="single_case_package">模式 A：单项目整包</option>
            <option value="batch_same_material">模式 B：同类材料批量归档</option>
          </select>
        </label>
        <label class="field">
          <span>审查策略</span>
          <select name="review_strategy">
            <option value="auto_review">直接审查：导入后立即生成审查结果</option>
            <option value="manual_desensitized_review">先脱敏后继续审查：先下载脱敏件，再手动继续</option>
          </select>
        </label>
        <label class="field">
          <span>ZIP 文件</span>
          <input type="file" name="file" accept=".zip" required>
        </label>
        {review_profile_fields}
        <div class="inline-actions">
          <button class="button-primary" type="submit" data-pending-label="分析中，请稍候">{icon("upload", "icon icon-sm")}开始分析</button>
          <a class="button-secondary" href="/submissions">{icon("layers", "icon icon-sm")}查看批次</a>
        </div>
        <div class="inline-pending-note" data-inline-pending hidden>
          <strong>分析已开始</strong>
          <span data-inline-step>系统会在完成后自动跳转到当前批次。</span>
        </div>
      </form>
      <aside class="import-console-side import-console-side-compact">
        <div class="import-console-copy">
          <strong>结果去向</strong>
          <p>材料、脱敏件、审查结果都在批次页继续处理。</p>
        </div>
        <div class="summary-grid import-summary-grid">
          <div class="summary-tile">
            <span>模式一</span>
            <strong>直接审查</strong>
            <small>上传后直接生成结果。</small>
          </div>
          <div class="summary-tile">
            <span>模式二</span>
            <strong>先脱敏后继续</strong>
            <small>先看脱敏件，再决定继续审查。</small>
          </div>
          <div class="summary-tile">
            <span>结果页</span>
            <strong>自动进入批次详情</strong>
            <small>无需回头再找入口。</small>
          </div>
        </div>
      </aside>
    </div>
    """


def render_home_page() -> str:
    submissions = sorted(store.submissions.values(), key=lambda item: item.created_at, reverse=True)
    cases = list(store.cases.values())
    reports = list(store.report_artifacts.values())

    latest_submission = submissions[0] if submissions else None
    latest_status = latest_submission.status if latest_submission else "idle"
    awaiting_continue_count = sum(1 for item in submissions if getattr(item, "status", "") == "awaiting_manual_review")

    header_meta = "".join(
        [
            pill("上传后自动进入批次", "success"),
            pill(f"{len(submissions)} 个批次", "info"),
            pill(f"{awaiting_continue_count} 个待继续审查", "warning" if awaiting_continue_count else "neutral"),
        ]
    )

    kpis = "".join(
        [
            metric_card("批次数", str(len(submissions)), "当前已导入的批次数量", "info", icon_name="layers"),
            metric_card("项目数", str(len(cases)), "当前已形成的项目数量", "success", icon_name="lock"),
            metric_card("报告数", str(len(reports)), "当前已生成的报告数量", "neutral", icon_name="report"),
        ]
    )

    if latest_submission:
        latest_result_body = (
            '<div class="summary-grid">'
            + _summary_tile("最近批次", latest_submission.filename, "最近一次上传的 ZIP")
            + _summary_tile("处理状态", status_label(latest_submission.status), "当前状态")
            + _summary_tile("导入模式", mode_label(latest_submission.mode), "当前批次模式")
            + _summary_tile("审查策略", review_strategy_label(getattr(latest_submission, "review_strategy", "auto_review")), "当前处理路径")
            + _summary_tile("当前阶段", review_stage_label(getattr(latest_submission, "review_stage", "review_completed")), "当前处理进度")
            + "</div>"
            + '<div class="inline-actions">'
            + f'<a class="button-primary" href="/submissions/{latest_submission.id}">{icon("search", "icon icon-sm")}查看本次结果</a>'
            + f'<a class="button-secondary button-compact" href="/submissions/{latest_submission.id}/materials">{icon("download", "icon icon-sm")}材料与脱敏件</a>'
            + f'<a class="button-secondary button-compact" href="/submissions/{latest_submission.id}/operator">{icon("wrench", "icon icon-sm")}人工处理</a>'
            + f'<a class="button-secondary button-compact" href="/submissions/{latest_submission.id}/exports">{icon("download", "icon icon-sm")}导出结果</a>'
            + "</div>"
        )
    else:
        latest_result_body = (
            empty_state("还没有分析结果", "先上传一个 ZIP，完成后这里会出现最近结果入口。")
            + '<div class="inline-actions"><a class="button-secondary" href="#import-console">'
            + icon("upload", "icon icon-sm")
            + "去上传入口</a></div>"
        )

    recent_rows = [
        [
            link(f"/submissions/{submission.id}", submission.filename),
            escape_html(mode_label(submission.mode)),
            escape_html(review_strategy_label(getattr(submission, "review_strategy", "auto_review"))),
            escape_html(review_stage_label(getattr(submission, "review_stage", "review_completed"))),
            pill(status_label(submission.status), status_tone(submission.status)),
            escape_html(submission.created_at),
        ]
        for submission in submissions[:6]
    ]
    recent_body = (
        table(["批次", "导入模式", "审查策略", "当前阶段", "状态", "导入时间"], recent_rows)
        if recent_rows
        else empty_state("暂无导入记录", "上传 ZIP 后，这里会出现最近的批次和状态。")
    )

    content = f"""
    <section class="kpi-grid">{kpis}</section>
    <section class="dashboard-grid">
      {panel('导入入口', _import_form(), kicker='主入口', extra_class='span-12 panel-soft panel-import-console', icon_name='upload', description='', panel_id='import-console')}
      {panel('最近一次结果', latest_result_body, kicker='结果入口', extra_class='span-12', icon_name='search', description='', panel_id='latest-result')}
      {panel('最近导入记录', recent_body, kicker='运行状态', extra_class='span-12', icon_name='clock', description='', panel_id='recent-imports')}
    </section>
    """

    return layout(
        title="总控台",
        active_nav="home",
        header_tag="总控台",
        header_title="上传一个软著并开始处理",
        header_subtitle="上传 ZIP，选择模式并开始处理。",
        header_meta=header_meta,
        content=content,
        header_note="首页只负责导入和进入最近结果。",
        page_links=[
            ("#import-console", "上传入口", "upload"),
            ("#latest-result", "最近结果", "search"),
            ("#recent-imports", "历史批次", "clock"),
        ],
    )
