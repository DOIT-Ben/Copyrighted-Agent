from __future__ import annotations

import argparse
import json

from app.core.services.app_config import load_app_config
from app.core.services.provider_probe import build_provider_probe_config, run_provider_probe


def _render_text(result: dict) -> str:
    readiness = result.get("readiness", {})
    probe = result.get("probe", {})
    lines = [
        f"provider_probe status={result.get('status', 'unknown')}",
        f"phase={result.get('phase', '')}",
        f"provider={readiness.get('provider', '')}",
        f"summary={result.get('summary', readiness.get('summary', ''))}",
        f"recommended_action={result.get('recommended_action', readiness.get('recommended_action', ''))}",
    ]
    for check in readiness.get("checks", []):
        value = f" value={check.get('value', '')}" if str(check.get("value", "")).strip() else ""
        lines.append(f"- [{check.get('status', 'unknown')}] {check.get('name', '')}: {check.get('detail', '')}{value}")
    if probe.get("attempted"):
        lines.append(
            f"probe status={probe.get('status', 'unknown')} "
            f"http_status={probe.get('http_status', 0)} "
            f"error_code={probe.get('error_code', '')}"
        )
    else:
        lines.append(f"probe status={probe.get('status', 'skipped')} detail={probe.get('detail', '')}")
    normalized = probe.get("normalized_response") or {}
    if normalized:
        lines.append(
            f"provider_status={normalized.get('provider_status', '')} "
            f"provider_request_id={normalized.get('provider_request_id', '')}"
        )
    request_summary = result.get("request_summary") or {}
    if request_summary:
        lines.append(
            "request_audit="
            f"llm_safe={request_summary.get('llm_safe', False)} "
            f"raw_user_material={request_summary.get('contains_raw_user_material', False)} "
            f"rule_issue_count={request_summary.get('rule_issue_count', 0)}"
        )
    if result.get("artifact_path"):
        lines.append(f"artifact_path={result.get('artifact_path', '')}")
    if result.get("history_artifact_path"):
        lines.append(f"history_artifact_path={result.get('history_artifact_path', '')}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate external_http provider readiness and optionally send a safe probe.")
    parser.add_argument("--config", default="", help="Optional config JSON path.")
    parser.add_argument("--provider", default="", help="Optional provider override.")
    parser.add_argument("--endpoint", default="", help="Optional endpoint override.")
    parser.add_argument("--model", default="", help="Optional model override.")
    parser.add_argument("--api-key-env", default="", help="Optional API key env override.")
    parser.add_argument("--timeout-seconds", type=int, default=0, help="Optional timeout override.")
    parser.add_argument("--probe", action="store_true", help="Send a safe llm_safe probe request.")
    parser.add_argument("--enable-ai", action="store_true", help="Force ai_enabled=true for readiness evaluation.")
    parser.add_argument("--disable-fallback", action="store_true", help="Force ai_fallback_to_mock=false.")
    parser.add_argument("--artifact-path", default="", help="Optional path to persist the latest provider probe summary.")
    parser.add_argument("--history-dir", default="", help="Optional directory to persist timestamped provider probe history artifacts.")
    parser.add_argument("--no-write-artifact", action="store_true", help="Do not persist the latest provider probe summary artifact.")
    parser.add_argument("--no-write-history-artifact", action="store_true", help="Do not persist timestamped provider probe history artifacts.")
    parser.add_argument("--json", action="store_true", help="Print JSON payload.")
    args = parser.parse_args()

    base_config = load_app_config(args.config or None)
    effective_config = build_provider_probe_config(
        base_config,
        ai_enabled=True if args.enable_ai else base_config.ai_enabled,
        ai_provider=(args.provider.strip().lower() or base_config.ai_provider),
        ai_endpoint=(args.endpoint.strip() or base_config.ai_endpoint),
        ai_model=(args.model.strip() or base_config.ai_model),
        ai_api_key_env=(args.api_key_env.strip() or base_config.ai_api_key_env),
        ai_timeout_seconds=(args.timeout_seconds or base_config.ai_timeout_seconds),
        ai_fallback_to_mock=False if args.disable_fallback else base_config.ai_fallback_to_mock,
    )

    result = run_provider_probe(
        effective_config,
        send_request=args.probe,
        persist_result=not args.no_write_artifact,
        persist_history=(args.probe and not args.no_write_history_artifact and not args.no_write_artifact),
        artifact_path=(args.artifact_path.strip() or None),
        history_dir=(args.history_dir.strip() or None),
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(_render_text(result))


if __name__ == "__main__":
    main()
