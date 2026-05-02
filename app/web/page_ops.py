from __future__ import annotations

from app.core.services.ops_status import (
    format_signed_delta,
    latest_metrics_baseline_status,
    latest_runtime_backup_status,
    list_metrics_baseline_history,
)
from app.core.services.sqlite_repository import list_correction_feedback, list_manual_review_queue, list_retryable_jobs
from app.core.services.submission_insights import (
    label_for_correction_outcome,
    label_for_correction_reason,
    label_for_manual_review_reason,
    label_for_parse_reason,
    label_for_unknown_reason,
)
from app.core.utils.text import escape_html
from app.web.view_helpers import download_chip, empty_state, layout, link, list_pairs, metric_card, panel, pill, status_label, status_tone, table


STATUS_TEXT = {
    "mock_mode": "本地 mock",
    "provider_no_probe_required": "无需探针",
    "disabled": "已关闭",
    "configured_disabled": "已配置未启用",
    "not_configured": "未配置",
    "partially_configured": "部分配置",
    "ready_for_probe": "可探针",
    "probe_passed": "探针通过",
    "probe_failed": "探针失败",
    "probe_skipped": "探针跳过",
    "ready_for_business_handoff": "可业务交付",
    "ready_for_operator_trial": "可试跑",
    "not_ready": "未就绪",
}

PROVIDER_TEXT = {
    "mock": "本地 mock",
    "safe_stub": "安全桩",
    "external_http": "外部 HTTP",
}

LABEL_TEXT = {
    "Provider": "提供方",
    "Provider Readiness": "模型通道",
    "HTTP Probe": "探针",
    "Endpoint": "接口地址",
    "Model": "模型标识",
    "API Key Env": "API Key 环境变量",
    "Fallback": "回退策略",
    "Release Gate": "发布闸门",
    "Latest Release Validation": "最近校验",
    "Real Sample Baseline": "真实样本基线",
    "Runtime Backup": "运行时备份",
    "Acceptance Checklist": "验收清单",
    "Startup Self Check": "启动自检",
    "Data Root": "数据目录",
    "Uploads": "上传目录",
    "SQLite Parent": "SQLite 上级目录",
    "Log Parent": "日志上级目录",
    "Config Template": "配置模板",
    "Local Config": "本地配置",
    "AI Boundary": "AI 边界",
}

TEXT_REPLACEMENTS = {
    "directory writable": "目录可写",
    "parent directory writable": "上级目录可写",
    "config template found": "已找到配置模板",
    "local config found": "已找到本地配置",
    "not configured": "未配置",
    "not recorded": "未记录",
    "none recorded": "无",
    "desensitized only": "仅允许脱敏载荷",
    "No Baseline Yet": "暂无基线",
    "No Backup Yet": "暂无备份",
    "Release gate status is unavailable.": "暂无发布闸门结论。",
    "No latest provider probe yet.": "暂无最新探针记录。",
    "No rolling baseline artifact is available yet.": "暂无滚动基线产物。",
    "No successful provider probe is available yet.": "暂无成功探针记录。",
    "No failed provider probe is available yet.": "暂无失败探针记录。",
}


def _localize_text(value: object, default: str = "-") -> str:
    text = str(value or "").strip()
    if not text:
        return default
    for source, target in TEXT_REPLACEMENTS.items():
        text = text.replace(source, target)
    return text


def _display_value(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return "-"
    normalized = text.lower()
    if normalized in STATUS_TEXT:
        return STATUS_TEXT[normalized]
    if normalized in PROVIDER_TEXT:
        return PROVIDER_TEXT[normalized]
    if normalized in {"true", "false"}:
        return "是" if normalized == "true" else "否"
    return _localize_text(text, text)


def _label(value: object) -> str:
    text = str(value or "").strip()
    return LABEL_TEXT.get(text, text or "-")


def _status_pill(value: object) -> str:
    status = str(value or "unknown")
    return pill(status_label(status), status_tone(status))


def _summary_tile(label: str, value: str) -> str:
    return (
        '<div class="summary-tile">'
        f"<span>{escape_html(label)}</span>"
        f"<strong>{escape_html(value)}</strong>"
        "</div>"
    )


def _command_block(title: str, command: str) -> str:
    return (
        '<div class="command-block">'
        f"<strong>{escape_html(title)}</strong>"
        f"<code>{escape_html(command)}</code>"
        "</div>"
    )


def _details_block(index: str, title: str, body: str, *, open_by_default: bool = False) -> str:
    open_attr = " open" if open_by_default else ""
    return (
        f'<details class="operator-group"{open_attr}>'
        "<summary>"
        f'<span class="operator-group-index">{escape_html(index)}</span>'
        f"<div><strong>{escape_html(title)}</strong></div>"
        "</summary>"
        f'<div class="control-grid">{body}</div>'
        "</details>"
    )


def _ops_callout_text(status: object, summary: object, recommended_action: object, default_text: str) -> str:
    summary_text = _localize_text(summary, "").strip()
    action_text = _localize_text(recommended_action, "").strip()
    normalized_status = str(status or "warning").strip().lower()
    if normalized_status == "pass":
        return summary_text or default_text
    if action_text:
        return action_text
    return summary_text or default_text


def _closeout_action_list(actions: list[object]) -> str:
    if not actions:
        return "<li>当前没有额外动作，可以继续交付、试运行或现场演示。</li>"
    return "".join(f"<li>{escape_html(_localize_text(item, str(item or '')))}</li>" for item in actions[:4])


def _ops_table(rows: list[list[str]], headers: list[str], empty_title: str, empty_note: str) -> str:
    if not rows:
        return empty_state(empty_title, empty_note)
    return table(headers, rows)


def _retryable_job_rows(limit: int = 8, *, status_filter: str = "", error_filter: str = "") -> list[dict]:
    rows = list_retryable_jobs(limit=limit, status_filter=status_filter, error_filter=error_filter)
    for payload in rows:
        payload["can_retry"] = True
    return rows


def _retryable_jobs_panel(filters: dict | None = None) -> str:
    filters = dict(filters or {})
    status_filter = str(filters.get("job_status", "") or "").strip().lower()
    error_filter = str(filters.get("job_error", "") or "").strip().lower()
    rows = _retryable_job_rows(status_filter=status_filter, error_filter=error_filter)
    filter_form = (
        '<form class="quick-filter-form" action="/ops" method="get">'
        '<label class="field"><span>任务状态</span>'
        '<select name="job_status">'
        f'<option value=""{" selected" if not status_filter else ""}>全部</option>'
        f'<option value="failed"{" selected" if status_filter == "failed" else ""}>失败</option>'
        f'<option value="interrupted"{" selected" if status_filter == "interrupted" else ""}>已中断</option>'
        "</select></label>"
        f'<label class="field"><span>失败码包含</span><input type="text" name="job_error" value="{escape_html(error_filter)}" placeholder="例如：filesystem"></label>'
        '<div class="inline-actions"><button class="button-secondary button-compact" type="submit">筛选</button><a class="button-secondary button-compact" href="/ops#ops-retry-jobs">清空</a></div>'
        "</form>"
    )
    if not rows:
        return filter_form + empty_state("暂无可重试任务", "当前没有失败或中断且支持重试的导入任务。")

    table_rows = []
    for item in rows:
        submission_id = str(item.get("scope_id", "") or "").strip()
        error_value = str(item.get("error_code", "") or item.get("error_message", "") or item.get("detail", "") or "-").strip() or "-"
        table_rows.append(
            [
                link(f"/submissions/{submission_id}", submission_id or "submission"),
                _status_pill(item.get("status", "warning")),
                escape_html(error_value),
                escape_html(str((item.get("metadata", {}) or {}).get("retry_count", 0) or 0)),
                escape_html(str(item.get("updated_at", "") or item.get("started_at", "") or "-")),
            ]
        )
    return filter_form + table(["批次", "状态", "失败原因", "已重试", "最近更新时间"], table_rows)


def _manual_review_queue_panel() -> str:
    rows = list_manual_review_queue(limit=8)
    if not rows:
        return empty_state("暂无待人工复核解析", "当前没有需要优先人工确认的解析结果。")

    table_rows: list[list[str]] = []
    for item in rows:
        metadata = dict(item.get("metadata_json", {}) or {})
        triage = dict(metadata.get("triage", {}) or {})
        parse_quality = dict(metadata.get("parse_quality", {}) or {})
        reason_code = str(
            triage.get("manual_review_reason_code")
            or triage.get("unknown_reason")
            or triage.get("quality_review_reason_code")
            or parse_quality.get("review_reason_code")
            or ""
        ).strip()
        if reason_code.startswith("manual_review_required_"):
            reason_label = label_for_manual_review_reason(reason_code)
        elif reason_code in {"blocked_low_quality_content_signal", "binary_doc_parse_failed", "no_matching_rule"}:
            reason_label = label_for_unknown_reason(reason_code)
        else:
            reason_label = label_for_parse_reason(reason_code)
        table_rows.append(
            [
                escape_html(str(item.get("material_id", "") or "-")),
                pill("待复核", "warning"),
                escape_html(str(parse_quality.get("quality_level", "") or "-")),
                escape_html(reason_label),
                escape_html(str(triage.get("legacy_doc_bucket") or parse_quality.get("legacy_doc_bucket") or "-")),
            ]
        )
    return table(["材料", "状态", "质量", "原因", "桶位"], table_rows)


def _correction_feedback_panel() -> str:
    rows = list_correction_feedback(limit=8)
    if not rows:
        return empty_state("暂无更正闭环数据", "当前还没有可展示的人工纠错效果记录。")

    table_rows: list[list[str]] = []
    for item in rows:
        analysis = dict(item.get("analysis", {}) or {})
        delta = dict(analysis.get("delta", {}) or {})
        outcome_code = str(item.get("outcome_code", "") or analysis.get("outcome_code", "") or "")
        table_rows.append(
            [
                escape_html(label_for_correction_reason(str(item.get("reason_code", "") or ""))),
                escape_html(label_for_correction_outcome(outcome_code)),
                escape_html(f"{int(delta.get('unknown_materials', 0) or 0):+d}"),
                escape_html(f"{int(delta.get('manual_review_materials', 0) or 0):+d}"),
                escape_html(str(item.get("corrected_at", "") or "-")),
            ]
        )
    return table(["动作原因", "效果", "未知材料变化", "待复核变化", "时间"], table_rows)


def render_ops_page_legacy(config: dict, self_check: dict) -> str:
    provider_readiness = dict(self_check.get("provider_readiness", {}) or {})
    provider_probe_status = dict(self_check.get("provider_probe_status", {}) or {})
    provider_probe_history = list(self_check.get("provider_probe_history", []) or [])
    provider_probe_last_success = dict(self_check.get("provider_probe_last_success", {}) or {})
    provider_probe_last_failure = dict(self_check.get("provider_probe_last_failure", {}) or {})
    release_gate = dict(self_check.get("release_gate", {}) or {})
    delivery_closeout = dict(self_check.get("delivery_closeout", {}) or {})
    local_config = dict(self_check.get("local_config", {}) or {})

    baseline_status = latest_metrics_baseline_status()
    baseline_history = list_metrics_baseline_history(limit=6)
    latest_baseline = baseline_history[0] if baseline_history else {}
    backup_status = latest_runtime_backup_status()

    closeout_rows = [
        [
            escape_html(_label(item.get("label", item.get("name", "")))),
            _status_pill(item.get("status", "warning")),
            escape_html(_display_value(item.get("value", ""))),
            escape_html(_localize_text(item.get("summary", ""))),
        ]
        for item in delivery_closeout.get("checks", [])
    ]
    release_rows = [
        [
            escape_html(_label(item.get("label", item.get("name", "")))),
            _status_pill(item.get("status", "warning")),
            escape_html(_display_value(item.get("value", ""))),
            escape_html(_localize_text(item.get("detail", ""))),
        ]
        for item in release_gate.get("checks", [])
    ]
    provider_rows = [
        [
            escape_html(_label(item.get("label", item.get("name", "")))),
            _status_pill(item.get("status", "warning")),
            escape_html(_display_value(item.get("value", ""))),
            escape_html(_localize_text(item.get("detail", ""))),
        ]
        for item in provider_readiness.get("checks", [])
    ]
    startup_rows = [
        [
            escape_html(_label(item.get("label", item.get("name", "")))),
            _status_pill(item.get("status", "warning")),
            escape_html(item.get("path", "") or "-"),
            escape_html(_localize_text(item.get("detail", ""))),
        ]
        for item in self_check.get("checks", [])
    ]
    probe_rows = [
        [
            escape_html(item.get("file_name", "") or "-"),
            _status_pill(item.get("probe_status", "not_run")),
            escape_html(item.get("generated_at", "") or item.get("updated_at", "") or "-"),
            escape_html(str(item.get("http_status", 0) or "n/a") if item.get("attempted") else "n/a"),
            escape_html(item.get("error_code", "") or _localize_text(item.get("summary", ""), "-")),
        ]
        for item in provider_probe_history[:8]
    ]
    baseline_rows = [
        [
            escape_html(item.get("file_name", "") or "-"),
            _status_pill(item.get("status", "warning")),
            escape_html(item.get("generated_at", "") or item.get("updated_at", "") or "-"),
            escape_html(str(item.get("totals", {}).get("needs_review", 0))),
            escape_html(str(item.get("totals", {}).get("low_quality", 0))),
            escape_html(format_signed_delta(item.get("delta_totals", {}).get("needs_review"))),
        ]
        for item in baseline_history
    ]

    latest_probe_status = str(provider_probe_status.get("probe_status", "not_run") or "not_run")
    latest_probe_download = (
        download_chip("/downloads/ops/provider-probe/latest", "最新 Probe JSON")
        if provider_probe_status.get("exists")
        else ""
    )

    common_commands = "".join(
        [
            _command_block("启动演示", r"powershell -ExecutionPolicy Bypass -File scripts\start_mock_web.ps1"),
            _command_block("启动真实桥接", r"powershell -ExecutionPolicy Bypass -File scripts\start_real_bridge.ps1"),
            _command_block("启动真实 Web", r"powershell -ExecutionPolicy Bypass -File scripts\start_real_web.ps1"),
            _command_block("真实验证", r"powershell -ExecutionPolicy Bypass -File scripts\run_real_validation.ps1"),
            _command_block("查看栈状态", r"powershell -ExecutionPolicy Bypass -File scripts\show_stack_status.ps1"),
            _command_block("发布闸门", r"py -m app.tools.release_gate --config config\local.json"),
        ]
    )
    maintenance_commands = "".join(
        [
            _command_block("运行时清理", "py -m app.tools.runtime_cleanup"),
            _command_block("运行时备份", "py -m app.tools.runtime_backup create"),
            _command_block("Provider Sandbox", "py -m app.tools.provider_sandbox"),
            _command_block("Provider Probe", "py -m app.tools.provider_probe"),
            _command_block("Delivery Closeout", "py -m app.tools.delivery_closeout"),
            _command_block(
                "MiniMax 桥接",
                r"py -m app.tools.minimax_bridge --port 18011 --upstream-base-url https://api.minimaxi.com/v1 --upstream-model MiniMax-M2.7-highspeed --upstream-api-key-env MINIMAX_API_KEY",
            ),
        ]
    )

    closeout_actions = list(delivery_closeout.get("operator_actions", []) or [])
    closeout_action_list = _closeout_action_list(closeout_actions)

    kpis = "".join(
        [
            metric_card("业务收尾", status_label(str(delivery_closeout.get("status", "warning"))), "", status_tone(delivery_closeout.get("status", "warning")), icon_name="shield"),
            metric_card("发布闸门", status_label(str(release_gate.get("status", "warning"))), "", status_tone(release_gate.get("status", "warning")), icon_name="alert"),
            metric_card("模型通道就绪度", _display_value(provider_readiness.get("phase", "not_configured")), "", status_tone(provider_readiness.get("status", "warning")), icon_name="spark"),
        ]
    )

    closeout_primary_download = download_chip("/downloads/ops/delivery-closeout/latest-md", "Closeout MD")

    closeout_body = f"""
    <div class="closeout-board">
      <div class="closeout-callout">
        <div class="closeout-callout-copy">
          <strong>当前结论</strong>
          <p>{escape_html(_localize_text(delivery_closeout.get("summary", ""), "先看收尾结论，再决定是否进入交付。"))}</p>
        </div>
        <div class="ops-status-badges">
          {_status_pill(delivery_closeout.get("status", "warning"))}
          {pill(_display_value(delivery_closeout.get("milestone", "not_ready")), "info")}
        </div>
      </div>
      <div class="summary-grid closeout-summary-grid">
        {_summary_tile("里程碑", _display_value(delivery_closeout.get("milestone", "not_ready")))}
        {_summary_tile("待处理", str(len(closeout_actions)))}
      </div>
      <div class="closeout-action-block">
        <strong>下一步</strong>
        <ul class="action-list">{closeout_action_list}</ul>
      </div>
      <div class="inline-actions">
        {closeout_primary_download}
      </div>
      {_details_block("1", "收尾明细", _ops_table(closeout_rows, ["检查项", "状态", "当前值", "说明"], "暂无收尾明细", "当前还没有可展示的收尾记录。"))}
    </div>
    """

    quick_context = list_pairs(
        [
            ("提供方", escape_html(_display_value(provider_readiness.get("provider", config.get("ai_provider", "mock"))))),
            ("接口地址", escape_html(config.get("ai_endpoint", "") or "未配置")),
            ("模型标识", escape_html(config.get("ai_model", "") or "未配置")),
            ("本地配置", escape_html(local_config.get("path", "config/local.json"))),
        ],
        css_class="ops-context-grid",
    )

    command_body = f"""
    <div class="ops-workbench">{quick_context}</div>
    <div class="summary-grid ops-detail-summary">
      {_summary_tile("最新备份", str(backup_status.get("file_name", "") or "暂无"))}
      {_summary_tile("最新基线", str(latest_baseline.get("file_name", "") or baseline_status.get("file_name", "") or "暂无"))}
      {_summary_tile("最新探针", str(provider_probe_status.get("file_name", "") or provider_probe_last_success.get("file_name", "") or "暂无"))}
    </div>
    <div class="inline-actions">
      {download_chip("/downloads/logs/app", "应用日志")}
      {download_chip("/downloads/ops/delivery-closeout/latest-json", "收尾 JSON")}
      {download_chip("/downloads/ops/delivery-closeout/latest-md", "收尾 MD")}
    </div>
    <div class="operator-group-grid">
      {_details_block("1", "真实通道冒烟", common_commands, open_by_default=True)}
      {_details_block("2", "低频维护", maintenance_commands)}
    </div>
    """

    release_body = (
        '<div class="ops-detail-stack">'
        '<div class="ops-detail-callout">'
        f"<strong>发布结论</strong><p>{escape_html(_ops_callout_text(release_gate.get('status', 'warning'), release_gate.get('summary', ''), release_gate.get('recommended_action', ''), '先清掉阻塞项，再继续真实联调。'))}</p>"
        "</div>"
        + '<div class="summary-grid ops-detail-summary">'
        + _summary_tile("状态", status_label(str(release_gate.get("status", "warning"))))
        + _summary_tile("探针", status_label(latest_probe_status))
        + "</div>"
        + _details_block("1", "查看明细", _ops_table(release_rows, ["检查项", "状态", "当前值", "说明"], "暂无发布记录", "当前还没有可展示的发布检查。"))
        + "</div>"
    )

    provider_body = (
        '<div class="ops-detail-stack">'
        '<div class="ops-detail-callout">'
        f"<strong>通道结论</strong><p>{escape_html(_ops_callout_text(provider_readiness.get('status', 'warning'), provider_readiness.get('summary', ''), provider_readiness.get('recommended_action', ''), '先确认 provider、endpoint、API key 和脱敏边界。'))}</p>"
        "</div>"
        + '<div class="summary-grid ops-detail-summary">'
        + _summary_tile("提供方", _display_value(provider_readiness.get("provider", config.get("ai_provider", "mock"))))
        + _summary_tile("阶段", _display_value(provider_readiness.get("phase", "not_configured")))
        + "</div>"
        + _details_block("1", "查看明细", _ops_table(provider_rows, ["检查项", "状态", "当前值", "说明"], "暂无通道记录", "当前还没有可展示的通道检查。"))
        + "</div>"
    )

    probe_body = f"""
    <div class="probe-observatory">
      <div class="summary-grid probe-summary-grid">
        {_summary_tile("最新探针", status_label(latest_probe_status))}
        {_summary_tile("HTTP", str(provider_probe_status.get("http_status", "n/a") or "n/a"))}
        {_summary_tile("最近成功", str(provider_probe_last_success.get("generated_at", "") or provider_probe_last_success.get("file_name", "") or "未记录"))}
        {_summary_tile("最近失败", _localize_text(provider_probe_last_failure.get("error_code", "") or provider_probe_last_failure.get("summary", "") or "无"))}
      </div>
      <div class="inline-actions">{latest_probe_download}</div>
    </div>
    """

    trend_body = f"""
    <div class="trend-board">
      <div class="summary-grid trend-summary-grid">
        {_summary_tile("最新基线", str(latest_baseline.get("file_name", "") or baseline_status.get("file_name", "") or "暂无"))}
        {_summary_tile("待复核", str((latest_baseline.get("totals", {}) or {}).get("needs_review", 0)))}
        {_summary_tile("低质量", str((latest_baseline.get("totals", {}) or {}).get("low_quality", 0)))}
        {_summary_tile("变化", format_signed_delta((latest_baseline.get("delta_totals", {}) or {}).get("needs_review")))}
      </div>
      {_ops_table(baseline_rows, ["基线文件", "状态", "生成时间", "待复核", "低质量", "变化"], "暂无基线", "当前还没有生成可对比的基线。")}
    </div>
    """

    observatory_body = (
        '<div class="operator-group-grid">'
        + _details_block("1", "启动自检", _ops_table(startup_rows, ["检查项", "状态", "路径", "说明"], "暂无自检结果", "当前还没有自检明细。"), open_by_default=True)
        + _details_block("2", "探针观测 / 探针历史", probe_body + _ops_table(probe_rows, ["产物", "结果", "生成时间", "HTTP", "错误"], "暂无探针历史", "当前还没有探针记录。"))
        + _details_block("3", "滚动基线 / 质量趋势", trend_body)
        + "</div>"
    )

    content = f"""
    <section class="kpi-grid kpi-grid-ops">{kpis}</section>
    <section class="dashboard-grid">
      {panel("业务收尾", closeout_body, extra_class="span-12 panel-soft", icon_name="shield", panel_id="delivery-closeout")}
      {panel("常用运维入口", command_body, extra_class="span-12", icon_name="terminal", panel_id="operator-commands")}
      {panel("发布闸门", release_body, extra_class="span-6", icon_name="alert", panel_id="release-gate")}
      {panel("模型通道就绪度", provider_body, extra_class="span-6", icon_name="spark", panel_id="provider-readiness")}
      {panel("更多观测", observatory_body, extra_class="span-12", icon_name="bar", panel_id="ops-observatory")}
    </section>
    """

    header_meta = "".join(
        [
            _status_pill(release_gate.get("status", "warning")),
            pill(_display_value(config.get("ai_provider", "mock")), "info"),
        ]
    )

    return layout(
        title="运维中心",
        active_nav="ops",
        header_tag="运维中心",
        header_title="运维与发布",
        header_subtitle="先看交付和放行，再按需展开观测。",
        header_meta=header_meta,
        content=content,
        header_note="",
        page_links=[
            ("#delivery-closeout", "业务收尾", "shield"),
            ("#operator-commands", "常用运维入口", "terminal"),
            ("#release-gate", "发布闸门", "alert"),
            ("#provider-readiness", "模型通道就绪度", "spark"),
        ],
    )


def render_ops_page(config: dict, self_check: dict, filters: dict | None = None) -> str:
    provider_readiness = dict(self_check.get("provider_readiness", {}) or {})
    provider_probe_status = dict(self_check.get("provider_probe_status", {}) or {})
    provider_probe_history = list(self_check.get("provider_probe_history", []) or [])
    provider_probe_last_success = dict(self_check.get("provider_probe_last_success", {}) or {})
    provider_probe_last_failure = dict(self_check.get("provider_probe_last_failure", {}) or {})
    release_gate = dict(self_check.get("release_gate", {}) or {})
    delivery_closeout = dict(self_check.get("delivery_closeout", {}) or {})
    local_config = dict(self_check.get("local_config", {}) or {})

    baseline_status = latest_metrics_baseline_status()
    baseline_history = list_metrics_baseline_history(limit=6)
    latest_baseline = baseline_history[0] if baseline_history else {}
    backup_status = latest_runtime_backup_status()

    closeout_rows = [
        [escape_html(_label(item.get("label", item.get("name", "")))), _status_pill(item.get("status", "warning")), escape_html(_display_value(item.get("value", ""))), escape_html(_localize_text(item.get("summary", "")))]
        for item in delivery_closeout.get("checks", [])
    ]
    release_rows = [
        [escape_html(_label(item.get("label", item.get("name", "")))), _status_pill(item.get("status", "warning")), escape_html(_display_value(item.get("value", ""))), escape_html(_localize_text(item.get("detail", "")))]
        for item in release_gate.get("checks", [])
    ]
    provider_rows = [
        [escape_html(_label(item.get("label", item.get("name", "")))), _status_pill(item.get("status", "warning")), escape_html(_display_value(item.get("value", ""))), escape_html(_localize_text(item.get("detail", "")))]
        for item in provider_readiness.get("checks", [])
    ]
    startup_rows = [
        [escape_html(_label(item.get("label", item.get("name", "")))), _status_pill(item.get("status", "warning")), escape_html(item.get("path", "") or "-"), escape_html(_localize_text(item.get("detail", "")))]
        for item in self_check.get("checks", [])
    ]
    probe_rows = [
        [
            escape_html(item.get("file_name", "") or "-"),
            _status_pill(item.get("probe_status", "not_run")),
            escape_html(item.get("generated_at", "") or item.get("updated_at", "") or "-"),
            escape_html(str(item.get("http_status", 0) or "n/a") if item.get("attempted") else "n/a"),
            escape_html(item.get("error_code", "") or _localize_text(item.get("summary", ""), "-")),
        ]
        for item in provider_probe_history[:8]
    ]
    baseline_rows = [
        [
            escape_html(item.get("file_name", "") or "-"),
            _status_pill(item.get("status", "warning")),
            escape_html(item.get("generated_at", "") or item.get("updated_at", "") or "-"),
            escape_html(str(item.get("totals", {}).get("needs_review", 0))),
            escape_html(str(item.get("totals", {}).get("low_quality", 0))),
            escape_html(format_signed_delta(item.get("delta_totals", {}).get("needs_review"))),
        ]
        for item in baseline_history
    ]

    latest_probe_status = str(provider_probe_status.get("probe_status", "not_run") or "not_run")
    latest_probe_download = download_chip("/downloads/ops/provider-probe/latest", "最新 Probe JSON") if provider_probe_status.get("exists") else ""

    common_commands = "".join(
        [
            _command_block("启动演示", r"powershell -ExecutionPolicy Bypass -File scripts\start_mock_web.ps1"),
            _command_block("启动真实桥接", r"powershell -ExecutionPolicy Bypass -File scripts\start_real_bridge.ps1"),
            _command_block("启动真实 Web", r"powershell -ExecutionPolicy Bypass -File scripts\start_real_web.ps1"),
            _command_block("真实验证", r"powershell -ExecutionPolicy Bypass -File scripts\run_real_validation.ps1"),
            _command_block("查看栈状态", r"powershell -ExecutionPolicy Bypass -File scripts\show_stack_status.ps1"),
            _command_block("发布闸门", r"py -m app.tools.release_gate --config config\local.json"),
        ]
    )
    maintenance_commands = "".join(
        [
            _command_block("运行时清理", "py -m app.tools.runtime_cleanup"),
            _command_block("运行时备份", "py -m app.tools.runtime_backup create"),
            _command_block("Provider Sandbox", "py -m app.tools.provider_sandbox"),
            _command_block("Provider Probe", "py -m app.tools.provider_probe"),
            _command_block("Delivery Closeout", "py -m app.tools.delivery_closeout"),
            _command_block("MiniMax 桥接", r"py -m app.tools.minimax_bridge --port 18011 --upstream-base-url https://api.minimaxi.com/v1 --upstream-model MiniMax-M2.7-highspeed --upstream-api-key-env MINIMAX_API_KEY"),
        ]
    )

    closeout_actions = list(delivery_closeout.get("operator_actions", []) or [])
    closeout_action_list = _closeout_action_list(closeout_actions)

    kpis = "".join(
        [
            metric_card("业务收尾", status_label(str(delivery_closeout.get("status", "warning"))), "", status_tone(delivery_closeout.get("status", "warning")), icon_name="shield"),
            metric_card("发布闸门", status_label(str(release_gate.get("status", "warning"))), "", status_tone(release_gate.get("status", "warning")), icon_name="alert"),
            metric_card("模型通道就绪度", _display_value(provider_readiness.get("phase", "not_configured")), "", status_tone(provider_readiness.get("status", "warning")), icon_name="spark"),
        ]
    )

    closeout_body = f"""
    <div class="closeout-board">
      <div class="closeout-callout">
        <div class="closeout-callout-copy">
          <strong>当前结论</strong>
          <p>{escape_html(_localize_text(delivery_closeout.get("summary", ""), "先看收尾结论，再决定是否进入交付。"))}</p>
        </div>
        <div class="ops-status-badges">
          {_status_pill(delivery_closeout.get("status", "warning"))}
          {pill(_display_value(delivery_closeout.get("milestone", "not_ready")), "info")}
        </div>
      </div>
      <div class="summary-grid closeout-summary-grid">
        {_summary_tile("里程碑", _display_value(delivery_closeout.get("milestone", "not_ready")))}
        {_summary_tile("待处理", str(len(closeout_actions)))}
      </div>
      <div class="closeout-action-block">
        <strong>下一步</strong>
        <ul class="action-list">{closeout_action_list}</ul>
      </div>
      <div class="inline-actions">
        {download_chip("/downloads/ops/delivery-closeout/latest-md", "Closeout MD")}
      </div>
      {_details_block("1", "收尾明细", _ops_table(closeout_rows, ["检查项", "状态", "当前值", "说明"], "暂无收尾明细", "当前还没有可展示的收尾记录。"))}
    </div>
    """

    command_body = f"""
    <div class="summary-grid ops-detail-summary">
      {_summary_tile("最新备份", str(backup_status.get("file_name", "") or "暂无"))}
      {_summary_tile("最新基线", str(latest_baseline.get("file_name", "") or baseline_status.get("file_name", "") or "暂无"))}
      {_summary_tile("最新探针", str(provider_probe_status.get("file_name", "") or provider_probe_last_success.get("file_name", "") or "暂无"))}
    </div>
    <div class="inline-actions">
      {download_chip("/downloads/logs/app", "应用日志")}
      {download_chip("/downloads/ops/delivery-closeout/latest-json", "收尾 JSON")}
      {download_chip("/downloads/ops/delivery-closeout/latest-md", "收尾 MD")}
    </div>
    <div class="operator-group-grid">
      {_details_block("1", "真实通道冒烟", common_commands, open_by_default=True)}
      {_details_block("2", "低频维护", maintenance_commands)}
    </div>
    """

    gate_body = (
        '<div class="operator-group-grid">'
        + _details_block(
            "1",
            "发布闸门",
            '<div class="ops-detail-stack">'
            + '<div class="ops-detail-callout">'
            + f"<strong>发布结论</strong><p>{escape_html(_ops_callout_text(release_gate.get('status', 'warning'), release_gate.get('summary', ''), release_gate.get('recommended_action', ''), '先清掉阻塞项，再继续真实联调。'))}</p>"
            + "</div>"
            + '<div class="summary-grid ops-detail-summary">'
            + _summary_tile("状态", status_label(str(release_gate.get("status", "warning"))))
            + _summary_tile("探针", status_label(latest_probe_status))
            + "</div>"
            + _ops_table(release_rows, ["检查项", "状态", "当前值", "说明"], "暂无发布记录", "当前还没有可展示的发布检查。")
            + "</div>",
            open_by_default=True,
        )
        + _details_block(
            "2",
            "模型通道就绪度",
            '<div class="ops-detail-stack">'
            + '<div class="ops-detail-callout">'
            + f"<strong>通道结论</strong><p>{escape_html(_ops_callout_text(provider_readiness.get('status', 'warning'), provider_readiness.get('summary', ''), provider_readiness.get('recommended_action', ''), '先确认 provider、endpoint、API key 和脱敏边界。'))}</p>"
            + "</div>"
            + '<div class="summary-grid ops-detail-summary">'
            + _summary_tile("提供方", _display_value(provider_readiness.get("provider", config.get("ai_provider", "mock"))))
            + _summary_tile("阶段", _display_value(provider_readiness.get("phase", "not_configured")))
            + _summary_tile("本地配置", local_config.get("path", "config/local.json"))
            + "</div>"
            + _ops_table(provider_rows, ["检查项", "状态", "当前值", "说明"], "暂无通道记录", "当前还没有可展示的通道检查。")
            + "</div>",
        )
        + "</div>"
    )

    probe_body = f"""
    <div class="probe-observatory">
      <div class="summary-grid probe-summary-grid">
        {_summary_tile("最新探针", status_label(latest_probe_status))}
        {_summary_tile("HTTP", str(provider_probe_status.get("http_status", "n/a") or "n/a"))}
        {_summary_tile("最近成功", str(provider_probe_last_success.get("generated_at", "") or provider_probe_last_success.get("file_name", "") or "未记录"))}
        {_summary_tile("最近失败", _localize_text(provider_probe_last_failure.get("error_code", "") or provider_probe_last_failure.get("summary", "") or "无"))}
      </div>
      <div class="inline-actions">{latest_probe_download}</div>
    </div>
    """

    trend_body = f"""
    <div class="trend-board">
      <div class="summary-grid trend-summary-grid">
        {_summary_tile("最新基线", str(latest_baseline.get("file_name", "") or baseline_status.get("file_name", "") or "暂无"))}
        {_summary_tile("待复核", str((latest_baseline.get("totals", {}) or {}).get("needs_review", 0)))}
        {_summary_tile("低质量", str((latest_baseline.get("totals", {}) or {}).get("low_quality", 0)))}
        {_summary_tile("变化", format_signed_delta((latest_baseline.get("delta_totals", {}) or {}).get("needs_review")))}
      </div>
      {_ops_table(baseline_rows, ["基线文件", "状态", "生成时间", "待复核", "低质量", "变化"], "暂无基线", "当前还没有生成可对比的基线。")}
    </div>
    """

    observatory_body = (
        '<div class="operator-group-grid">'
        + _details_block("1", "启动自检", _ops_table(startup_rows, ["检查项", "状态", "路径", "说明"], "暂无自检结果", "当前还没有自检明细。"), open_by_default=True)
        + _details_block("2", "探针观测 / 探针历史", probe_body + _ops_table(probe_rows, ["产物", "结果", "生成时间", "HTTP", "错误"], "暂无探针历史", "当前还没有探针记录。"))
        + _details_block("3", "滚动基线 / 质量趋势", trend_body)
        + "</div>"
    )

    content = f"""
    <section class="kpi-grid kpi-grid-ops">{kpis}</section>
    <section class="dashboard-grid">
      {panel("业务收尾", closeout_body, extra_class="span-12 panel-soft", icon_name="shield", panel_id="delivery-closeout")}
      {panel("常用运维入口", command_body, extra_class="span-12", icon_name="terminal", panel_id="operator-commands")}
      {panel("放行判断", gate_body, extra_class="span-12", icon_name="alert", panel_id="ops-gate")}
      {panel("失败与重试", _retryable_jobs_panel(filters), extra_class="span-12", icon_name="refresh", panel_id="ops-retry-jobs")}
      {panel("更多观测", observatory_body, extra_class="span-12", icon_name="bar", panel_id="ops-observatory")}
    </section>
    """

    header_meta = "".join([_status_pill(release_gate.get("status", "warning")), pill(_display_value(config.get("ai_provider", "mock")), "info")])
    return layout(
        title="运维中心",
        active_nav="ops",
        header_tag="运维中心",
        header_title="运维与发布",
        header_subtitle="先看交付结论和放行判断，再按需展开命令与观测。",
        header_meta=header_meta,
        content=content,
        header_note="",
        page_links=[
            ("#delivery-closeout", "业务收尾", "shield"),
            ("#operator-commands", "常用运维入口", "terminal"),
            ("#ops-gate", "放行判断", "alert"),
            ("#ops-retry-jobs", "失败与重试", "refresh"),
            ("#ops-observatory", "更多观测", "bar"),
        ],
    )


def render_ops_page_v2(config: dict, self_check: dict, filters: dict | None = None) -> str:
    provider_readiness = dict(self_check.get("provider_readiness", {}) or {})
    provider_probe_status = dict(self_check.get("provider_probe_status", {}) or {})
    provider_probe_history = list(self_check.get("provider_probe_history", []) or [])
    provider_probe_last_success = dict(self_check.get("provider_probe_last_success", {}) or {})
    provider_probe_last_failure = dict(self_check.get("provider_probe_last_failure", {}) or {})
    release_gate = dict(self_check.get("release_gate", {}) or {})
    delivery_closeout = dict(self_check.get("delivery_closeout", {}) or {})
    local_config = dict(self_check.get("local_config", {}) or {})

    baseline_status = latest_metrics_baseline_status()
    baseline_history = list_metrics_baseline_history(limit=6)
    latest_baseline = baseline_history[0] if baseline_history else {}
    backup_status = latest_runtime_backup_status()

    closeout_rows = [
        [escape_html(_label(item.get("label", item.get("name", "")))), _status_pill(item.get("status", "warning")), escape_html(_display_value(item.get("value", ""))), escape_html(_localize_text(item.get("summary", "")))]
        for item in delivery_closeout.get("checks", [])
    ]
    release_rows = [
        [escape_html(_label(item.get("label", item.get("name", "")))), _status_pill(item.get("status", "warning")), escape_html(_display_value(item.get("value", ""))), escape_html(_localize_text(item.get("detail", "")))]
        for item in release_gate.get("checks", [])
    ]
    provider_rows = [
        [escape_html(_label(item.get("label", item.get("name", "")))), _status_pill(item.get("status", "warning")), escape_html(_display_value(item.get("value", ""))), escape_html(_localize_text(item.get("detail", "")))]
        for item in provider_readiness.get("checks", [])
    ]
    startup_rows = [
        [escape_html(_label(item.get("label", item.get("name", "")))), _status_pill(item.get("status", "warning")), escape_html(item.get("path", "") or "-"), escape_html(_localize_text(item.get("detail", "")))]
        for item in self_check.get("checks", [])
    ]
    probe_rows = [
        [
            escape_html(item.get("file_name", "") or "-"),
            _status_pill(item.get("probe_status", "not_run")),
            escape_html(item.get("generated_at", "") or item.get("updated_at", "") or "-"),
            escape_html(str(item.get("http_status", 0) or "n/a") if item.get("attempted") else "n/a"),
            escape_html(item.get("error_code", "") or _localize_text(item.get("summary", ""), "-")),
        ]
        for item in provider_probe_history[:8]
    ]
    baseline_rows = [
        [
            escape_html(item.get("file_name", "") or "-"),
            _status_pill(item.get("status", "warning")),
            escape_html(item.get("generated_at", "") or item.get("updated_at", "") or "-"),
            escape_html(str(item.get("totals", {}).get("needs_review", 0))),
            escape_html(str(item.get("totals", {}).get("low_quality", 0))),
            escape_html(format_signed_delta(item.get("delta_totals", {}).get("needs_review"))),
        ]
        for item in baseline_history
    ]

    latest_probe_status = str(provider_probe_status.get("probe_status", "not_run") or "not_run")
    latest_probe_download = download_chip("/downloads/ops/provider-probe/latest", "Latest Probe JSON") if provider_probe_status.get("exists") else ""

    common_commands = "".join(
        [
            _command_block("启动演示", r"powershell -ExecutionPolicy Bypass -File scripts\start_mock_web.ps1"),
            _command_block("启动真实桥接", r"powershell -ExecutionPolicy Bypass -File scripts\start_real_bridge.ps1"),
            _command_block("启动真实 Web", r"powershell -ExecutionPolicy Bypass -File scripts\start_real_web.ps1"),
            _command_block("真实验证", r"powershell -ExecutionPolicy Bypass -File scripts\run_real_validation.ps1"),
            _command_block("查看栈状态", r"powershell -ExecutionPolicy Bypass -File scripts\show_stack_status.ps1"),
            _command_block("发布闸门", r"py -m app.tools.release_gate --config config\local.json"),
        ]
    )
    maintenance_commands = "".join(
        [
            _command_block("运行时清理", "py -m app.tools.runtime_cleanup"),
            _command_block("运行时备份", "py -m app.tools.runtime_backup create"),
            _command_block("Provider Sandbox", "py -m app.tools.provider_sandbox"),
            _command_block("Provider Probe", "py -m app.tools.provider_probe"),
            _command_block("Delivery Closeout", "py -m app.tools.delivery_closeout"),
            _command_block("MiniMax 桥接", r"py -m app.tools.minimax_bridge --port 18011 --upstream-base-url https://api.minimaxi.com/v1 --upstream-model MiniMax-M2.7-highspeed --upstream-api-key-env MINIMAX_API_KEY"),
        ]
    )

    closeout_actions = list(delivery_closeout.get("operator_actions", []) or [])
    kpis = "".join(
        [
            metric_card("业务收尾", status_label(str(delivery_closeout.get("status", "warning"))), "", status_tone(delivery_closeout.get("status", "warning")), icon_name="shield"),
            metric_card("发布闸门", status_label(str(release_gate.get("status", "warning"))), "", status_tone(release_gate.get("status", "warning")), icon_name="alert"),
            metric_card("模型通道就绪度", _display_value(provider_readiness.get("phase", "not_configured")), "", status_tone(provider_readiness.get("status", "warning")), icon_name="spark"),
        ]
    )

    closeout_body = f"""
    <div class="closeout-board">
      <div class="closeout-callout">
        <div class="closeout-callout-copy">
          <strong>当前结论</strong>
          <p>{escape_html(_localize_text(delivery_closeout.get("summary", ""), "先看收尾结论，再决定是否进入交付。"))}</p>
        </div>
        <div class="ops-status-badges">
          {_status_pill(delivery_closeout.get("status", "warning"))}
          {pill(_display_value(delivery_closeout.get("milestone", "not_ready")), "info")}
        </div>
      </div>
      <div class="summary-grid closeout-summary-grid">
        {_summary_tile("里程碑", _display_value(delivery_closeout.get("milestone", "not_ready")))}
        {_summary_tile("待处理", str(len(closeout_actions)))}
      </div>
      <div class="closeout-action-block">
        <strong>下一步</strong>
        <ul class="action-list">{_closeout_action_list(closeout_actions)}</ul>
      </div>
      <div class="inline-actions">
        {download_chip("/downloads/ops/delivery-closeout/latest-md", "Closeout MD")}
      </div>
      {_details_block("1", "收尾明细", _ops_table(closeout_rows, ["检查项", "状态", "当前值", "说明"], "暂无收尾明细", "当前还没有可展示的收尾记录。"))}
    </div>
    """

    command_body = f"""
    <div class="summary-grid ops-detail-summary">
      {_summary_tile("最新备份", str(backup_status.get("file_name", "") or "暂无"))}
      {_summary_tile("最新基线", str(latest_baseline.get("file_name", "") or baseline_status.get("file_name", "") or "暂无"))}
      {_summary_tile("最新探针", str(provider_probe_status.get("file_name", "") or provider_probe_last_success.get("file_name", "") or "暂无"))}
    </div>
    <div class="inline-actions">
      {download_chip("/downloads/logs/app", "应用日志")}
      {download_chip("/downloads/ops/delivery-closeout/latest-json", "收尾 JSON")}
      {download_chip("/downloads/ops/delivery-closeout/latest-md", "收尾 MD")}
    </div>
    <div class="operator-group-grid">
      {_details_block("1", "真实通道冒烟", common_commands, open_by_default=True)}
      {_details_block("2", "低频维护", maintenance_commands)}
    </div>
    """

    gate_body = (
        '<div class="operator-group-grid">'
        + _details_block(
            "1",
            "发布闸门",
            '<div class="ops-detail-stack">'
            + '<div class="ops-detail-callout">'
            + f"<strong>发布结论</strong><p>{escape_html(_ops_callout_text(release_gate.get('status', 'warning'), release_gate.get('summary', ''), release_gate.get('recommended_action', ''), '先清掉阻塞项，再继续真实联调。'))}</p>"
            + "</div>"
            + '<div class="summary-grid ops-detail-summary">'
            + _summary_tile("状态", status_label(str(release_gate.get("status", "warning"))))
            + _summary_tile("探针", status_label(latest_probe_status))
            + "</div>"
            + _ops_table(release_rows, ["检查项", "状态", "当前值", "说明"], "暂无发布记录", "当前还没有可展示的发布检查。")
            + "</div>",
            open_by_default=True,
        )
        + _details_block(
            "2",
            "模型通道就绪度",
            '<div class="ops-detail-stack">'
            + '<div class="ops-detail-callout">'
            + f"<strong>通道结论</strong><p>{escape_html(_ops_callout_text(provider_readiness.get('status', 'warning'), provider_readiness.get('summary', ''), provider_readiness.get('recommended_action', ''), '先确认 provider、endpoint、API key 和脱敏边界。'))}</p>"
            + "</div>"
            + '<div class="summary-grid ops-detail-summary">'
            + _summary_tile("提供方", _display_value(provider_readiness.get("provider", config.get("ai_provider", "mock"))))
            + _summary_tile("阶段", _display_value(provider_readiness.get("phase", "not_configured")))
            + _summary_tile("本地配置", local_config.get("path", "config/local.json"))
            + "</div>"
            + _ops_table(provider_rows, ["检查项", "状态", "当前值", "说明"], "暂无通道记录", "当前还没有可展示的通道检查。")
            + "</div>",
        )
        + "</div>"
    )

    probe_body = f"""
    <div class="probe-observatory">
      <div class="summary-grid probe-summary-grid">
        {_summary_tile("最新探针", status_label(latest_probe_status))}
        {_summary_tile("HTTP", str(provider_probe_status.get("http_status", "n/a") or "n/a"))}
        {_summary_tile("最近成功", str(provider_probe_last_success.get("generated_at", "") or provider_probe_last_success.get("file_name", "") or "未记录"))}
        {_summary_tile("最近失败", _localize_text(provider_probe_last_failure.get("error_code", "") or provider_probe_last_failure.get("summary", "") or "无"))}
      </div>
      <div class="inline-actions">{latest_probe_download}</div>
    </div>
    """

    trend_body = f"""
    <div class="trend-board">
      <div class="summary-grid trend-summary-grid">
        {_summary_tile("最新基线", str(latest_baseline.get("file_name", "") or baseline_status.get("file_name", "") or "暂无"))}
        {_summary_tile("待复核", str((latest_baseline.get("totals", {}) or {}).get("needs_review", 0)))}
        {_summary_tile("低质量", str((latest_baseline.get("totals", {}) or {}).get("low_quality", 0)))}
        {_summary_tile("变化", format_signed_delta((latest_baseline.get("delta_totals", {}) or {}).get("needs_review")))}
      </div>
      {_ops_table(baseline_rows, ["基线文件", "状态", "生成时间", "待复核", "低质量", "变化"], "暂无基线", "当前还没有生成可对比的基线。")}
    </div>
    """

    observatory_body = (
        '<div class="operator-group-grid">'
        + _details_block("1", "启动自检", _ops_table(startup_rows, ["检查项", "状态", "路径", "说明"], "暂无自检结果", "当前还没有自检明细。"), open_by_default=True)
        + _details_block("2", "探针观测 / 探针历史", probe_body + _ops_table(probe_rows, ["产物", "结果", "生成时间", "HTTP", "错误"], "暂无探针历史", "当前还没有探针记录。"))
        + _details_block("3", "滚动基线 / 质量趋势", trend_body)
        + "</div>"
    )

    content = f"""
    <section class="kpi-grid kpi-grid-ops">{kpis}</section>
    <section class="dashboard-grid">
      {panel("业务收尾", closeout_body, extra_class="span-12 panel-soft", icon_name="shield", panel_id="delivery-closeout")}
      {panel("常用运维入口", command_body, extra_class="span-12", icon_name="terminal", panel_id="operator-commands")}
      {panel("放行判断", gate_body, extra_class="span-12", icon_name="alert", panel_id="ops-gate")}
      {panel("失败与重试", _retryable_jobs_panel(filters), extra_class="span-12", icon_name="refresh", panel_id="ops-retry-jobs")}
      {panel("解析复核队列", _manual_review_queue_panel(), extra_class="span-12", icon_name="search", panel_id="ops-manual-review")}
      {panel("纠错反馈闭环", _correction_feedback_panel(), extra_class="span-12", icon_name="clock", panel_id="ops-correction-feedback")}
      {panel("更多观测", observatory_body, extra_class="span-12", icon_name="bar", panel_id="ops-observatory")}
    </section>
    """

    header_meta = "".join([_status_pill(release_gate.get("status", "warning")), pill(_display_value(config.get("ai_provider", "mock")), "info")])
    return layout(
        title="运维中心",
        active_nav="ops",
        header_tag="运维中心",
        header_title="运维与发布",
        header_subtitle="先看交付结论和放行判断，再按需展开命令与观测。",
        header_meta=header_meta,
        content=content,
        header_note="",
        page_links=[
            ("#delivery-closeout", "业务收尾", "shield"),
            ("#operator-commands", "常用运维入口", "terminal"),
            ("#ops-gate", "放行判断", "alert"),
            ("#ops-retry-jobs", "失败与重试", "refresh"),
            ("#ops-manual-review", "解析复核", "search"),
            ("#ops-correction-feedback", "纠错反馈", "clock"),
            ("#ops-observatory", "更多观测", "bar"),
        ],
    )


render_ops_page = render_ops_page_v2


__all__ = ["render_ops_page"]
