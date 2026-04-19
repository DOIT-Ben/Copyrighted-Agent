from __future__ import annotations

import argparse
import json

from app.core.services.release_validation import (
    DEFAULT_MODE_A_SMOKE_PATH,
    DEFAULT_MODE_B_SMOKE_PATH,
    run_release_validation,
)


def _render_text(result: dict) -> str:
    lines = [
        f"release_validation status={result.get('status', 'blocked')}",
        f"summary={result.get('summary', '')}",
        f"provider_probe={result.get('provider_probe', {}).get('probe_status', 'skipped')}",
        f"release_gate={result.get('release_gate', {}).get('status', 'warning')}",
        f"mode_a_smoke={result.get('mode_a_smoke', {}).get('status', 'blocked')}",
        f"mode_b_smoke={result.get('mode_b_smoke', {}).get('status', 'blocked')}",
    ]
    if result.get("recommended_action"):
        lines.append(f"recommended_action={result.get('recommended_action', '')}")
    artifacts = dict(result.get("artifacts", {}) or {})
    for key in ("latest_markdown_path", "latest_json_path", "history_markdown_path", "history_json_path"):
        if artifacts.get(key):
            lines.append(f"{key}={artifacts[key]}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run end-to-end release validation for real-provider readiness and sample smokes.")
    parser.add_argument("--config", default="", help="Optional config JSON path.")
    parser.add_argument("--mode-a-path", default=str(DEFAULT_MODE_A_SMOKE_PATH), help="Mode A smoke ZIP path.")
    parser.add_argument("--mode-b-path", default=str(DEFAULT_MODE_B_SMOKE_PATH), help="Mode B smoke directory or ZIP path.")
    parser.add_argument("--docs-dir", default="docs\\dev", help="Directory for validation artifacts.")
    parser.add_argument("--skip-probe", action="store_true", help="Skip sending a live provider probe request.")
    parser.add_argument("--no-write-artifacts", action="store_true", help="Do not write markdown/json validation artifacts.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    args = parser.parse_args()

    result = run_release_validation(
        config_path=(args.config or None),
        mode_a_path=args.mode_a_path,
        mode_b_path=args.mode_b_path,
        dev_root=args.docs_dir,
        send_probe=not args.skip_probe,
        write_artifacts=not args.no_write_artifacts,
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(_render_text(result))


if __name__ == "__main__":
    main()

