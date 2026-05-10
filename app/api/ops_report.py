from __future__ import annotations

from app.core.services.delivery_closeout import latest_delivery_closeout_status
from app.core.services.provider_probe import (
    latest_failed_provider_probe_status,
    latest_successful_provider_probe_status,
    list_provider_probe_history,
)
from app.core.services.release_gate import evaluate_release_gate
from app.core.services.startup_checks import run_startup_self_check


def build_ops_report(config) -> dict:
    startup_report = run_startup_self_check(config)
    startup_report["provider_probe_history"] = list_provider_probe_history(config, limit=8)
    startup_report["provider_probe_last_success"] = latest_successful_provider_probe_status(config)
    startup_report["provider_probe_last_failure"] = latest_failed_provider_probe_status(config)
    startup_report["release_gate"] = evaluate_release_gate(config, startup_report=startup_report)
    startup_report["delivery_closeout"] = latest_delivery_closeout_status()
    return startup_report
