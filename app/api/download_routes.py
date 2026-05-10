from __future__ import annotations

from typing import Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response

from app.core.services.app_config import load_app_config
from app.core.services.app_logging import log_event, read_log_tail
from app.core.services.delivery_closeout import get_delivery_closeout_artifact_download
from app.core.services.exports import (
    build_submission_export_bundle,
    get_material_artifact,
    get_report_download,
    get_report_json_download,
)
from app.core.services.provider_probe import get_provider_probe_artifact_download


DownloadResponseFactory = Callable[[bytes, str, str], Response]


def register_download_routes(app: FastAPI, download_response: DownloadResponseFactory) -> None:
    @app.get("/downloads/reports/{report_id}")
    def download_report(request: Request, report_id: str):
        del request
        try:
            artifact = get_report_download(report_id)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc
        log_event("download_report", {"report_id": report_id})
        return download_response(artifact["payload"], artifact["filename"], artifact["media_type"])

    @app.get("/downloads/reports/{report_id}/json")
    def download_report_json(request: Request, report_id: str):
        del request
        try:
            artifact = get_report_json_download(report_id)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc
        log_event("download_report_json", {"report_id": report_id})
        return download_response(artifact["payload"], artifact["filename"], artifact["media_type"])

    @app.get("/downloads/materials/{material_id}/{artifact_kind}")
    def download_material_artifact(request: Request, material_id: str, artifact_kind: str):
        del request
        try:
            artifact = get_material_artifact(material_id, artifact_kind)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc
        log_event("download_material_artifact", {"material_id": material_id, "artifact_kind": artifact_kind})
        return download_response(artifact["path"].read_bytes(), artifact["filename"], artifact["media_type"])

    @app.get("/downloads/submissions/{submission_id}/bundle")
    def download_submission_bundle(request: Request, submission_id: str):
        del request
        try:
            artifact = build_submission_export_bundle(submission_id)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc
        log_event("download_submission_bundle", {"submission_id": submission_id})
        return download_response(artifact["payload"], artifact["filename"], artifact["media_type"])

    @app.get("/downloads/logs/app")
    def download_app_log(request: Request):
        del request
        config = load_app_config()
        log_text = read_log_tail(max_bytes=config.max_log_download_bytes).encode("utf-8")
        log_event("download_app_log", {"max_bytes": config.max_log_download_bytes})
        return download_response(log_text, "app.jsonl", "application/jsonl; charset=utf-8")

    @app.get("/downloads/ops/provider-probe/latest")
    def download_latest_provider_probe_artifact(request: Request):
        del request
        config = load_app_config()
        try:
            artifact = get_provider_probe_artifact_download(config_or_root=config)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc
        log_event("download_provider_probe_latest", {"filename": artifact["filename"]})
        return download_response(artifact["path"].read_bytes(), artifact["filename"], artifact["media_type"])

    @app.get("/downloads/ops/provider-probe/history/{file_name}")
    def download_provider_probe_history_artifact(request: Request, file_name: str):
        del request
        config = load_app_config()
        try:
            artifact = get_provider_probe_artifact_download(config_or_root=config, file_name=file_name)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc
        log_event("download_provider_probe_history", {"filename": artifact["filename"]})
        return download_response(artifact["path"].read_bytes(), artifact["filename"], artifact["media_type"])

    @app.get("/downloads/ops/delivery-closeout/latest-json")
    def download_latest_delivery_closeout_json(request: Request):
        del request
        try:
            artifact = get_delivery_closeout_artifact_download(file_name="delivery-closeout-latest.json")
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(404, str(exc)) from exc
        log_event("download_delivery_closeout_latest_json", {"filename": artifact["filename"]})
        return download_response(artifact["payload"], artifact["filename"], artifact["media_type"])

    @app.get("/downloads/ops/delivery-closeout/latest-md")
    def download_latest_delivery_closeout_markdown(request: Request):
        del request
        try:
            artifact = get_delivery_closeout_artifact_download(file_name="delivery-closeout-latest.md")
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(404, str(exc)) from exc
        log_event("download_delivery_closeout_latest_md", {"filename": artifact["filename"]})
        return download_response(artifact["payload"], artifact["filename"], artifact["media_type"])
