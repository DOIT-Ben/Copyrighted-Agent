from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from fastapi import HTTPException, UploadFile
from fastapi.responses import Response

from app.core.services.app_config import load_app_config
from app.core.utils.text import ensure_dir, slug_id


def save_uploaded_zip(upload: UploadFile) -> Path:
    config = load_app_config()
    content = bytes(upload.content or b"")
    if config.max_upload_bytes > 0 and len(content) > config.max_upload_bytes:
        raise HTTPException(413, f"ZIP 文件超过上传限制：{config.max_upload_bytes} bytes")
    original_name = Path(str(upload.filename or "upload.zip")).name
    safe_name = _download_filename_fallback(original_name)
    if not safe_name.lower().endswith(".zip"):
        safe_name = f"{safe_name}.zip"
    uploads_dir = ensure_dir(Path(config.data_root) / "uploads")
    target = uploads_dir / f"{slug_id('upload')}_{safe_name}"
    target.write_bytes(content)
    return target


def _download_filename_fallback(filename: str) -> str:
    fallback = "".join(character if 32 <= ord(character) < 127 and character not in {'"', "\\"} else "_" for character in filename)
    fallback = fallback.strip(" .") or "download"
    return fallback


def download_response(payload: bytes, filename: str, media_type: str) -> Response:
    fallback = _download_filename_fallback(filename)
    encoded = quote(filename, safe="")
    disposition = f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{encoded}"
    response = Response(payload, status_code=200, headers={"Content-Disposition": disposition})
    response.media_type = media_type
    return response
