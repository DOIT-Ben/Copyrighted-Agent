from __future__ import annotations

import zipfile

from app.core.domain.enums import JobStatus
from app.core.services.runtime_store import store
from app.core.utils.text import now_iso


ACTIVE_JOB_STATUSES = {
    JobStatus.QUEUED.value,
    JobStatus.PENDING.value,
    JobStatus.RUNNING.value,
    "processing",
}
TERMINAL_JOB_STATUSES = {
    JobStatus.COMPLETED.value,
    JobStatus.FAILED.value,
    JobStatus.INTERRUPTED.value,
}
RETRYABLE_FAILURE_CODES = {
    "worker_interrupted_during_runtime",
    "filesystem_io_error",
    "unexpected_runtime_error",
}


def classify_job_failure(exc: Exception) -> tuple[str, bool]:
    message = str(exc or "").strip()
    if isinstance(exc, zipfile.BadZipFile):
        return "invalid_zip_archive", False
    if isinstance(exc, FileNotFoundError):
        return "source_file_missing", False
    if isinstance(exc, PermissionError):
        return "filesystem_permission_denied", False
    if isinstance(exc, OSError):
        return "filesystem_io_error", True
    if isinstance(exc, ValueError):
        lowered = message.lower()
        if "unsupported submission mode" in lowered:
            return "unsupported_submission_mode", False
        if "unsupported review strategy" in lowered:
            return "unsupported_review_strategy", False
        if "unsupported input source" in lowered:
            return "unsupported_input_source", False
        return "invalid_submission_request", False
    return "unexpected_runtime_error", True


def update_job_state(
    job,
    *,
    status: str | None = None,
    progress: int | None = None,
    stage: str | None = None,
    detail: str | None = None,
    error_message: str | None = None,
    error_code: str | None = None,
    retryable: bool | None = None,
    metadata_updates: dict | None = None,
    finished: bool = False,
    timestamp: str | None = None,
) -> None:
    stamp = timestamp or now_iso()
    if status is not None:
        job.status = status
    if progress is not None:
        job.progress = progress
    if stage is not None:
        job.stage = stage
    if detail is not None:
        job.detail = detail
    if error_message is not None:
        job.error_message = error_message
    if error_code is not None:
        job.error_code = error_code
    if retryable is not None:
        job.retryable = retryable
    if metadata_updates:
        merged = dict(getattr(job, "metadata", {}) or {})
        merged.update(metadata_updates)
        job.metadata = merged
    job.updated_at = stamp
    if finished or str(job.status or "").strip().lower() in TERMINAL_JOB_STATUSES:
        job.finished_at = stamp


def recover_interrupted_jobs(*, timestamp: str | None = None) -> list[dict]:
    stamp = timestamp or now_iso()
    recovered: list[dict] = []
    for job in list(store.jobs.values()):
        status = str(getattr(job, "status", "") or "").strip().lower()
        if status not in ACTIVE_JOB_STATUSES:
            continue

        update_job_state(
            job,
            status=JobStatus.INTERRUPTED.value,
            progress=max(int(getattr(job, "progress", 0) or 0), 1),
            stage="任务已中断",
            detail="服务上次退出时任务尚未完成，请重新提交或重试。",
            error_message="worker_interrupted_during_runtime",
            error_code="worker_interrupted_during_runtime",
            retryable=True,
            finished=True,
            timestamp=stamp,
        )

        submission_id = str(getattr(job, "scope_id", "") or "").strip()
        submission = store.submissions.get(submission_id)
        if submission and str(getattr(submission, "status", "") or "").strip().lower() in {
            "queued",
            "pending",
            "processing",
            "running",
        }:
            submission.status = "failed"

        recovered.append(
            {
                "job_id": getattr(job, "id", ""),
                "scope_id": submission_id,
                "previous_status": status,
                "recovered_status": JobStatus.INTERRUPTED.value,
            }
        )
    return recovered
