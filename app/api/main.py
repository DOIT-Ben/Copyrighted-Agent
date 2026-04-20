from __future__ import annotations

from pathlib import Path
from urllib.parse import urlencode
from wsgiref.simple_server import make_server

from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from app.core.pipelines.submission_pipeline import ingest_submission
from app.core.services.app_config import load_app_config
from app.core.services.app_logging import log_event, read_log_text
from app.core.services.corrections import (
    assign_material_to_case,
    change_material_type,
    create_case_from_materials,
    merge_cases,
    rerun_case_review,
)
from app.core.services.exports import build_submission_export_bundle, get_material_artifact, get_report_download
from app.core.services.provider_probe import (
    get_provider_probe_artifact_download,
    latest_failed_provider_probe_status,
    latest_successful_provider_probe_status,
    list_provider_probe_history,
)
from app.core.services.release_gate import evaluate_release_gate
from app.core.services.sqlite_repository import load_all_into_store
from app.core.services.startup_checks import run_startup_self_check
from app.core.services.runtime_store import store
from app.core.utils.text import ensure_dir, slug_id
from app.web.pages import (
    render_case_detail,
    render_home_page,
    render_ops_page,
    render_report_page,
    render_stylesheet,
    render_submission_detail,
    render_submissions_index,
)


def _save_uploaded_zip(upload: UploadFile) -> Path:
    uploads_dir = ensure_dir(Path(load_app_config().data_root) / "uploads")
    target = uploads_dir / f"{slug_id('upload')}_{upload.filename}"
    target.write_bytes(upload.content)
    return target


def _download_response(payload: bytes, filename: str, media_type: str) -> Response:
    response = Response(
        payload,
        status_code=200,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
    response.media_type = media_type
    return response


def _build_ops_report(config) -> dict:
    startup_report = run_startup_self_check(config)
    startup_report["provider_probe_history"] = list_provider_probe_history(config, limit=8)
    startup_report["provider_probe_last_success"] = latest_successful_provider_probe_status(config)
    startup_report["provider_probe_last_failure"] = latest_failed_provider_probe_status(config)
    startup_report["release_gate"] = evaluate_release_gate(config, startup_report=startup_report)
    return startup_report


SUBMISSION_NOTICE_MAP = {
    "material_type_updated": {
        "title": "材料类型已更新",
        "message": "选中的材料类型已完成更正，相关留痕已同步写入更正审计。",
        "tone": "success",
        "icon_name": "check",
        "meta": ["已记录留痕", "批次页已刷新"],
    },
    "material_assigned": {
        "title": "材料已归入项目",
        "message": "选中的材料已移入目标项目，项目分组结果已刷新。",
        "tone": "success",
        "icon_name": "merge",
        "meta": ["项目分组已更新", "人工操作已留痕"],
    },
    "case_created": {
        "title": "新项目已创建",
        "message": "系统已基于选中材料创建新项目。若开启真实模型，后续审查耗时可能略有上升。",
        "tone": "success",
        "icon_name": "lock",
        "meta": ["项目分组已更新", "审查链路已保留"],
    },
    "cases_merged": {
        "title": "项目已合并",
        "message": "源项目已并入目标项目，当前批次页已呈现新的聚合结果。",
        "tone": "success",
        "icon_name": "merge",
        "meta": ["分组结果已更新", "审计链路已保留"],
    },
    "case_review_rerun": {
        "title": "项目审查已重跑",
        "message": "选中的项目已重新审查，新的报告和 AI 信号会在可用时同步显示。",
        "tone": "info",
        "icon_name": "refresh",
        "meta": ["审查结果已刷新", "导出中心可能更新"],
    },
}


def _submission_notice_payload(code: str) -> dict | None:
    return SUBMISSION_NOTICE_MAP.get(str(code or "").strip())


def _submission_notice_location(submission_id: str, code: str, *, focus: str = "") -> str:
    base = f"/submissions/{submission_id}"
    query = urlencode({"notice": code}) if code else ""
    fragment = f"#{focus}" if focus else ""
    if not query:
        return f"{base}{fragment}"
    return f"{base}?{query}{fragment}"


def create_app(testing: bool = False):
    startup_report = run_startup_self_check()
    if not testing:
        load_all_into_store()
        try:
            log_event(
                "startup_self_check",
                {
                    "status": startup_report.get("status", "unknown"),
                    "failed_checks": [
                        item.get("name") for item in startup_report.get("checks", []) if item.get("status") == "failed"
                    ],
                },
            )
        except OSError:
            pass
    app = FastAPI(title="软著分析平台")

    @app.get("/")
    def home(request: Request):
        return HTMLResponse(render_home_page())

    @app.get("/submissions")
    def submission_index(request: Request):
        return HTMLResponse(render_submissions_index())

    @app.get("/ops")
    def ops_page(request: Request):
        config = load_app_config()
        return HTMLResponse(render_ops_page(config.to_dict(), _build_ops_report(config)))

    @app.get("/static/styles.css")
    def styles(request: Request):
        response = Response(
            render_stylesheet(),
            status_code=200,
            headers={"Cache-Control": "no-store"},
        )
        response.media_type = "text/css; charset=utf-8"
        return response

    @app.post("/upload")
    def upload_page(request: Request):
        upload = request.files.get("file")
        mode = request.form_data.get("mode", "single_case_package")
        if not upload:
            raise HTTPException(400, "缺少 ZIP 文件")
        if not upload.filename.lower().endswith(".zip"):
            raise HTTPException(415, "仅支持 ZIP 文件")
        saved = _save_uploaded_zip(upload)
        result = ingest_submission(saved, mode=mode)
        submission_id = result["submission"]["id"]
        log_event("upload_submission_html", {"submission_id": submission_id, "mode": mode, "filename": upload.filename})
        return RedirectResponse(f"/submissions/{submission_id}", status_code=302)

    @app.post("/api/submissions")
    def api_create_submission(request: Request):
        upload = request.files.get("file")
        mode = request.form_data.get("mode", "")
        if not upload:
            raise HTTPException(400, "缺少文件")
        if not upload.filename.lower().endswith(".zip"):
            raise HTTPException(415, "仅支持 ZIP 文件")
        if not mode:
            raise HTTPException(422, "缺少导入模式")
        saved = _save_uploaded_zip(upload)
        result = ingest_submission(saved, mode=mode)
        payload = {
            "id": result["submission"]["id"],
            "status": result["submission"]["status"],
            "cases": result["cases"],
            "materials": result["materials"],
            "reports": result["reports"],
        }
        log_event("upload_submission_api", {"submission_id": payload["id"], "mode": mode, "filename": upload.filename})
        return JSONResponse(payload, status_code=201)

    @app.get("/api/submissions/{submission_id}")
    def api_get_submission(request: Request, submission_id: str):
        submission = store.submissions.get(submission_id)
        if not submission:
            raise HTTPException(404, "未找到批次")
        return JSONResponse(submission.to_dict())

    @app.get("/api/submissions/{submission_id}/corrections")
    def api_get_submission_corrections(request: Request, submission_id: str):
        submission = store.submissions.get(submission_id)
        if not submission:
            raise HTTPException(404, "未找到批次")
        corrections = [store.corrections[item_id].to_dict() for item_id in submission.correction_ids if item_id in store.corrections]
        return JSONResponse({"corrections": corrections})

    @app.get("/api/submissions/{submission_id}/files")
    def api_get_submission_files(request: Request, submission_id: str):
        submission = store.submissions.get(submission_id)
        if not submission:
            raise HTTPException(404, "未找到批次")
        materials = [store.materials[item_id].to_dict() for item_id in submission.material_ids if item_id in store.materials]
        return JSONResponse({"files": materials})

    @app.get("/api/cases/{case_id}")
    def api_get_case(request: Request, case_id: str):
        case = store.cases.get(case_id)
        if not case:
            raise HTTPException(404, "未找到项目")
        return JSONResponse(case.to_dict())

    @app.get("/api/jobs/{job_id}")
    def api_get_job(request: Request, job_id: str):
        job = store.jobs.get(job_id)
        if not job:
            raise HTTPException(404, "未找到任务")
        return JSONResponse(job.to_dict())

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
        return RedirectResponse(_submission_notice_location(submission_id, "material_type_updated", focus="correction-audit"), status_code=303)

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
        return RedirectResponse(_submission_notice_location(submission_id, "material_assigned", focus="case-registry"), status_code=303)

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
        return RedirectResponse(_submission_notice_location(submission_id, "case_created", focus="case-registry"), status_code=303)

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
        return RedirectResponse(_submission_notice_location(submission_id, "cases_merged", focus="case-registry"), status_code=303)

    @app.post("/submissions/{submission_id}/actions/rerun-review")
    def rerun_review_page(request: Request, submission_id: str):
        case_id = request.form_data.get("case_id", "")
        note = request.form_data.get("note", "")
        corrected_by = request.form_data.get("corrected_by", "operator_ui")
        if not case_id:
            raise HTTPException(422, "缺少 case_id")
        try:
            rerun_case_review(case_id, corrected_by=corrected_by, note=note)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        log_event("rerun_case_review_html", {"submission_id": submission_id, "case_id": case_id, "by": corrected_by})
        return RedirectResponse(_submission_notice_location(submission_id, "case_review_rerun", focus="export-center"), status_code=303)

    @app.get("/downloads/reports/{report_id}")
    def download_report(request: Request, report_id: str):
        try:
            artifact = get_report_download(report_id)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc
        log_event("download_report", {"report_id": report_id})
        return _download_response(artifact["payload"], artifact["filename"], artifact["media_type"])

    @app.get("/downloads/materials/{material_id}/{artifact_kind}")
    def download_material_artifact(request: Request, material_id: str, artifact_kind: str):
        try:
            artifact = get_material_artifact(material_id, artifact_kind)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc
        log_event("download_material_artifact", {"material_id": material_id, "artifact_kind": artifact_kind})
        return _download_response(artifact["path"].read_bytes(), artifact["filename"], artifact["media_type"])

    @app.get("/downloads/submissions/{submission_id}/bundle")
    def download_submission_bundle(request: Request, submission_id: str):
        try:
            artifact = build_submission_export_bundle(submission_id)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc
        log_event("download_submission_bundle", {"submission_id": submission_id})
        return _download_response(artifact["payload"], artifact["filename"], artifact["media_type"])

    @app.get("/downloads/logs/app")
    def download_app_log(request: Request):
        log_text = read_log_text().encode("utf-8")
        log_event("download_app_log", {})
        return _download_response(log_text, "app.jsonl", "application/jsonl; charset=utf-8")

    @app.get("/downloads/ops/provider-probe/latest")
    def download_latest_provider_probe_artifact(request: Request):
        config = load_app_config()
        try:
            artifact = get_provider_probe_artifact_download(config_or_root=config)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc
        log_event("download_provider_probe_latest", {"filename": artifact["filename"]})
        return _download_response(artifact["path"].read_bytes(), artifact["filename"], artifact["media_type"])

    @app.get("/downloads/ops/provider-probe/history/{file_name}")
    def download_provider_probe_history_artifact(request: Request, file_name: str):
        config = load_app_config()
        try:
            artifact = get_provider_probe_artifact_download(config_or_root=config, file_name=file_name)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc
        log_event("download_provider_probe_history", {"filename": artifact["filename"]})
        return _download_response(artifact["path"].read_bytes(), artifact["filename"], artifact["media_type"])

    @app.get("/submissions/{submission_id}")
    def submission_detail(request: Request, submission_id: str):
        submission = store.submissions.get(submission_id)
        if not submission:
            raise HTTPException(404, "未找到批次")
        materials = [store.materials[item_id].to_dict() for item_id in submission.material_ids if item_id in store.materials]
        cases = [store.cases[item_id].to_dict() for item_id in submission.case_ids if item_id in store.cases]
        reports = [store.report_artifacts[item_id].to_dict() for item_id in submission.report_ids if item_id in store.report_artifacts]
        parse_results = [store.parse_results[item_id].to_dict() for item_id in submission.material_ids if item_id in store.parse_results]
        notice = _submission_notice_payload(request.query_params.get("notice", ""))
        return HTMLResponse(render_submission_detail(submission.to_dict(), materials, cases, reports, parse_results, notice=notice))

    @app.get("/cases/{case_id}")
    def case_detail(request: Request, case_id: str):
        case = store.cases.get(case_id)
        if not case:
            raise HTTPException(404, "未找到项目")
        materials = [store.materials[item_id].to_dict() for item_id in case.material_ids if item_id in store.materials]
        report = store.report_artifacts.get(case.report_id)
        review_result = store.review_results.get(case.review_result_id)
        return HTMLResponse(
            render_case_detail(
                case.to_dict(),
                materials,
                report.to_dict() if report else None,
                review_result.to_dict() if review_result else None,
            )
        )

    @app.get("/reports/{report_id}")
    def report_page(request: Request, report_id: str):
        report = store.report_artifacts.get(report_id)
        if not report:
            raise HTTPException(404, "未找到报告")
        return HTMLResponse(render_report_page(report.to_dict()))

    return app


def main():
    app = create_app()
    config = load_app_config()
    host = config.host
    port = config.port
    with make_server(host, port, app) as server:
        print(f"软著分析平台运行中: http://{host}:{port}")
        server.serve_forever()


if __name__ == "__main__":
    main()
