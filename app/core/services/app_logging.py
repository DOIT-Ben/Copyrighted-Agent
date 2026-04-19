from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.services.app_config import AppConfig, load_app_config
from app.core.utils.text import ensure_dir, now_iso


LOG_PATH = Path("data") / "runtime" / "logs" / "app.jsonl"


def _log_path(config: AppConfig | None = None) -> Path:
    settings = config or load_app_config()
    target = Path(settings.log_path or LOG_PATH)
    ensure_dir(target.parent)
    return target


def log_event(event_type: str, payload: dict[str, Any] | None = None) -> Path:
    record = {
        "ts": now_iso(),
        "event_type": event_type,
        "payload": payload or {},
    }
    target = _log_path()
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return target


def read_log_text() -> str:
    target = _log_path()
    if not target.exists():
        return ""
    return target.read_text(encoding="utf-8")
