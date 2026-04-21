from __future__ import annotations

import json
from pathlib import Path

from app.core.services.app_config import AppConfig, load_app_config
from app.core.services.ops_status import latest_metrics_baseline_status, latest_runtime_backup_status
from app.core.services.release_gate import evaluate_release_gate
from app.core.utils.text import ensure_dir, now_iso


DEFAULT_DEV_ROOT = Path("docs") / "dev"
DEFAULT_BACKUPS_ROOT = Path("data") / "backups"
LATEST_JSON_NAME = "delivery-closeout-latest.json"
LATEST_MARKDOWN_NAME = "delivery-closeout-latest.md"
HISTORY_STEM = "delivery_closeout"
REAL_PROVIDER_VALIDATION_LATEST = "real-provider-validation-latest.json"
REAL_PROVIDER_ACCEPTANCE_CHECKLIST = "106-real-provider-acceptance-checklist.md"

STATUS_ORDER = {"pass": 0, "warning": 1, "blocked": 2}


def _merge_status(current: str, candidate: str) -> str:
    return candidate if STATUS_ORDER.get(candidate, 0) > STATUS_ORDER.get(current, 0) else current


def _history_base_paths(dev_root: Path, generated_at: str) -> tuple[Path, Path]:
    history_root = ensure_dir(dev_root / "history")
    digits = "".join(character for character in str(generated_at) if character.isdigit())
    stamp = f"{digits[:8]}_{digits[8:14]}" if len(digits) >= 14 else (digits or "latest")
    return (
        history_root / f"{HISTORY_STEM}_{stamp}.json",
        history_root / f"{HISTORY_STEM}_{stamp}.md",
    )


def _load_latest_release_validation(dev_root: Path) -> dict:
    target = dev_root / REAL_PROVIDER_VALIDATION_LATEST
    if not target.exists():
        return {
            "exists": False,
            "status": "blocked",
            "summary": "No real-provider validation artifact is available yet.",
            "generated_at": "",
            "file_name": REAL_PROVIDER_VALIDATION_LATEST,
            "file_path": str(target),
            "provider_probe": "not_recorded",
            "mode_a_smoke": "not_recorded",
            "mode_b_smoke": "not_recorded",
            "recommended_action": "Run py -m app.tools.release_validation before business closeout.",
        }
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "exists": True,
            "status": "warning",
            "summary": f"Latest real-provider validation artifact could not be parsed: {exc}",
            "generated_at": "",
            "file_name": target.name,
            "file_path": str(target),
            "provider_probe": "unknown",
            "mode_a_smoke": "unknown",
            "mode_b_smoke": "unknown",
            "recommended_action": "Regenerate the real-provider validation artifact before handoff.",
        }
    return {
        "exists": True,
        "status": str(payload.get("status", "blocked") or "blocked"),
        "summary": str(payload.get("summary", "") or ""),
        "generated_at": str(payload.get("generated_at", "") or ""),
        "file_name": target.name,
        "file_path": str(target),
        "provider_probe": str((payload.get("provider_probe", {}) or {}).get("probe_status", "unknown") or "unknown"),
        "mode_a_smoke": str((payload.get("mode_a_smoke", {}) or {}).get("status", "unknown") or "unknown"),
        "mode_b_smoke": str((payload.get("mode_b_smoke", {}) or {}).get("status", "unknown") or "unknown"),
        "recommended_action": str(payload.get("recommended_action", "") or ""),
    }


def _acceptance_checklist_status(dev_root: Path) -> dict:
    target = dev_root / REAL_PROVIDER_ACCEPTANCE_CHECKLIST
    if target.exists():
        return {
            "exists": True,
            "status": "pass",
            "summary": "Acceptance checklist is available for operator and business handoff.",
            "file_name": target.name,
            "file_path": str(target),
            "recommended_action": "",
        }
    return {
        "exists": False,
        "status": "warning",
        "summary": "Acceptance checklist is missing from docs/dev.",
        "file_name": target.name,
        "file_path": str(target),
        "recommended_action": "Add or restore the acceptance checklist before final business handoff.",
    }


def _check(name: str, label: str, status: str, summary: str, *, value: str = "", recommended_action: str = "") -> dict:
    return {
        "name": name,
        "label": label,
        "status": status,
        "summary": summary,
        "value": value,
        "recommended_action": recommended_action,
    }


def _baseline_closeout_check(baseline_status: dict) -> dict:
    totals = dict(baseline_status.get("totals", {}) or {})
    needs_review = int(totals.get("needs_review", 0) or 0)
    low_quality = int(totals.get("low_quality", 0) or 0)
    unknown = int(totals.get("unknown", 0) or 0)

    if not baseline_status.get("exists", False):
        return _check(
            "real_sample_baseline",
            "Real Sample Baseline",
            "blocked",
            "No rolling baseline is available for business closeout.",
            value="not_generated",
            recommended_action="Run py -m app.tools.metrics_baseline before final closeout.",
        )
    if unknown > 0 or needs_review > 0 or low_quality > 0:
        return _check(
            "real_sample_baseline",
            "Real Sample Baseline",
            "warning",
            "The latest real-sample baseline still contains review debt.",
            value=f"unknown={unknown}, needs_review={needs_review}, low_quality={low_quality}",
            recommended_action="Reduce unknown / needs_review / low_quality debt, then rerun the baseline.",
        )
    return _check(
        "real_sample_baseline",
        "Real Sample Baseline",
        "pass",
        "The latest real-sample baseline is clean enough for handoff.",
        value=str(baseline_status.get("file_name", "") or "baseline"),
    )


def _backup_closeout_check(backup_status: dict) -> dict:
    if not backup_status.get("exists", False):
        return _check(
            "runtime_backup",
            "Runtime Backup",
            "warning",
            "No runtime backup archive is recorded for rollback.",
            value="not_recorded",
            recommended_action="Run py -m app.tools.runtime_backup create before business handoff.",
        )
    return _check(
        "runtime_backup",
        "Runtime Backup",
        "pass",
        "A runtime backup archive is available as a rollback point.",
        value=str(backup_status.get("file_name", "") or "backup"),
    )


def _operator_action_items(checks: list[dict]) -> list[str]:
    actions: list[str] = []
    for severity in ("blocked", "warning"):
        for item in checks:
            if item.get("status") != severity:
                continue
            action = str(item.get("recommended_action", "") or "").strip()
            if action and action not in actions:
                actions.append(action)
    return actions


def _render_markdown(payload: dict) -> str:
    lines = [
        "# Delivery Closeout",
        "",
        "## Summary",
        "",
        f"- generated_at: `{payload.get('generated_at', '')}`",
        f"- status: `{payload.get('status', 'blocked')}`",
        f"- milestone: `{payload.get('milestone', 'blocked')}`",
        f"- summary: {payload.get('summary', '')}",
        "",
        "## Checks",
        "",
    ]
    for item in payload.get("checks", []):
        lines.append(f"- {item.get('label', '')}: `{item.get('status', 'warning')}` | `{item.get('value', '')}` | {item.get('summary', '')}")
    lines.extend(["", "## Recommended Actions", ""])
    actions = list(payload.get("operator_actions", []) or [])
    if not actions:
        lines.append("- No follow-up action is required.")
    else:
        for action in actions:
            lines.append(f"- {action}")
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            f"- release_validation: `{payload.get('release_validation', {}).get('file_path', '')}`",
            f"- baseline: `{payload.get('baseline', {}).get('file_path', '')}`",
            f"- backup: `{payload.get('backup', {}).get('file_path', '')}`",
            f"- acceptance_checklist: `{payload.get('acceptance_checklist', {}).get('file_path', '')}`",
        ]
    )
    return "\n".join(lines) + "\n"


def write_delivery_closeout_artifacts(payload: dict, *, dev_root: str | Path | None = None) -> dict:
    root = ensure_dir(Path(dev_root or DEFAULT_DEV_ROOT))
    latest_json_path = root / LATEST_JSON_NAME
    latest_markdown_path = root / LATEST_MARKDOWN_NAME
    history_json_path, history_markdown_path = _history_base_paths(root, str(payload.get("generated_at", "") or now_iso()))

    artifact_paths = {
        "latest_json_path": str(latest_json_path),
        "latest_markdown_path": str(latest_markdown_path),
        "history_json_path": str(history_json_path),
        "history_markdown_path": str(history_markdown_path),
    }

    materialized = dict(payload)
    materialized["artifacts"] = artifact_paths

    latest_json_path.write_text(json.dumps(materialized, ensure_ascii=False, indent=2), encoding="utf-8")
    latest_markdown_path.write_text(_render_markdown(materialized), encoding="utf-8")
    history_json_path.write_text(json.dumps(materialized, ensure_ascii=False, indent=2), encoding="utf-8")
    history_markdown_path.write_text(_render_markdown(materialized), encoding="utf-8")

    return artifact_paths


def run_delivery_closeout(
    *,
    config: AppConfig | None = None,
    config_path: str | Path | None = None,
    dev_root: str | Path | None = None,
    backups_root: str | Path | None = None,
    write_artifacts: bool = True,
) -> dict:
    settings = config or load_app_config(config_path)
    generated_at = now_iso()
    docs_root = Path(dev_root or DEFAULT_DEV_ROOT)
    runtime_backups_root = Path(backups_root or DEFAULT_BACKUPS_ROOT)

    release_validation = _load_latest_release_validation(docs_root)
    release_gate = evaluate_release_gate(settings, dev_root=docs_root)
    baseline = latest_metrics_baseline_status(docs_root)
    backup = latest_runtime_backup_status(runtime_backups_root)
    acceptance_checklist = _acceptance_checklist_status(docs_root)

    checks = [
        _check(
            "latest_release_validation",
            "Latest Release Validation",
            str(release_validation.get("status", "blocked") or "blocked"),
            str(release_validation.get("summary", "") or ""),
            value=str(release_validation.get("generated_at", "") or release_validation.get("file_name", "") or "not_recorded"),
            recommended_action=str(release_validation.get("recommended_action", "") or "Run py -m app.tools.release_validation before business closeout."),
        ),
        _check(
            "release_gate",
            "Release Gate",
            str(release_gate.get("status", "warning") or "warning"),
            str(release_gate.get("summary", "") or ""),
            value=str(release_gate.get("mode", "") or "unknown"),
            recommended_action=str(release_gate.get("recommended_action", "") or ""),
        ),
        _baseline_closeout_check(baseline),
        _backup_closeout_check(backup),
        _check(
            "acceptance_checklist",
            "Acceptance Checklist",
            str(acceptance_checklist.get("status", "warning") or "warning"),
            str(acceptance_checklist.get("summary", "") or ""),
            value=str(acceptance_checklist.get("file_name", "") or "missing"),
            recommended_action=str(acceptance_checklist.get("recommended_action", "") or ""),
        ),
    ]

    status = "pass"
    for item in checks:
        status = _merge_status(status, str(item.get("status", "pass")))

    operator_actions = _operator_action_items(checks)
    if status == "pass":
        milestone = "ready_for_business_handoff"
        summary = "Business closeout is complete. Provider validation, sample quality, rollback point, and handoff artifacts are ready."
    elif status == "warning":
        milestone = "ready_for_operator_trial"
        summary = "Business closeout is usable for operator trial, but follow-up items still need to be cleared before final handoff."
    else:
        milestone = "blocked"
        summary = "Business closeout is blocked. Clear the blocking validation or handoff items first."

    result = {
        "generated_at": generated_at,
        "status": status,
        "milestone": milestone,
        "summary": summary,
        "operator_actions": operator_actions,
        "checks": checks,
        "config": settings.to_dict(),
        "release_validation": release_validation,
        "release_gate": {
            "status": release_gate.get("status", "warning"),
            "summary": release_gate.get("summary", ""),
            "recommended_action": release_gate.get("recommended_action", ""),
            "mode": release_gate.get("mode", ""),
        },
        "baseline": baseline,
        "backup": backup,
        "acceptance_checklist": acceptance_checklist,
        "paths": {
            "dev_root": str(docs_root),
            "backups_root": str(runtime_backups_root),
        },
        "artifacts": {},
    }

    if write_artifacts:
        result["artifacts"] = write_delivery_closeout_artifacts(result, dev_root=docs_root)

    return result
