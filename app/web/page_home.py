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
    materials = list(store.materials.values())
    cases = list(store.cases.values())
    reports = list(store.report_artifacts.values())

    latest_submission = submissions[0] if submissions else None
    latest_status = latest_submission.status if latest_submission else "idle"
    needs_review_count = sum(
        1 for material in materials if str(getattr(material, "review_status", "")).lower() == "needs_review"
    )

    header_meta = "".join(
        [
            pill("上传即分析", "success"),
            pill(f"{len(submissions)} 个批次", "info"),
            pill("完成后直达结果页", "success"),
        ]
    )

    kpis = "".join(
        [
            metric_card("批次数", str(len(submissions)), "当前运行时已导入的批次数", "info", icon_name="layers"),
            metric_card("项目数", str(len(cases)), "已形成的项目视图", "success", icon_name="lock"),
            metric_card("报告数", str(len(reports)), "可追溯的审查产物", "neutral", icon_name="report"),
            metric_card(
                "待复核",
                str(needs_review_count),
                "等待人工确认的材料",
                "warning" if needs_review_count else status_tone(latest_status),
                icon_name="alert",
            ),
        ]
    )

    import_body = """
    <div class="import-console-grid">
      <div class="import-console-main task-focus-main">
        <div class="helper-chip-row">
          <span class="helper-chip">1. 选择模式</span>
          <span class="helper-chip">2. 上传 ZIP</span>
          <span class="helper-chip">3. 进入批次详情</span>
        </div>
        <div class="import-console-copy">
          <strong>上传一个软著包，然后直接看分析结果</strong>
          <p>首页现在只承担一个任务：把 ZIP 导入系统。提交后会自动跳转到批次详情页，在那里查看待复核队列、项目分组、人工干预台、报告和导出中心。</p>
        </div>
        <div class="summary-grid task-focus-grid">
          <div class="summary-tile">
            <span>模式 A</span>
            <strong>单项目整包</strong>
            <small>一个 ZIP 里已经包含同一个软著项目的完整材料。</small>
          </div>
          <div class="summary-tile">
            <span>模式 B</span>
            <strong>同类批量归档</strong>
            <small>多个软著的同类材料先统一建档，再去批次详情做重组。</small>
          </div>
          <div class="summary-tile">
            <span>结果入口</span>
            <strong>自动跳到批次详情</strong>
            <small>不需要回头找页面，上传完成后直接进入结果工作台。</small>
          </div>
        </div>
      </div>
      <aside class="import-console-side">
        <form class="admin-form import-console-form" action="/upload" method="post" enctype="multipart/form-data">
          <div class="operator-note">
            <strong>浏览器端导入说明</strong>
            <span>先选模式，再上传 ZIP。系统会完成解析、分类、审查，并把你带到当前批次的结果页。</span>
          </div>
          <label class="field">
            <span>导入模式</span>
            <select name="mode">
              <option value="single_case_package">模式 A：单项目整包</option>
              <option value="batch_same_material">模式 B：同类批量归档</option>
            </select>
            <span class="field-hint">不知道怎么选时，如果 ZIP 里是一个完整软著项目，优先选模式 A。</span>
          </label>
          <label class="field">
            <span>ZIP 文件</span>
            <input type="file" name="file" accept=".zip" required>
            <span class="field-hint">仅支持 ZIP。提交后会直接跳转到该批次的详情页。</span>
          </label>
          <div class="helper-chip-row">
            <span class="helper-chip">上传后自动看结果</span>
            <span class="helper-chip">结果页可人工纠偏</span>
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
        </div>
        <div class="operator-note">
          <strong>上传后的查看路径</strong>
          <span>先看待复核队列，再看项目分组和报告，最后进入人工干预台或导出中心。</span>
        </div>
        <div class="inline-actions">
          <a class="button-primary" href="/submissions/%s">%s查看本次结果</a>
          <a class="button-secondary button-compact" href="/submissions/%s#needs-review">%s看待复核</a>
          <a class="button-secondary button-compact" href="/submissions/%s#operator-console">%s去人工干预</a>
          <a class="button-secondary button-compact" href="/submissions/%s#export-center">%s去导出中心</a>
        </div>
        """ % (
            _summary_tile("最近批次", latest_submission.filename, "最近一次上传的 ZIP"),
            _summary_tile("处理状态", status_label(latest_submission.status), "当前这次分析的状态"),
            _summary_tile("材料数", str(len(latest_submission.material_ids)), "这个批次中识别出的材料数量"),
            _summary_tile("项目数", str(len(latest_submission.case_ids)), "系统归组后的项目数量"),
            latest_submission.id,
            icon("search", "icon icon-sm"),
            latest_submission.id,
            icon("alert", "icon icon-sm"),
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
            pill(status_label(submission.status), status_tone(submission.status)),
            escape_html(str(len(submission.material_ids))),
            escape_html(str(len(submission.case_ids))),
            escape_html(submission.created_at),
        ]
        for submission in submissions[:5]
    ]

    recent_body = (
        table(["批次", "模式", "状态", "材料数", "项目数", "导入时间"], recent_rows)
        if recent_rows
        else empty_state("暂无导入记录", "上传 ZIP 后，这里会出现最近的批次和状态。")
    )

    process_body = """
    <div class="sequence-board">
      <article class="sequence-step">
        <span class="sequence-index">1</span>
        <div>
          <strong>上传 ZIP</strong>
          <p>在首页选模式并提交 ZIP。</p>
        </div>
      </article>
      <article class="sequence-step">
        <span class="sequence-index">2</span>
        <div>
          <strong>查看批次详情</strong>
          <p>系统完成处理后，直接进入批次详情页查看材料矩阵和待复核队列。</p>
        </div>
      </article>
      <article class="sequence-step">
        <span class="sequence-index">3</span>
        <div>
          <strong>人工纠偏与导出</strong>
          <p>在批次详情页完成人工干预、重跑审查，再导出报告和批次产物。</p>
        </div>
      </article>
    </div>
    """

    mode_body = """
    <div class="mode-grid">
      <article class="mode-tile">
        <span class="mode-icon">%s</span>
        <strong>模式 A：单项目整包</strong>
        <p>面向同一个软著项目的完整材料包，上传后直接形成一个项目视图和对应报告。</p>
      </article>
      <article class="mode-tile">
        <span class="mode-icon">%s</span>
        <strong>模式 B：同类批量归档</strong>
        <p>面向多个软著的同类材料批量入库，后续在批次详情页进行分组和纠偏。</p>
      </article>
    </div>
    """ % (icon("lock", "icon icon-sm"), icon("layers", "icon icon-sm"))

    content = f"""
    <section class="kpi-grid">{kpis}</section>
    <section class="dashboard-grid">
      {panel('导入台', import_body, kicker='主入口', extra_class='span-12 panel-soft panel-import-console', icon_name='upload', description='先上传，再看结果，不让首页说明文字盖过真正操作。', panel_id='import-console')}
      {panel('最近一次分析', latest_result_body, kicker='结果入口', extra_class='span-12', icon_name='search', description='你刚上传的内容会先回到这里，直接进入待复核、人工干预和导出。', panel_id='latest-result')}
      {panel('怎么走这条链路', process_body, kicker='操作顺序', extra_class='span-7 panel-soft', icon_name='spark', description='首页只负责导入，真正的结果查看和纠偏都在批次详情页。', panel_id='workflow')}
      {panel('两种导入模式', mode_body, kicker='模式选择', extra_class='span-5', icon_name='layers', description='用最少的信息告诉你现在该选哪一种模式。', panel_id='mode-guide')}
      {panel('最近导入记录', recent_body, kicker='运行状态', extra_class='span-12', icon_name='clock', description='如果你想回看之前的分析结果，从这里进入历史批次。', panel_id='recent-imports')}
    </section>
    """

    return layout(
        title="总控台",
        active_nav="home",
        header_tag="总控台",
        header_title="上传一个软著并直接看结果",
        header_subtitle="首页只保留上传、模式选择和结果入口。批次详情页负责看待复核、人工干预、报告和导出。",
        header_meta=header_meta,
        content=content,
        header_note="上传完成后直接跳转到批次详情页；如果要回看历史结果，就从最近批次或批次总览进入。",
        page_links=[
            ("#import-console", "上传入口", "upload"),
            ("#latest-result", "最近结果", "search"),
            ("#recent-imports", "历史批次", "clock"),
        ],
    )
