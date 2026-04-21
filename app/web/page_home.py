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
            pill("可用版本", "success"),
            pill(f"{len(submissions)} 个批次", "info"),
            pill("先脱敏再调用", "success"),
        ]
    )

    kpis = "".join(
        [
            metric_card("批次数", str(len(submissions)), "当前运行时已导入的批次", "info", icon_name="layers"),
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
    <div class="import-console-grid">
      <div class="import-console-main">
        <div class="helper-chip-row">
          <span class="helper-chip">ZIP 专用</span>
          <span class="helper-chip">本地脱敏</span>
          <span class="helper-chip">产物可追溯</span>
        </div>
        <div class="import-console-intro">
          <div class="import-console-copy">
            <strong>先判断资料组织方式，再进入导入</strong>
            <p>顶部主入口只做两件事：帮你选对导入模式，并在不挤压文字的前提下直接提交 ZIP。左侧说清模式差异与产物预期，右侧只保留表单与提交动作。</p>
          </div>
          <div class="import-summary-grid">
            <article class="summary-tile">
              <span>导入路径</span>
              <strong>提交后直达批次详情</strong>
              <small>不需要先去别的页面，导入完成后直接进入复核工作区。</small>
            </article>
            <article class="summary-tile">
              <span>模式 A</span>
              <strong>适合单项目整包</strong>
              <small>同一个软著项目的多类材料已经被收在同一个 ZIP 里。</small>
            </article>
            <article class="summary-tile">
              <span>模式 B</span>
              <strong>适合同类批量归档</strong>
              <small>先建档、后分组，适合合作协议、说明文档等同类文件批量入库。</small>
            </article>
          </div>
        </div>
        <div class="compare-grid compare-grid-import">
          <article class="compare-card compare-card-featured">
            <span class="compare-card-label">推荐起点</span>
            <strong>模式 A：单项目整包</strong>
            <p>一个 ZIP 里包含同一个软著项目的多类材料时，用这个模式最稳，导入后可以直接进入完整项目视图。</p>
            <ul class="checklist">
              <li>信息采集表、源代码、说明文档、合作协议都在同一个包里</li>
              <li>希望一次生成项目级结论和批次视图</li>
              <li>适合正式审查前的完整整理</li>
            </ul>
          </article>
          <article class="compare-card">
            <span class="compare-card-label">批量归档</span>
            <strong>模式 B：同类材料批量归档</strong>
            <p>多个软著的同类文件需要先统一入库、再人工重组时，先走这个模式，再在批次详情里做归组和复核。</p>
            <ul class="checklist">
              <li>手上是多个项目的合作协议或同类文档</li>
              <li>先建档，再做分组与纠偏</li>
              <li>适合批量清点与归档前处理</li>
            </ul>
          </article>
        </div>
      </div>
      <aside class="import-console-side">
        <form class="admin-form import-console-form" action="/upload" method="post" enctype="multipart/form-data">
          <div class="operator-note">
            <strong>浏览器端导入说明</strong>
            <span>如果你手上是“同一个项目的完整材料包”，选模式 A；如果是“不同软著的同类文件批量建档”，选模式 B。</span>
          </div>
          <label class="field">
            <span>导入模式</span>
            <select name="mode">
              <option value="single_case_package">模式 A：单项目整包</option>
              <option value="batch_same_material">模式 B：同类批量归档</option>
            </select>
            <span class="field-hint">模式 A 用于同一个软著项目的完整材料包，模式 B 用于不同软著的同类材料批量归档。</span>
          </label>
          <label class="field">
            <span>ZIP 文件</span>
            <input type="file" name="file" accept=".zip" required>
            <span class="field-hint">提交后会自动进入新批次的详情工作区，若启用真实模型，耗时会略有上升。</span>
          </label>
          <div class="helper-chip-row">
            <span class="helper-chip">导入后自动打开批次详情</span>
            <span class="helper-chip">始终先过脱敏边界</span>
            <span class="helper-chip">真实模型可能略慢</span>
          </div>
          <div class="operator-note">
            <strong>提交前检查</strong>
            <span>确认 ZIP 内没有可执行文件，中文文件名尽量保持语义清晰，真实模型联调场景下建议优先用完整材料包做第一轮验证。</span>
          </div>
          <div class="inline-actions">
            <button class="button-primary" type="submit">%s开始导入</button>
            <a class="button-secondary" href="/submissions">%s打开批次总览</a>
          </div>
        </form>
      </aside>
    </div>
    """ % (icon("upload", "icon icon-sm"), icon("layers", "icon icon-sm"))

    trust_body = """
    <div class="trust-signal-grid">
      <article class="trust-signal-card">
        %s
        <strong>AI 边界安全</strong>
        <p>所有非 mock 边界都只接收本地脱敏后的 llm_safe 载荷，真实模型不直接接触原始敏感材料。</p>
      </article>
      <article class="trust-signal-card">
        %s
        <strong>ZIP 入口加固</strong>
        <p>ZIP 导入包含 Zip Slip 防护、可执行文件拦截与 Windows 文件名清洗，入口阶段先把风险卡住。</p>
      </article>
      <article class="trust-signal-card">
        %s
        <strong>产物链路可追溯</strong>
        <p>批次、项目、报告三层产物都可追溯、可下载、可复盘，便于后续复核和交付留痕。</p>
      </article>
    </div>
    """ % (
        pill("AI 边界安全", "success"),
        pill("ZIP 入口加固", "info"),
        pill("产物链路可追溯", "warning"),
    )

    process_body = """
    <div class="process-board">
      <article class="process-step">
        <span class="step-icon">%s</span>
        <strong>导入受理</strong>
        <p>接收 ZIP、展开目录、验证文件边界，并建立批次记录。</p>
      </article>
      <article class="process-step">
        <span class="step-icon">%s</span>
        <strong>材料识别</strong>
        <p>结合文件名、目录和正文特征，完成材料类型分析与归类。</p>
      </article>
      <article class="process-step">
        <span class="step-icon">%s</span>
        <strong>规则审查</strong>
        <p>检查一致性、版本、乱码风险、签署要素和跨材料问题。</p>
      </article>
      <article class="process-step">
        <span class="step-icon">%s</span>
        <strong>报告交付</strong>
        <p>输出材料报告、项目报告与批次级分析视图。</p>
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
        <strong>模式 A</strong>
        <p>面向同一软著项目的完整材料包，目标是一次生成完整的项目视图和综合报告。</p>
      </article>
      <article class="mode-tile">
        <span class="mode-icon">%s</span>
        <strong>模式 B</strong>
        <p>面向不同软著、同一类文档的批量归档，先建档，再重组。</p>
      </article>
    </div>
    """ % (icon("lock", "icon icon-sm"), icon("layers", "icon icon-sm"))

    recent_body = (
        table(["批次", "模式", "状态", "材料数", "项目数", "导入时间"], recent_rows)
        if recent_rows
        else empty_state("暂无导入记录", "上传 ZIP 后，这里会出现最近的批次和运行动态。")
    )

    start_body = """
    <div class="sequence-board">
      <article class="sequence-step">
        <span class="sequence-index">1</span>
        <div>
          <strong>先选导入模式</strong>
          <p>整包走模式 A，同类批量走模式 B，避免后面重复重组。</p>
        </div>
      </article>
      <article class="sequence-step">
        <span class="sequence-index">2</span>
        <div>
          <strong>再看批次详情</strong>
          <p>导入完成后先看待复核队列和材料矩阵，不要直接跳到导出。</p>
        </div>
      </article>
      <article class="sequence-step">
        <span class="sequence-index">3</span>
        <div>
          <strong>最后做人工纠偏</strong>
          <p>改材料类型、调分组、重跑审查，再进入报告和交付。</p>
        </div>
      </article>
    </div>
    """

    content = f"""
    {panel('开始前看这里', start_body, kicker='操作顺序', extra_class='span-12 panel-soft', icon_name='spark', description='先把正确的导入路径走对，后面的复核和导出会顺很多。', panel_id='start-here')}
    <section class="kpi-grid">{kpis}</section>
    <section class="dashboard-grid">
      {panel('导入台', import_body, kicker='总控台', extra_class='span-12 panel-primary', icon_name='upload', description='从这里进入主处理链路：上传、分类、审查、输出。', panel_id='import-console')}
      {panel('可信信号', trust_body, kicker='本地安全', extra_class='span-12', icon_name='shield', description='先建立信任边界，再让操作人员进入分析工作流。', panel_id='trust-signals')}
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
