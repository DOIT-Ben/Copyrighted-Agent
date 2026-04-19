from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from app.core.services.app_config import AppConfig, load_app_config
from app.core.utils.text import ensure_dir, now_iso


BACKUP_FORMAT_VERSION = "soft_review.runtime_backup.v1"
DEFAULT_BACKUP_DIR = Path("data") / "backups"


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _sqlite_snapshot(source_path: Path, snapshot_path: Path) -> str:
    try:
        source_connection = sqlite3.connect(source_path)
        target_connection = sqlite3.connect(snapshot_path)
        try:
            source_connection.backup(target_connection)
            target_connection.commit()
            return "sqlite_backup_api"
        finally:
            target_connection.close()
            source_connection.close()
    except sqlite3.DatabaseError:
        shutil.copy2(source_path, snapshot_path)
        return "file_copy"


def _archive_member_record(source_path: Path, archive_path: str, restore_relative_path: str, category: str) -> dict:
    return {
        "source_path": str(source_path),
        "archive_path": archive_path,
        "restore_relative_path": restore_relative_path,
        "category": category,
        "size_bytes": source_path.stat().st_size if source_path.exists() else 0,
        "mtime": datetime.fromtimestamp(source_path.stat().st_mtime).isoformat(timespec="seconds") if source_path.exists() else "",
    }


def _runtime_entries(config: AppConfig, *, output_path: Path, working_dir: Path) -> tuple[list[dict], dict]:
    data_root = Path(config.data_root)
    sqlite_path = Path(config.sqlite_path)
    entries: list[dict] = []
    sqlite_snapshot = {"included": False, "mode": "not_included", "archive_path": "", "restore_relative_path": ""}
    sqlite_snapshot_path: Path | None = None

    if sqlite_path.exists():
        sqlite_snapshot_path = working_dir / sqlite_path.name
        sqlite_snapshot_mode = _sqlite_snapshot(sqlite_path, sqlite_snapshot_path)
        if data_root.exists() and _is_within(sqlite_path, data_root):
            relative = sqlite_path.relative_to(data_root).as_posix()
            sqlite_snapshot = {
                "included": True,
                "mode": sqlite_snapshot_mode,
                "archive_path": f"runtime/{relative}",
                "restore_relative_path": relative,
            }
        else:
            sqlite_snapshot = {
                "included": True,
                "mode": sqlite_snapshot_mode,
                "archive_path": f"runtime/_external/sqlite/{sqlite_path.name}",
                "restore_relative_path": f"_external/sqlite/{sqlite_path.name}",
            }

    if data_root.exists():
        for file_path in sorted(data_root.rglob("*")):
            if not file_path.is_file():
                continue
            if file_path.resolve() == output_path.resolve():
                continue

            source_path = file_path
            relative = file_path.relative_to(data_root).as_posix()
            category = "runtime_file"
            if sqlite_snapshot["included"] and file_path.resolve() == sqlite_path.resolve() and sqlite_snapshot_path:
                source_path = sqlite_snapshot_path
                category = "sqlite_snapshot"
            entries.append(_archive_member_record(source_path, f"runtime/{relative}", relative, category))

    elif sqlite_snapshot["included"] and sqlite_snapshot_path:
        entries.append(
            _archive_member_record(
                sqlite_snapshot_path,
                sqlite_snapshot["archive_path"],
                sqlite_snapshot["restore_relative_path"],
                "sqlite_snapshot",
            )
        )

    if sqlite_snapshot["included"] and sqlite_snapshot["restore_relative_path"] not in {item["restore_relative_path"] for item in entries}:
        entries.append(
            _archive_member_record(
                sqlite_snapshot_path,
                sqlite_snapshot["archive_path"],
                sqlite_snapshot["restore_relative_path"],
                "sqlite_snapshot",
            )
        )

    return entries, sqlite_snapshot


def create_runtime_backup(config: AppConfig | None = None, *, output_path: str | Path | None = None) -> dict:
    settings = config or load_app_config()
    created_at = now_iso()
    target = Path(output_path) if output_path else DEFAULT_BACKUP_DIR / f"runtime_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    ensure_dir(target.parent)

    with tempfile.TemporaryDirectory(prefix="runtime_backup_") as working_dir_text:
        working_dir = Path(working_dir_text)
        entries, sqlite_snapshot = _runtime_entries(settings, output_path=target, working_dir=working_dir)
        manifest = {
            "format_version": BACKUP_FORMAT_VERSION,
            "created_at": created_at,
            "data_root": settings.data_root,
            "sqlite_path": settings.sqlite_path,
            "log_path": settings.log_path,
            "retention_days": settings.retention_days,
            "sqlite_snapshot": sqlite_snapshot,
            "entries": [
                {
                    "archive_path": item["archive_path"],
                    "restore_relative_path": item["restore_relative_path"],
                    "category": item["category"],
                    "size_bytes": item["size_bytes"],
                    "mtime": item["mtime"],
                }
                for item in entries
            ],
        }

        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            for item in entries:
                archive.write(item["source_path"], arcname=item["archive_path"])

    return {
        "archive_path": str(target),
        "created_at": created_at,
        "file_count": len(entries),
        "size_bytes": target.stat().st_size if target.exists() else 0,
        "manifest": manifest,
    }


def inspect_runtime_backup(archive_path: str | Path) -> dict:
    target = Path(archive_path)
    with zipfile.ZipFile(target, "r") as archive:
        return json.loads(archive.read("manifest.json").decode("utf-8"))


def build_runtime_restore_plan(archive_path: str | Path, *, target_root: str | Path) -> dict:
    archive_target = Path(archive_path)
    restore_root = Path(target_root)
    manifest = inspect_runtime_backup(archive_target)

    with zipfile.ZipFile(archive_target, "r") as archive:
        names = set(archive.namelist())

    entries = []
    for item in manifest.get("entries", []):
        archive_name = str(item["archive_path"])
        if archive_name not in names:
            raise ValueError(f"backup archive is missing member: {archive_name}")
        restore_relative_path = Path(item["restore_relative_path"])
        target_path = restore_root / restore_relative_path
        entries.append(
            {
                "archive_path": archive_name,
                "restore_relative_path": str(restore_relative_path),
                "target_path": str(target_path),
                "category": item.get("category", "runtime_file"),
                "size_bytes": int(item.get("size_bytes", 0)),
                "will_overwrite": target_path.exists(),
            }
        )

    return {
        "archive_path": str(archive_target),
        "target_root": str(restore_root),
        "format_version": manifest.get("format_version", ""),
        "created_at": manifest.get("created_at", ""),
        "entries": entries,
        "summary": {
            "entry_count": len(entries),
            "overwrite_count": sum(1 for item in entries if item["will_overwrite"]),
        },
    }


def execute_runtime_restore(plan: dict, *, apply: bool = False, overwrite: bool = False) -> dict:
    archive_target = Path(plan["archive_path"])
    target_root = Path(plan["target_root"])
    results: list[dict] = []

    with zipfile.ZipFile(archive_target, "r") as archive:
        for item in plan.get("entries", []):
            target_path = Path(item["target_path"])
            if not _is_within(target_path, target_root):
                raise ValueError(f"restore target is outside target root: {target_path}")

            result = dict(item)
            if not apply:
                result["status"] = "planned"
                results.append(result)
                continue

            if target_path.exists() and not overwrite:
                result["status"] = "skipped_existing"
                results.append(result)
                continue

            ensure_dir(target_path.parent)
            with archive.open(item["archive_path"], "r") as source, target_path.open("wb") as target_file:
                shutil.copyfileobj(source, target_file)
            result["status"] = "restored"
            results.append(result)

    return {
        "generated_at": now_iso(),
        "apply": apply,
        "overwrite": overwrite,
        "results": results,
        "summary": {
            "planned_count": sum(1 for item in results if item["status"] == "planned"),
            "restored_count": sum(1 for item in results if item["status"] == "restored"),
            "skipped_existing_count": sum(1 for item in results if item["status"] == "skipped_existing"),
        },
    }


def _render_create_text(result: dict) -> str:
    return (
        f"runtime_backup created_at={result['created_at']} "
        f"archive_path={result['archive_path']} "
        f"file_count={result['file_count']} "
        f"size_bytes={result['size_bytes']}"
    )


def _render_inspect_text(manifest: dict) -> str:
    return (
        f"runtime_backup format_version={manifest.get('format_version', '')} "
        f"created_at={manifest.get('created_at', '')} "
        f"entry_count={len(manifest.get('entries', []))} "
        f"sqlite_snapshot_mode={manifest.get('sqlite_snapshot', {}).get('mode', '')}"
    )


def _render_restore_text(plan: dict, execution: dict) -> str:
    lines = [
        f"runtime_restore archive_path={plan['archive_path']}",
        f"target_root={plan['target_root']}",
        f"entry_count={plan['summary']['entry_count']}",
        f"overwrite_count={plan['summary']['overwrite_count']}",
    ]
    preview = execution["results"][:10]
    for item in preview:
        lines.append(f"- [{item['status']}] {item['restore_relative_path']} -> {item['target_path']}")
    remaining = len(execution["results"]) - len(preview)
    if remaining > 0:
        lines.append(f"... {remaining} more entries omitted")
    return "\n".join(lines)


def _emit_text(text: str) -> None:
    payload = text if text.endswith("\n") else f"{text}\n"
    sys.stdout.buffer.write(payload.encode("utf-8", errors="ignore"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Create, inspect, or restore runtime backups.")
    subparsers = parser.add_subparsers(dest="command")

    create_parser = subparsers.add_parser("create", help="Create a runtime backup archive.")
    create_parser.add_argument("--output", default="", help="Optional output zip path.")
    create_parser.add_argument("--json", action="store_true", help="Print JSON payload.")

    inspect_parser = subparsers.add_parser("inspect", help="Inspect a runtime backup archive.")
    inspect_parser.add_argument("--archive", required=True, help="Backup archive path.")
    inspect_parser.add_argument("--json", action="store_true", help="Print JSON payload.")

    restore_parser = subparsers.add_parser("restore", help="Restore a runtime backup into a target directory.")
    restore_parser.add_argument("--archive", required=True, help="Backup archive path.")
    restore_parser.add_argument("--target", required=True, help="Restore target root.")
    restore_parser.add_argument("--apply", action="store_true", help="Execute restore. Default is dry-run.")
    restore_parser.add_argument("--overwrite", action="store_true", help="Overwrite existing files during restore.")
    restore_parser.add_argument("--json", action="store_true", help="Print JSON payload.")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    if args.command == "create":
        result = create_runtime_backup(output_path=args.output or None)
        if args.json:
            _emit_text(json.dumps(result, ensure_ascii=False, indent=2))
            return
        _emit_text(_render_create_text(result))
        return

    if args.command == "inspect":
        manifest = inspect_runtime_backup(args.archive)
        if args.json:
            _emit_text(json.dumps(manifest, ensure_ascii=False, indent=2))
            return
        _emit_text(_render_inspect_text(manifest))
        return

    if args.command == "restore":
        plan = build_runtime_restore_plan(args.archive, target_root=args.target)
        execution = execute_runtime_restore(plan, apply=args.apply, overwrite=args.overwrite)
        payload = {"plan": plan, "execution": execution}
        if args.json:
            _emit_text(json.dumps(payload, ensure_ascii=False, indent=2))
            return
        _emit_text(_render_restore_text(plan, execution))


if __name__ == "__main__":
    main()
