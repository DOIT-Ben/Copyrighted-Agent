from __future__ import annotations

from typing import Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.domain.enums import JobStatus
from app.core.services.review_profile import list_review_rule_history, normalize_review_profile
from app.core.services.runtime_store import store
from app.core.services.sqlite_repository import (
    list_correction_feedback,
    list_manual_review_queue,
    list_retryable_jobs,
)
from app.core.services.submission_insights import submission_quality_snapshot


SubmissionDiagnosticsBuilder = Callable[[str], dict]


def register_api_read_routes(app: FastAPI, *, submission_diagnostics_payload: SubmissionDiagnosticsBuilder) -> None:
    @app.get("/api/submissions/{submission_id}")
    def api_get_submission(request: Request, submission_id: str):
        del request
        submission = store.submissions.get(submission_id)
        if not submission:
            raise HTTPException(404, "未找到批次")
        return JSONResponse(submission.to_dict())

    @app.get("/api/submissions/{submission_id}/corrections")
    def api_get_submission_corrections(request: Request, submission_id: str):
        del request
        submission = store.submissions.get(submission_id)
        if not submission:
            raise HTTPException(404, "未找到批次")
        corrections = [store.corrections[item_id].to_dict() for item_id in submission.correction_ids if item_id in store.corrections]
        return JSONResponse(
            {
                "submission_id": submission_id,
                "summary": submission_quality_snapshot(submission_id),
                "review_profile_meta": dict((getattr(submission, "review_profile", {}) or {}).get("rulebook_meta", {}) or {}),
                "corrections": corrections,
            }
        )

    @app.get("/api/submissions/{submission_id}/diagnostics")
    def api_get_submission_diagnostics(request: Request, submission_id: str):
        del request
        return JSONResponse(submission_diagnostics_payload(submission_id))

    @app.get("/api/submissions/{submission_id}/review-rules/{dimension_key}/history")
    def api_get_submission_review_rule_history(request: Request, submission_id: str, dimension_key: str):
        del request
        submission = store.submissions.get(submission_id)
        if not submission:
            raise HTTPException(404, "submission not found")
        review_profile = normalize_review_profile(getattr(submission, "review_profile", {}) or {})
        rulebook_meta = dict(review_profile.get("rulebook_meta", {}) or {})
        return JSONResponse(
            {
                "submission_id": submission_id,
                "dimension_key": dimension_key,
                "current_revision": int(rulebook_meta.get("revision", 1) or 1),
                "items": list_review_rule_history(submission_id, dimension_key, limit=20),
            }
        )

    @app.get("/api/submissions/{submission_id}/files")
    def api_get_submission_files(request: Request, submission_id: str):
        del request
        submission = store.submissions.get(submission_id)
        if not submission:
            raise HTTPException(404, "未找到批次")
        materials = [store.materials[item_id].to_dict() for item_id in submission.material_ids if item_id in store.materials]
        return JSONResponse({"files": materials})

    @app.get("/api/cases/{case_id}")
    def api_get_case(request: Request, case_id: str):
        del request
        case = store.cases.get(case_id)
        if not case:
            raise HTTPException(404, "未找到项目")
        return JSONResponse(case.to_dict())

    @app.get("/api/jobs/{job_id}")
    def api_get_job(request: Request, job_id: str):
        del request
        job = store.jobs.get(job_id)
        if not job:
            raise HTTPException(404, "未找到任务")
        payload = job.to_dict()
        payload["can_retry"] = bool(
            payload.get("retryable")
            and payload.get("job_type") == "ingest_submission"
            and str(payload.get("status", "") or "").strip().lower() in {JobStatus.FAILED.value, JobStatus.INTERRUPTED.value}
            and str((payload.get("metadata") or {}).get("source_path", "")).strip()
        )
        payload["retry_url"] = f"/api/jobs/{job_id}/retry" if payload["can_retry"] else ""
        return JSONResponse(payload)

    @app.get("/api/ops/manual-review-queue")
    def api_get_manual_review_queue(request: Request):
        del request
        return JSONResponse({"items": list_manual_review_queue(limit=12)})

    @app.get("/api/ops/correction-feedback")
    def api_get_correction_feedback(request: Request):
        del request
        return JSONResponse({"items": list_correction_feedback(limit=12)})

    @app.get("/api/ops/retryable-jobs")
    def api_get_retryable_jobs(request: Request):
        del request
        return JSONResponse({"items": list_retryable_jobs(limit=12)})
