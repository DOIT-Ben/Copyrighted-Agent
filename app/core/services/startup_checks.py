from __future__ import annotations

from pathlib import Path

from app.core.services.app_config import AppConfig, load_app_config
from app.core.services.provider_probe import evaluate_provider_readiness, latest_provider_probe_status
from app.core.utils.text import ensure_dir


def _probe_directory(path: Path) -> tuple[str, str]:
    try:
        ensure_dir(path)
        probe = path / ".probe_write"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return "ok", "directory writable"
    except OSError as exc:
        return "failed", str(exc)


def _probe_file_parent(path: Path) -> tuple[str, str]:
    try:
        ensure_dir(path.parent)
        probe = path.parent / ".probe_write"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return "ok", "parent directory writable"
    except OSError as exc:
        return "failed", str(exc)


def _check_record(name: str, label: str, target: Path, status: str, detail: str) -> dict:
    return {
        "name": name,
        "label": label,
        "status": status,
        "path": str(target),
        "detail": detail,
    }


def run_startup_self_check(config: AppConfig | None = None) -> dict:
    settings = config or load_app_config()
    data_root = Path(settings.data_root)
    sqlite_path = Path(settings.sqlite_path)
    log_path = Path(settings.log_path)
    uploads_dir = data_root / "uploads"
    config_local_path = Path("config") / "local.json"
    config_template_path = Path("config") / "local.example.json"

    checks = []
    for name, label, target, probe in (
        ("data_root", "Data Root", data_root, _probe_directory),
        ("uploads_dir", "Uploads", uploads_dir, _probe_directory),
        ("sqlite_parent", "SQLite Parent", sqlite_path, _probe_file_parent),
        ("log_dir", "Log Parent", log_path, _probe_file_parent),
    ):
        status, detail = probe(target)
        checks.append(_check_record(name, label, target, status, detail))

    config_template_status = "ok" if config_template_path.exists() else "warning"
    config_template_detail = "config template found" if config_template_path.exists() else "config template missing"
    checks.append(_check_record("config_template", "Config Template", config_template_path, config_template_status, config_template_detail))

    if config_local_path.exists():
        local_config_status = "ok"
        local_config_detail = "local config found"
    elif settings.ai_provider == "mock" and not settings.ai_enabled:
        local_config_status = "ok"
        local_config_detail = "local config missing, but default mock configuration is active"
    else:
        local_config_status = "warning"
        local_config_detail = "local config missing; use env overrides or create config/local.json for repeatable provider smoke"
    checks.append(_check_record("config_local", "Local Config", config_local_path, local_config_status, local_config_detail))

    boundary_status = "ok" if settings.ai_require_desensitized else "warning"
    boundary_detail = (
        "non-mock providers require desensitized payload"
        if settings.ai_require_desensitized
        else "desensitized boundary is disabled"
    )
    checks.append(
        _check_record(
            "ai_boundary",
            "AI Boundary",
            Path(settings.ai_endpoint or "local_stub"),
            boundary_status,
            boundary_detail,
        )
    )

    provider_readiness = evaluate_provider_readiness(settings)
    provider_probe_status = latest_provider_probe_status(settings)
    checks.append(
        _check_record(
            "ai_provider_readiness",
            "Provider Readiness",
            Path(settings.ai_endpoint or "external_http"),
            provider_readiness["status"],
            provider_readiness["summary"],
        )
    )

    status = "ok"
    if any(item["status"] == "failed" for item in checks):
        status = "failed"
    elif any(item["status"] == "warning" for item in checks):
        status = "warning"

    return {
        "status": status,
        "checks": checks,
        "paths": {
            "data_root": str(data_root),
            "uploads_dir": str(uploads_dir),
            "sqlite_path": str(sqlite_path),
            "log_path": str(log_path),
            "config_local_path": str(config_local_path),
            "config_template_path": str(config_template_path),
        },
        "retention_days": settings.retention_days,
        "ai_provider": settings.ai_provider,
        "ai_enabled": settings.ai_enabled,
        "local_config": {
            "status": local_config_status,
            "exists": config_local_path.exists(),
            "detail": local_config_detail,
            "path": str(config_local_path),
        },
        "provider_readiness": provider_readiness,
        "provider_probe_status": provider_probe_status,
    }
