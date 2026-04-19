from __future__ import annotations

import argparse
import json

from app.core.services.app_config import load_app_config
from app.core.services.release_gate import evaluate_release_gate


def _render_text(result: dict) -> str:
    lines = [
        f"release_gate status={result.get('status', 'warning')}",
        f"mode={result.get('mode', 'unknown')}",
        f"summary={result.get('summary', '')}",
    ]
    if str(result.get("recommended_action", "")).strip():
        lines.append(f"recommended_action={result.get('recommended_action', '')}")
    for item in result.get("checks", []):
        value = f" value={item.get('value', '')}" if str(item.get("value", "")).strip() else ""
        lines.append(f"- [{item.get('status', 'warning')}] {item.get('name', '')}: {item.get('detail', '')}{value}")
    for command in result.get("commands", []):
        lines.append(f"* {command.get('label', 'Command')}: {command.get('command', '')}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the release gate for startup checks, provider smoke, and baseline health.")
    parser.add_argument("--config", default="", help="Optional config JSON path.")
    parser.add_argument("--json", action="store_true", help="Print JSON payload.")
    args = parser.parse_args()

    config = load_app_config(args.config or None)
    result = evaluate_release_gate(config)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(_render_text(result))


if __name__ == "__main__":
    main()
