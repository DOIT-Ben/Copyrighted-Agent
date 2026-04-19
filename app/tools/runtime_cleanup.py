from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from app.core.services.app_config import AppConfig, load_app_config
from app.core.utils.text import now_iso


SQLITE_STRATEGY = "manual_backup_only"


def _resolve_now(now: datetime | None = None) -> datetime:
    return now or datetime.now()


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _path_size(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size

    total = 0
    for child in path.rglob("*"):
        if child.is_file():
            total += child.stat().st_size
    return total


def _age_days(path: Path, now: datetime) -> int:
    if not path.exists():
        return 0
    modified_at = datetime.fromtimestamp(path.stat().st_mtime)
    age = now - modified_at
    return max(int(age.total_seconds() // 86400), 0)


def _mtime_text(path: Path) -> str:
    if not path.exists():
        return ""
    return datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")


def _candidate_record(scope: str, path: Path, now: datetime) -> dict:
    return {
        "scope": scope,
        "kind": "directory" if path.is_dir() else "file",
        "path": str(path),
        "size_bytes": _path_size(path),
        "mtime": _mtime_text(path),
        "age_days": _age_days(path, now),
        "action": "delete",
    }


def _skip_record(scope: str, path: Path, reason: str, now: datetime) -> dict:
    return {
        "scope": scope,
        "kind": "directory" if path.is_dir() else "file",
        "path": str(path),
        "size_bytes": _path_size(path),
        "mtime": _mtime_text(path),
        "age_days": _age_days(path, now),
        "reason": reason,
    }


def _expired_children(root: Path, scope: str, *, cutoff: datetime, now: datetime) -> list[dict]:
    if not root.exists():
        return []

    candidates: list[dict] = []
    for child in sorted(root.iterdir(), key=lambda item: item.name):
        modified_at = datetime.fromtimestamp(child.stat().st_mtime)
        if modified_at <= cutoff:
            candidates.append(_candidate_record(scope, child, now))
    return candidates


def _scan_logs(log_dir: Path, active_log_path: Path, *, cutoff: datetime, now: datetime) -> tuple[list[dict], list[dict]]:
    if not log_dir.exists():
        return [], []

    candidates: list[dict] = []
    skipped: list[dict] = []
    for child in sorted(log_dir.iterdir(), key=lambda item: item.name):
        modified_at = datetime.fromtimestamp(child.stat().st_mtime)
        if modified_at > cutoff:
            continue
        if child.resolve() == active_log_path.resolve():
            skipped.append(_skip_record("logs", child, "active_log_file", now))
            continue
        candidates.append(_candidate_record("logs", child, now))
    return candidates, skipped


def _sqlite_record(sqlite_path: Path, now: datetime) -> dict:
    if not sqlite_path.exists():
        return {
            "path": str(sqlite_path),
            "exists": False,
            "action": "missing",
            "reason": "sqlite_not_found",
            "strategy": SQLITE_STRATEGY,
            "mtime": "",
            "age_days": 0,
            "size_bytes": 0,
            "recommended_backup_name": f"{sqlite_path.stem}.{now.strftime('%Y%m%d%H%M%S')}.bak{sqlite_path.suffix}",
        }
    return {
        "path": str(sqlite_path),
        "exists": True,
        "action": "skip_manual_backup",
        "reason": "sqlite_requires_manual_backup",
        "strategy": SQLITE_STRATEGY,
        "mtime": _mtime_text(sqlite_path),
        "age_days": _age_days(sqlite_path, now),
        "size_bytes": _path_size(sqlite_path),
        "recommended_backup_name": f"{sqlite_path.stem}.{now.strftime('%Y%m%d%H%M%S')}.bak{sqlite_path.suffix}",
    }


def build_runtime_cleanup_plan(
    config: AppConfig | None = None,
    *,
    now: datetime | None = None,
    retention_days: int | None = None,
) -> dict:
    settings = config or load_app_config()
    clock = _resolve_now(now)
    retention = retention_days if retention_days is not None else settings.retention_days
    cutoff = clock - timedelta(days=retention)

    data_root = Path(settings.data_root)
    submissions_dir = data_root / "submissions"
    uploads_dir = data_root / "uploads"
    log_path = Path(settings.log_path)
    log_dir = log_path.parent
    sqlite_path = Path(settings.sqlite_path)

    candidates = []
    candidates.extend(_expired_children(submissions_dir, "submissions", cutoff=cutoff, now=clock))
    candidates.extend(_expired_children(uploads_dir, "uploads", cutoff=cutoff, now=clock))

    log_candidates, log_skips = _scan_logs(log_dir, log_path, cutoff=cutoff, now=clock)
    candidates.extend(log_candidates)

    skipped = list(log_skips)
    sqlite = _sqlite_record(sqlite_path, clock)

    return {
        "generated_at": clock.isoformat(timespec="seconds"),
        "dry_run": True,
        "retention_days": retention,
        "cutoff_before": cutoff.isoformat(timespec="seconds"),
        "data_root": str(data_root),
        "targets": {
            "submissions_dir": str(submissions_dir),
            "uploads_dir": str(uploads_dir),
            "log_dir": str(log_dir),
            "active_log_path": str(log_path),
            "sqlite_path": str(sqlite_path),
        },
        "candidates": candidates,
        "skipped": skipped,
        "sqlite": sqlite,
        "summary": {
            "candidate_count": len(candidates),
            "candidate_bytes": sum(item["size_bytes"] for item in candidates),
            "skipped_count": len(skipped),
        },
    }


def _allowed_cleanup_roots(plan: dict) -> list[Path]:
    targets = plan.get("targets", {})
    roots = []
    for key in ("submissions_dir", "uploads_dir", "log_dir"):
        value = str(targets.get(key, "")).strip()
        if value:
            roots.append(Path(value))
    return roots


def _assert_cleanup_path_allowed(path: Path, allowed_roots: list[Path]) -> None:
    if not any(_is_within(path, root) for root in allowed_roots):
        raise ValueError(f"cleanup candidate is outside allowed cleanup roots: {path}")


def execute_runtime_cleanup(plan: dict, *, apply: bool = False) -> dict:
    allowed_roots = _allowed_cleanup_roots(plan)
    results: list[dict] = []

    for candidate in plan.get("candidates", []):
        path = Path(candidate["path"])
        _assert_cleanup_path_allowed(path, allowed_roots)

        result = dict(candidate)
        if not apply:
            result["status"] = "planned"
            results.append(result)
            continue

        if not path.exists():
            result["status"] = "missing"
            results.append(result)
            continue

        try:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            result["status"] = "deleted"
        except OSError as exc:
            result["status"] = "failed"
            result["error"] = str(exc)
        results.append(result)

    return {
        "generated_at": now_iso(),
        "apply": apply,
        "sqlite": plan.get("sqlite", {}),
        "skipped": plan.get("skipped", []),
        "results": results,
        "summary": {
            "planned_count": sum(1 for item in results if item["status"] == "planned"),
            "deleted_count": sum(1 for item in results if item["status"] == "deleted"),
            "missing_count": sum(1 for item in results if item["status"] == "missing"),
            "failed_count": sum(1 for item in results if item["status"] == "failed"),
        },
    }


def _render_text(plan: dict, execution: dict) -> str:
    lines = [
        f"runtime_cleanup dry_run={not execution['apply']} retention_days={plan['retention_days']}",
        f"cutoff_before={plan['cutoff_before']}",
        f"candidate_count={plan['summary']['candidate_count']} candidate_bytes={plan['summary']['candidate_bytes']}",
        f"skipped_count={plan['summary']['skipped_count']}",
        f"sqlite_action={plan['sqlite']['action']} sqlite_reason={plan['sqlite']['reason']}",
    ]
    if execution["results"]:
        lines.append("candidates:")
        for item in execution["results"]:
            lines.append(
                f"- [{item['status']}] {item['scope']} {item['kind']} {item['path']} "
                f"age_days={item['age_days']} size_bytes={item['size_bytes']}"
            )
    if execution["skipped"]:
        lines.append("skipped:")
        for item in execution["skipped"]:
            lines.append(f"- [{item['reason']}] {item['scope']} {item['path']}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect or clean expired runtime artifacts.")
    parser.add_argument("--apply", action="store_true", help="Delete expired runtime artifacts. Default is dry-run.")
    parser.add_argument("--retention-days", type=int, default=None, help="Override configured retention window in days.")
    parser.add_argument("--json", action="store_true", help="Print JSON payload instead of text summary.")
    args = parser.parse_args()

    plan = build_runtime_cleanup_plan(retention_days=args.retention_days)
    execution = execute_runtime_cleanup(plan, apply=args.apply)

    if args.json:
        print(json.dumps({"plan": plan, "execution": execution}, ensure_ascii=False, indent=2))
        return

    print(_render_text(plan, execution))


if __name__ == "__main__":
    main()
