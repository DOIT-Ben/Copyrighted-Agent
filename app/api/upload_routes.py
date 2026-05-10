from __future__ import annotations

from pathlib import Path
from typing import Callable

from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse

from app.core.domain.models import Job
from app.core.pipelines.submission_pipeline import ingest_submission
from app.core.services.app_logging import log_event


UploadSaver = Callable[[UploadFile], Path]
ReviewProfileExtractor = Callable[[dict], dict]
AsyncSubmissionStarter = Callable[..., tuple[Job, str]]


def _uploaded_zip(request: Request, *, missing_message: str) -> UploadFile:
    upload = request.files.get("file")
    if not upload:
        raise HTTPException(400, missing_message)
    if not upload.filename.lower().endswith(".zip"):
        raise HTTPException(415, "仅支持 ZIP 文件")
    return upload


def register_upload_routes(
    app: FastAPI,
    *,
    save_uploaded_zip: UploadSaver,
    extract_review_profile: ReviewProfileExtractor,
    start_async_submission_job: AsyncSubmissionStarter,
) -> None:
    @app.post("/upload")
    def upload_page(request: Request):
        upload = _uploaded_zip(request, missing_message="缺少 ZIP 文件")
        mode = request.form_data.get("mode", "single_case_package")
        review_strategy = request.form_data.get("review_strategy", "auto_review")
        review_profile = extract_review_profile(request.form_data)
        saved = save_uploaded_zip(upload)
        result = ingest_submission(saved, mode=mode, review_strategy=review_strategy, review_profile=review_profile)
        submission_id = result["submission"]["id"]
        log_event(
            "upload_submission_html",
            {
                "submission_id": submission_id,
                "mode": mode,
                "review_strategy": review_strategy,
                "review_profile": review_profile,
                "filename": upload.filename,
            },
        )
        return RedirectResponse(f"/submissions/{submission_id}", status_code=302)

    @app.post("/api/submissions")
    def api_create_submission(request: Request):
        upload = _uploaded_zip(request, missing_message="缺少文件")
        mode = request.form_data.get("mode", "")
        review_strategy = request.form_data.get("review_strategy", "auto_review")
        review_profile = extract_review_profile(request.form_data)
        if not mode:
            raise HTTPException(422, "缺少导入模式")
        saved = save_uploaded_zip(upload)
        result = ingest_submission(saved, mode=mode, review_strategy=review_strategy, review_profile=review_profile)
        payload = {
            "id": result["submission"]["id"],
            "status": result["submission"]["status"],
            "review_strategy": result["submission"]["review_strategy"],
            "review_profile": result["submission"].get("review_profile", {}),
            "cases": result["cases"],
            "materials": result["materials"],
            "reports": result["reports"],
        }
        log_event(
            "upload_submission_api",
            {
                "submission_id": payload["id"],
                "mode": mode,
                "review_strategy": review_strategy,
                "review_profile": review_profile,
                "filename": upload.filename,
            },
        )
        return JSONResponse(payload, status_code=201)

    @app.post("/api/submissions/async")
    def api_create_submission_async(request: Request):
        upload = _uploaded_zip(request, missing_message="缺少文件")
        mode = request.form_data.get("mode", "")
        review_strategy = request.form_data.get("review_strategy", "auto_review")
        review_profile = extract_review_profile(request.form_data)
        if not mode:
            raise HTTPException(422, "缺少导入模式")

        saved = save_uploaded_zip(upload)
        job, submission_id = start_async_submission_job(
            saved_path=saved,
            original_filename=upload.filename,
            mode=mode,
            review_strategy=review_strategy,
            review_profile=review_profile,
        )
        log_event(
            "upload_submission_async_started",
            {
                "submission_id": submission_id,
                "job_id": job.id,
                "mode": mode,
                "review_strategy": review_strategy,
                "review_profile": review_profile,
                "filename": upload.filename,
            },
        )
        return JSONResponse(
            {
                "job_id": job.id,
                "submission_id": submission_id,
                "status_url": f"/api/jobs/{job.id}",
                "redirect_url": f"/submissions/{submission_id}",
            },
            status_code=202,
        )
