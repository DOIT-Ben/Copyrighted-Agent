from __future__ import annotations

import os
import time
from datetime import datetime
from pathlib import Path

import pytest

from tests.helpers.contracts import require_symbol

REFERENCE_NOW = datetime(2026, 4, 19, 12, 0, 0)


def _write_file(path: Path, content: str = "data") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _mark_age(path: Path, days_old: int) -> None:
    timestamp = time.mktime(REFERENCE_NOW.timetuple()) - (days_old * 24 * 60 * 60)
    os.utime(path, (timestamp, timestamp))


@pytest.mark.unit
@pytest.mark.contract
def test_runtime_cleanup_plan_selects_only_expired_runtime_artifacts(tmp_path):
    AppConfig = require_symbol("app.core.services.app_config", "AppConfig")
    build_runtime_cleanup_plan = require_symbol("app.tools.runtime_cleanup", "build_runtime_cleanup_plan")

    runtime_root = tmp_path / "runtime"
    old_submission = _write_file(runtime_root / "submissions" / "sub_old" / "summary.json")
    new_submission = _write_file(runtime_root / "submissions" / "sub_new" / "summary.json")
    old_upload = _write_file(runtime_root / "uploads" / "old_package.zip")
    new_upload = _write_file(runtime_root / "uploads" / "fresh_package.zip")
    archived_log = _write_file(runtime_root / "logs" / "archived-2026-03-01.jsonl")
    active_log = _write_file(runtime_root / "logs" / "app.jsonl")
    sqlite_path = _write_file(runtime_root / "soft_review.db")

    for item in (old_submission.parent, old_submission, old_upload, archived_log, active_log, sqlite_path):
        _mark_age(item, 20)
    for item in (new_submission.parent, new_submission, new_upload):
        _mark_age(item, 2)

    config = AppConfig(
        data_root=str(runtime_root),
        sqlite_path=str(sqlite_path),
        log_path=str(active_log),
        retention_days=14,
    )

    plan = build_runtime_cleanup_plan(config=config, now=datetime(2026, 4, 19, 12, 0, 0))

    candidate_paths = {Path(item["path"]).name: item for item in plan["candidates"]}
    skipped_paths = {Path(item["path"]).name: item for item in plan["skipped"]}

    assert "sub_old" in candidate_paths
    assert "old_package.zip" in candidate_paths
    assert "archived-2026-03-01.jsonl" in candidate_paths
    assert "sub_new" not in candidate_paths
    assert "fresh_package.zip" not in candidate_paths
    assert skipped_paths["app.jsonl"]["reason"] == "active_log_file"
    assert plan["sqlite"]["action"] == "skip_manual_backup"
    assert plan["sqlite"]["reason"] == "sqlite_requires_manual_backup"
    assert plan["summary"]["candidate_count"] == 3


@pytest.mark.unit
@pytest.mark.contract
def test_runtime_cleanup_execute_apply_deletes_candidates_and_preserves_active_log(tmp_path):
    AppConfig = require_symbol("app.core.services.app_config", "AppConfig")
    build_runtime_cleanup_plan = require_symbol("app.tools.runtime_cleanup", "build_runtime_cleanup_plan")
    execute_runtime_cleanup = require_symbol("app.tools.runtime_cleanup", "execute_runtime_cleanup")

    runtime_root = tmp_path / "runtime"
    old_submission = _write_file(runtime_root / "submissions" / "sub_old" / "summary.json")
    old_upload = _write_file(runtime_root / "uploads" / "old_package.zip")
    archived_log = _write_file(runtime_root / "logs" / "archived-2026-03-01.jsonl")
    active_log = _write_file(runtime_root / "logs" / "app.jsonl")
    sqlite_path = _write_file(runtime_root / "soft_review.db")

    for item in (old_submission.parent, old_submission, old_upload, archived_log, active_log, sqlite_path):
        _mark_age(item, 20)

    config = AppConfig(
        data_root=str(runtime_root),
        sqlite_path=str(sqlite_path),
        log_path=str(active_log),
        retention_days=14,
    )
    plan = build_runtime_cleanup_plan(config=config, now=datetime(2026, 4, 19, 12, 0, 0))
    result = execute_runtime_cleanup(plan, apply=True)

    assert not old_submission.parent.exists()
    assert not old_upload.exists()
    assert not archived_log.exists()
    assert active_log.exists()
    assert sqlite_path.exists()
    assert result["summary"]["deleted_count"] == 3
    assert result["summary"]["failed_count"] == 0


@pytest.mark.unit
@pytest.mark.contract
def test_runtime_cleanup_rejects_candidate_outside_allowed_roots(tmp_path):
    AppConfig = require_symbol("app.core.services.app_config", "AppConfig")
    build_runtime_cleanup_plan = require_symbol("app.tools.runtime_cleanup", "build_runtime_cleanup_plan")
    execute_runtime_cleanup = require_symbol("app.tools.runtime_cleanup", "execute_runtime_cleanup")

    runtime_root = tmp_path / "runtime"
    old_upload = _write_file(runtime_root / "uploads" / "old_package.zip")
    active_log = _write_file(runtime_root / "logs" / "app.jsonl")
    sqlite_path = _write_file(runtime_root / "soft_review.db")
    outside_file = _write_file(tmp_path / "outside.txt")

    for item in (old_upload, active_log, sqlite_path, outside_file):
        _mark_age(item, 20)

    config = AppConfig(
        data_root=str(runtime_root),
        sqlite_path=str(sqlite_path),
        log_path=str(active_log),
        retention_days=14,
    )
    plan = build_runtime_cleanup_plan(config=config, now=datetime(2026, 4, 19, 12, 0, 0))
    plan["candidates"].append(
        {
            "scope": "uploads",
            "kind": "file",
            "path": str(outside_file),
            "size_bytes": outside_file.stat().st_size,
            "mtime": datetime.fromtimestamp(outside_file.stat().st_mtime).isoformat(timespec="seconds"),
            "age_days": 20,
            "action": "delete",
        }
    )

    with pytest.raises(ValueError):
        execute_runtime_cleanup(plan, apply=True)
