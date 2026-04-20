from __future__ import annotations

from app.core.services.runtime_store import store
from app.core.utils.text import escape_html

from app.web.view_helpers import empty_state, icon, layout, link, metric_card, mode_label, panel, pill, status_tone, table


def render_home_page() -> str:
    submissions = sorted(store.submissions.values(), key=lambda item: item.created_at, reverse=True)
    materials = list(store.materials.values())
    cases = list(store.cases.values())
    reports = list(store.report_artifacts.values())

    needs_review_count = sum(1 for material in materials if str(getattr(material, "review_status", "")).lower() == "needs_review")
    latest_status = submissions[0].status if submissions else "idle"

    header_meta = "".join(
        [
            pill("MVP Ready", "success"),
            pill(f"{len(submissions)} submissions", "info"),
            pill("Desensitize First", "success"),
        ]
    )

    kpis = "".join(
        [
            metric_card("Submissions", str(len(submissions)), "Imported batches", "info", icon_name="layers"),
            metric_card("Cases", str(len(cases)), "Grouped project views", "success", icon_name="lock"),
            metric_card("Reports", str(len(reports)), "Traceable review artifacts", "neutral", icon_name="report"),
            metric_card(
                "Needs Review",
                str(needs_review_count),
                "Materials waiting for human confirmation",
                "warning" if needs_review_count else status_tone(latest_status),
                icon_name="alert",
            ),
        ]
    )

    recent_rows = [
        [
            link(f"/submissions/{submission.id}", submission.filename),
            escape_html(mode_label(submission.mode)),
            pill(submission.status, status_tone(submission.status)),
            escape_html(str(len(submission.material_ids))),
            escape_html(str(len(submission.case_ids))),
            escape_html(submission.created_at),
        ]
        for submission in submissions[:5]
    ]

    import_body = """
    <div class="helper-chip-row">
      <span class="helper-chip">ZIP only</span>
      <span class="helper-chip">Local desensitization</span>
      <span class="helper-chip">Traceable report chain</span>
    </div>
    <form class="admin-form" action="/upload" method="post" enctype="multipart/form-data">
      <div class="control-grid">
        <label class="field">
          <span>Import Mode</span>
          <select name="mode">
            <option value="single_case_package">single_case_package / 同一软著，多份材料</option>
            <option value="batch_same_material">batch_same_material / 不同软著，同类材料</option>
          </select>
          <span class="field-hint">Mode A handles one project bundle. Mode B handles one material class across multiple projects before regrouping.</span>
        </label>
        <label class="field">
          <span>ZIP Package</span>
          <input type="file" name="file" accept=".zip" required>
          <span class="field-hint">After submit, the console opens the new submission workspace automatically. Live-provider review can make this step take longer.</span>
        </label>
      </div>
      <div class="operator-note">
        <strong>浏览器端导入说明</strong>
        <span>Mode A 用于同一个项目材料成组导入，Mode B 用于同类材料批量归档后再重组。</span>
      </div>
      <div class="helper-chip-row">
        <span class="helper-chip">Opens submission detail after upload</span>
        <span class="helper-chip">Keeps desensitization boundary first</span>
        <span class="helper-chip">Live review may add a short delay</span>
      </div>
      <div class="inline-actions">
        <button class="button-primary" type="submit">%s开始导入</button>
        <a class="button-secondary" href="/submissions">%sOpen Batch Registry</a>
      </div>
    </form>
    """ % (icon("upload", "icon icon-sm"), icon("layers", "icon icon-sm"))

    trust_body = """
    <div class="status-stack">
      <article class="status-card">
        %s
        <span>所有非 mock 边界都只接收本地脱敏后的 llm_safe 载荷。</span>
      </article>
      <article class="status-card">
        %s
        <span>ZIP 导入包含 Zip Slip 防护、可执行文件拦截与 Windows 文件名清洗。</span>
      </article>
      <article class="status-card">
        %s
        <span>Submission、Case、Report 三层产物都可追溯、可下载、可复盘。</span>
      </article>
    </div>
    """ % (
        pill("AI Boundary Safe", "success"),
        pill("ZIP Hardening", "info"),
        pill("Traceable Outputs", "warning"),
    )

    process_body = """
    <div class="process-board">
      <article class="process-step">
        <span class="step-icon">%s</span>
        <strong>Upload Intake</strong>
        <p>接收 ZIP、展开目录、验证文件边界并建立 Submission。</p>
      </article>
      <article class="process-step">
        <span class="step-icon">%s</span>
        <strong>Material Classification</strong>
        <p>结合文件名、目录和正文特征完成材料类型识别。</p>
      </article>
      <article class="process-step">
        <span class="step-icon">%s</span>
        <strong>Rule Review</strong>
        <p>检查一致性、版本、乱码、签署风险与跨材料问题。</p>
      </article>
      <article class="process-step">
        <span class="step-icon">%s</span>
        <strong>Report Delivery</strong>
        <p>输出材料报告、项目报告与批次级综合视图。</p>
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
        <strong>Mode A</strong>
        <p>同一个软著的完整材料包。目标是一次形成完整 Case 与综合报告。</p>
      </article>
      <article class="mode-tile">
        <span class="mode-icon">%s</span>
        <strong>Mode B</strong>
        <p>不同软著、同一类材料的批量归档。先建立档案，再做 regroup。</p>
      </article>
    </div>
    """ % (icon("lock", "icon icon-sm"), icon("layers", "icon icon-sm"))

    recent_body = (
        table(["Submission", "Mode", "Status", "Materials", "Cases", "Created"], recent_rows)
        if recent_rows
        else empty_state("No Imports Yet", "Upload a ZIP package to populate the registry and recent activity feed.")
    )

    content = f"""
    <section class="kpi-grid">{kpis}</section>
    <section class="dashboard-grid">
      {panel('Import Console', import_body, kicker='Control Center', extra_class='span-7 panel-primary', icon_name='upload', description='从这里进入主处理链路：上传、分类、审查、输出。', panel_id='import-console')}
      {panel('Trust Signals', trust_body, kicker='Local Safety', extra_class='span-5', icon_name='shield', description='先建立信任边界，再让操作员进入分析工作流。', panel_id='trust-signals')}
      {panel('Pipeline Analysis', process_body, kicker='Pipeline Analysis', extra_class='span-7', icon_name='bar', description='工作台比营销文案更重要，流程节点必须一眼可见。', panel_id='pipeline-analysis')}
      {panel('Mode Matrix', mode_body, kicker='Import Modes', extra_class='span-5', icon_name='layers', description='两种导入模式服务两类真实工作方式。', panel_id='mode-matrix')}
      {panel('Recent Imports', recent_body, kicker='Runtime Feed', extra_class='span-12', icon_name='clock', description='最近导入的批次、状态和规模都会沉淀到这里。', panel_id='recent-imports')}
    </section>
    """

    return layout(
        title="Control Center",
        active_nav="home",
        header_tag="Control Center",
        header_title="Import Console",
        header_subtitle="Use the admin console to import ZIP packages, compare intake modes, and review the current runtime state.",
        header_meta=header_meta,
        content=content,
        header_note="Start with import intake, confirm the trust boundary, then move directly into recent batches and downstream review.",
        page_links=[
            ("#import-console", "Import Console", "upload"),
            ("#pipeline-analysis", "Pipeline", "bar"),
            ("#recent-imports", "Recent Imports", "clock"),
        ],
    )
