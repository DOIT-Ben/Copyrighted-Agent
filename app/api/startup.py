from __future__ import annotations

from app.core.services.app_logging import log_event
from app.core.services.job_runtime import recover_interrupted_jobs
from app.core.services.sqlite_repository import load_all_into_store, save_submission_graph
from app.core.services.startup_checks import run_startup_self_check


def prepare_runtime(*, testing: bool = False) -> dict:
    startup_report = run_startup_self_check()
    if testing:
        return startup_report

    load_all_into_store()
    recovered_jobs = recover_interrupted_jobs()
    for item in recovered_jobs:
        if item.get("scope_id"):
            save_submission_graph(item["scope_id"])
    try:
        log_event(
            "startup_self_check",
            {
                "status": startup_report.get("status", "unknown"),
                "failed_checks": [item.get("name") for item in startup_report.get("checks", []) if item.get("status") == "failed"],
                "recovered_jobs": recovered_jobs,
            },
        )
    except OSError:
        pass
    return startup_report
