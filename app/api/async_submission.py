from __future__ import annotations

from pathlib import Path
from threading import Thread

from app.core.domain.enums import JobStatus
from app.core.domain.models import Job
from app.core.pipelines.submission_pipeline import ingest_submission
from app.core.services.app_logging import log_event
from app.core.services.job_runtime import classify_job_failure, update_job_state
from app.core.services.review_profile import normalize_review_profile
from app.core.services.runtime_store import store
from app.core.services.sqlite_repository import save_submission_graph
from app.core.utils.text import now_iso, slug_id


def _build_async_job_metadata(
    *,
    saved_path: Path,
    original_filename: str,
    mode: str,
    review_strategy: str,
    review_profile: dict,
    retry_count: int = 0,
    retry_of_job_id: str = "",
    retry_of_submission_id: str = "",
) -> dict:
    return {
        "source_path": str(saved_path),
        "original_filename": original_filename,
        "mode": mode,
        "review_strategy": review_strategy,
        "review_profile": dict(review_profile),
        "retry_count": max(int(retry_count or 0), 0),
        "retry_of_job_id": retry_of_job_id,
        "retry_of_submission_id": retry_of_submission_id,
    }


def start_async_submission_job(
    *,
    saved_path: Path,
    original_filename: str,
    mode: str,
    review_strategy: str,
    review_profile: dict,
    retry_count: int = 0,
    retry_of_job_id: str = "",
    retry_of_submission_id: str = "",
) -> tuple[Job, str]:
    submission_id = slug_id("sub")
    job = store.add_job(
        Job(
            id=slug_id("job"),
            job_type="ingest_submission",
            scope_type="submission",
            scope_id=submission_id,
            status=JobStatus.QUEUED.value,
            progress=2,
            stage="文件已接收",
            detail=f"已收到 {original_filename}，正在进入处理队列。",
            started_at=now_iso(),
            updated_at=now_iso(),
            retryable=False,
            metadata=_build_async_job_metadata(
                saved_path=saved_path,
                original_filename=original_filename,
                mode=mode,
                review_strategy=review_strategy,
                review_profile=review_profile,
                retry_count=retry_count,
                retry_of_job_id=retry_of_job_id,
                retry_of_submission_id=retry_of_submission_id,
            ),
        )
    )
    worker = Thread(
        target=_run_async_submission,
        kwargs={
            "saved_path": saved_path,
            "original_filename": original_filename,
            "mode": mode,
            "review_strategy": review_strategy,
            "review_profile": review_profile,
            "submission_id": submission_id,
            "job_id": job.id,
        },
        daemon=True,
    )
    worker.start()
    return job, submission_id


def retry_async_submission_job(job_id: str) -> tuple[Job, str]:
    job = store.jobs.get(job_id)
    if not job:
        raise ValueError("job_not_found")
    if str(getattr(job, "job_type", "") or "") != "ingest_submission":
        raise ValueError("unsupported_job_type")
    if str(getattr(job, "status", "") or "").strip().lower() not in {JobStatus.FAILED.value, JobStatus.INTERRUPTED.value}:
        raise ValueError("job_not_retryable_in_current_status")
    if not bool(getattr(job, "retryable", False)):
        raise ValueError("job_retry_disabled")

    metadata = dict(getattr(job, "metadata", {}) or {})
    source_path_raw = str(metadata.get("source_path", "") or "").strip()
    mode = str(metadata.get("mode", "") or "").strip()
    if not source_path_raw:
        raise ValueError("missing_source_path")
    source_path = Path(source_path_raw)
    if not source_path.exists():
        raise ValueError("missing_source_file")
    if not mode:
        raise ValueError("missing_submission_mode")

    original_filename = str(metadata.get("original_filename", "") or source_path.name).strip() or source_path.name
    review_strategy = str(metadata.get("review_strategy", "auto_review") or "auto_review").strip()
    review_profile = normalize_review_profile(dict(metadata.get("review_profile", {}) or {}))
    next_retry_count = int(metadata.get("retry_count", 0) or 0) + 1
    return start_async_submission_job(
        saved_path=source_path,
        original_filename=original_filename,
        mode=mode,
        review_strategy=review_strategy,
        review_profile=review_profile,
        retry_count=next_retry_count,
        retry_of_job_id=job_id,
        retry_of_submission_id=str(getattr(job, "scope_id", "") or ""),
    )


def _run_async_submission(
    saved_path: Path,
    *,
    original_filename: str,
    mode: str,
    review_strategy: str,
    review_profile: dict,
    submission_id: str,
    job_id: str,
) -> None:
    try:
        result = ingest_submission(
            saved_path,
            mode=mode,
            created_by="web_async",
            review_strategy=review_strategy,
            review_profile=review_profile,
            submission_id=submission_id,
            job_id=job_id,
        )
        log_event(
            "upload_submission_async_completed",
            {
                "submission_id": submission_id,
                "job_id": job_id,
                "mode": mode,
                "review_strategy": review_strategy,
                "review_profile": review_profile,
                "filename": original_filename,
                "material_count": len(result.get("materials", [])),
            },
        )
    except Exception as exc:
        error_message = str(exc)
        job = store.jobs.get(job_id)
        if job:
            error_code, retryable = classify_job_failure(exc)
            update_job_state(
                job,
                status="failed",
                progress=100,
                stage="处理失败",
                detail=error_message or "系统处理时发生错误。",
                error_message=error_message,
                error_code=error_code,
                retryable=retryable,
                finished=True,
            )
        submission = store.submissions.get(submission_id)
        if submission:
            submission.status = "failed"
            save_submission_graph(submission_id)
        log_event(
            "upload_submission_async_failed",
            {
                "submission_id": submission_id,
                "job_id": job_id,
                "mode": mode,
                "review_strategy": review_strategy,
                "review_profile": review_profile,
                "filename": original_filename,
                "error": error_message,
            },
        )
