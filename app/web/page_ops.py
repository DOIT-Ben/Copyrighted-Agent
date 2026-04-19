from __future__ import annotations

from app.core.services.ops_status import (
    format_signed_delta,
    latest_metrics_baseline_status,
    latest_runtime_backup_status,
    list_metrics_baseline_history,
)
from app.core.services.runtime_store import store
from app.core.utils.text import escape_html

from app.web.view_helpers import download_chip, layout, link, list_pairs, metric_card, panel, pill, status_tone, table


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

    snapshot = {
        "submissions": len(store.submissions),
        "cases": len(store.cases),
        "materials": len(store.materials),
    }

    self_check_rows = [
        [
            escape_html(item.get("label", item.get("name", ""))),
            pill(item.get("status", "unknown"), status_tone(item.get("status", "unknown"))),
            escape_html(item.get("path", "")),
            escape_html(item.get("detail", "")),
        ]
        for item in self_check.get("checks", [])
    ]
    provider_rows = [
        [
            escape_html(item.get("label", item.get("name", ""))),
            pill(item.get("status", "unknown"), status_tone(item.get("status", "unknown"))),
            escape_html(str(item.get("value", "") or "-")),
            escape_html(item.get("detail", "")),
        ]
        for item in provider_readiness.get("checks", [])
    ]
    release_gate_rows = [
        [
            escape_html(item.get("label", item.get("name", ""))),
            pill(item.get("status", "warning"), status_tone(item.get("status", "warning"))),
            escape_html(str(item.get("value", "") or "-")),
            escape_html(item.get("detail", "")),
        ]
        for item in release_gate.get("checks", [])
    ]
    probe_history_rows = [
        [
            escape_html(item.get("file_name", "")),
            pill(item.get("probe_status", "not_run"), status_tone(item.get("probe_status", "not_run"))),
            escape_html(item.get("generated_at", "") or item.get("updated_at", "") or "-"),
            escape_html(str(item.get("http_status", 0) or "n/a") if item.get("attempted") else "n/a"),
            escape_html(item.get("error_code", "") or item.get("summary", "") or "-"),
            download_chip(f"/downloads/ops/provider-probe/history/{item.get('file_name', '')}", "JSON")
            if item.get("file_name")
            else "-",
        ]
        for item in provider_probe_history
    ]
    baseline_rows = [
        [
            escape_html(item.get("file_name", "")),
            pill(item.get("status", "warning"), status_tone(item.get("status", "warning"))),
            escape_html(item.get("generated_at", "") or item.get("updated_at", "") or "-"),
            escape_html(str(item.get("totals", {}).get("needs_review", 0))),
            escape_html(str(item.get("totals", {}).get("low_quality", 0))),
            escape_html(format_signed_delta(item.get("delta_totals", {}).get("needs_review"))),
        ]
        for item in baseline_history
    ]

    support_commands = """
    <div class="command-list command-grid">
      <div class="command-block"><strong>Start Mock Web</strong><code>powershell -ExecutionPolicy Bypass -File scripts\\start_mock_web.ps1</code></div>
      <div class="command-block"><strong>Start Real Bridge</strong><code>powershell -ExecutionPolicy Bypass -File scripts\\start_real_bridge.ps1</code></div>
      <div class="command-block"><strong>Start Real Web</strong><code>powershell -ExecutionPolicy Bypass -File scripts\\start_real_web.ps1 -Port 18080</code></div>
      <div class="command-block"><strong>Run Real Validation</strong><code>powershell -ExecutionPolicy Bypass -File scripts\\run_real_validation.ps1</code></div>
      <div class="command-block"><strong>Stack Status</strong><code>powershell -ExecutionPolicy Bypass -File scripts\\show_stack_status.ps1</code></div>
      <div class="command-block"><strong>Runtime Cleanup</strong><code>py -m app.tools.runtime_cleanup</code></div>
      <div class="command-block"><strong>Runtime Backup</strong><code>py -m app.tools.runtime_backup create</code></div>
      <div class="command-block"><strong>Provider Sandbox</strong><code>py -m app.tools.provider_sandbox --port 8010</code></div>
      <div class="command-block"><strong>MiniMax Bridge</strong><code>py -m app.tools.minimax_bridge --port 18011 --upstream-base-url https://api.minimaxi.com/v1 --upstream-model MiniMax-M2.7-highspeed --upstream-api-key-env MINIMAX_API_KEY</code></div>
      <div class="command-block"><strong>Provider Probe</strong><code>py -m app.tools.provider_probe --config config\\local.json</code></div>
      <div class="command-block"><strong>Real Provider Smoke</strong><code>py -m app.tools.provider_probe --config config\\local.json --probe</code></div>
      <div class="command-block"><strong>Release Gate</strong><code>py -m app.tools.release_gate --config config\\local.json</code></div>
      <div class="command-block"><strong>Rolling Baseline</strong><code>py -m app.tools.metrics_baseline --compare-latest-in-dir docs\\dev --archive-dir docs\\dev\\history --archive-stem real-sample-baseline</code></div>
      <div class="command-block"><strong>Start Web</strong><code>py -m app.api.main</code></div>
    </div>
    """

    ops_pairs = list_pairs(
        [
            ("Config Local", escape_html(local_config.get("path", "config/local.json"))),
            (
                "Latest Probe",
                download_chip("/downloads/ops/provider-probe/latest", "Latest JSON")
                if provider_probe_status.get("exists")
                else "not recorded",
            ),
            ("App Log", link("/downloads/logs/app", "/downloads/logs/app")),
            ("Provider", escape_html(provider_readiness.get("provider", config.get("ai_provider", "mock")))),
            ("Phase", escape_html(str(provider_readiness.get("phase", "not_configured")).replace("_", " "))),
            ("Endpoint", escape_html(config.get("ai_endpoint", "") or "not configured")),
            ("Model", escape_html(config.get("ai_model", "") or "not configured")),
            ("Boundary", "desensitized only" if config.get("ai_require_desensitized", True) else "disabled"),
        ]
    )
    probe_observatory = list_pairs(
        [
            ("Latest Probe", pill(provider_probe_status.get("probe_status", "not_run"), status_tone(provider_probe_status.get("probe_status", "not_run")))),
            ("Latest Success", escape_html(provider_probe_last_success.get("generated_at", "") or provider_probe_last_success.get("file_name", "") or "not recorded")),
            ("Latest Failure", escape_html(provider_probe_last_failure.get("error_code", "") or provider_probe_last_failure.get("file_name", "") or "none recorded")),
            ("Request Audit", escape_html(str((provider_probe_status.get("request_summary") or {}).get("llm_safe", False)))),
        ]
    )
    provider_checklist = list_pairs(
        [
            ("Latest Backup", escape_html(backup_status.get("file_name", "") or "No Backup Yet")),
            ("Latest Baseline", escape_html(baseline_status.get("file_name", "") or "No Baseline Yet")),
            ("Submissions", escape_html(str(snapshot["submissions"]))),
            ("Cases", escape_html(str(snapshot["cases"]))),
            ("Materials", escape_html(str(snapshot["materials"]))),
            ("Web Port", escape_html(str(config.get("port", 8000)))),
        ]
    )

    status_cards = (
        '<div class="ops-status-grid">'
        + _ops_status_card(
            "Release Gate",
            str(release_gate.get("summary", "") or "Release gate status is unavailable."),
            [
                pill(release_gate.get("status", "warning"), status_tone(release_gate.get("status", "warning"))),
                pill(config.get("ai_provider", "mock"), "info"),
            ],
            [
                ("Mode", escape_html(str(release_gate.get("mode", "-")))),
                ("Recommended", escape_html(str(release_gate.get("recommended_action", "-")))),
            ],
        )
        + _ops_status_card(
            "Provider Probe",
            str(provider_probe_status.get("summary", "") or "No latest provider probe yet."),
            [
                pill(provider_probe_status.get("probe_status", "not_run"), status_tone(provider_probe_status.get("probe_status", "not_run"))),
                pill("LLM Safe", "success" if (provider_probe_status.get("request_summary") or {}).get("llm_safe", False) else "warning"),
            ],
            [
                ("HTTP", escape_html(str(provider_probe_status.get("http_status", "n/a") or "n/a"))),
                ("Success", escape_html(provider_probe_last_success.get("generated_at", "") or "not recorded")),
            ],
        )
        + _ops_status_card(
            "Runtime Protection",
            "Backups, baselines, and local configuration should remain visible to the operator.",
            [
                pill(backup_status.get("status", "warning"), status_tone(backup_status.get("status", "warning"))),
                pill(baseline_status.get("status", "warning"), status_tone(baseline_status.get("status", "warning"))),
            ],
            [
                ("Latest Backup", escape_html(backup_status.get("file_name", "") or "none")),
                ("Latest Baseline", escape_html(baseline_status.get("file_name", "") or "none")),
            ],
        )
        + _ops_status_card(
            "Local Config",
            str(local_config.get("detail", "") or "Local provider configuration state."),
            [
                pill(local_config.get("status", "warning"), status_tone(local_config.get("status", "warning"))),
                pill("Local Redaction", "success"),
            ],
            [
                ("Path", escape_html(local_config.get("path", "config/local.json"))),
                ("Exists", escape_html(str(local_config.get("exists", False)))),
            ],
        )
        + "</div>"
    )

    boundary_note = """
    <p class="highlight-note">
      Support / Ops keeps the desensitization boundary, provider readiness, release gate, and probe artifacts on one surface so operators can decide whether a real-model run is safe before they trigger it.
    </p>
    """

    content = f"""
    <section class="kpi-grid">
      {metric_card('Release Gate', str(release_gate.get('status', 'warning')).upper(), release_gate.get('summary', 'Release gate status is unavailable.'), status_tone(release_gate.get('status', 'warning')), icon_name='shield')}
      {metric_card('Startup Self Check', str(self_check.get('status', 'warning')).upper(), 'Writable paths, local config, boundary, and provider readiness.', status_tone(self_check.get('status', 'warning')), icon_name='check')}
      {metric_card('Latest Probe', str(provider_probe_status.get('probe_status', 'not_run')).upper(), provider_probe_status.get('summary', 'No latest probe yet.'), status_tone(provider_probe_status.get('probe_status', 'not_run')), icon_name='spark')}
      {metric_card('Latest Baseline', str(baseline_status.get('status', 'warning')).upper(), baseline_status.get('summary', 'No baseline yet.'), status_tone(baseline_status.get('status', 'warning')), icon_name='trend')}
    </section>
    {status_cards}
    <section class="dashboard-grid">
      {panel('Operator Commands', boundary_note + support_commands + ops_pairs, kicker='Support / Ops', extra_class='span-5', icon_name='terminal', description='Common operations stay visible and copyable from the same workspace.')}
      {panel('Provider Checklist', provider_checklist, kicker='Provider Checklist', extra_class='span-7', icon_name='layers', description='A compact audit of backup, baseline, and runtime inventory before deeper inspection.')}
      {panel('Provider Readiness', table(['Check', 'Status', 'Value', 'Detail'], provider_rows), kicker='Provider Readiness', extra_class='span-6', icon_name='spark', description='Readiness shows whether the current provider path is safe and complete enough to use.')}
      {panel('Release Gate', table(['Check', 'Status', 'Value', 'Detail'], release_gate_rows), kicker='Release Gate', extra_class='span-6', icon_name='shield', description='The release gate compresses the go or no-go signals into one review table.')}
      {panel('Startup Self Check', table(['Check', 'Status', 'Path', 'Detail'], self_check_rows), kicker='Startup Self Check', extra_class='span-7', icon_name='check', description='Writable paths, configuration, and boundary checks run at startup so operators do not guess.')}
      {panel('Probe Observatory', probe_observatory, kicker='Probe Observatory', extra_class='span-5', icon_name='bar', description='Keep the newest probe, most recent success, and latest failure in immediate view.')}
      {panel('Probe History', table(['Artifact', 'Probe', 'Generated', 'HTTP', 'Error', 'Download'], probe_history_rows), kicker='Probe History', extra_class='span-6', icon_name='clock', description='Historical probe artifacts support regression tracking and incident review.')}
      {panel('Trend Watch', table(['Artifact', 'Status', 'Generated', 'Needs Review', 'Low Quality', 'Delta'], baseline_rows), kicker='Baseline History', extra_class='span-6', icon_name='trend', description='Rolling baselines show whether quality is drifting release to release.')}
    </section>
    """
    return layout(
        title="Support / Ops",
        active_nav="ops",
        header_tag="Support / Ops",
        header_title="Support / Ops",
        header_subtitle="Track the release gate, startup self-checks, provider readiness, probe observability, and rolling baseline history in one admin view.",
        header_meta="".join(
            [
                pill(release_gate.get("status", "warning"), status_tone(release_gate.get("status", "warning"))),
                pill(config.get("ai_provider", "mock"), "info"),
                pill("Local Redaction", "success"),
            ]
        ),
        content=content,
    )
