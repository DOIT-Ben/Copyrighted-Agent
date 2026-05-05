from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.core.pipelines.submission_pipeline import ingest_submission
from app.core.services.app_config import AppConfig, load_app_config
from app.core.services.provider_probe import run_provider_probe
from app.core.services.release_gate import evaluate_release_gate
from app.core.services.startup_checks import run_startup_self_check
from app.core.utils.text import ensure_dir, now_iso
from app.tools.input_runner import collect_metrics_bundle


DEFAULT_MODE_A_SMOKE_PATH = Path("input") / "软著材料" / "2501_软著材料.zip"
DEFAULT_MODE_B_SMOKE_PATH = Path("input") / "合作协议"
DEFAULT_DEV_ROOT = Path("docs") / "dev"
LATEST_JSON_NAME = "real-provider-validation-latest.json"
LATEST_MARKDOWN_NAME = "real-provider-validation-latest.md"
HISTORY_STEM = "real_provider_validation"

STATUS_ORDER = {"pass": 0, "warning": 1, "blocked": 2}


def _merge_status(current: str, candidate: str) -> str:
    return candidate if STATUS_ORDER.get(candidate, 0) > STATUS_ORDER.get(current, 0) else current


def _config_env_overrides(config: AppConfig) -> dict[str, str]:
    return {
        "SOFT_REVIEW_DATA_ROOT": str(config.data_root),
        "SOFT_REVIEW_SQLITE_PATH": str(config.sqlite_path),
        "SOFT_REVIEW_LOG_PATH": str(config.log_path),
        "SOFT_REVIEW_AI_ENABLED": "true" if config.ai_enabled else "false",
        "SOFT_REVIEW_AI_PROVIDER": str(config.ai_provider),
        "SOFT_REVIEW_AI_REQUIRE_DESENSITIZED": "true" if config.ai_require_desensitized else "false",
        "SOFT_REVIEW_AI_TIMEOUT_SECONDS": str(config.ai_timeout_seconds),
        "SOFT_REVIEW_AI_ENDPOINT": str(config.ai_endpoint),
        "SOFT_REVIEW_AI_MODEL": str(config.ai_model),
        "SOFT_REVIEW_AI_API_KEY_ENV": str(config.ai_api_key_env),
        "SOFT_REVIEW_AI_FALLBACK_TO_MOCK": "true" if config.ai_fallback_to_mock else "false",
    }


@contextmanager
def _temporary_env(overrides: dict[str, str]) -> Iterator[None]:
    previous: dict[str, str | None] = {}
    try:
        for key, value in overrides.items():
            previous[key] = os.environ.get(key)
            if value == "":
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _metrics_from_submission_result(result: dict) -> dict:
    materials = result.get("materials", [])
    parse_results = result.get("parse_results", [])
    project_reports = [
        item
        for item in result.get("reports", [])
        if item.get("report_type") != "submission_global_review_markdown"
    ]
    type_totals: dict[str, int] = {}
    review_reason_totals: dict[str, int] = {}
    legacy_bucket_totals: dict[str, int] = {}
    needs_review = 0
    low_quality = 0
    redactions = 0
    unknown = 0

    for material in materials:
        material_type = str(material.get("material_type", "unknown") or "unknown")
        type_totals[material_type] = type_totals.get(material_type, 0) + 1
        if material_type == "unknown":
            unknown += 1

    for item in parse_results:
        metadata = dict(item.get("metadata_json", {}) or {})
        triage = dict(metadata.get("triage", {}) or {})
        parse_quality = dict(metadata.get("parse_quality", {}) or {})
        privacy = dict(metadata.get("privacy", {}) or {})
        if triage.get("needs_manual_review"):
            needs_review += 1
        if parse_quality.get("quality_level") == "low":
            low_quality += 1
        redactions += int(privacy.get("total_replacements", 0) or 0)

        review_reason = str(triage.get("quality_review_reason_code") or parse_quality.get("review_reason_code") or "").strip()
        if review_reason:
            review_reason_totals[review_reason] = review_reason_totals.get(review_reason, 0) + 1

        legacy_bucket = str(triage.get("legacy_doc_bucket") or parse_quality.get("legacy_doc_bucket") or "").strip()
        if legacy_bucket:
            legacy_bucket_totals[legacy_bucket] = legacy_bucket_totals.get(legacy_bucket, 0) + 1

    return {
        "materials": len(materials),
        "cases": len(result.get("cases", [])),
        "reports": len(project_reports),
        "types": type_totals,
        "needs_review": needs_review,
        "low_quality": low_quality,
        "redactions": redactions,
        "unknown": unknown,
        "review_reasons": review_reason_totals,
        "legacy_doc_buckets": legacy_bucket_totals,
    }


def _skipped_smoke(label: str, reason: str) -> dict:
    return {
        "label": label,
        "attempted": False,
        "status": "blocked",
        "summary": reason,
        "recommended_action": "Fix provider readiness and rerun the release validation command.",
    }


def _run_mode_a_smoke(config: AppConfig, source_path: Path) -> dict:
    if not source_path.exists():
        return {
            "label": "mode_a_smoke",
            "attempted": False,
            "status": "blocked",
            "path": str(source_path),
            "summary": "Mode A smoke sample path does not exist.",
            "recommended_action": "Provide a valid Mode A ZIP path before rerunning release validation.",
        }

    with _temporary_env(_config_env_overrides(config)):
        result = ingest_submission(source_path, mode="single_case_package", created_by="release_validation")

    review_results = list(result.get("review_results", []) or [])
    if not review_results:
        return {
            "label": "mode_a_smoke",
            "attempted": True,
            "status": "blocked",
            "path": str(source_path),
            "summary": "Mode A smoke completed without a case review result.",
            "recommended_action": "Inspect the single-case pipeline and ensure a case review result is produced.",
        }

    metrics = _metrics_from_submission_result(result)
    review = review_results[0]
    ai_provider = str(review.get("ai_provider", "") or "")
    ai_resolution = str(review.get("ai_resolution", "") or "")
    submission = dict(result.get("submission", {}) or {})

    status = "pass"
    summary = "Mode A smoke passed."
    recommended_action = ""
    if ai_provider != config.ai_provider:
        status = "blocked"
        summary = f"Mode A smoke used provider={ai_provider or 'unknown'} instead of {config.ai_provider}."
        recommended_action = "Check AI config, provider reachability, and fallback behavior before rerunning."
    elif ai_resolution in {"provider_exception_fallback", "mock_fallback", "ai_disabled_fallback"}:
        status = "blocked"
        summary = f"Mode A smoke fell back during AI review: resolution={ai_resolution}."
        recommended_action = "Fix the provider path so the single-case review no longer falls back."
    elif metrics["unknown"] > 0 or metrics["needs_review"] > 0 or metrics["low_quality"] > 0:
        status = "warning"
        summary = "Mode A smoke completed, but review debt remains in the sample package."
        recommended_action = "Inspect the sample output and reduce remaining unknown / needs_review / low_quality debt."

    return {
        "label": "mode_a_smoke",
        "attempted": True,
        "status": status,
        "path": str(source_path),
        "submission_id": str(submission.get("id", "") or ""),
        "submission_status": str(submission.get("status", "") or ""),
        "review_provider": ai_provider,
        "review_resolution": ai_resolution,
        "metrics": metrics,
        "summary": summary,
        "recommended_action": recommended_action,
    }


def _run_mode_b_smoke(config: AppConfig, source_path: Path) -> dict:
    if not source_path.exists():
        return {
            "label": "mode_b_smoke",
            "attempted": False,
            "status": "blocked",
            "path": str(source_path),
            "summary": "Mode B smoke sample path does not exist.",
            "recommended_action": "Provide a valid Mode B directory or ZIP path before rerunning release validation.",
        }

    with _temporary_env(_config_env_overrides(config)):
        bundle = collect_metrics_bundle(source_path, "batch_same_material")

    aggregate = dict(bundle.get("aggregate", {}) or {})
    status = "pass"
    summary = "Mode B smoke passed."
    recommended_action = ""
    if int(aggregate.get("materials", 0) or 0) <= 0:
        status = "blocked"
        summary = "Mode B smoke did not ingest any materials."
        recommended_action = "Check the Mode B sample path and supported file types."
    elif int(aggregate.get("unknown", 0) or 0) > 0 or int(aggregate.get("needs_review", 0) or 0) > 0 or int(aggregate.get("low_quality", 0) or 0) > 0:
        status = "warning"
        summary = "Mode B smoke completed, but review debt remains in the sample corpus."
        recommended_action = "Inspect the batch sample output and reduce remaining unknown / needs_review / low_quality debt."

    return {
        "label": "mode_b_smoke",
        "attempted": True,
        "status": status,
        "path": str(source_path),
        "aggregate": aggregate,
        "entries": list(bundle.get("entries", []) or []),
        "summary": summary,
        "recommended_action": recommended_action,
    }


def _history_base_paths(dev_root: Path, generated_at: str) -> tuple[Path, Path]:
    history_root = ensure_dir(dev_root / "history")
    digits = "".join(character for character in str(generated_at) if character.isdigit())
    stamp = f"{digits[:8]}_{digits[8:14]}" if len(digits) >= 14 else (digits or "latest")
    return (
        history_root / f"{HISTORY_STEM}_{stamp}.json",
        history_root / f"{HISTORY_STEM}_{stamp}.md",
    )


def _render_markdown(result: dict) -> str:
    lines = [
        "# Real Provider Validation",
        "",
        "## Summary",
        "",
        f"- generated_at: `{result.get('generated_at', '')}`",
        f"- status: `{result.get('status', 'blocked')}`",
        f"- summary: {result.get('summary', '')}",
        "",
        "## Config",
        "",
        f"- provider: `{result.get('config', {}).get('ai_provider', '')}`",
        f"- ai_enabled: `{result.get('config', {}).get('ai_enabled', False)}`",
        f"- endpoint: `{result.get('config', {}).get('ai_endpoint', '')}`",
        f"- model: `{result.get('config', {}).get('ai_model', '')}`",
        f"- api_key_env: `{result.get('config', {}).get('ai_api_key_env', '')}`",
        "",
        "## Provider Probe",
        "",
        f"- status: `{result.get('provider_probe', {}).get('status', 'blocked')}`",
        f"- probe_status: `{result.get('provider_probe', {}).get('probe_status', 'skipped')}`",
        f"- summary: {result.get('provider_probe', {}).get('summary', '')}",
        "",
        "## Release Gate",
        "",
        f"- status: `{result.get('release_gate', {}).get('status', 'blocked')}`",
        f"- summary: {result.get('release_gate', {}).get('summary', '')}",
        "",
        "## Mode A Smoke",
        "",
        f"- status: `{result.get('mode_a_smoke', {}).get('status', 'blocked')}`",
        f"- path: `{result.get('mode_a_smoke', {}).get('path', '')}`",
        f"- provider: `{result.get('mode_a_smoke', {}).get('review_provider', '')}`",
        f"- resolution: `{result.get('mode_a_smoke', {}).get('review_resolution', '')}`",
        f"- summary: {result.get('mode_a_smoke', {}).get('summary', '')}",
        "",
        "## Mode B Smoke",
        "",
        f"- status: `{result.get('mode_b_smoke', {}).get('status', 'blocked')}`",
        f"- path: `{result.get('mode_b_smoke', {}).get('path', '')}`",
        f"- summary: {result.get('mode_b_smoke', {}).get('summary', '')}",
        "",
        "## Recommended Action",
        "",
        f"- {result.get('recommended_action', '')}",
    ]
    return "\n".join(lines) + "\n"


def write_release_validation_artifacts(
    result: dict,
    *,
    dev_root: str | Path | None = None,
) -> dict:
    root = ensure_dir(Path(dev_root or DEFAULT_DEV_ROOT))
    latest_json_path = root / LATEST_JSON_NAME
    latest_markdown_path = root / LATEST_MARKDOWN_NAME
    history_json_path, history_markdown_path = _history_base_paths(root, str(result.get("generated_at", "") or now_iso()))

    artifact_paths = {
        "latest_json_path": str(latest_json_path),
        "latest_markdown_path": str(latest_markdown_path),
        "history_json_path": str(history_json_path),
        "history_markdown_path": str(history_markdown_path),
    }
    payload = dict(result)
    payload["artifacts"] = artifact_paths

    latest_json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    latest_markdown_path.write_text(_render_markdown(payload), encoding="utf-8")
    history_json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    history_markdown_path.write_text(_render_markdown(payload), encoding="utf-8")

    return artifact_paths


def run_release_validation(
    *,
    config: AppConfig | None = None,
    config_path: str | Path | None = None,
    mode_a_path: str | Path | None = None,
    mode_b_path: str | Path | None = None,
    dev_root: str | Path | None = None,
    send_probe: bool = True,
    write_artifacts: bool = True,
) -> dict:
    settings = config or load_app_config(config_path)
    generated_at = now_iso()
    mode_a_source = Path(mode_a_path) if mode_a_path else DEFAULT_MODE_A_SMOKE_PATH
    mode_b_source = Path(mode_b_path) if mode_b_path else DEFAULT_MODE_B_SMOKE_PATH
    docs_root = Path(dev_root or DEFAULT_DEV_ROOT)

    startup_report = run_startup_self_check(settings)
    probe_result = run_provider_probe(
        settings,
        send_request=send_probe,
        persist_result=True,
        persist_history=send_probe,
    )
    release_gate = evaluate_release_gate(settings, startup_report=run_startup_self_check(settings), dev_root=docs_root)

    provider_probe_summary = {
        "status": "pass" if probe_result.get("probe", {}).get("status") == "ok" else "blocked",
        "probe_status": probe_result.get("probe", {}).get("status", "skipped"),
        "summary": probe_result.get("summary", ""),
        "recommended_action": probe_result.get("recommended_action", ""),
        "phase": probe_result.get("phase", ""),
    }

    if provider_probe_summary["status"] == "pass":
        mode_a_smoke = _run_mode_a_smoke(settings, mode_a_source)
        mode_b_smoke = _run_mode_b_smoke(settings, mode_b_source)
    else:
        blocking_reason = "Real-provider probe did not pass, so sample smokes were not executed."
        mode_a_smoke = _skipped_smoke("mode_a_smoke", blocking_reason)
        mode_b_smoke = _skipped_smoke("mode_b_smoke", blocking_reason)
        mode_a_smoke["path"] = str(mode_a_source)
        mode_b_smoke["path"] = str(mode_b_source)

    overall_status = "pass"
    overall_status = _merge_status(overall_status, provider_probe_summary["status"])
    overall_status = _merge_status(overall_status, str(release_gate.get("status", "warning")))
    overall_status = _merge_status(overall_status, str(mode_a_smoke.get("status", "blocked")))
    overall_status = _merge_status(overall_status, str(mode_b_smoke.get("status", "blocked")))

    recommended_action = ""
    for item in (provider_probe_summary, release_gate, mode_a_smoke, mode_b_smoke):
        candidate_status = str(item.get("status", "pass"))
        if candidate_status in {"blocked", "warning"} and str(item.get("recommended_action", "")).strip():
            recommended_action = str(item.get("recommended_action", ""))
            break

    if overall_status == "pass":
        summary = "Real-provider validation passed for probe, release gate, and sample smokes."
    elif overall_status == "warning":
        summary = "Real-provider validation completed, but warnings remain."
    else:
        summary = "Real-provider validation is blocked."

    result = {
        "generated_at": generated_at,
        "status": overall_status,
        "summary": summary,
        "recommended_action": recommended_action,
        "config": settings.to_dict(),
        "provider_probe": provider_probe_summary,
        "release_gate": {
            "status": release_gate.get("status", "warning"),
            "summary": release_gate.get("summary", ""),
            "recommended_action": release_gate.get("recommended_action", ""),
            "mode": release_gate.get("mode", ""),
        },
        "mode_a_smoke": mode_a_smoke,
        "mode_b_smoke": mode_b_smoke,
        "paths": {
            "mode_a_path": str(mode_a_source),
            "mode_b_path": str(mode_b_source),
            "dev_root": str(docs_root),
        },
        "artifacts": {},
    }

    if write_artifacts:
        result["artifacts"] = write_release_validation_artifacts(result, dev_root=docs_root)

    return result
