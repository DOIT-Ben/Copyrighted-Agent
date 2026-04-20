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


def render_home_page() -> str:
    submissions = sorted(store.submissions.values(), key=lambda item: item.created_at, reverse=True)
    materials = list(store.materials.values())
    cases = list(store.cases.values())
    reports = list(store.report_artifacts.values())

    needs_review_count = sum(1 for material in materials if str(getattr(material, "review_status", "")).lower() == "needs_review")
    latest_status = submissions[0].status if submissions else "idle"

    header_meta = "".join(
        [
            pill("\u53ef\u7528\u7248\u672c", "success"),
            pill(f"{len(submissions)} \u4e2a\u6279\u6b21", "info"),
            pill("\u5148\u8131\u654f\u518d\u8c03\u7528", "success"),
        ]
    )

    kpis = "".join(
        [
            metric_card("\u6279\u6b21\u6570", str(len(submissions)), "\u5f53\u524d\u8fd0\u884c\u65f6\u5df2\u5bfc\u5165\u7684\u6279\u6b21", "info", icon_name="layers"),
            metric_card("\u9879\u76ee\u6570", str(len(cases)), "\u5df2\u5f62\u6210\u7684\u9879\u76ee\u89c6\u56fe", "success", icon_name="lock"),
            metric_card("\u62a5\u544a\u6570", str(len(reports)), "\u53ef\u8ffd\u6eaf\u7684\u5ba1\u67e5\u4ea7\u7269", "neutral", icon_name="report"),
            metric_card(
                "\u5f85\u590d\u6838",
                str(needs_review_count),
                "\u7b49\u5f85\u4eba\u5de5\u786e\u8ba4\u7684\u6750\u6599",
                "warning" if needs_review_count else status_tone(latest_status),
                icon_name="alert",
            ),
        ]
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

    import_body = """
    <div class="helper-chip-row">
      <span class="helper-chip">ZIP \u4e13\u7528</span>
      <span class="helper-chip">\u672c\u5730\u8131\u654f</span>
      <span class="helper-chip">\u4ea7\u7269\u53ef\u8ffd\u6eaf</span>
    </div>
    <form class="admin-form" action="/upload" method="post" enctype="multipart/form-data">
      <div class="control-grid">
        <label class="field">
          <span>\u5bfc\u5165\u6a21\u5f0f</span>
          <select name="mode">
            <option value="single_case_package">\u6a21\u5f0f A\uff1a\u5355\u9879\u76ee\u6574\u5305</option>
            <option value="batch_same_material">\u6a21\u5f0f B\uff1a\u540c\u7c7b\u6279\u91cf\u5f52\u6863</option>
          </select>
          <span class="field-hint">\u6a21\u5f0f A \u7528\u4e8e\u540c\u4e00\u4e2a\u8f6f\u8457\u9879\u76ee\u7684\u5b8c\u6574\u6750\u6599\u5305\uff0c\u6a21\u5f0f B \u7528\u4e8e\u4e0d\u540c\u8f6f\u8457\u7684\u540c\u7c7b\u6750\u6599\u6279\u91cf\u5f52\u6863\u3002</span>
        </label>
        <label class="field">
          <span>ZIP \u6587\u4ef6</span>
          <input type="file" name="file" accept=".zip" required>
          <span class="field-hint">\u63d0\u4ea4\u540e\u4f1a\u81ea\u52a8\u8fdb\u5165\u65b0\u6279\u6b21\u7684\u8be6\u60c5\u5de5\u4f5c\u533a\uff0c\u82e5\u542f\u7528\u771f\u5b9e\u6a21\u578b\uff0c\u8017\u65f6\u4f1a\u7565\u6709\u4e0a\u5347\u3002</span>
        </label>
      </div>
      <div class="operator-note">
        <strong>\u6d4f\u89c8\u5668\u7aef\u5bfc\u5165\u8bf4\u660e</strong>
        <span>\u6a21\u5f0f A \u9002\u5408\u201c\u540c\u4e00\u9879\u76ee\u591a\u4efd\u6750\u6599\u201d\uff0c\u6a21\u5f0f B \u9002\u5408\u201c\u4e0d\u540c\u8f6f\u8457\u7684\u540c\u7c7b\u6587\u6863\u6279\u91cf\u6784\u5efa\u201d\u3002</span>
      </div>
      <div class="helper-chip-row">
        <span class="helper-chip">\u5bfc\u5165\u540e\u81ea\u52a8\u6253\u5f00\u6279\u6b21\u8be6\u60c5</span>
        <span class="helper-chip">\u59cb\u7ec8\u5148\u8fc7\u8131\u654f\u8fb9\u754c</span>
        <span class="helper-chip">\u771f\u5b9e\u6a21\u578b\u53ef\u80fd\u7565\u6162</span>
      </div>
      <div class="inline-actions">
        <button class="button-primary" type="submit">%s\u5f00\u59cb\u5bfc\u5165</button>
        <a class="button-secondary" href="/submissions">%s\u6253\u5f00\u6279\u6b21\u603b\u89c8</a>
      </div>
    </form>
    """ % (icon("upload", "icon icon-sm"), icon("layers", "icon icon-sm"))

    trust_body = """
    <div class="status-stack">
      <article class="status-card">
        %s
        <span>\u6240\u6709\u975e mock \u8fb9\u754c\u90fd\u53ea\u63a5\u6536\u672c\u5730\u8131\u654f\u540e\u7684 llm_safe \u8f7d\u8377\u3002</span>
      </article>
      <article class="status-card">
        %s
        <span>ZIP \u5bfc\u5165\u5305\u542b Zip Slip \u9632\u62a4\u3001\u53ef\u6267\u884c\u6587\u4ef6\u62e6\u622a\u4e0e Windows \u6587\u4ef6\u540d\u6e05\u6d17\u3002</span>
      </article>
      <article class="status-card">
        %s
        <span>\u6279\u6b21\u3001\u9879\u76ee\u3001\u62a5\u544a\u4e09\u5c42\u4ea7\u7269\u90fd\u53ef\u8ffd\u6eaf\u3001\u53ef\u4e0b\u8f7d\u3001\u53ef\u590d\u76d8\u3002</span>
      </article>
    </div>
    """ % (
        pill("AI \u8fb9\u754c\u5b89\u5168", "success"),
        pill("ZIP \u5165\u53e3\u52a0\u56fa", "info"),
        pill("\u4ea7\u7269\u94fe\u8def\u53ef\u8ffd\u6eaf", "warning"),
    )

    process_body = """
    <div class="process-board">
      <article class="process-step">
        <span class="step-icon">%s</span>
        <strong>\u5bfc\u5165\u53d7\u7406</strong>
        <p>\u63a5\u6536 ZIP\u3001\u5c55\u5f00\u76ee\u5f55\u3001\u9a8c\u8bc1\u6587\u4ef6\u8fb9\u754c\uff0c\u5e76\u5efa\u7acb\u6279\u6b21\u8bb0\u5f55\u3002</p>
      </article>
      <article class="process-step">
        <span class="step-icon">%s</span>
        <strong>\u6750\u6599\u8bc6\u522b</strong>
        <p>\u7ed3\u5408\u6587\u4ef6\u540d\u3001\u76ee\u5f55\u548c\u6b63\u6587\u7279\u5f81\uff0c\u5b8c\u6210\u6750\u6599\u7c7b\u578b\u5206\u6790\u4e0e\u5f52\u7c7b\u3002</p>
      </article>
      <article class="process-step">
        <span class="step-icon">%s</span>
        <strong>\u89c4\u5219\u5ba1\u67e5</strong>
        <p>\u68c0\u67e5\u4e00\u81f4\u6027\u3001\u7248\u672c\u3001\u4e71\u7801\u98ce\u9669\u3001\u7b7e\u7f72\u8981\u7d20\u548c\u8de8\u6750\u6599\u95ee\u9898\u3002</p>
      </article>
      <article class="process-step">
        <span class="step-icon">%s</span>
        <strong>\u62a5\u544a\u4ea4\u4ed8</strong>
        <p>\u8f93\u51fa\u6750\u6599\u62a5\u544a\u3001\u9879\u76ee\u62a5\u544a\u4e0e\u6279\u6b21\u7ea7\u5206\u6790\u89c6\u56fe\u3002</p>
      </article>
    </div>
    """ % (
        icon("upload", "icon icon-sm"),
        icon("cluster", "icon icon-sm"),
        icon("shield", "icon icon-sm"),
        icon("report", "icon icon-sm"),
    )

    mode_body = """
    <div class="mode-grid">
      <article class="mode-tile">
        <span class="mode-icon">%s</span>
        <strong>\u6a21\u5f0f A</strong>
        <p>\u9762\u5411\u540c\u4e00\u8f6f\u8457\u9879\u76ee\u7684\u5b8c\u6574\u6750\u6599\u5305\uff0c\u76ee\u6807\u662f\u4e00\u6b21\u751f\u6210\u5b8c\u6574\u7684\u9879\u76ee\u89c6\u56fe\u548c\u7efc\u5408\u62a5\u544a\u3002</p>
      </article>
      <article class="mode-tile">
        <span class="mode-icon">%s</span>
        <strong>\u6a21\u5f0f B</strong>
        <p>\u9762\u5411\u4e0d\u540c\u8f6f\u8457\u3001\u540c\u4e00\u7c7b\u6587\u6863\u7684\u6279\u91cf\u5f52\u6863\uff0c\u5148\u5efa\u6863\uff0c\u518d\u91cd\u7ec4\u3002</p>
      </article>
    </div>
    """ % (icon("lock", "icon icon-sm"), icon("layers", "icon icon-sm"))

    recent_body = (
        table(["\u6279\u6b21", "\u6a21\u5f0f", "\u72b6\u6001", "\u6750\u6599\u6570", "\u9879\u76ee\u6570", "\u5bfc\u5165\u65f6\u95f4"], recent_rows)
        if recent_rows
        else empty_state("\u6682\u65e0\u5bfc\u5165\u8bb0\u5f55", "\u4e0a\u4f20 ZIP \u540e\uff0c\u8fd9\u91cc\u4f1a\u51fa\u73b0\u6700\u8fd1\u7684\u6279\u6b21\u548c\u8fd0\u884c\u52a8\u6001\u3002")
    )

    content = f"""
    <section class="kpi-grid">{kpis}</section>
    <section class="dashboard-grid">
      {panel('导入台', import_body, kicker='总控台', extra_class='span-7 panel-primary', icon_name='upload', description='从这里进入主处理链路：上传、分类、审查、输出。', panel_id='import-console')}
      {panel('可信信号', trust_body, kicker='本地安全', extra_class='span-5', icon_name='shield', description='先建立信任边界，再让操作人员进入分析工作流。', panel_id='trust-signals')}
      {panel('流程总览', process_body, kicker='处理链路', extra_class='span-7', icon_name='bar', description='工作台重点不是宣传文案，而是让每个处理节点一眼可见。', panel_id='pipeline-analysis')}
      {panel('模式说明', mode_body, kicker='导入模式', extra_class='span-5', icon_name='layers', description='两种导入模式分别对应两类真实工作场景。', panel_id='mode-matrix')}
      {panel('最近导入', recent_body, kicker='运行动态', extra_class='span-12', icon_name='clock', description='最近导入的批次、状态和规模会沉淀到这里。', panel_id='recent-imports')}
    </section>
    """

    return layout(
        title="总控台",
        active_nav="home",
        header_tag="总控台",
        header_title="导入与分析入口",
        header_subtitle="从这里导入 ZIP 包，对比两种导入模式，并快速掌握当前运行状态。",
        header_meta=header_meta,
        content=content,
        header_note="先完成导入受理，再确认可信边界，然后直接进入批次详情与后续审查。",
        page_links=[
            ("#import-console", "导入台", "upload"),
            ("#pipeline-analysis", "流程总览", "bar"),
            ("#recent-imports", "最近导入", "clock"),
        ],
    )
