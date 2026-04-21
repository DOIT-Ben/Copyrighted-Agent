from __future__ import annotations

import argparse
import json

from app.core.services.delivery_closeout import run_delivery_closeout


def _render_text(result: dict) -> str:
    lines = [
        f"delivery_closeout status={result.get('status', 'blocked')}",
        f"milestone={result.get('milestone', 'blocked')}",
        f"summary={result.get('summary', '')}",
    ]
    for item in result.get("checks", []):
        lines.append(
            f"{item.get('name', 'check')}={item.get('status', 'warning')} value={item.get('value', '')} summary={item.get('summary', '')}"
        )
    for action in result.get("operator_actions", []):
        lines.append(f"action={action}")
    artifacts = dict(result.get("artifacts", {}) or {})
    for key in ("latest_markdown_path", "latest_json_path", "history_markdown_path", "history_json_path"):
        if artifacts.get(key):
            lines.append(f"{key}={artifacts[key]}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize business handoff readiness from release validation, baseline, backup, and checklist artifacts.")
    parser.add_argument("--config", default="", help="Optional config JSON path.")
    parser.add_argument("--docs-dir", default="docs\\dev", help="Directory containing closeout and validation artifacts.")
    parser.add_argument("--backups-dir", default="data\\backups", help="Directory containing runtime backup archives.")
    parser.add_argument("--no-write-artifacts", action="store_true", help="Do not write closeout markdown/json artifacts.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    args = parser.parse_args()

    result = run_delivery_closeout(
        config_path=(args.config or None),
        dev_root=args.docs_dir,
        backups_root=args.backups_dir,
        write_artifacts=not args.no_write_artifacts,
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(_render_text(result))


if __name__ == "__main__":
    main()
