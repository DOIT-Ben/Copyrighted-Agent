from __future__ import annotations

import json
import zipfile
from datetime import datetime
from pathlib import Path


NUMERIC_BASELINE_KEYS = ("materials", "cases", "reports", "unknown", "needs_review", "low_quality", "redactions")


def _iso_from_timestamp(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp).isoformat(timespec="seconds")


def format_size_label(size_bytes: int) -> str:
    value = float(max(size_bytes, 0))
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    while value >= 1024 and unit_index < len(units) - 1:
        value /= 1024
        unit_index += 1
    if unit_index == 0:
        return f"{int(value)} {units[unit_index]}"
    return f"{value:.1f} {units[unit_index]}"


def _empty_baseline_status(summary: str) -> dict:
    return {
        "status": "warning",
        "exists": False,
        "summary": summary,
        "file_name": "",
        "file_path": "",
        "generated_at": "",
        "updated_at": "",
        "target_count": 0,
        "totals": {key: 0 for key in NUMERIC_BASELINE_KEYS},
        "targets": [],
        "comparison_available": False,
        "delta_totals": {key: None for key in NUMERIC_BASELINE_KEYS},
    }


def _load_baseline_history_item(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    snapshot = payload.get("snapshot", payload)
    comparison = payload.get("comparison", {})
    comparison_map = {item["label"]: item for item in comparison.get("comparisons", [])}

    totals = {key: 0 for key in NUMERIC_BASELINE_KEYS}
    delta_totals: dict[str, int | None] = {key: None for key in NUMERIC_BASELINE_KEYS}
    targets = []
    for item in snapshot.get("targets", []):
        aggregate = item.get("aggregate", {})
        for key in NUMERIC_BASELINE_KEYS:
            totals[key] += int(aggregate.get(key, 0) or 0)
        comparison_item = comparison_map.get(item.get("label", "")) or {}
        deltas = comparison_item.get("delta", {}) if comparison_item.get("has_previous") else {}
        for key in NUMERIC_BASELINE_KEYS:
            delta_value = deltas.get(key)
            if isinstance(delta_value, int):
                delta_totals[key] = (delta_totals[key] or 0) + delta_value
        targets.append(
            {
                "label": item.get("label", ""),
                "mode": item.get("mode", ""),
                "path": item.get("path", ""),
                "aggregate": aggregate,
                "delta": deltas,
                "has_previous": bool(comparison_item.get("has_previous")),
            }
        )

    has_delta = any(isinstance(value, int) for value in delta_totals.values())
    status = "ok" if totals["needs_review"] == 0 and totals["low_quality"] == 0 else "warning"
    return {
        "status": status,
        "exists": True,
        "summary": "Metrics baseline artifact loaded successfully.",
        "file_name": path.name,
        "file_path": str(path),
        "generated_at": str(snapshot.get("generated_at", "")),
        "updated_at": _iso_from_timestamp(path.stat().st_mtime),
        "target_count": len(targets),
        "totals": totals,
        "targets": targets,
        "comparison_available": bool(comparison.get("comparisons")),
        "delta_totals": delta_totals if has_delta else {key: None for key in NUMERIC_BASELINE_KEYS},
    }


def format_signed_delta(value: int | None) -> str:
    if value is None:
        return "-"
    return f"+{value}" if value > 0 else str(value)


def list_metrics_baseline_history(dev_root: str | Path | None = None, *, limit: int = 5) -> list[dict]:
    root = Path(dev_root or (Path("docs") / "dev"))
    if not root.exists():
        return []

    candidates = sorted(
        (path for path in root.rglob("*baseline*.json") if path.is_file()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    history: list[dict] = []
    for path in candidates[: max(limit, 0)]:
        try:
            history.append(_load_baseline_history_item(path))
        except Exception:
            history.append(
                {
                    "status": "warning",
                    "exists": True,
                    "summary": "Metrics baseline artifact could not be parsed.",
                    "file_name": path.name,
                    "file_path": str(path),
                    "generated_at": "",
                    "updated_at": _iso_from_timestamp(path.stat().st_mtime),
                    "target_count": 0,
                    "totals": {key: 0 for key in NUMERIC_BASELINE_KEYS},
                    "targets": [],
                    "comparison_available": False,
                    "delta_totals": {key: None for key in NUMERIC_BASELINE_KEYS},
                }
            )
    return history


def latest_runtime_backup_status(backups_root: str | Path | None = None) -> dict:
    root = Path(backups_root or (Path("data") / "backups"))
    if not root.exists():
        return {
            "status": "warning",
            "exists": False,
            "summary": "No backup directory found yet.",
            "file_name": "",
            "file_path": "",
            "size_bytes": 0,
            "size_label": "0 B",
            "updated_at": "",
            "created_at": "",
            "entry_count": 0,
            "sqlite_snapshot_mode": "",
        }

    candidates = sorted((path for path in root.glob("*.zip") if path.is_file()), key=lambda path: path.stat().st_mtime, reverse=True)
    if not candidates:
        return {
            "status": "warning",
            "exists": False,
            "summary": "No runtime backup archive has been created yet.",
            "file_name": "",
            "file_path": "",
            "size_bytes": 0,
            "size_label": "0 B",
            "updated_at": "",
            "created_at": "",
            "entry_count": 0,
            "sqlite_snapshot_mode": "",
        }

    latest = candidates[0]
    summary = {
        "status": "ok",
        "exists": True,
        "summary": "Latest runtime backup is available.",
        "file_name": latest.name,
        "file_path": str(latest),
        "size_bytes": latest.stat().st_size,
        "size_label": format_size_label(latest.stat().st_size),
        "updated_at": _iso_from_timestamp(latest.stat().st_mtime),
        "created_at": "",
        "entry_count": 0,
        "sqlite_snapshot_mode": "",
    }
    try:
        with zipfile.ZipFile(latest, "r") as archive:
            manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
        summary["created_at"] = str(manifest.get("created_at", ""))
        summary["entry_count"] = len(manifest.get("entries", []))
        summary["sqlite_snapshot_mode"] = str(manifest.get("sqlite_snapshot", {}).get("mode", ""))
    except Exception as exc:
        summary["status"] = "warning"
        summary["summary"] = f"Backup exists but manifest inspection failed: {exc}"
    return summary


def latest_metrics_baseline_status(dev_root: str | Path | None = None) -> dict:
    root = Path(dev_root or (Path("docs") / "dev"))
    if not root.exists():
        return _empty_baseline_status("docs/dev does not exist yet.")

    history = list_metrics_baseline_history(root, limit=1)
    if not history:
        return _empty_baseline_status("No metrics baseline JSON has been generated yet.")

    latest = dict(history[0])
    latest["summary"] = "Latest metrics baseline is available."
    return latest
