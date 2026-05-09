from __future__ import annotations

import hmac
import re
import secrets
from pathlib import Path
from threading import Thread
from urllib.parse import quote, urlencode, urlsplit, urlunsplit
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIServer, make_server

from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from app.core.domain.enums import JobStatus
from app.core.domain.models import Job
from app.core.pipelines.submission_pipeline import ingest_submission
from app.core.services.app_config import load_app_config
from app.core.services.app_logging import log_event, read_log_text
from app.core.services.corrections import (
    assign_material_to_case,
    change_material_type,
    continue_case_review_from_desensitized,
    create_case_from_materials,
    merge_cases,
    rerun_case_review,
    reset_submission_review_dimension_rule,
    update_case_online_filing,
    update_submission_internal_state,
    update_submission_review_dimension_rule,
    upload_desensitized_package,
)
from app.core.services.delivery_closeout import get_delivery_closeout_artifact_download, latest_delivery_closeout_status
from app.core.services.exports import build_submission_export_bundle, get_material_artifact, get_report_download, get_report_json_download
from app.core.services.job_runtime import classify_job_failure, recover_interrupted_jobs, update_job_state
from app.core.services.provider_probe import (
    get_provider_probe_artifact_download,
    latest_failed_provider_probe_status,
    latest_successful_provider_probe_status,
    list_provider_probe_history,
)
from app.core.services.online_filing import parse_online_filing_form
from app.core.services.review_profile import _load_global_review_profile, list_review_rule_history, normalize_review_profile, parse_review_profile_form, save_global_review_profile
from app.core.services.review_rulebook import parse_dimension_rule_items_from_form
from app.core.services.release_gate import evaluate_release_gate
from app.core.services.runtime_store import store
from app.core.services.sqlite_repository import (
    list_correction_feedback,
    list_manual_review_queue,
    list_retryable_jobs,
    load_all_into_store,
    save_submission_graph,
)
from app.core.services.startup_checks import run_startup_self_check
from app.core.services.submission_insights import parse_diagnostic_snapshot, submission_quality_snapshot
from app.core.utils.text import ensure_dir, now_iso, slug_id
from app.web.page_submission import (
    render_submission_exports_page,
    render_submission_materials_page,
    render_submission_operator_page,
)
from app.web.page_review_rule import render_global_rule_detail_page, render_review_rule_detail_page
from app.web.pages import (
    render_app_script,
    render_case_detail,
    render_home_page,
    render_ops_page,
    render_report_page,
    render_stylesheet,
    render_submission_detail,
    render_submissions_index,
)


CSRF_FIELD_NAME = "csrf_token"
CSRF_HEADER_NAME = "x-csrf-token"
SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'"
    ),
    "Referrer-Policy": "same-origin",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}
POST_FORM_PATTERN = re.compile(
    r"(<form\b(?=[^>]*\bmethod=[\"']post[\"'])[^>]*>)(.*?</form>)",
    re.IGNORECASE | re.DOTALL,
)


def _request_header(request: Request, name: str) -> str:
    target = name.lower()
    for key, value in (request.headers or {}).items():
        if str(key).lower() == target:
            return str(value)
    return ""


def _csrf_token_input(token: str) -> str:
    return f'<input type="hidden" name="{CSRF_FIELD_NAME}" value="{quote(token, safe="")}">'


def _inject_csrf_tokens(html: str, token: str) -> str:
    if not token:
        return html

    def replace(match: re.Match[str]) -> str:
        opening_tag = match.group(1)
        form_body = match.group(2)
        if f'name="{CSRF_FIELD_NAME}"' in form_body or f"name='{CSRF_FIELD_NAME}'" in form_body:
            return match.group(0)
        return opening_tag + "\n        " + _csrf_token_input(token) + form_body

    return POST_FORM_PATTERN.sub(replace, html)


def _apply_security_headers(response: Response) -> Response:
    for key, value in SECURITY_HEADERS.items():
        response.headers.setdefault(key, value)
    return response


def _validate_csrf_request(request: Request) -> Response | None:
    if request.method != "POST" or not getattr(request.app, "csrf_enforced", True):
        return None
    if not _requires_csrf(request.path):
        return None
    expected = str(getattr(request.app, "csrf_token", "") or "")
    provided = str(request.form_data.get(CSRF_FIELD_NAME, "") or _request_header(request, CSRF_HEADER_NAME))
    if expected and hmac.compare_digest(provided, expected):
        return None
    return JSONResponse({"detail": "CSRF token missing or invalid"}, status_code=403)


def _requires_csrf(path: str) -> bool:
    return path == "/upload" or (
        path.startswith("/submissions/") and ("/actions/" in path or "/review-rules/" in path)
    )


def _harden_response(request: Request, response: Response) -> Response:
    token = str(getattr(request.app, "csrf_token", "") or "")
    media_type = str(getattr(response, "media_type", "") or "")
    if response.status_code == 200 and media_type.startswith("text/html"):
        html = response.body.decode("utf-8", errors="ignore")
        response.body = _inject_csrf_tokens(html, token).encode("utf-8")
    return _apply_security_headers(response)


def _save_uploaded_zip(upload: UploadFile) -> Path:
    uploads_dir = ensure_dir(Path(load_app_config().data_root) / "uploads")
    target = uploads_dir / f"{slug_id('upload')}_{upload.filename}"
    target.write_bytes(upload.content)
    return target


def _download_filename_fallback(filename: str) -> str:
    fallback = "".join(character if 32 <= ord(character) < 127 and character not in {'"', "\\"} else "_" for character in filename)
    fallback = fallback.strip(" .") or "download"
    return fallback


def _download_response(payload: bytes, filename: str, media_type: str) -> Response:
    fallback = _download_filename_fallback(filename)
    encoded = quote(filename, safe="")
    disposition = f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{encoded}"
    response = Response(payload, status_code=200, headers={"Content-Disposition": disposition})
    response.media_type = media_type
    return response


def _extract_review_profile(form_data, *, fallback: dict | None = None) -> dict:
    return normalize_review_profile(parse_review_profile_form(form_data, fallback=fallback))


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


def _start_async_submission_job(
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


def _retry_async_submission_job(job_id: str) -> tuple[Job, str]:
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
    return _start_async_submission_job(
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


def _build_ops_report(config) -> dict:
    startup_report = run_startup_self_check(config)
    startup_report["provider_probe_history"] = list_provider_probe_history(config, limit=8)
    startup_report["provider_probe_last_success"] = latest_successful_provider_probe_status(config)
    startup_report["provider_probe_last_failure"] = latest_failed_provider_probe_status(config)
    startup_report["release_gate"] = evaluate_release_gate(config, startup_report=startup_report)
    startup_report["delivery_closeout"] = latest_delivery_closeout_status()
    return startup_report


SUBMISSION_NOTICE_MAP = {
    "job_retried": {
        "title": "任务已重新发起",
        "message": "系统已经基于原始上传文件重新创建处理任务，可继续查看新的批次详情。",
        "tone": "success",
        "icon_name": "refresh",
        "meta": ["已生成新任务", "可继续跟踪处理链路"],
    },
    "internal_state_updated": {
        "title": "内部处理状态已更新",
        "message": "负责人、内部状态和下一步备注已经保存，批次页面已刷新。",
        "tone": "success",
        "icon_name": "wrench",
        "meta": ["内部状态已保存", "操作已留痕"],
    },
    "material_type_updated": {
        "title": "材料类型已更新",
        "message": "选中的材料类型已经完成修正，相关留痕已写入更正审计。",
        "tone": "success",
        "icon_name": "check",
        "meta": ["已记录留痕", "批次页面已刷新"],
    },
    "material_assigned": {
        "title": "材料已归入项目",
        "message": "选中的材料已移动到目标项目，项目分组结果已刷新。",
        "tone": "success",
        "icon_name": "merge",
        "meta": ["项目分组已更新", "人工操作已留痕"],
    },
    "case_created": {
        "title": "新项目已创建",
        "message": "系统已基于选中的材料创建新项目。",
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
        "message": "选中的项目已重新审查，新的报告和 AI 信号会同步显示。",
        "tone": "info",
        "icon_name": "refresh",
        "meta": ["审查结果已刷新", "导出中心可能更新"],
    },
    "case_review_continued": {
        "title": "脱敏后继续审查已启动",
        "message": "系统已基于脱敏产物继续完成项目审查，报告和结果已刷新。",
        "tone": "success",
        "icon_name": "check",
        "meta": ["脱敏流程已闭环", "可立即查看报告"],
    },
    "desensitized_package_uploaded": {
        "title": "脱敏包已导入",
        "message": "系统已接收你上传的脱敏包，当前批次可继续进入正式审查。",
        "tone": "success",
        "icon_name": "upload",
        "meta": ["脱敏文件已回传", "可进入下一步审查"],
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


def _safe_submission_return_target(value: str) -> str:
    target = str(value or "").strip()
    if not target:
        return ""
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc:
        return ""
    if parsed.path == "/submissions" or (parsed.path.startswith("/submissions/") and parsed.path.endswith("/exports")):
        suffix = f"?{parsed.query}" if parsed.query else ""
        fragment = f"#{parsed.fragment}" if parsed.fragment else ""
        return f"{parsed.path}{suffix}{fragment}"
    return ""


def _submission_context(submission_id: str) -> tuple[dict, list[dict], list[dict], list[dict], list[dict]]:
    submission = store.submissions.get(submission_id)
    if not submission:
        raise HTTPException(404, "未找到批次")
    materials = [store.materials[item_id].to_dict() for item_id in submission.material_ids if item_id in store.materials]
    cases = [store.cases[item_id].to_dict() for item_id in submission.case_ids if item_id in store.cases]
    reports = [store.report_artifacts[item_id].to_dict() for item_id in submission.report_ids if item_id in store.report_artifacts]
    parse_results = [store.parse_results[item_id].to_dict() for item_id in submission.material_ids if item_id in store.parse_results]
    return submission.to_dict(), materials, cases, reports, parse_results


def _submission_diagnostics_payload(submission_id: str) -> dict:
    submission = store.submissions.get(submission_id)
    if not submission:
        raise HTTPException(404, "未找到批次")
    diagnostics: list[dict] = []
    for material_id in submission.material_ids:
        material = store.materials.get(material_id)
        parse_result = store.parse_results.get(material_id)
        if not material:
            continue
        diagnostics.append(
            {
                "material_id": material.id,
                "original_filename": material.original_filename,
                "material_type": material.material_type,
                **parse_diagnostic_snapshot(material.to_dict(), parse_result.to_dict() if parse_result else {}),
            }
        )
    return {
        "submission_id": submission_id,
        "summary": submission_quality_snapshot(submission_id),
        "diagnostics": diagnostics,
    }


def create_app(testing: bool = False):
    startup_report = run_startup_self_check()
    if not testing:
        load_all_into_store()
        recovered_jobs = recover_interrupted_jobs()
        for item in recovered_jobs:
            if item.get("scope_id"):
                save_submission_graph(item["scope_id"])
        try:
            log_event(
                "startup_self_check",
                {
                    "status": startup_report.get("status", "unknown"),
                    "failed_checks": [item.get("name") for item in startup_report.get("checks", []) if item.get("status") == "failed"],
                    "recovered_jobs": recovered_jobs,
                },
            )
        except OSError:
            pass

    app = FastAPI(title="软著分析平台")
    app.csrf_token = secrets.token_urlsafe(32)
    app.csrf_enforced = not testing
    app.add_before_request_hook(_validate_csrf_request)
    app.add_after_response_hook(_harden_response)

    @app.get("/")
    def home(request: Request):
        del request
        return HTMLResponse(render_home_page())

    @app.get("/submissions")
    def submission_index(request: Request):
        return HTMLResponse(render_submissions_index(dict(request.query_params or {})))

    @app.get("/ops")
    def ops_page(request: Request):
        config = load_app_config()
        return HTMLResponse(render_ops_page(config.to_dict(), _build_ops_report(config), dict(request.query_params or {})))

    @app.get("/static/styles.css")
    def styles(request: Request):
        del request
        response = Response(render_stylesheet(), status_code=200, headers={"Cache-Control": "public, max-age=86400"})
        response.media_type = "text/css; charset=utf-8"
        return response

    @app.get("/static/app.js")
    def app_js(request: Request):
        del request
        response = Response(render_app_script(), status_code=200, headers={"Cache-Control": "public, max-age=86400"})
        response.media_type = "application/javascript; charset=utf-8"
        return response

    @app.post("/upload")
    def upload_page(request: Request):
        upload = request.files.get("file")
        mode = request.form_data.get("mode", "single_case_package")
        review_strategy = request.form_data.get("review_strategy", "auto_review")
        review_profile = _extract_review_profile(request.form_data)
        if not upload:
            raise HTTPException(400, "缺少 ZIP 文件")
        if not upload.filename.lower().endswith(".zip"):
            raise HTTPException(415, "仅支持 ZIP 文件")
        saved = _save_uploaded_zip(upload)
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
        upload = request.files.get("file")
        mode = request.form_data.get("mode", "")
        review_strategy = request.form_data.get("review_strategy", "auto_review")
        review_profile = _extract_review_profile(request.form_data)
        if not upload:
            raise HTTPException(400, "缺少文件")
        if not upload.filename.lower().endswith(".zip"):
            raise HTTPException(415, "仅支持 ZIP 文件")
        if not mode:
            raise HTTPException(422, "缺少导入模式")
        saved = _save_uploaded_zip(upload)
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
        upload = request.files.get("file")
        mode = request.form_data.get("mode", "")
        review_strategy = request.form_data.get("review_strategy", "auto_review")
        review_profile = _extract_review_profile(request.form_data)
        if not upload:
            raise HTTPException(400, "缺少文件")
        if not upload.filename.lower().endswith(".zip"):
            raise HTTPException(415, "仅支持 ZIP 文件")
        if not mode:
            raise HTTPException(422, "缺少导入模式")

        saved = _save_uploaded_zip(upload)
        job, submission_id = _start_async_submission_job(
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
        return JSONResponse(_submission_diagnostics_payload(submission_id))

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

    @app.post("/api/global-rules")
    def api_save_global_rules(request: Request):
        try:
            profile = parse_review_profile_form(request.form_data)
            save_global_review_profile(profile)
            log_event("global_review_profile_saved", {"preset_key": profile.get("preset_key"), "enabled_dimensions": profile.get("enabled_dimensions")})
            return JSONResponse({"success": True, "message": "规则配置已保存"})
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.post("/api/jobs/{job_id}/retry")
    def api_retry_job(request: Request, job_id: str):
        del request
        original_job = store.jobs.get(job_id)
        if not original_job:
            raise HTTPException(404, "任务不存在")
        try:
            retried_job, submission_id = _retry_async_submission_job(job_id)
        except ValueError as exc:
            error_code = str(exc)
            if error_code == "job_not_found":
                raise HTTPException(404, "任务不存在") from exc
            if error_code == "unsupported_job_type":
                raise HTTPException(400, "当前仅支持重试导入任务") from exc
            if error_code == "missing_source_file":
                raise HTTPException(409, "原始上传文件已不存在，无法重试") from exc
            if error_code == "missing_source_path":
                raise HTTPException(409, "任务缺少可重试的源文件路径") from exc
            if error_code == "missing_submission_mode":
                raise HTTPException(409, "任务缺少导入模式，无法重试") from exc
            raise HTTPException(409, "当前任务不可重试") from exc
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
        return_to = _safe_submission_return_target(request.form_data.get("return_to", ""))
        if not job_id:
            raise HTTPException(422, "缺少 job_id")
        original_job = store.jobs.get(job_id)
        if not original_job:
            raise HTTPException(404, "任务不存在")
        if str(getattr(original_job, "scope_id", "") or "") != submission_id:
            raise HTTPException(400, "任务与批次不匹配")
        try:
            retried_job, new_submission_id = _retry_async_submission_job(job_id)
        except ValueError as exc:
            error_code = str(exc)
            if error_code == "job_not_found":
                raise HTTPException(404, "任务不存在") from exc
            if error_code == "unsupported_job_type":
                raise HTTPException(400, "当前仅支持重试导入任务") from exc
            if error_code == "missing_source_file":
                raise HTTPException(409, "原始上传文件已不存在，无法重试") from exc
            if error_code == "missing_source_path":
                raise HTTPException(409, "任务缺少可重试的源文件路径") from exc
            if error_code == "missing_submission_mode":
                raise HTTPException(409, "任务缺少导入模式，无法重试") from exc
            raise HTTPException(409, "当前任务不可重试") from exc
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
        return RedirectResponse(_submission_notice_location(new_submission_id, "job_retried", focus="internal-workbench"), status_code=303)

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
        saved = _save_uploaded_zip(upload)
        try:
            result = upload_desensitized_package(submission_id, saved, corrected_by=corrected_by, note=note)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        return JSONResponse(result)

    @app.post("/submissions/{submission_id}/actions/update-internal-state")
    def update_internal_state_page(request: Request, submission_id: str):
        owner = request.form_data.get("internal_owner", "")
        internal_status = request.form_data.get("internal_status", "unassigned")
        next_step = request.form_data.get("internal_next_step", "")
        note = request.form_data.get("internal_note", "")
        updated_by = request.form_data.get("updated_by", "operator_ui")
        return_to = _safe_submission_return_target(request.form_data.get("return_to", ""))
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
            parsed = urlsplit(return_to)
            existing_query = parsed.query
            notice_param = urlencode({"notice": "internal_state_updated"})
            merged_query = f"{existing_query}&{notice_param}" if existing_query else notice_param
            return_with_notice = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, merged_query, parsed.fragment))
            return RedirectResponse(return_with_notice, status_code=303)
        return RedirectResponse(_submission_notice_location(submission_id, "internal_state_updated", focus="internal-workbench"), status_code=303)

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
        return RedirectResponse(_submission_notice_location(submission_id, "material_assigned", focus="correction-audit"), status_code=303)

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
        return RedirectResponse(_submission_notice_location(submission_id, "case_created", focus="correction-audit"), status_code=303)

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
        return RedirectResponse(_submission_notice_location(submission_id, "cases_merged", focus="correction-audit"), status_code=303)

    @app.post("/submissions/{submission_id}/actions/rerun-review")
    def rerun_review_page(request: Request, submission_id: str):
        case_id = request.form_data.get("case_id", "")
        note = request.form_data.get("note", "")
        corrected_by = request.form_data.get("corrected_by", "operator_ui")
        submission = store.submissions.get(submission_id)
        review_profile = _extract_review_profile(
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
        return RedirectResponse(_submission_notice_location(submission_id, "case_review_rerun", focus="export-center"), status_code=303)

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
        return RedirectResponse(_submission_notice_location(submission_id, "case_review_rerun", focus="operator-console"), status_code=303)

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
        return RedirectResponse(_submission_notice_location(submission_id, "case_review_continued", focus="export-center"), status_code=303)

    @app.post("/submissions/{submission_id}/actions/upload-desensitized-package")
    def upload_desensitized_package_page(request: Request, submission_id: str):
        upload = request.files.get("file")
        note = request.form_data.get("note", "")
        corrected_by = request.form_data.get("corrected_by", "operator_ui")
        if not upload:
            raise HTTPException(400, "缺少 ZIP 文件")
        if not upload.filename.lower().endswith(".zip"):
            raise HTTPException(415, "仅支持 ZIP 文件")
        saved = _save_uploaded_zip(upload)
        try:
            upload_desensitized_package(submission_id, saved, corrected_by=corrected_by, note=note)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        log_event("upload_desensitized_package_html", {"submission_id": submission_id, "filename": upload.filename, "by": corrected_by})
        return RedirectResponse(
            _submission_notice_location(submission_id, "desensitized_package_uploaded", focus="operator-console"),
            status_code=303,
        )

    @app.get("/downloads/reports/{report_id}")
    def download_report(request: Request, report_id: str):
        del request
        try:
            artifact = get_report_download(report_id)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc
        log_event("download_report", {"report_id": report_id})
        return _download_response(artifact["payload"], artifact["filename"], artifact["media_type"])

    @app.get("/downloads/reports/{report_id}/json")
    def download_report_json(request: Request, report_id: str):
        del request
        try:
            artifact = get_report_json_download(report_id)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc
        log_event("download_report_json", {"report_id": report_id})
        return _download_response(artifact["payload"], artifact["filename"], artifact["media_type"])

    @app.get("/downloads/materials/{material_id}/{artifact_kind}")
    def download_material_artifact(request: Request, material_id: str, artifact_kind: str):
        del request
        try:
            artifact = get_material_artifact(material_id, artifact_kind)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc
        log_event("download_material_artifact", {"material_id": material_id, "artifact_kind": artifact_kind})
        return _download_response(artifact["path"].read_bytes(), artifact["filename"], artifact["media_type"])

    @app.get("/downloads/submissions/{submission_id}/bundle")
    def download_submission_bundle(request: Request, submission_id: str):
        del request
        try:
            artifact = build_submission_export_bundle(submission_id)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc
        log_event("download_submission_bundle", {"submission_id": submission_id})
        return _download_response(artifact["payload"], artifact["filename"], artifact["media_type"])

    @app.get("/downloads/logs/app")
    def download_app_log(request: Request):
        del request
        log_text = read_log_text().encode("utf-8")
        log_event("download_app_log", {})
        return _download_response(log_text, "app.jsonl", "application/jsonl; charset=utf-8")

    @app.get("/downloads/ops/provider-probe/latest")
    def download_latest_provider_probe_artifact(request: Request):
        del request
        config = load_app_config()
        try:
            artifact = get_provider_probe_artifact_download(config_or_root=config)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc
        log_event("download_provider_probe_latest", {"filename": artifact["filename"]})
        return _download_response(artifact["path"].read_bytes(), artifact["filename"], artifact["media_type"])

    @app.get("/downloads/ops/provider-probe/history/{file_name}")
    def download_provider_probe_history_artifact(request: Request, file_name: str):
        del request
        config = load_app_config()
        try:
            artifact = get_provider_probe_artifact_download(config_or_root=config, file_name=file_name)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc
        log_event("download_provider_probe_history", {"filename": artifact["filename"]})
        return _download_response(artifact["path"].read_bytes(), artifact["filename"], artifact["media_type"])

    @app.get("/downloads/ops/delivery-closeout/latest-json")
    def download_latest_delivery_closeout_json(request: Request):
        del request
        try:
            artifact = get_delivery_closeout_artifact_download(file_name="delivery-closeout-latest.json")
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(404, str(exc)) from exc
        log_event("download_delivery_closeout_latest_json", {"filename": artifact["filename"]})
        return _download_response(artifact["payload"], artifact["filename"], artifact["media_type"])

    @app.get("/downloads/ops/delivery-closeout/latest-md")
    def download_latest_delivery_closeout_markdown(request: Request):
        del request
        try:
            artifact = get_delivery_closeout_artifact_download(file_name="delivery-closeout-latest.md")
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(404, str(exc)) from exc
        log_event("download_delivery_closeout_latest_md", {"filename": artifact["filename"]})
        return _download_response(artifact["payload"], artifact["filename"], artifact["media_type"])

    @app.get("/submissions/{submission_id}")
    def submission_detail(request: Request, submission_id: str):
        submission, materials, cases, reports, parse_results = _submission_context(submission_id)
        notice = _submission_notice_payload(request.query_params.get("notice", ""))
        return HTMLResponse(render_submission_detail(submission, materials, cases, reports, parse_results, notice=notice))

    @app.get("/submissions/{submission_id}/materials")
    def submission_materials_page(request: Request, submission_id: str):
        del request
        submission, materials, cases, reports, parse_results = _submission_context(submission_id)
        return HTMLResponse(render_submission_materials_page(submission, materials, cases, reports, parse_results))

    @app.get("/submissions/{submission_id}/operator")
    def submission_operator_page(request: Request, submission_id: str):
        del request
        submission, materials, cases, reports, parse_results = _submission_context(submission_id)
        return HTMLResponse(render_submission_operator_page(submission, materials, cases, reports, parse_results))

    @app.get("/submissions/{submission_id}/exports")
    def submission_exports_page(request: Request, submission_id: str):
        del request
        submission, materials, cases, reports, parse_results = _submission_context(submission_id)
        return HTMLResponse(render_submission_exports_page(submission, materials, cases, reports, parse_results))

    @app.get("/submissions/{submission_id}/review-rules/{dimension_key}")
    def submission_review_rule_page(request: Request, submission_id: str, dimension_key: str):
        selected_case_id = str(request.query_params.get("case_id", "") or "").strip()
        submission, materials, cases, reports, parse_results = _submission_context(submission_id)
        del materials, reports, parse_results
        try:
            return HTMLResponse(
                render_review_rule_detail_page(
                    submission,
                    cases,
                    dimension_key,
                    selected_case_id=selected_case_id,
                )
            )
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.post("/submissions/{submission_id}/review-rules/{dimension_key}")
    def submission_review_rule_save(request: Request, submission_id: str, dimension_key: str):
        action = str(request.form_data.get("action", "save") or "save").strip()
        case_id = str(request.form_data.get("case_id", "") or "").strip()
        note = str(request.form_data.get("note", "") or "").strip()
        corrected_by = str(request.form_data.get("corrected_by", "operator_ui") or "operator_ui").strip()
        try:
            if action == "restore_default":
                result = reset_submission_review_dimension_rule(
                    submission_id,
                    dimension_key,
                    corrected_by=corrected_by,
                    note=note,
                )
            else:
                result = update_submission_review_dimension_rule(
                    submission_id,
                    dimension_key,
                    title=str(request.form_data.get("title", "") or "").strip(),
                    objective=str(request.form_data.get("objective", "") or "").strip(),
                    checkpoints=str(request.form_data.get("checkpoints", "") or "").strip(),
                    evidence_targets=str(request.form_data.get("evidence_targets", "") or "").strip(),
                    common_failures=str(request.form_data.get("common_failures", "") or "").strip(),
                    operator_notes=str(request.form_data.get("operator_notes", "") or "").strip(),
                    llm_focus=str(request.form_data.get("llm_focus", "") or "").strip(),
                    rules=parse_dimension_rule_items_from_form(request.form_data, dimension_key),
                    corrected_by=corrected_by,
                    note=note,
                )
            if action == "save_and_rerun" and case_id:
                rerun_case_review(
                    case_id,
                    corrected_by=corrected_by,
                    note=note or f"rule_update:{dimension_key}",
                    review_profile=result["review_profile"],
                )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        log_event(
            "submission_review_rule_saved_html",
            {
                "submission_id": submission_id,
                "dimension_key": dimension_key,
                "action": action,
                "case_id": case_id,
                "by": corrected_by,
            },
        )
        if action == "save_and_rerun" and case_id:
            return RedirectResponse(_submission_notice_location(submission_id, "case_review_rerun", focus="review-profile"), status_code=303)
        return RedirectResponse(f"/submissions/{submission_id}/review-rules/{dimension_key}?case_id={quote(case_id)}", status_code=303)

    @app.get("/global-rules/{dimension_key}")
    def global_rule_detail(request: Request, dimension_key: str):
        del request
        return HTMLResponse(render_global_rule_detail_page(dimension_key))

    @app.post("/api/global-rules/{dimension_key}")
    def api_save_global_dimension_rule(request: Request, dimension_key: str):
        try:
            global_profile = _load_global_review_profile() or {}
            profile = normalize_review_profile(global_profile)
            rulebook = dimension_rulebook_from_profile(profile)
            if dimension_key not in rulebook:
                raise HTTPException(404, "维度不存在")

            rule_entry = dict(rulebook[dimension_key])
            rules = parse_dimension_rule_items_from_form(request.form_data, dimension_key)
            rule_entry["rules"] = rules

            profile["dimension_rulebook"] = {**profile.get("dimension_rulebook", {}), dimension_key: rule_entry}
            profile["rulebook_meta"] = _normalize_rulebook_meta(profile, preset_key=profile.get("preset_key", "balanced_default"))

            save_global_review_profile(profile)
            log_event("global_dimension_rule_saved", {"dimension_key": dimension_key})
            return JSONResponse({"success": True, "message": "规则已保存"})
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.get("/cases/{case_id}")
    def case_detail(request: Request, case_id: str):
        del request
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
        del request
        report = store.report_artifacts.get(report_id)
        if not report:
            raise HTTPException(404, "未找到报告")
        return HTMLResponse(render_report_page(report.to_dict()))

    return app


class _ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


def main():
    app = create_app()
    config = load_app_config()
    host = config.host
    port = config.port
    with make_server(host, port, app, server_class=_ThreadingWSGIServer) as server:
        print(f"软著分析平台运行中: http://{host}:{port}")
        server.serve_forever()


if __name__ == "__main__":
    main()
