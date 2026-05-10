from __future__ import annotations

from typing import Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.core.domain.models import Job
from app.core.services.app_logging import log_event
from app.core.services.runtime_store import store


RetrySubmissionJob = Callable[[str], tuple[Job, str]]


def _retry_error(exc: ValueError) -> HTTPException:
    error_code = str(exc)
    if error_code == "job_not_found":
        return HTTPException(404, "任务不存在")
    if error_code == "unsupported_job_type":
        return HTTPException(400, "当前仅支持重试导入任务")
    if error_code == "missing_source_file":
        return HTTPException(409, "原始上传文件已不存在，无法重试")
    if error_code == "missing_source_path":
        return HTTPException(409, "任务缺少可重试的源文件路径")
    if error_code == "missing_submission_mode":
        return HTTPException(409, "任务缺少导入模式，无法重试")
    return HTTPException(409, "当前任务不可重试")


def register_job_retry_routes(
    app: FastAPI,
    *,
    retry_async_submission_job: RetrySubmissionJob,
    safe_submission_return_target: Callable[[str], str],
    submission_notice_location: Callable[..., str],
) -> None:
    @app.post("/api/jobs/{job_id}/retry")
    def api_retry_job(request: Request, job_id: str):
        del request
        original_job = store.jobs.get(job_id)
        if not original_job:
            raise HTTPException(404, "任务不存在")
        try:
            retried_job, submission_id = retry_async_submission_job(job_id)
        except ValueError as exc:
            raise _retry_error(exc) from exc
        log_event(
            "upload_submission_async_retried",
            {
                "retry_of_job_id": job_id,
                "retry_of_submission_id": str(getattr(original_job, "scope_id", "") or ""),
                "job_id": retried_job.id,
                "submission_id": submission_id,
                "mode": str((getattr(retried_job, "metadata", {}) or {}).get("mode", "") or ""),
                "review_strategy": str((getattr(retried_job, "metadata", {}) or {}).get("review_strategy", "") or ""),
                "retry_count": int((getattr(retried_job, "metadata", {}) or {}).get("retry_count", 0) or 0),
            },
        )
        return JSONResponse(
            {
                "job_id": retried_job.id,
                "submission_id": submission_id,
                "status_url": f"/api/jobs/{retried_job.id}",
                "redirect_url": f"/submissions/{submission_id}",
                "retry_of_job_id": job_id,
            },
            status_code=202,
        )

    @app.post("/submissions/{submission_id}/actions/retry-job")
    def retry_job_page(request: Request, submission_id: str):
        job_id = request.form_data.get("job_id", "")
        return_to = safe_submission_return_target(request.form_data.get("return_to", ""))
        if not job_id:
            raise HTTPException(422, "缺少 job_id")
        original_job = store.jobs.get(job_id)
        if not original_job:
            raise HTTPException(404, "任务不存在")
        if str(getattr(original_job, "scope_id", "") or "") != submission_id:
            raise HTTPException(400, "任务与批次不匹配")
        try:
            retried_job, new_submission_id = retry_async_submission_job(job_id)
        except ValueError as exc:
            raise _retry_error(exc) from exc
        log_event(
            "upload_submission_async_retried_html",
            {
                "retry_of_job_id": job_id,
                "retry_of_submission_id": submission_id,
                "job_id": retried_job.id,
                "submission_id": new_submission_id,
            },
        )
        if return_to:
            return RedirectResponse(return_to, status_code=303)
        return RedirectResponse(submission_notice_location(new_submission_id, "job_retried", focus="internal-workbench"), status_code=303)
