from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.core.utils.text import now_iso
from app.tools.input_runner import collect_metrics_bundle


NUMERIC_METRIC_KEYS = ("materials", "cases", "reports", "unknown", "needs_review", "low_quality", "redactions")
DEFAULT_TARGETS = [
    {"label": "mode_a_real", "mode": "single_case_package", "path": "input\\软著材料"},
    {"label": "mode_b_real", "mode": "batch_same_material", "path": "input\\合作协议"},
]


def parse_target_spec(spec: str) -> dict:
    parts = [item.strip() for item in str(spec or "").split("|", 2)]
    if len(parts) != 3 or not all(parts):
        raise ValueError("target spec must use format label|mode|path")
    return {"label": parts[0], "mode": parts[1], "path": parts[2]}


def load_snapshot_from_path(path: str | Path) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return payload.get("snapshot", payload)


def find_latest_baseline_json(search_root: str | Path, *, exclude_path: str | Path | None = None) -> Path | None:
    root = Path(search_root)
    if not root.exists():
        return None
    excluded = Path(exclude_path).resolve() if exclude_path else None
    candidates = []
    for path in root.rglob("*baseline*.json"):
        if not path.is_file():
            continue
        if excluded and path.resolve() == excluded:
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        snapshot = payload.get("snapshot", payload)
        if not isinstance(snapshot, dict) or "targets" not in snapshot:
            continue
        candidates.append(path)
    if not candidates:
        return None
    return max(candidates, key=lambda item: item.stat().st_mtime)


def build_archive_output_paths(archive_dir: str | Path, *, archive_stem: str, generated_at: str) -> dict[str, Path]:
    root = Path(archive_dir)
    timestamp = (
        str(generated_at or now_iso())
        .replace("-", "")
        .replace(":", "")
        .replace("T", "_")
        .replace(".", "")
    )
    if len(timestamp) > 15:
        timestamp = timestamp[:15]
    stem = f"{archive_stem}_{timestamp}"
    return {
        "json": root / f"{stem}.json",
        "markdown": root / f"{stem}.md",
    }


def build_baseline_snapshot(targets: list[dict] | None = None) -> dict:
    resolved_targets = targets or DEFAULT_TARGETS
    snapshots = []
    for target in resolved_targets:
        bundle = collect_metrics_bundle(Path(target["path"]), target["mode"])
        snapshots.append(
            {
                "label": target["label"],
                "mode": target["mode"],
                "path": target["path"],
                "entries": bundle["entries"],
                "aggregate": bundle["aggregate"],
            }
        )
    return {"generated_at": now_iso(), "targets": snapshots}


def compare_baseline_snapshots(current: dict, previous: dict | None) -> dict:
    previous_targets = {item["label"]: item for item in (previous or {}).get("targets", [])}
    comparisons = []
    for item in current.get("targets", []):
        previous_item = previous_targets.get(item["label"])
        delta = {}
        for key in NUMERIC_METRIC_KEYS:
            current_value = int(item.get("aggregate", {}).get(key, 0))
            if not previous_item:
                delta[key] = None
                continue
            delta[key] = current_value - int(previous_item.get("aggregate", {}).get(key, 0))
        comparisons.append({"label": item["label"], "has_previous": previous_item is not None, "delta": delta})
    return {"generated_at": now_iso(), "comparisons": comparisons}


def render_baseline_markdown(snapshot: dict, comparison: dict | None = None) -> str:
    comparison_map = {item["label"]: item for item in (comparison or {}).get("comparisons", [])}
    lines = ["# Real Sample Metrics Baseline", "", f"- generated_at: {snapshot.get('generated_at', '')}", ""]
    for item in snapshot.get("targets", []):
        lines.append(f"## {item['label']}")
        lines.append("")
        lines.append(f"- path: `{item['path']}`")
        lines.append(f"- mode: `{item['mode']}`")
        aggregate = item.get("aggregate", {})
        for key in NUMERIC_METRIC_KEYS:
            lines.append(f"- {key}: {aggregate.get(key, 0)}")
        comparison_item = comparison_map.get(item["label"])
        if comparison_item and comparison_item.get("has_previous"):
            lines.append("- delta:")
            for key in NUMERIC_METRIC_KEYS:
                delta_value = comparison_item["delta"].get(key)
                sign = "+" if isinstance(delta_value, int) and delta_value > 0 else ""
                lines.append(f"  - {key}: {sign}{delta_value}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _write_optional(path_value: str, payload: str) -> None:
    if not path_value:
        return
    target = Path(path_value)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(payload, encoding="utf-8")


def _write_path(target: Path, payload: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(payload, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture and compare real-sample metrics baselines.")
    parser.add_argument(
        "--target",
        action="append",
        default=[],
        help="Target spec in format label|mode|path. Can be provided multiple times.",
    )
    parser.add_argument("--compare", default="", help="Optional previous baseline JSON path.")
    parser.add_argument("--compare-latest-in-dir", default="", help="Automatically compare against the latest baseline JSON under this directory.")
    parser.add_argument("--json-path", default="", help="Optional path to write current snapshot JSON.")
    parser.add_argument("--markdown-path", default="", help="Optional path to write markdown summary.")
    parser.add_argument("--archive-dir", default="", help="Optional directory to also write timestamped archive copies.")
    parser.add_argument("--archive-stem", default="real-sample-baseline", help="Filename stem used with --archive-dir.")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout instead of markdown.")
    args = parser.parse_args()

    targets = [parse_target_spec(item) for item in args.target] if args.target else list(DEFAULT_TARGETS)
    snapshot = build_baseline_snapshot(targets)

    previous = None
    compare_path = args.compare
    if not compare_path and args.compare_latest_in_dir:
        latest_path = find_latest_baseline_json(args.compare_latest_in_dir, exclude_path=args.json_path or None)
        compare_path = str(latest_path) if latest_path else ""
    if compare_path:
        previous = load_snapshot_from_path(compare_path)
    comparison = compare_baseline_snapshots(snapshot, previous)

    json_payload = json.dumps({"snapshot": snapshot, "comparison": comparison}, ensure_ascii=False, indent=2)
    markdown_payload = render_baseline_markdown(snapshot, comparison)

    _write_optional(args.json_path, json_payload)
    _write_optional(args.markdown_path, markdown_payload)
    if args.archive_dir:
        archive_paths = build_archive_output_paths(args.archive_dir, archive_stem=args.archive_stem, generated_at=snapshot.get("generated_at", ""))
        _write_path(archive_paths["json"], json_payload)
        _write_path(archive_paths["markdown"], markdown_payload)

    if args.json:
        print(json_payload)
        return
    print(markdown_payload)


if __name__ == "__main__":
    main()
