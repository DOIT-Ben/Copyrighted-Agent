from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from tests.helpers.contracts import require_symbol


def _write_file(path: Path, content: str = "data") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _create_sqlite(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    try:
        connection.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, name TEXT)")
        connection.execute("INSERT INTO sample(name) VALUES ('runtime-backup')")
        connection.commit()
    finally:
        connection.close()
    return path


@pytest.mark.unit
@pytest.mark.contract
def test_runtime_backup_creates_archive_with_manifest_and_runtime_files(tmp_path):
    AppConfig = require_symbol("app.core.services.app_config", "AppConfig")
    create_runtime_backup = require_symbol("app.tools.runtime_backup", "create_runtime_backup")
    inspect_runtime_backup = require_symbol("app.tools.runtime_backup", "inspect_runtime_backup")

    runtime_root = tmp_path / "runtime"
    _write_file(runtime_root / "submissions" / "sub_1" / "submission.json", "{}")
    _write_file(runtime_root / "logs" / "app.jsonl", "{\"ok\": true}")
    _create_sqlite(runtime_root / "soft_review.db")

    archive_path = tmp_path / "backups" / "runtime_snapshot.zip"
    config = AppConfig(
        data_root=str(runtime_root),
        sqlite_path=str(runtime_root / "soft_review.db"),
        log_path=str(runtime_root / "logs" / "app.jsonl"),
    )

    backup = create_runtime_backup(config=config, output_path=archive_path)
    manifest = inspect_runtime_backup(archive_path)

    assert archive_path.exists()
    assert backup["file_count"] >= 3
    assert manifest["format_version"] == "soft_review.runtime_backup.v1"
    assert any(item["restore_relative_path"] == "submissions/sub_1/submission.json" for item in manifest["entries"])
    assert any(item["restore_relative_path"] == "soft_review.db" for item in manifest["entries"])


@pytest.mark.unit
@pytest.mark.contract
def test_runtime_backup_restore_can_rehydrate_snapshot_into_target_root(tmp_path):
    AppConfig = require_symbol("app.core.services.app_config", "AppConfig")
    create_runtime_backup = require_symbol("app.tools.runtime_backup", "create_runtime_backup")
    build_runtime_restore_plan = require_symbol("app.tools.runtime_backup", "build_runtime_restore_plan")
    execute_runtime_restore = require_symbol("app.tools.runtime_backup", "execute_runtime_restore")

    runtime_root = tmp_path / "runtime"
    _write_file(runtime_root / "submissions" / "sub_1" / "submission.json", "{\"id\": 1}")
    _write_file(runtime_root / "uploads" / "batch.zip", "zip-data")
    _write_file(runtime_root / "logs" / "app.jsonl", "{\"ok\": true}")
    _create_sqlite(runtime_root / "soft_review.db")

    archive_path = tmp_path / "backups" / "runtime_snapshot.zip"
    restored_root = tmp_path / "restored"
    config = AppConfig(
        data_root=str(runtime_root),
        sqlite_path=str(runtime_root / "soft_review.db"),
        log_path=str(runtime_root / "logs" / "app.jsonl"),
    )

    create_runtime_backup(config=config, output_path=archive_path)
    plan = build_runtime_restore_plan(archive_path=archive_path, target_root=restored_root)
    result = execute_runtime_restore(plan, apply=True, overwrite=False)

    assert result["summary"]["restored_count"] >= 4
    assert (restored_root / "submissions" / "sub_1" / "submission.json").exists()
    assert (restored_root / "uploads" / "batch.zip").exists()
    assert (restored_root / "soft_review.db").exists()
