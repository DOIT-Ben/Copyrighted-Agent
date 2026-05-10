from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


DEFAULT_CONFIG_PATH = Path("config") / "local.json"


@dataclass(frozen=True)
class AppConfig:
    host: str = "127.0.0.1"
    port: int = 8000
    data_root: str = "data/runtime"
    sqlite_path: str = "data/runtime/soft_review.db"
    log_path: str = "data/runtime/logs/app.jsonl"
    retention_days: int = 14
    ai_enabled: bool = False
    ai_provider: str = "mock"
    ai_require_desensitized: bool = True
    ai_timeout_seconds: int = 30
    ai_endpoint: str = ""
    ai_model: str = ""
    ai_api_key_env: str = ""
    ai_fallback_to_mock: bool = True
    max_upload_bytes: int = 50 * 1024 * 1024
    max_zip_members: int = 300
    max_zip_member_bytes: int = 25 * 1024 * 1024
    max_zip_total_uncompressed_bytes: int = 200 * 1024 * 1024
    max_log_download_bytes: int = 2 * 1024 * 1024

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _bool_from_value(value: Any, default: bool) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _int_from_value(value: Any, default: int) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _read_file_payload(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        return {}
    return json.loads(config_path.read_text(encoding="utf-8"))


def load_app_config(config_path: str | Path | None = None) -> AppConfig:
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    file_payload = _read_file_payload(path)

    host = str(os.getenv("SOFT_REVIEW_HOST", file_payload.get("host", "127.0.0.1")) or "127.0.0.1")
    port = _int_from_value(os.getenv("SOFT_REVIEW_PORT", file_payload.get("port", 8000)), 8000)
    data_root = str(os.getenv("SOFT_REVIEW_DATA_ROOT", file_payload.get("data_root", "data/runtime")) or "data/runtime")
    sqlite_path = str(
        os.getenv("SOFT_REVIEW_SQLITE_PATH", file_payload.get("sqlite_path", "data/runtime/soft_review.db"))
        or "data/runtime/soft_review.db"
    )
    log_path = str(
        os.getenv("SOFT_REVIEW_LOG_PATH", file_payload.get("log_path", "data/runtime/logs/app.jsonl"))
        or "data/runtime/logs/app.jsonl"
    )
    retention_days = _int_from_value(os.getenv("SOFT_REVIEW_RETENTION_DAYS", file_payload.get("retention_days", 14)), 14)
    ai_enabled = _bool_from_value(os.getenv("SOFT_REVIEW_AI_ENABLED", file_payload.get("ai_enabled")), False)
    ai_provider = str(os.getenv("SOFT_REVIEW_AI_PROVIDER", file_payload.get("ai_provider", "mock")) or "mock").strip().lower()
    ai_require_desensitized = _bool_from_value(
        os.getenv("SOFT_REVIEW_AI_REQUIRE_DESENSITIZED", file_payload.get("ai_require_desensitized")),
        True,
    )
    ai_timeout_seconds = _int_from_value(
        os.getenv("SOFT_REVIEW_AI_TIMEOUT_SECONDS", file_payload.get("ai_timeout_seconds", 30)),
        30,
    )
    ai_endpoint = str(os.getenv("SOFT_REVIEW_AI_ENDPOINT", file_payload.get("ai_endpoint", "")) or "").strip()
    ai_model = str(os.getenv("SOFT_REVIEW_AI_MODEL", file_payload.get("ai_model", "")) or "").strip()
    ai_api_key_env = str(os.getenv("SOFT_REVIEW_AI_API_KEY_ENV", file_payload.get("ai_api_key_env", "")) or "").strip()
    ai_fallback_to_mock = _bool_from_value(
        os.getenv("SOFT_REVIEW_AI_FALLBACK_TO_MOCK", file_payload.get("ai_fallback_to_mock")),
        True,
    )
    max_upload_bytes = _int_from_value(
        os.getenv("SOFT_REVIEW_MAX_UPLOAD_BYTES", file_payload.get("max_upload_bytes", 50 * 1024 * 1024)),
        50 * 1024 * 1024,
    )
    max_zip_members = _int_from_value(
        os.getenv("SOFT_REVIEW_MAX_ZIP_MEMBERS", file_payload.get("max_zip_members", 300)),
        300,
    )
    max_zip_member_bytes = _int_from_value(
        os.getenv("SOFT_REVIEW_MAX_ZIP_MEMBER_BYTES", file_payload.get("max_zip_member_bytes", 25 * 1024 * 1024)),
        25 * 1024 * 1024,
    )
    max_zip_total_uncompressed_bytes = _int_from_value(
        os.getenv(
            "SOFT_REVIEW_MAX_ZIP_TOTAL_UNCOMPRESSED_BYTES",
            file_payload.get("max_zip_total_uncompressed_bytes", 200 * 1024 * 1024),
        ),
        200 * 1024 * 1024,
    )
    max_log_download_bytes = _int_from_value(
        os.getenv("SOFT_REVIEW_MAX_LOG_DOWNLOAD_BYTES", file_payload.get("max_log_download_bytes", 2 * 1024 * 1024)),
        2 * 1024 * 1024,
    )

    return AppConfig(
        host=host,
        port=port,
        data_root=data_root,
        sqlite_path=sqlite_path,
        log_path=log_path,
        retention_days=retention_days,
        ai_enabled=ai_enabled,
        ai_provider=ai_provider,
        ai_require_desensitized=ai_require_desensitized,
        ai_timeout_seconds=ai_timeout_seconds,
        ai_endpoint=ai_endpoint,
        ai_model=ai_model,
        ai_api_key_env=ai_api_key_env,
        ai_fallback_to_mock=ai_fallback_to_mock,
        max_upload_bytes=max_upload_bytes,
        max_zip_members=max_zip_members,
        max_zip_member_bytes=max_zip_member_bytes,
        max_zip_total_uncompressed_bytes=max_zip_total_uncompressed_bytes,
        max_log_download_bytes=max_log_download_bytes,
    )
