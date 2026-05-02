from __future__ import annotations

import pytest

from tests.helpers.contracts import require_symbol


@pytest.mark.integration
@pytest.mark.contract
def test_create_app_recovers_persisted_active_jobs_on_startup(monkeypatch, tmp_path):
    Submission = require_symbol("app.core.domain.models", "Submission")
    Job = require_symbol("app.core.domain.models", "Job")
    runtime_store = require_symbol("app.core.services.runtime_store", "store")
    save_submission_graph = require_symbol("app.core.services.sqlite_repository", "save_submission_graph")
    clear_database = require_symbol("app.core.services.sqlite_repository", "clear_database")
    create_app = require_symbol("app.api.main", "create_app")

    runtime_root = tmp_path / "runtime"
    sqlite_path = runtime_root / "soft_review.db"
    log_path = runtime_root / "logs" / "app.jsonl"
    monkeypatch.setenv("SOFT_REVIEW_DATA_ROOT", str(runtime_root))
    monkeypatch.setenv("SOFT_REVIEW_SQLITE_PATH", str(sqlite_path))
    monkeypatch.setenv("SOFT_REVIEW_LOG_PATH", str(log_path))

    clear_database()
    submission = runtime_store.add_submission(
        Submission(
            id="sub_boot_recover",
            mode="single_case_package",
            filename="boot.zip",
            storage_path=str(runtime_root / "uploads" / "boot.zip"),
            status="processing",
            created_at="2026-05-02T09:00:00",
        )
    )
    runtime_store.add_job(
        Job(
            id="job_boot_recover",
            job_type="ingest_submission",
            scope_type="submission",
            scope_id=submission.id,
            status="queued",
            progress=2,
            started_at="2026-05-02T09:00:01",
            updated_at="2026-05-02T09:00:01",
        )
    )
    save_submission_graph(submission.id)
    runtime_store.reset()

    app = create_app(testing=False)
    assert app is not None

    restored_job = runtime_store.jobs["job_boot_recover"]
    restored_submission = runtime_store.submissions[submission.id]
    assert restored_job.status == "interrupted"
    assert restored_job.finished_at
    assert restored_submission.status == "failed"

    clear_database()
