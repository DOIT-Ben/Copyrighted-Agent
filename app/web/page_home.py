from __future__ import annotations

from app.core.services.review_profile import default_review_profile
from app.core.services.runtime_store import store
from app.core.utils.text import escape_html

from app.web.review_profile_widgets import render_review_profile_form_fields
from app.web.view_helpers import (
    contract_markers,
    empty_state,
    icon,
    layout,
    panel,
    pill,
    status_label,
)


def _import_form() -> str:
    review_profile_fields = render_review_profile_form_fields(default_review_profile(), submit_context="import")
    return f"""
    <form
      class="admin-form import-console-form import-console-form-primary home-intake-form"
      action="/upload"
      method="post"
      enctype="multipart/form-data"
      data-async-upload-url="/api/submissions/async"
      data-pending-text="处理中"
      data-pending-detail="请稍候，完成后将自动跳转。"
      data-pending-steps="已提交|解析中|审查中|已完成"
    >
      <div class="review-profile-grid import-console-setup-grid">
        <label class="field">
          <span>ZIP 文件</span>
          <input type="file" name="file" accept=".zip" required>
        </label>
        <label class="field">
          <span>导入模式</span>
          <select name="mode">
            <option value="single_case_package">单项目整包</option>
            <option value="batch_same_material">同类材料批量</option>
          </select>
        </label>
        <label class="field">
          <span>审查策略</span>
          <select name="review_strategy">
            <option value="auto_review">直接审查</option>
            <option value="manual_desensitized_review">先脱敏后继续</option>
          </select>
        </label>
      </div>
      {review_profile_fields}
      <div class="inline-actions">
        <button class="button-primary home-primary-action" type="submit" data-pending-label="分析中，请稍候">
          {icon("upload", "icon icon-sm")}开始审查
        </button>
        <a class="button-secondary" href="/submissions">{icon("layers", "icon icon-sm")}查看批次</a>
      </div>
      <div class="inline-pending-note" data-inline-pending hidden>
        <strong>处理中</strong>
        <span data-inline-step>请稍候</span>
      </div>
    </form>
    """


def _quiet_item(label: str, value: str) -> str:
    return (
        '<div class="home-quiet-item">'
        f"<span>{escape_html(label)}</span>"
        f"<strong>{escape_html(value)}</strong>"
        "</div>"
    )


def render_home_page() -> str:
    submissions = sorted(store.submissions.values(), key=lambda item: item.created_at, reverse=True)
    cases = list(store.cases.values())
    reports = list(store.report_artifacts.values())

    latest_submission = submissions[0] if submissions else None
    awaiting_continue_count = sum(1 for item in submissions if getattr(item, "status", "") == "awaiting_manual_review")

    header_meta = "".join(
        [pill(f"{len(submissions)} 批次", "info")]
        + ([pill(f"{awaiting_continue_count} 待继续", "warning")] if awaiting_continue_count else [])
    )

    if latest_submission:
        latest_result_body = (
            '<div class="home-quiet-list">'
            + _quiet_item("最近批次", latest_submission.filename)
            + _quiet_item("当前状态", status_label(latest_submission.status))
            + "</div>"
            + '<div class="inline-actions">'
            + f'<a class="button-primary" href="/submissions/{latest_submission.id}">{icon("search", "icon icon-sm")}查看</a>'
            + "</div>"
        )
    else:
        latest_result_body = empty_state("暂无结果", "上传 ZIP 后查看分析结果")

    overview_body = (
        '<div class="home-quiet-list">'
        + _quiet_item("批次", str(len(submissions)))
        + _quiet_item("项目", str(len(cases)))
        + _quiet_item("报告", str(len(reports)))
        + "</div>"
    )

    content = f"""
    {contract_markers("浏览器端导入说明")}
    <section class="home-stage home-stage-minimal" id="import-console">
      <div class="home-stage-panel">
        {_import_form()}
      </div>
    </section>

    <section class="dashboard-grid home-secondary-grid home-secondary-grid-quiet">
      {panel('最近结果', latest_result_body, kicker='', extra_class='span-7', icon_name='search', description='', panel_id='latest-result')}
      {panel('当前概览', overview_body, kicker='', extra_class='span-5', icon_name='layers', description='', panel_id='recent-imports')}
    </section>

    <aside id="rule-drawer" class="rule-drawer" data-drawer>
      <div class="rule-drawer-backdrop" data-close-drawer></div>
      <div class="rule-drawer-panel">
        <div class="rule-drawer-header">
          <h2>规则配置</h2>
          <button class="rule-drawer-close" data-close-drawer aria-label="关闭">{icon('x', 'icon icon-sm')}</button>
        </div>
        <div class="rule-drawer-content">
          <form class="admin-form" action="/api/global-rules" method="post" data-async-form>
            {render_review_profile_form_fields(default_review_profile(), submit_context="global")}
            <div class="rule-drawer-actions">
              <button class="button-primary" type="submit">{icon('check', 'icon icon-sm')}保存配置</button>
              <button class="button-secondary" type="button" data-close-drawer>取消</button>
            </div>
          </form>
        </div>
      </div>
    </aside>

    <button class="rule-drawer-trigger" data-open-drawer>{icon('settings', 'icon icon-sm')}规则配置</button>
    """

    return layout(
        title="总控台",
        active_nav="home",
        header_tag="",
        header_title="软著审查",
        header_subtitle="导入 ZIP，然后继续查看批次或报告。",
        header_meta=header_meta,
        content=content,
        header_note="",
        page_links=[],
    )
