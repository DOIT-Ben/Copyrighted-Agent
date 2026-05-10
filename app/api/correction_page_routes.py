from __future__ import annotations

from pathlib import Path
from typing import Callable
from urllib.parse import urlencode, urlsplit, urlunsplit

from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse

from app.core.services.app_logging import log_event
from app.core.services.corrections import (
    assign_material_to_case,
    change_material_type,
    continue_case_review_from_desensitized,
    create_case_from_materials,
    merge_cases,
    rerun_case_review,
    update_case_online_filing,
    update_submission_internal_state,
    upload_desensitized_package,
)
from app.core.services.online_filing import parse_online_filing_form
from app.core.services.runtime_store import store


UploadSaver = Callable[[UploadFile], Path]
ReviewProfileExtractor = Callable[..., dict]


def _with_notice(target: str, notice: str) -> str:
    parsed = urlsplit(target)
    existing_query = parsed.query
    notice_param = urlencode({"notice": notice})
    merged_query = f"{existing_query}&{notice_param}" if existing_query else notice_param
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, merged_query, parsed.fragment))


def register_correction_page_routes(
    app: FastAPI,
    *,
    save_uploaded_zip: UploadSaver,
    extract_review_profile: ReviewProfileExtractor,
    safe_submission_return_target: Callable[[str], str],
    submission_notice_location: Callable[..., str],
) -> None:
    @app.post("/submissions/{submission_id}/actions/update-internal-state")
    def update_internal_state_page(request: Request, submission_id: str):
        owner = request.form_data.get("internal_owner", "")
        internal_status = request.form_data.get("internal_status", "unassigned")
        next_step = request.form_data.get("internal_next_step", "")
        note = request.form_data.get("internal_note", "")
        updated_by = request.form_data.get("updated_by", "operator_ui")
        return_to = safe_submission_return_target(request.form_data.get("return_to", ""))
        try:
            update_submission_internal_state(
                submission_id,
                owner=owner,
                internal_status=internal_status,
                next_step=next_step,
                note=note,
                updated_by=updated_by,
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        log_event(
            "update_internal_state_html",
            {"submission_id": submission_id, "internal_status": internal_status, "owner": owner, "by": updated_by},
        )
        if return_to:
            return RedirectResponse(_with_notice(return_to, "internal_state_updated"), status_code=303)
        return RedirectResponse(submission_notice_location(submission_id, "internal_state_updated", focus="internal-workbench"), status_code=303)

    @app.post("/submissions/{submission_id}/actions/change-type")
    def change_material_type_page(request: Request, submission_id: str):
        material_id = request.form_data.get("material_id", "")
        material_type = request.form_data.get("material_type", "")
        note = request.form_data.get("note", "")
        corrected_by = request.form_data.get("corrected_by", "operator_ui")
        if not material_id or not material_type:
            raise HTTPException(422, "缺少 material_id 或 material_type")
        try:
            change_material_type(material_id, material_type, corrected_by=corrected_by, note=note)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        log_event(
            "change_material_type_html",
            {"submission_id": submission_id, "material_id": material_id, "material_type": material_type, "by": corrected_by},
        )
        return RedirectResponse(submission_notice_location(submission_id, "material_type_updated", focus="correction-audit"), status_code=303)

    @app.post("/submissions/{submission_id}/actions/assign-case")
    def assign_case_page(request: Request, submission_id: str):
        material_id = request.form_data.get("material_id", "")
        case_id = request.form_data.get("case_id", "")
        note = request.form_data.get("note", "")
        corrected_by = request.form_data.get("corrected_by", "operator_ui")
        if not material_id or not case_id:
            raise HTTPException(422, "缺少 material_id 或 case_id")
        try:
            assign_material_to_case(material_id, case_id, corrected_by=corrected_by, note=note)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        log_event(
            "assign_material_to_case_html",
            {"submission_id": submission_id, "material_id": material_id, "case_id": case_id, "by": corrected_by},
        )
        return RedirectResponse(submission_notice_location(submission_id, "material_assigned", focus="correction-audit"), status_code=303)

    @app.post("/submissions/{submission_id}/actions/create-case")
    def create_case_page(request: Request, submission_id: str):
        material_ids_raw = request.form_data.get("material_ids", "")
        case_name = request.form_data.get("case_name", "")
        version = request.form_data.get("version", "")
        company_name = request.form_data.get("company_name", "")
        note = request.form_data.get("note", "")
        corrected_by = request.form_data.get("corrected_by", "operator_ui")
        material_ids = [item.strip() for item in material_ids_raw.split(",") if item.strip()]
        if not material_ids:
            raise HTTPException(422, "缺少 material_ids")
        try:
            create_case_from_materials(
                submission_id,
                material_ids,
                case_name=case_name,
                version=version,
                company_name=company_name,
                corrected_by=corrected_by,
                note=note,
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        log_event(
            "create_case_from_materials_html",
            {"submission_id": submission_id, "material_ids": material_ids, "case_name": case_name, "by": corrected_by},
        )
        return RedirectResponse(submission_notice_location(submission_id, "case_created", focus="correction-audit"), status_code=303)

    @app.post("/submissions/{submission_id}/actions/merge-cases")
    def merge_cases_page(request: Request, submission_id: str):
        source_case_id = request.form_data.get("source_case_id", "")
        target_case_id = request.form_data.get("target_case_id", "")
        note = request.form_data.get("note", "")
        corrected_by = request.form_data.get("corrected_by", "operator_ui")
        if not source_case_id or not target_case_id:
            raise HTTPException(422, "缺少 source_case_id 或 target_case_id")
        try:
            merge_cases(source_case_id, target_case_id, corrected_by=corrected_by, note=note)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        log_event(
            "merge_cases_html",
            {"submission_id": submission_id, "source_case_id": source_case_id, "target_case_id": target_case_id, "by": corrected_by},
        )
        return RedirectResponse(submission_notice_location(submission_id, "cases_merged", focus="correction-audit"), status_code=303)

    @app.post("/submissions/{submission_id}/actions/rerun-review")
    def rerun_review_page(request: Request, submission_id: str):
        case_id = request.form_data.get("case_id", "")
        note = request.form_data.get("note", "")
        corrected_by = request.form_data.get("corrected_by", "operator_ui")
        submission = store.submissions.get(submission_id)
        review_profile = extract_review_profile(
            request.form_data,
            fallback=getattr(submission, "review_profile", {}) if submission else {},
        )
        if not case_id:
            raise HTTPException(422, "缺少 case_id")
        try:
            rerun_case_review(case_id, corrected_by=corrected_by, note=note, review_profile=review_profile)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        log_event(
            "rerun_case_review_html",
            {"submission_id": submission_id, "case_id": case_id, "review_profile": review_profile, "by": corrected_by},
        )
        return RedirectResponse(submission_notice_location(submission_id, "case_review_rerun", focus="export-center"), status_code=303)

    @app.post("/submissions/{submission_id}/actions/update-online-filing")
    def update_online_filing_page(request: Request, submission_id: str):
        case_id = request.form_data.get("case_id", "")
        note = request.form_data.get("note", "")
        corrected_by = request.form_data.get("corrected_by", "operator_ui")
        if not case_id:
            raise HTTPException(422, "缺少 case_id")
        try:
            update_case_online_filing(
                case_id,
                parse_online_filing_form(request.form_data),
                corrected_by=corrected_by,
                note=note,
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        log_event(
            "update_case_online_filing_html",
            {"submission_id": submission_id, "case_id": case_id, "by": corrected_by},
        )
        return RedirectResponse(submission_notice_location(submission_id, "case_review_rerun", focus="operator-console"), status_code=303)

    @app.post("/submissions/{submission_id}/actions/continue-review")
    def continue_review_page(request: Request, submission_id: str):
        case_id = request.form_data.get("case_id", "")
        note = request.form_data.get("note", "")
        corrected_by = request.form_data.get("corrected_by", "operator_ui")
        if not case_id:
            raise HTTPException(422, "缺少 case_id")
        try:
            continue_case_review_from_desensitized(case_id, corrected_by=corrected_by, note=note)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        log_event("continue_case_review_html", {"submission_id": submission_id, "case_id": case_id, "by": corrected_by})
        return RedirectResponse(submission_notice_location(submission_id, "case_review_continued", focus="export-center"), status_code=303)

    @app.post("/submissions/{submission_id}/actions/upload-desensitized-package")
    def upload_desensitized_package_page(request: Request, submission_id: str):
        upload = request.files.get("file")
        note = request.form_data.get("note", "")
        corrected_by = request.form_data.get("corrected_by", "operator_ui")
        if not upload:
            raise HTTPException(400, "缺少 ZIP 文件")
        if not upload.filename.lower().endswith(".zip"):
            raise HTTPException(415, "仅支持 ZIP 文件")
        saved = save_uploaded_zip(upload)
        try:
            upload_desensitized_package(submission_id, saved, corrected_by=corrected_by, note=note)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        log_event("upload_desensitized_package_html", {"submission_id": submission_id, "filename": upload.filename, "by": corrected_by})
        return RedirectResponse(
            submission_notice_location(submission_id, "desensitized_package_uploaded", focus="operator-console"),
            status_code=303,
        )
