from __future__ import annotations

import pytest

from tests.helpers.contracts import require_symbol


@pytest.mark.unit
@pytest.mark.contract
def test_recover_interrupted_jobs_marks_active_jobs_and_processing_submission(tmp_path):
    Submission = require_symbol("app.core.domain.models", "Submission")
    Job = require_symbol("app.core.domain.models", "Job")
    runtime_store = require_symbol("app.core.services.runtime_store", "store")
    recover_interrupted_jobs = require_symbol("app.core.services.job_runtime", "recover_interrupted_jobs")

    submission = Submission(
        id="sub_runtime",
        mode="single_case_package",
        filename="sample.zip",
        storage_path=str(tmp_path / "sample.zip"),
        status="processing",
        created_at="2026-05-02T10:00:00",
    )
    runtime_store.add_submission(submission)
    running_job = runtime_store.add_job(
        Job(
            id="job_running",
            job_type="ingest_submission",
            scope_type="submission",
            scope_id=submission.id,
            status="running",
            progress=42,
            started_at="2026-05-02T10:00:01",
        )
    )
    completed_job = runtime_store.add_job(
        Job(
            id="job_done",
            job_type="ingest_submission",
            scope_type="submission",
            scope_id=submission.id,
            status="completed",
            progress=100,
            started_at="2026-05-02T10:00:01",
            updated_at="2026-05-02T10:01:00",
            finished_at="2026-05-02T10:01:00",
        )
    )

    recovered = recover_interrupted_jobs(timestamp="2026-05-02T10:05:00")

    assert recovered == [
        {
            "job_id": "job_running",
            "scope_id": submission.id,
            "previous_status": "running",
            "recovered_status": "interrupted",
        }
    ]
    assert running_job.status == "interrupted"
    assert running_job.stage == "任务已中断"
    assert running_job.error_message == "worker_interrupted_during_runtime"
    assert running_job.error_code == "worker_interrupted_during_runtime"
    assert running_job.retryable is True
    assert running_job.updated_at == "2026-05-02T10:05:00"
    assert running_job.finished_at == "2026-05-02T10:05:00"
    assert runtime_store.submissions[submission.id].status == "failed"
    assert completed_job.status == "completed"


@pytest.mark.unit
@pytest.mark.contract
def test_classify_job_failure_distinguishes_retryable_and_non_retryable_cases():
    classify_job_failure = require_symbol("app.core.services.job_runtime", "classify_job_failure")

    assert classify_job_failure(ValueError("Unsupported submission mode: bad_mode")) == ("unsupported_submission_mode", False)
    assert classify_job_failure(FileNotFoundError("missing")) == ("source_file_missing", False)
    assert classify_job_failure(OSError("busy")) == ("filesystem_io_error", True)
    assert classify_job_failure(RuntimeError("boom")) == ("unexpected_runtime_error", True)
