from __future__ import annotations

from fastapi import FastAPI

from app.api.api_read_routes import register_api_read_routes
from app.api.async_submission import retry_async_submission_job, start_async_submission_job
from app.api.correction_api_routes import register_correction_api_routes
from app.api.correction_page_routes import register_correction_page_routes
from app.api.download_routes import register_download_routes
from app.api.file_transfer import download_response, save_uploaded_zip
from app.api.job_retry_routes import register_job_retry_routes
from app.api.ops_report import build_ops_report
from app.api.page_routes import register_page_routes
from app.api.rule_routes import register_rule_routes
from app.api.static_routes import register_static_routes
from app.api.submission_support import (
    safe_submission_return_target,
    submission_context,
    submission_diagnostics_payload,
    submission_notice_location,
    submission_notice_payload,
)
from app.api.upload_routes import register_upload_routes
from app.core.services.review_profile import normalize_review_profile, parse_review_profile_form


def _extract_review_profile(form_data, *, fallback: dict | None = None) -> dict:
    return normalize_review_profile(parse_review_profile_form(form_data, fallback=fallback))


def register_routes(app: FastAPI) -> None:
    register_page_routes(
        app,
        build_ops_report=build_ops_report,
        submission_context=submission_context,
        submission_notice_payload=submission_notice_payload,
    )
    register_static_routes(app)
    register_upload_routes(
        app,
        save_uploaded_zip=save_uploaded_zip,
        extract_review_profile=_extract_review_profile,
        start_async_submission_job=start_async_submission_job,
    )

    register_api_read_routes(app, submission_diagnostics_payload=submission_diagnostics_payload)
    register_rule_routes(app, submission_notice_location=submission_notice_location)
    register_job_retry_routes(
        app,
        retry_async_submission_job=retry_async_submission_job,
        safe_submission_return_target=safe_submission_return_target,
        submission_notice_location=submission_notice_location,
    )
    register_correction_api_routes(app, save_uploaded_zip=save_uploaded_zip)
    register_correction_page_routes(
        app,
        save_uploaded_zip=save_uploaded_zip,
        extract_review_profile=_extract_review_profile,
        safe_submission_return_target=safe_submission_return_target,
        submission_notice_location=submission_notice_location,
    )
    register_download_routes(app, download_response)
