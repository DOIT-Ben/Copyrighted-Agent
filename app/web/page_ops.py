from __future__ import annotations

from app.core.services.ops_status import (
    format_signed_delta,
    latest_metrics_baseline_status,
    latest_runtime_backup_status,
    list_metrics_baseline_history,
)
from app.core.services.runtime_store import store
from app.core.utils.text import escape_html

from app.web.view_helpers import (
    download_chip,
    layout,
    link,
    list_pairs,
    metric_card,
    panel,
    pill,
    status_label,
    status_tone,
    table,
)


LABEL_MAP = {
    "Data Root": "数据根目录",
    "Uploads": "上传目录",
    "SQLite Parent": "SQLite 上级目录",
    "Log Parent": "日志上级目录",
    "Config Template": "配置模板",
    "Local Config": "本地配置",
    "AI Boundary": "AI 边界",
    "Provider Readiness": "模型通道就绪度",
    "AI Enabled": "AI 启用状态",
    "Provider": "提供方",
    "Boundary": "脱敏边界",
    "HTTP Probe": "探针检查",
    "Endpoint": "接口地址",
    "Model": "模型标识",
    "API Key Env": "API Key 环境变量",
    "Fallback": "回退策略",
    "Startup Self Check": "启动自检",
    "Latest Probe": "最新探针",
    "Latest Success": "最近成功",
    "Latest Failure": "最近失败",
    "Latest Baseline": "最新基线",
    "Latest Backup": "最新备份",
    "Release Gate": "发布闸门",
}

PHASE_MAP = {
    "mock_mode": "本地 mock",
    "provider_no_probe_required": "无需探针",
    "disabled": "已关闭",
    "configured_disabled": "已配置但未启用",
    "not_configured": "未配置",
    "partially_configured": "部分配置",
    "ready_for_probe": "可进行探针",
    "probe_passed": "探针通过",
    "probe_failed": "探针失败",
    "probe_skipped": "探针跳过",
}

PROVIDER_LABELS = {
    "mock": "本地 mock",
    "safe_stub": "安全桩",
    "external_http": "外部 HTTP",
}

TEXT_REPLACEMENTS = {
    "directory writable": "目录可写",
    "parent directory writable": "上级目录可写",
    "config template found": "已找到配置模板",
    "local config found": "已找到本地配置",
    "local config missing, but default mock configuration is active": "本地配置缺失，但当前已启用默认 mock 配置",
    "non-mock providers require desensitized payload": "非 mock 提供方只允许接收脱敏后的请求",
    "desensitized boundary is disabled": "脱敏边界已关闭",
    "Current provider is mock; live external_http probe is not required.": "当前为 mock 模式，无需执行 external_http 探针。",
    "No persisted provider probe result is available yet.": "暂无持久化探针结果。",
    "No successful provider probe is available yet.": "暂无成功的探针结果。",
    "No failed provider probe is available yet.": "暂无探针失败记录。",
    "Latest safe provider probe completed successfully.": "最近一次安全探针已成功完成。",
    "No rolling baseline artifact is available yet.": "暂无滚动基线产物。",
    "Release gate status is unavailable.": "暂无发布闸门结论。",
    "No latest provider probe yet.": "暂无最新探针记录。",
    "No baseline yet.": "暂无基线记录。",
    "No Backup Yet": "暂无备份",
    "No Baseline Yet": "暂无基线",
    "not recorded": "未记录",
    "none recorded": "无",
    "not configured": "未配置",
    "desensitized only": "仅允许脱敏载荷",
}


def _label(value: str) -> str:
    text = str(value or "").strip()
    return LABEL_MAP.get(text, text)


def _provider_label(value: str) -> str:
    normalized = str(value or "").strip().lower()
    return PROVIDER_LABELS.get(normalized, value or "-")


def _phase_label(value: str) -> str:
    normalized = str(value or "").strip().lower()
    return PHASE_MAP.get(normalized, status_label(normalized))


def _localize_text(value: str, default: str = "-") -> str:
    text = str(value or "").strip()
    if not text:
        return default
    for source, target in TEXT_REPLACEMENTS.items():
        text = text.replace(source, target)
    return text


def _display_status(value: str) -> str:
    return pill(status_label(value), status_tone(value))


def _display_value(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return "-"
    normalized = text.lower()
    if normalized in PHASE_MAP:
        return _phase_label(normalized)
    if normalized in PROVIDER_LABELS:
        return _provider_label(normalized)
    if normalized in {"true", "false"}:
        return "是" if normalized == "true" else "否"
    if normalized in {
        "ok",
        "completed",
        "healthy",
        "pass",
        "grouped",
        "success",
        "ready",
        "warning",
        "processing",
        "running",
        "needs_review",
        "skipped",
        "failed",
        "error",
        "blocked",
        "danger",
        "severe",
        "info",
        "active",
        "not_run",
        "not_configured",
    }:
        return status_label(normalized)
    return _localize_text(text, text)


def _summary_tile(label: str, value: str, note: str) -> str:
    return (
        '<div class="summary-tile">'
        f"<span>{escape_html(label)}</span>"
        f"<strong>{escape_html(value)}</strong>"
        f"<small>{escape_html(note)}</small>"
        "</div>"
    )


def _ops_status_card(title: str, summary: str, badges: list[str], metrics: list[tuple[str, str]]) -> str:
    badges_html = "".join(badges)
    metrics_html = "".join(
        f"<div><span>{escape_html(label)}</span><strong>{value}</strong></div>"
        for label, value in metrics
    )
    return (
        '<article class="ops-status-card">'
        '<div class="ops-status-top">'
        '<div class="ops-status-copy">'
        f"<strong>{escape_html(title)}</strong>"
        f"<small>{escape_html(summary)}</small>"
        "</div>"
        f'<div class="ops-status-badges">{badges_html}</div>'
        "</div>"
        f'<div class="ops-mini-list">{metrics_html}</div>'
        "</article>"
    )


def _command_block(title: str, command: str, note: str) -> str:
    return (
        '<div class="command-block">'
        f"<strong>{escape_html(title)}</strong>"
        f"<small>{escape_html(note)}</small>"
        f"<code>{escape_html(command)}</code>"
        "</div>"
    )


def _command_cluster(title: str, note: str, blocks: list[str]) -> str:
    return (
        '<section class="command-cluster">'
        '<div class="command-cluster-head">'
        f"<strong>{escape_html(title)}</strong>"
        f"<span>{escape_html(note)}</span>"
        "</div>"
        f'<div class="command-list command-grid">{ "".join(blocks) }</div>'
        "</section>"
    )


def _release_summary(status: str) -> str:
    normalized = str(status or "").strip().lower()
    if normalized == "pass":
        return "当前环境已满足发布前主要门禁，可以继续真实链路验证。"
    if normalized == "blocked":
        return "当前环境仍存在阻塞项，不建议推进真实模型发布。"
    return "当前环境仍有提示项，建议先完成运维复核再推进。"


def _probe_summary(probe_status: str, error_code: str) -> str:
    normalized = str(probe_status or "").strip().lower()
    if normalized == "ok":
        return "最近一次探针已通过，可作为真实通道联调前的参考信号。"
    if normalized == "failed":
        return f"探针最近一次执行失败，请先处理错误代码：{error_code or '-'}。"
    return "探针还未形成稳定结果，先确认提供方就绪度再执行。"


def _runtime_summary(backup_status: dict, baseline_status: dict) -> str:
    if backup_status.get("exists") and baseline_status.get("exists"):
        return "运行备份和质量基线都已可见，适合做回溯与趋势对比。"
    return "备份与基线仍是发布前最重要的保护线，请保持持续可见。"


def _config_summary(local_config: dict, provider_name: str) -> str:
    if local_config.get("exists"):
        return f"本地配置已落地，当前提供方为 {_provider_label(provider_name)}。"
    return "本地配置尚未完整落地，请避免在未检查完的情况下直接进入真实模型运行。"


def _trend_summary(latest_item: dict) -> str:
    delta = (latest_item.get("delta_totals", {}) or {}).get("needs_review")
    if delta is None:
        return "当前还没有形成可对比的滚动基线，建议先完成一轮真实样本校验。"
    if delta > 0:
        return "待复核数量相较上一份基线有所上升，发布前建议重点复看近期新增问题。"
    if delta < 0:
        return "待复核数量相较上一份基线有所下降，当前质量趋势向好，但仍需结合探针结果判断。"
    return "待复核数量与上一份基线持平，适合结合低质量数量和探针历史做最终判断。"


def render_ops_page(config: dict, self_check: dict) -> str:
    provider_readiness = self_check.get("provider_readiness", {})
    provider_probe_status = self_check.get("provider_probe_status", {})
    provider_probe_history = self_check.get("provider_probe_history", [])
    provider_probe_last_success = self_check.get("provider_probe_last_success", {})
    provider_probe_last_failure = self_check.get("provider_probe_last_failure", {})
    release_gate = self_check.get("release_gate", {})
    local_config = self_check.get("local_config", {})
    backup_status = latest_runtime_backup_status()
    baseline_status = latest_metrics_baseline_status()
    baseline_history = list_metrics_baseline_history(limit=6)
    latest_baseline = baseline_history[0] if baseline_history else {}

    snapshot = {
        "submissions": len(store.submissions),
        "cases": len(store.cases),
        "materials": len(store.materials),
    }

    self_check_rows = [
        [
            escape_html(_label(item.get("label", item.get("name", "")))),
            _display_status(item.get("status", "unknown")),
            escape_html(item.get("path", "")),
            escape_html(_localize_text(item.get("detail", ""))),
        ]
        for item in self_check.get("checks", [])
    ]
    provider_rows = [
        [
            escape_html(_label(item.get("label", item.get("name", "")))),
            _display_status(item.get("status", "unknown")),
            escape_html(_display_value(item.get("value", ""))),
            escape_html(_localize_text(item.get("detail", ""))),
        ]
        for item in provider_readiness.get("checks", [])
    ]
    release_gate_rows = [
        [
            escape_html(_label(item.get("label", item.get("name", "")))),
            _display_status(item.get("status", "warning")),
            escape_html(_display_value(item.get("value", ""))),
            escape_html(_localize_text(item.get("detail", ""))),
        ]
        for item in release_gate.get("checks", [])
    ]
    probe_history_rows = [
        [
            escape_html(item.get("file_name", "")),
            _display_status(item.get("probe_status", "not_run")),
            escape_html(item.get("generated_at", "") or item.get("updated_at", "") or "-"),
            escape_html(str(item.get("http_status", 0) or "n/a") if item.get("attempted") else "n/a"),
            escape_html(item.get("error_code", "") or _localize_text(item.get("summary", ""))),
            download_chip(f"/downloads/ops/provider-probe/history/{item.get('file_name', '')}", "JSON")
            if item.get("file_name")
            else "-",
        ]
        for item in provider_probe_history
    ]
    baseline_rows = [
        [
            escape_html(item.get("file_name", "")),
            _display_status(item.get("status", "warning")),
            escape_html(item.get("generated_at", "") or item.get("updated_at", "") or "-"),
            escape_html(str(item.get("totals", {}).get("needs_review", 0))),
            escape_html(str(item.get("totals", {}).get("low_quality", 0))),
            escape_html(format_signed_delta(item.get("delta_totals", {}).get("needs_review"))),
        ]
        for item in baseline_history
    ]

    launch_cluster = _command_cluster(
        "环境启动",
        "先把本地演示、真实桥接和前端入口启动起来。",
        [
            _command_block("启动本地演示", "powershell -ExecutionPolicy Bypass -File scripts\\start_mock_web.ps1", "用于本地 UI 和流程演示。"),
            _command_block("启动真实桥接", "powershell -ExecutionPolicy Bypass -File scripts\\start_real_bridge.ps1", "接通真实模型前的桥接服务入口。"),
            _command_block("启动真实前端", "powershell -ExecutionPolicy Bypass -File scripts\\start_real_web.ps1 -Port 18080", "真实联调时使用的前端端口。"),
            _command_block("查看栈状态", "powershell -ExecutionPolicy Bypass -File scripts\\show_stack_status.ps1", "快速确认桥接、Web 和探针是否在线。"),
        ],
    )
    validation_cluster = _command_cluster(
        "校验与联调",
        "把探针、闸门和真实链路验证放在一组，便于按顺序执行。",
        [
            _command_block("执行真实验证", "powershell -ExecutionPolicy Bypass -File scripts\\run_real_validation.ps1", "跑完整的真实链路校验脚本。"),
            _command_block("安全探针", "py -m app.tools.provider_probe --config config\\local.json", "只验证链路边界，不发送真实业务负载。"),
            _command_block("真实通道冒烟", "py -m app.tools.provider_probe --config config\\local.json --probe", "对真实通道做一次最小可行探针。"),
            _command_block("发布闸门检查", "py -m app.tools.release_gate --config config\\local.json", "综合启动自检、探针和基线判断是否可推进。"),
        ],
    )
    maintenance_cluster = _command_cluster(
        "回溯与维护",
        "运维清理、备份、沙箱和基线都集中在这里，便于问题排查后快速回收现场。",
        [
            _command_block("运行时清理", "py -m app.tools.runtime_cleanup", "清理 submissions、uploads 和日志等运行产物。"),
            _command_block("运行时备份", "py -m app.tools.runtime_backup create", "在调整前先留一份回滚点。"),
            _command_block("提供方沙箱", "py -m app.tools.provider_sandbox --port 8010", "本地模拟 external_http 提供方。"),
            _command_block(
                "MiniMax 桥接",
                "py -m app.tools.minimax_bridge --port 18011 --upstream-base-url https://api.minimaxi.com/v1 --upstream-model MiniMax-M2.7-highspeed --upstream-api-key-env MINIMAX_API_KEY",
                "把项目 external_http 合约桥接到 MiniMax。",
            ),
            _command_block(
                "滚动基线",
                "py -m app.tools.metrics_baseline --compare-latest-in-dir docs\\dev --archive-dir docs\\dev\\history --archive-stem real-sample-baseline",
                "归档基线并生成趋势对比。",
            ),
            _command_block("直接启动 Web", "py -m app.api.main", "不走脚本时的直接启动方式。"),
        ],
    )

    support_commands = """
    <div class="operator-note">
      <strong>运维使用顺序</strong>
      <span>先看发布闸门和模型通道就绪度，再看探针历史与质量趋势，最后才决定是否进入真实模型联调。</span>
    </div>
    <div class="helper-chip-row">
      <span class="helper-chip">先看门禁</span>
      <span class="helper-chip">再看探针</span>
      <span class="helper-chip">最后看趋势</span>
    </div>
    """ + (
        '<div class="command-cluster-grid">'
        f"{launch_cluster}{validation_cluster}{maintenance_cluster}"
        "</div>"
    )

    ops_pairs = (
        '<div class="operator-note">'
        '<strong>运行上下文</strong>'
        '<span>这些上下文信息用于辅助判断当前环境到底处在 mock、本地桥接还是即将进入真实模型联调阶段。</span>'
        "</div>"
        + list_pairs(
            [
                ("本地配置", escape_html(local_config.get("path", "config/local.json"))),
                (
                    "最新探针 JSON",
                    download_chip("/downloads/ops/provider-probe/latest", "JSON") if provider_probe_status.get("exists") else "未记录",
                ),
                ("应用日志", link("/downloads/logs/app", "下载应用日志")),
                ("当前提供方", escape_html(_provider_label(provider_readiness.get("provider", config.get("ai_provider", "mock"))))),
                ("当前阶段", escape_html(_phase_label(provider_readiness.get("phase", "not_configured")))),
                ("接口地址", escape_html(config.get("ai_endpoint", "") or "未配置")),
                ("模型标识", escape_html(config.get("ai_model", "") or "未配置")),
                ("脱敏边界", "仅允许脱敏载荷" if config.get("ai_require_desensitized", True) else "已关闭"),
            ]
        )
    )

    probe_observatory = list_pairs(
        [
            ("最新探针", _display_status(provider_probe_status.get("probe_status", "not_run"))),
            (
                "最近成功",
                escape_html(provider_probe_last_success.get("generated_at", "") or provider_probe_last_success.get("file_name", "") or "未记录"),
            ),
            (
                "最近失败",
                escape_html(provider_probe_last_failure.get("error_code", "") or provider_probe_last_failure.get("file_name", "") or "无"),
            ),
            ("请求审计", escape_html("是" if (provider_probe_status.get("request_summary") or {}).get("llm_safe", False) else "否")),
            ("批次数", escape_html(str(snapshot["submissions"]))),
            ("项目数", escape_html(str(snapshot["cases"]))),
        ]
    )

    status_cards = (
        '<div class="ops-status-grid">'
        + _ops_status_card(
            "发布建议",
            _release_summary(release_gate.get("status", "warning")),
            [
                _display_status(release_gate.get("status", "warning")),
                pill(_provider_label(config.get("ai_provider", "mock")), "info"),
            ],
            [
                ("运行模式", escape_html(_localize_text(str(release_gate.get("mode", "-")), "-"))),
                ("建议动作", escape_html(_localize_text(str(release_gate.get("recommended_action", "") or "-"), "-"))),
            ],
        )
        + _ops_status_card(
            "通道探针",
            _probe_summary(provider_probe_status.get("probe_status", "not_run"), provider_probe_status.get("error_code", "")),
            [
                _display_status(provider_probe_status.get("probe_status", "not_run")),
                pill("LLM 安全", "success" if (provider_probe_status.get("request_summary") or {}).get("llm_safe", False) else "warning"),
            ],
            [
                ("HTTP", escape_html(str(provider_probe_status.get("http_status", "n/a") or "n/a"))),
                ("成功时间", escape_html(provider_probe_last_success.get("generated_at", "") or "未记录")),
            ],
        )
        + _ops_status_card(
            "运行保护",
            _runtime_summary(backup_status, baseline_status),
            [
                _display_status(backup_status.get("status", "warning")),
                _display_status(baseline_status.get("status", "warning")),
            ],
            [
                ("最新备份", escape_html(backup_status.get("file_name", "") or "无")),
                ("最新基线", escape_html(baseline_status.get("file_name", "") or "无")),
            ],
        )
        + _ops_status_card(
            "本地配置",
            _config_summary(local_config, provider_readiness.get("provider", config.get("ai_provider", "mock"))),
            [
                _display_status(local_config.get("status", "warning")),
                pill("本地脱敏", "success"),
            ],
            [
                ("配置文件", escape_html(local_config.get("path", "config/local.json"))),
                ("是否存在", "是" if local_config.get("exists", False) else "否"),
            ],
        )
        + "</div>"
    )

    trend_tiles = "".join(
        [
            _summary_tile("最近基线", str(latest_baseline.get("file_name", "") or baseline_status.get("file_name", "") or "暂无基线"), "当前用于对比的最新基线文件"),
            _summary_tile("待复核", str((latest_baseline.get("totals", {}) or {}).get("needs_review", 0)), "最新基线中的待复核数量"),
            _summary_tile("低质量", str((latest_baseline.get("totals", {}) or {}).get("low_quality", 0)), "最新基线中的低质量数量"),
            _summary_tile("变化值", format_signed_delta((latest_baseline.get("delta_totals", {}) or {}).get("needs_review")), "相较上一份基线的待复核变化"),
        ]
    )
    trend_body = f"""
    <div class="trend-board">
      <div class="trend-callout">
        <strong>趋势观察重点</strong>
        <span>{escape_html(_trend_summary(latest_baseline))}</span>
      </div>
      <div class="helper-chip-row">
        <span class="helper-chip">最近 6 份基线</span>
        <span class="helper-chip">优先看待复核变化</span>
        <span class="helper-chip">结合低质量与探针结果</span>
      </div>
      <div class="summary-grid trend-summary-grid">{trend_tiles}</div>
    </div>
    """

    command_panel_body = support_commands + ops_pairs

    flight_plan_body = """
    <div class="sequence-board">
      <article class="sequence-step">
        <span class="sequence-index">1</span>
        <div>
          <strong>先看发布闸门</strong>
          <p>先判断当前环境能不能推进真实模型验证，再决定是否继续深入。</p>
        </div>
      </article>
      <article class="sequence-step">
        <span class="sequence-index">2</span>
        <div>
          <strong>再看通道与探针</strong>
          <p>确认提供方是否就绪，再区分“环境未就绪”还是“真实调用失败”。</p>
        </div>
      </article>
      <article class="sequence-step">
        <span class="sequence-index">3</span>
        <div>
          <strong>最后看趋势与回滚点</strong>
          <p>结合基线、备份和低质量数量，决定是否进入联调或先回收现场。</p>
        </div>
      </article>
    </div>
    <div class="inline-actions">
      <a class="button-secondary button-compact" href="#release-gate">先看发布闸门</a>
      <a class="button-secondary button-compact" href="#provider-readiness">再看通道就绪</a>
      <a class="button-secondary button-compact" href="#probe-history">查看探针历史</a>
      <a class="button-secondary button-compact" href="#trend-watch">最后看质量趋势</a>
    </div>
    """

    content = f"""
    {panel('这页应该怎么看', flight_plan_body, kicker='运维顺序', extra_class='span-12 panel-soft', icon_name='bar', description='把运维和联调动作按顺序串起来，减少来回跳页和误判。', panel_id='ops-flight-plan')}
    <section class="kpi-grid">
      {metric_card('发布闸门', status_label(str(release_gate.get('status', 'warning'))), '用于判断是否进入真实模型发布验证', status_tone(release_gate.get('status', 'warning')), icon_name='shield')}
      {metric_card('启动自检', status_label(str(self_check.get('status', 'warning'))), '检查路径可写、配置与安全边界', status_tone(self_check.get('status', 'warning')), icon_name='check')}
      {metric_card('最新探针', status_label(str(provider_probe_status.get('probe_status', 'not_run'))), '观察最近一次通道探针的结果', status_tone(provider_probe_status.get('probe_status', 'not_run')), icon_name='spark')}
      {metric_card('最新基线', status_label(str(baseline_status.get('status', 'warning'))), '检查当前质量基线是否可用', status_tone(baseline_status.get('status', 'warning')), icon_name='trend')}
    </section>
    {status_cards}
    <section class="dashboard-grid">
      {panel('常用运维入口', command_panel_body, kicker='运维操作', extra_class='span-12', icon_name='terminal', description='把启动、联调、验证和维护命令按阶段分组，减少来回切换。', panel_id='operator-commands')}
      {panel('发布闸门详情', table(['检查项', '状态', '当前值', '说明'], release_gate_rows), kicker='发布闸门', extra_class='span-6', icon_name='shield', description='把能不能推进真实模型验证的主信号压缩到一张表里。', panel_id='release-gate')}
      {panel('模型通道就绪度', table(['检查项', '状态', '当前值', '说明'], provider_rows), kicker='模型通道', extra_class='span-6', icon_name='spark', description='确认当前提供方的接口、模型、Key 和回退策略是否完整。', panel_id='provider-readiness')}
      {panel('启动自检明细', table(['检查项', '状态', '路径', '说明'], self_check_rows), kicker='启动自检', extra_class='span-6', icon_name='check', description='检查运行目录、SQLite、日志和 AI 边界是否正常。', panel_id='startup-self-check')}
      {panel('探针概览', probe_observatory, kicker='探针观测', extra_class='span-6', icon_name='bar', description='一屏看完最新探针、最近成功、最近失败和 llm_safe 审计结果。', panel_id='probe-observatory')}
      {panel('探针历史', table(['产物', '结果', '生成时间', 'HTTP', '错误/摘要', '下载'], probe_history_rows), kicker='探针历史', extra_class='span-12', icon_name='clock', description='用于区分“环境未就绪”和“真实调用失败”两类问题。', panel_id='probe-history')}
      {panel('质量趋势', trend_body + table(['基线文件', '状态', '生成时间', '待复核', '低质量', '变化值'], baseline_rows), kicker='趋势看板', extra_class='span-12', icon_name='trend', description='发布前最后一轮最值得盯住的就是待复核变化、低质量数量和基线连续性。', panel_id='trend-watch')}
    </section>
    """
    return layout(
        title="运维中心",
        active_nav="ops",
        header_tag="运维中心",
        header_title="运行与发布中心",
        header_subtitle="统一查看发布闸门、启动自检、模型通道就绪度、安全探针、备份与质量趋势。",
        header_meta="".join(
            [
                _display_status(release_gate.get("status", "warning")),
                pill(_provider_label(config.get("ai_provider", "mock")), "info"),
                pill("本地脱敏", "success"),
            ]
        ),
        content=content,
        header_note="先看发布闸门和模型通道就绪度，再看探针历史与质量趋势，最后再决定是否进入真实模型联调。",
        page_links=[
            ("#release-gate", "发布闸门", "shield"),
            ("#provider-readiness", "通道就绪", "spark"),
            ("#probe-history", "探针历史", "clock"),
            ("#trend-watch", "质量趋势", "trend"),
        ],
    )
