from __future__ import annotations

from pathlib import Path

from app.core.services.app_config import AppConfig, load_app_config
from app.core.services.ops_status import latest_metrics_baseline_status
from app.core.services.provider_probe import (
    latest_failed_provider_probe_status,
    latest_provider_probe_status,
    latest_successful_provider_probe_status,
)
from app.core.services.startup_checks import run_startup_self_check


GATE_STATUS_ORDER = {"pass": 0, "warning": 1, "blocked": 2}


def _gate_check(
    name: str,
    label: str,
    status: str,
    detail: str,
    *,
    value: str = "",
    recommended_action: str = "",
) -> dict:
    return {
        "name": name,
        "label": label,
        "status": status,
        "detail": detail,
        "value": value,
        "recommended_action": recommended_action,
    }


def _merge_gate_status(current: str, candidate: str) -> str:
    return candidate if GATE_STATUS_ORDER.get(candidate, 0) > GATE_STATUS_ORDER.get(current, 0) else current


def _probe_marker(value: dict | None) -> str:
    item = dict(value or {})
    return str(item.get("generated_at", "") or item.get("file_name", "") or "")


def evaluate_release_gate(
    config: AppConfig | None = None,
    *,
    startup_report: dict | None = None,
    dev_root: str | Path | None = None,
) -> dict:
    settings = config or load_app_config()
    report = startup_report or run_startup_self_check(settings)

    provider_readiness = report.get("provider_readiness", {})
    latest_probe = report.get("provider_probe_status") or latest_provider_probe_status(settings)
    latest_success = report.get("provider_probe_last_success") or latest_successful_provider_probe_status(settings)
    latest_failure = report.get("provider_probe_last_failure") or latest_failed_provider_probe_status(settings)
    local_config = report.get("local_config", {})
    baseline_status = latest_metrics_baseline_status(dev_root)

    provider_name = str(provider_readiness.get("provider", settings.ai_provider or "mock") or "mock")
    provider_phase = str(provider_readiness.get("phase", "") or "")
    provider_mode = "mock_local" if provider_name == "mock" else "external_http" if provider_name == "external_http" else "custom_provider"

    checks: list[dict] = []

    startup_status = str(report.get("status", "warning") or "warning")
    if startup_status == "failed":
        checks.append(
            _gate_check(
                "startup_self_check",
                "Startup Self Check",
                "blocked",
                "Startup self-check has failed; do not promote the current environment.",
                value=startup_status,
                recommended_action="Fix failed writable-path or runtime checks before attempting a release gate.",
            )
        )
    elif startup_status == "warning":
        checks.append(
            _gate_check(
                "startup_self_check",
                "Startup Self Check",
                "warning",
                "Startup self-check still reports warnings.",
                value=startup_status,
                recommended_action="Review warning checks on /ops and resolve anything that affects the next smoke or release step.",
            )
        )
    else:
        checks.append(
            _gate_check(
                "startup_self_check",
                "Startup Self Check",
                "pass",
                "Startup self-check passed for the current environment.",
                value=startup_status,
            )
        )

    local_config_exists = bool(local_config.get("exists", False))
    if local_config_exists:
        checks.append(
            _gate_check(
                "local_config",
                "Local Config",
                "pass",
                "A local config file is present for repeatable environment setup.",
                value=str(local_config.get("path", "config/local.json")),
            )
        )
    elif provider_mode == "external_http":
        checks.append(
            _gate_check(
                "local_config",
                "Local Config",
                "blocked",
                "external_http is selected, but config/local.json is still missing.",
                value=str(local_config.get("path", "config/local.json")),
                recommended_action="Create config/local.json or provide equivalent env overrides before running the real provider gate.",
            )
        )
    else:
        checks.append(
            _gate_check(
                "local_config",
                "Local Config",
                "warning",
                "Local config is still absent; mock mode can continue, but repeatable real-provider smoke is not ready.",
                value=str(local_config.get("path", "config/local.json")),
                recommended_action="Create config/local.json once you are ready to move from mock mode to a real provider.",
            )
        )

    if provider_mode == "mock_local":
        checks.append(
            _gate_check(
                "provider_readiness",
                "Provider Readiness",
                "warning",
                "Current environment remains in mock mode; real-provider release validation is not complete.",
                value=provider_phase or "mock_mode",
                recommended_action="Switch ai_provider to external_http and fill the real endpoint, model, and key mapping when ready.",
            )
        )
    elif provider_mode != "external_http":
        checks.append(
            _gate_check(
                "provider_readiness",
                "Provider Readiness",
                "warning",
                f"Current provider is {provider_name}; external_http release smoke is not active in this environment.",
                value=provider_phase or provider_name,
                recommended_action="Use external_http if you need gateway-level release validation in this workspace.",
            )
        )
    elif provider_phase != "ready_for_probe":
        checks.append(
            _gate_check(
                "provider_readiness",
                "Provider Readiness",
                "blocked",
                str(provider_readiness.get("summary", "") or "Provider readiness is incomplete."),
                value=provider_phase or "not_configured",
                recommended_action=str(provider_readiness.get("recommended_action", "") or "Complete provider readiness before retrying the release gate."),
            )
        )
    else:
        checks.append(
            _gate_check(
                "provider_readiness",
                "Provider Readiness",
                "pass",
                "Provider readiness is complete for a safe external_http smoke.",
                value=provider_phase,
            )
        )

    latest_probe_state = str(latest_probe.get("probe_status", "not_run") or "not_run")
    if provider_mode == "external_http" and latest_probe_state != "ok":
        checks.append(
            _gate_check(
                "latest_probe",
                "Latest Probe",
                "blocked",
                str(latest_probe.get("summary", "") or "Latest provider probe is not successful."),
                value=latest_probe_state,
                recommended_action=str(latest_probe.get("recommended_action", "") or "Run a successful real provider probe before promoting this environment."),
            )
        )
    elif latest_probe_state == "ok":
        checks.append(
            _gate_check(
                "latest_probe",
                "Latest Probe",
                "pass",
                "The newest persisted provider probe completed successfully.",
                value=latest_probe_state,
            )
        )
    else:
        checks.append(
            _gate_check(
                "latest_probe",
                "Latest Probe",
                "warning",
                str(latest_probe.get("summary", "") or "No successful provider probe has been recorded yet."),
                value=latest_probe_state,
                recommended_action=str(latest_probe.get("recommended_action", "") or "Run a provider probe when the environment is ready."),
            )
        )

    if latest_success.get("exists") and latest_success.get("probe_status") == "ok":
        checks.append(
            _gate_check(
                "latest_success_probe",
                "Latest Success",
                "pass",
                "A successful provider probe is recorded in history.",
                value=str(latest_success.get("generated_at", "") or latest_success.get("file_name", "")),
            )
        )
    else:
        checks.append(
            _gate_check(
                "latest_success_probe",
                "Latest Success",
                "warning",
                "No successful provider probe is recorded in history yet.",
                value="not recorded",
                recommended_action="Validate sandbox-first, then run a successful real provider probe once real credentials are ready.",
            )
        )

    latest_success_marker = _probe_marker(latest_success)
    latest_failure_marker = _probe_marker(latest_failure)
    failure_is_current = bool(
        latest_failure.get("exists")
        and latest_failure.get("probe_status") == "failed"
        and (not latest_success_marker or latest_failure_marker >= latest_success_marker)
    )
    if failure_is_current:
        checks.append(
            _gate_check(
                "latest_failure_probe",
                "Latest Failure",
                "warning",
                "A failed provider probe exists in history; keep the remediation visible until a newer success supersedes it.",
                value=str(latest_failure.get("error_code", "") or latest_failure_marker),
                recommended_action=str(latest_failure.get("recommended_action", "") or "Review the last failed provider smoke before release."),
            )
        )
    else:
        checks.append(
            _gate_check(
                "latest_failure_probe",
                "Latest Failure",
                "pass",
                "No failed provider probe is recorded in recent history.",
                value="none recorded",
            )
        )

    baseline_gate_status = str(baseline_status.get("status", "warning") or "warning")
    if not baseline_status.get("exists", False):
        checks.append(
            _gate_check(
                "latest_baseline",
                "Latest Baseline",
                "warning",
                "No rolling baseline artifact is available yet.",
                value="not generated",
                recommended_action="Run metrics_baseline before the next release slice.",
            )
        )
    elif baseline_gate_status != "ok":
        checks.append(
            _gate_check(
                "latest_baseline",
                "Latest Baseline",
                "warning",
                str(baseline_status.get("summary", "") or "Baseline still reports review debt."),
                value=str(baseline_status.get("file_name", "") or "baseline"),
                recommended_action="Review the current baseline warnings and rerun after parser or workflow fixes.",
            )
        )
    else:
        checks.append(
            _gate_check(
                "latest_baseline",
                "Latest Baseline",
                "pass",
                "Latest rolling baseline is healthy.",
                value=str(baseline_status.get("file_name", "") or "baseline"),
            )
        )

    overall_status = "pass"
    for item in checks:
        overall_status = _merge_gate_status(overall_status, str(item.get("status", "pass")))

    if overall_status == "blocked":
        summary = "Release gate is blocked for the current environment."
    elif overall_status == "warning":
        summary = "Release gate is not fully satisfied yet; warnings remain."
    else:
        summary = "Release gate is satisfied for the current environment."

    recommended_action = ""
    for severity in ("blocked", "warning"):
        for item in checks:
            if item.get("status") == severity and str(item.get("recommended_action", "")).strip():
                recommended_action = str(item.get("recommended_action", ""))
                break
        if recommended_action:
            break

    commands = [
        {"label": "Release Gate", "command": r"py -m app.tools.release_gate --config config\local.json"},
        {
            "label": "Sandbox First",
            "command": r"py -m app.tools.provider_sandbox --port 8010" + "\n"
            + r"py -m app.tools.provider_probe --provider external_http --endpoint http://127.0.0.1:8010/review --model sandbox-model --probe",
        },
        {"label": "Real Provider Smoke", "command": r"py -m app.tools.provider_probe --config config\local.json --probe"},
        {
            "label": "Rolling Baseline",
            "command": r"py -m app.tools.metrics_baseline --compare-latest-in-dir docs\dev --archive-dir docs\dev\history --archive-stem real-sample-baseline",
        },
        {"label": "Full Regression", "command": r"py -m pytest"},
    ]

    return {
        "status": overall_status,
        "mode": provider_mode,
        "summary": summary,
        "recommended_action": recommended_action,
        "checks": checks,
        "commands": commands,
        "latest_probe": latest_probe,
        "latest_success": latest_success,
        "latest_failure": latest_failure,
        "latest_baseline": baseline_status,
    }
