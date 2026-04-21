from __future__ import annotations

from app.core.services.runtime_store import store
from app.core.utils.text import escape_html

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


def render_home_page() -> str:
    submissions = sorted(store.submissions.values(), key=lambda item: item.created_at, reverse=True)
    cases = list(store.cases.values())
    reports = list(store.report_artifacts.values())

    latest_submission = submissions[0] if submissions else None
    latest_status = latest_submission.status if latest_submission else "idle"
    awaiting_continue_count = sum(1 for item in submissions if getattr(item, "status", "") == "awaiting_manual_review")

    header_meta = "".join(
        [
            pill("上传即进入批次工作台", "success"),
            pill(f"{len(submissions)} 个批次", "info"),
            pill(f"{awaiting_continue_count} 个待继续审查", "warning" if awaiting_continue_count else "neutral"),
        ]
    )

    kpis = "".join(
        [
            metric_card("批次数", str(len(submissions)), "当前已导入的批次数量", "info", icon_name="layers"),
            metric_card("项目数", str(len(cases)), "当前已形成的项目视图数量", "success", icon_name="lock"),
            metric_card("报告数", str(len(reports)), "当前已生成的交付型报告数量", "neutral", icon_name="report"),
            metric_card(
                "待继续审查",
                str(awaiting_continue_count),
                "已完成脱敏、等待人工确认后继续审查的批次",
                "warning" if awaiting_continue_count else status_tone(latest_status),
                icon_name="alert",
            ),
        ]
    )

    import_body = """
    <div class="import-console-grid">
      <div class="import-console-main task-focus-main">
        <div class="helper-chip-row">
          <span class="helper-chip">1. 选择导入模式</span>
          <span class="helper-chip">2. 选择审查策略</span>
          <span class="helper-chip">3. 上传 ZIP 并进入批次</span>
        </div>
        <div class="import-console-copy">
          <strong>上传一个软著包，然后按你需要的节奏完成审查</strong>
          <p>首页只负责导入。提交后会自动跳到批次详情页，在那里继续下载脱敏件、查看进度、回传脱敏包、继续审查和导出结果。</p>
        </div>
        <div class="summary-grid task-focus-grid">
          <div class="summary-tile">
            <span>策略一</span>
            <strong>直接审查</strong>
            <small>上传后立即生成项目审查结果和报告，适合标准流程。</small>
          </div>
          <div class="summary-tile">
            <span>策略二</span>
            <strong>先脱敏后继续审查</strong>
            <small>系统先完成解析与脱敏，支持下载脱敏件，或上传脱敏包后再继续审查。</small>
          </div>
          <div class="summary-tile">
            <span>结果入口</span>
            <strong>自动跳到批次详情</strong>
            <small>不需要回头找页面，导入完成后直接进入当前批次工作台。</small>
          </div>
        </div>
      </div>
      <aside class="import-console-side">
        <form class="admin-form import-console-form" action="/upload" method="post" enctype="multipart/form-data">
          <div class="operator-note">
            <strong>浏览器端导入说明</strong>
            <span>先选导入模式，再选审查策略，然后上传 ZIP。系统会完成解析、分类和脱敏，并把你带到当前批次结果页。</span>
          </div>
          <label class="field">
            <span>导入模式</span>
            <select name="mode">
              <option value="single_case_package">模式 A：单项目整包</option>
              <option value="batch_same_material">模式 B：同类材料批量归档</option>
            </select>
            <span class="field-hint">如果 ZIP 里是一个完整软著项目，优先选择模式 A。</span>
          </label>
          <label class="field">
            <span>审查策略</span>
            <select name="review_strategy">
              <option value="auto_review">直接审查：导入后立即生成审查结果</option>
              <option value="manual_desensitized_review">先脱敏后继续审查：先下载脱敏件，再手动继续</option>
            </select>
            <span class="field-hint">如果你想先查看脱敏文件，再决定是否进入正式审查，请选择第二项。</span>
          </label>
          <label class="field">
            <span>ZIP 文件</span>
            <input type="file" name="file" accept=".zip" required>
            <span class="field-hint">仅支持 ZIP。提交后会直接跳到该批次的详情页。</span>
          </label>
          <div class="helper-chip-row">
            <span class="helper-chip">首页只做导入</span>
            <span class="helper-chip">批次页负责脱敏与审查</span>
            <span class="helper-chip">结果页可直接导出</span>
          </div>
          <div class="inline-actions">
            <button class="button-primary" type="submit">%s开始分析</button>
            <a class="button-secondary" href="/submissions">%s查看批次总览</a>
          </div>
        </form>
      </aside>
    </div>
    """ % (icon("upload", "icon icon-sm"), icon("layers", "icon icon-sm"))

    if latest_submission:
        latest_result_body = """
        <div class="summary-grid">
          %s
          %s
          %s
          %s
          %s
        </div>
        <div class="inline-actions">
          <a class="button-primary" href="/submissions/%s">%s查看本次结果</a>
          <a class="button-secondary button-compact" href="/submissions/%s/materials">%s看材料与脱敏件</a>
          <a class="button-secondary button-compact" href="/submissions/%s/operator">%s去人工处理</a>
          <a class="button-secondary button-compact" href="/submissions/%s/exports">%s去导出中心</a>
        </div>
        """ % (
            _summary_tile("最近批次", latest_submission.filename, "最近一次上传的 ZIP"),
            _summary_tile("处理状态", status_label(latest_submission.status), "当前这次导入的最新状态"),
            _summary_tile("导入模式", mode_label(latest_submission.mode), "当前批次使用的导入模式"),
            _summary_tile("审查策略", review_strategy_label(getattr(latest_submission, "review_strategy", "auto_review")), "决定是直接审查还是先脱敏后继续"),
            _summary_tile("当前阶段", review_stage_label(getattr(latest_submission, "review_stage", "review_completed")), "显示是否已完成脱敏、已回传脱敏包或已完成正式审查"),
            latest_submission.id,
            icon("search", "icon icon-sm"),
            latest_submission.id,
            icon("download", "icon icon-sm"),
            latest_submission.id,
            icon("wrench", "icon icon-sm"),
            latest_submission.id,
            icon("download", "icon icon-sm"),
        )
    else:
        latest_result_body = (
            empty_state("还没有分析结果", "先上传一个 ZIP，系统完成分析后会在这里给出最近一次结果入口。")
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
            escape_html(str(len(submission.material_ids))),
            escape_html(str(len(submission.case_ids))),
            escape_html(submission.created_at),
        ]
        for submission in submissions[:6]
    ]

    recent_body = (
        table(["批次", "导入模式", "审查策略", "当前阶段", "状态", "材料数", "项目数", "导入时间"], recent_rows)
        if recent_rows
        else empty_state("暂无导入记录", "上传 ZIP 后，这里会出现最近的批次和状态。")
    )

    process_body = """
    <div class="sequence-board">
      <article class="sequence-step">
        <span class="sequence-index">1</span>
        <div>
          <strong>上传 ZIP</strong>
          <p>在首页选导入模式和审查策略，然后提交 ZIP。</p>
        </div>
      </article>
      <article class="sequence-step">
        <span class="sequence-index">2</span>
        <div>
          <strong>查看脱敏与进度</strong>
          <p>系统完成解析后，进入批次详情页查看材料、脱敏件和当前阶段。</p>
        </div>
      </article>
      <article class="sequence-step">
        <span class="sequence-index">3</span>
        <div>
          <strong>回传脱敏包或继续审查</strong>
          <p>脱敏优先模式支持先下载脱敏件，也支持上传脱敏包后再继续项目审查。</p>
        </div>
      </article>
    </div>
    """

    content = f"""
    <section class="kpi-grid">{kpis}</section>
    <section class="dashboard-grid">
      {panel('导入入口', import_body, kicker='主入口', extra_class='span-12 panel-soft panel-import-console', icon_name='upload', description='先上传，再进入批次详情继续处理。', panel_id='import-console')}
      {panel('最近一次分析', latest_result_body, kicker='结果入口', extra_class='span-12', icon_name='search', description='最新一次上传会优先回到这里。', panel_id='latest-result')}
      {panel('处理顺序', process_body, kicker='流程说明', extra_class='span-5 panel-soft', icon_name='spark', description='首页只负责导入，批次页负责处理与结果。', panel_id='workflow')}
      {panel('最近导入记录', recent_body, kicker='运行状态', extra_class='span-7', icon_name='clock', description='如需回看历史结果，从这里进入对应批次。', panel_id='recent-imports')}
    </section>
    """

    return layout(
        title="总控台",
        active_nav="home",
        header_tag="总控台",
        header_title="上传一个软著并开始处理",
        header_subtitle="首页只保留导入、模式选择和结果入口。材料、脱敏、审查和导出都放到批次页继续完成。",
        header_meta=header_meta,
        content=content,
        header_note="如果想先看脱敏件，再选择“先脱敏后继续审查”；如果想直接得到结果，就选择“直接审查”。",
        page_links=[
            ("#import-console", "上传入口", "upload"),
            ("#latest-result", "最近结果", "search"),
            ("#recent-imports", "历史批次", "clock"),
        ],
    )
