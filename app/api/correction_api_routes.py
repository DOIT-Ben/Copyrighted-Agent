from __future__ import annotations

from pathlib import Path
from typing import Callable

from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from app.core.services.corrections import (
    assign_material_to_case,
    change_material_type,
    continue_case_review_from_desensitized,
    create_case_from_materials,
    merge_cases,
    rerun_case_review,
    update_case_online_filing,
    upload_desensitized_package,
)
from app.core.services.online_filing import parse_online_filing_form


UploadSaver = Callable[[UploadFile], Path]


def register_correction_api_routes(app: FastAPI, *, save_uploaded_zip: UploadSaver) -> None:
    @app.post("/api/materials/{material_id}/type")
    def api_change_material_type(request: Request, material_id: str):
        material_type = request.form_data.get("material_type", "")
        note = request.form_data.get("note", "")
        corrected_by = request.form_data.get("corrected_by", "local")
        if not material_type:
            raise HTTPException(422, "缺少 material_type")
        try:
            result = change_material_type(material_id, material_type, corrected_by=corrected_by, note=note)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        return JSONResponse(result)

    @app.post("/api/materials/{material_id}/assign-case")
    def api_assign_material_to_case(request: Request, material_id: str):
        case_id = request.form_data.get("case_id", "")
        note = request.form_data.get("note", "")
        corrected_by = request.form_data.get("corrected_by", "local")
        if not case_id:
            raise HTTPException(422, "缺少 case_id")
        try:
            result = assign_material_to_case(material_id, case_id, corrected_by=corrected_by, note=note)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        return JSONResponse(result)

    @app.post("/api/submissions/{submission_id}/cases")
    def api_create_case_from_materials(request: Request, submission_id: str):
        material_ids_raw = request.form_data.get("material_ids", "")
        case_name = request.form_data.get("case_name", "")
        version = request.form_data.get("version", "")
        company_name = request.form_data.get("company_name", "")
        note = request.form_data.get("note", "")
        corrected_by = request.form_data.get("corrected_by", "local")
        material_ids = [item.strip() for item in material_ids_raw.split(",") if item.strip()]
        if not material_ids:
            raise HTTPException(422, "缺少 material_ids")
        try:
            result = create_case_from_materials(
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
        return JSONResponse(result)

    @app.post("/api/cases/{case_id}/merge")
    def api_merge_cases(request: Request, case_id: str):
        target_case_id = request.form_data.get("target_case_id", "")
        note = request.form_data.get("note", "")
        corrected_by = request.form_data.get("corrected_by", "local")
        if not target_case_id:
            raise HTTPException(422, "缺少 target_case_id")
        try:
            result = merge_cases(case_id, target_case_id, corrected_by=corrected_by, note=note)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        return JSONResponse(result)

    @app.post("/api/cases/{case_id}/rerun-review")
    def api_rerun_case_review(request: Request, case_id: str):
        note = request.form_data.get("note", "")
        corrected_by = request.form_data.get("corrected_by", "local")
        try:
            result = rerun_case_review(case_id, corrected_by=corrected_by, note=note)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        return JSONResponse(result)

    @app.post("/api/cases/{case_id}/online-filing")
    def api_update_case_online_filing(request: Request, case_id: str):
        note = request.form_data.get("note", "")
        corrected_by = request.form_data.get("corrected_by", "local")
        try:
            result = update_case_online_filing(
                case_id,
                parse_online_filing_form(request.form_data),
                corrected_by=corrected_by,
                note=note,
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        return JSONResponse(result)

    @app.post("/api/cases/{case_id}/continue-review")
    def api_continue_case_review(request: Request, case_id: str):
        note = request.form_data.get("note", "")
        corrected_by = request.form_data.get("corrected_by", "local")
        try:
            result = continue_case_review_from_desensitized(case_id, corrected_by=corrected_by, note=note)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        return JSONResponse(result)

    @app.post("/api/submissions/{submission_id}/desensitized-package")
    def api_upload_desensitized_package(request: Request, submission_id: str):
        upload = request.files.get("file")
        note = request.form_data.get("note", "")
        corrected_by = request.form_data.get("corrected_by", "local")
        if not upload:
            raise HTTPException(400, "缺少 ZIP 文件")
        if not upload.filename.lower().endswith(".zip"):
            raise HTTPException(415, "仅支持 ZIP 文件")
        saved = save_uploaded_zip(upload)
        try:
            result = upload_desensitized_package(submission_id, saved, corrected_by=corrected_by, note=note)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        return JSONResponse(result)
