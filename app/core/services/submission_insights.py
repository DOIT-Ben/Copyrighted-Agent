from __future__ import annotations

from collections import Counter
from typing import Any

from app.core.services.runtime_store import store


PARSE_REASON_LABELS = {
    "clean_text_ready": "文本可直接使用",
    "text_too_short": "文本过短",
    "noise_too_high": "噪声过高",
    "ole_readable_segments_insufficient": "旧版 DOC 仅提取到零散片段",
    "low_signal_ratio": "有效文本信号不足",
    "empty_text": "未提取到可用文本",
}

UNKNOWN_REASON_LABELS = {
    "blocked_low_quality_content_signal": "文本质量过低，已阻断自动归类",
    "binary_doc_parse_failed": "旧版 DOC 解析失败",
    "no_matching_rule": "没有命中已知材料规则",
}

MANUAL_REVIEW_REASON_LABELS = {
    "manual_review_required_unknown_material": "材料类型未识别，需要人工归类",
    "manual_review_required_low_quality": "解析质量偏低，需要人工确认",
    "manual_review_required_low_confidence": "分类置信度偏低，需要人工确认",
}

CORRECTION_REASON_LABELS = {
    "manual_material_reclassified": "人工重分材料类型",
    "manual_case_regrouped": "人工调整项目归属",
    "manual_case_created": "人工新建项目",
    "manual_case_merged": "人工合并项目",
    "manual_review_rerun": "人工触发重审",
    "online_filing_enriched": "补录在线填报信息",
    "rule_dimension_tuned": "调整维度规则",
    "rule_dimension_reset": "恢复默认规则",
    "desensitized_review_continued": "脱敏确认后继续审查",
    "desensitized_package_uploaded": "回传脱敏包",
}

CORRECTION_OUTCOME_LABELS = {
    "reduced_manual_review_load": "减少待人工复核量",
    "reduced_unknown_materials": "减少未知材料",
    "stabilized_review_configuration": "审查配置已收敛",
    "refreshed_review_output": "审查结果已刷新",
    "awaiting_followup_validation": "已留痕，等待后续验证",
    "no_material_change_detected": "指标暂未变化",
}


def label_for_parse_reason(code: str) -> str:
    normalized = str(code or "").strip()
    return PARSE_REASON_LABELS.get(normalized, normalized or "-")


def label_for_unknown_reason(code: str) -> str:
    normalized = str(code or "").strip()
    return UNKNOWN_REASON_LABELS.get(normalized, normalized or "-")


def label_for_manual_review_reason(code: str) -> str:
    normalized = str(code or "").strip()
    return MANUAL_REVIEW_REASON_LABELS.get(normalized, normalized or "-")


def label_for_correction_reason(code: str) -> str:
    normalized = str(code or "").strip()
    return CORRECTION_REASON_LABELS.get(normalized, normalized or "-")


def label_for_correction_outcome(code: str) -> str:
    normalized = str(code or "").strip()
    return CORRECTION_OUTCOME_LABELS.get(normalized, normalized or "-")


def parse_diagnostic_snapshot(material: dict[str, Any] | None, parse_result: dict[str, Any] | None) -> dict[str, Any]:
    material_payload = dict(material or {})
    parse_payload = dict(parse_result or {})
    metadata = dict(parse_payload.get("metadata_json") or material_payload.get("metadata") or {})
    triage = dict(metadata.get("triage") or {})
    parse_quality = dict(metadata.get("parse_quality") or metadata.get("quality") or {})
    confidence = float(material_payload.get("metadata", {}).get("classification_confidence", 0.0) or 0.0)

    manual_review_reason_code = ""
    if material_payload.get("material_type") == "unknown":
        manual_review_reason_code = "manual_review_required_unknown_material"
    elif parse_quality.get("quality_level") == "low":
        manual_review_reason_code = "manual_review_required_low_quality"
    elif triage.get("needs_manual_review") and confidence and confidence < 0.85:
        manual_review_reason_code = "manual_review_required_low_confidence"

    parse_reason_code = str(triage.get("quality_review_reason_code") or parse_quality.get("review_reason_code") or "").strip()
    unknown_reason_code = str(triage.get("unknown_reason", "") or "").strip()
    return {
        "parse_reason_code": parse_reason_code,
        "parse_reason_label": label_for_parse_reason(parse_reason_code),
        "unknown_reason_code": unknown_reason_code,
        "unknown_reason_label": label_for_unknown_reason(unknown_reason_code),
        "manual_review_reason_code": manual_review_reason_code,
        "manual_review_reason_label": label_for_manual_review_reason(manual_review_reason_code),
        "needs_manual_review": bool(triage.get("needs_manual_review", False) or material_payload.get("material_type") == "unknown"),
        "quality_level": str(parse_quality.get("quality_level", "") or ""),
        "legacy_doc_bucket": str(triage.get("legacy_doc_bucket") or parse_quality.get("legacy_doc_bucket") or ""),
    }


def submission_quality_snapshot(submission_id: str) -> dict[str, Any]:
    submission = store.submissions.get(submission_id)
    if not submission:
        return {
            "materials_total": 0,
            "unknown_materials": 0,
            "manual_review_materials": 0,
            "low_quality_materials": 0,
            "pending_cases": 0,
            "corrections_total": 0,
            "jobs_retryable": 0,
            "manual_review_reasons": {},
        }

    unknown_materials = 0
    manual_review_materials = 0
    low_quality_materials = 0
    manual_review_reasons: Counter[str] = Counter()
    for material_id in submission.material_ids:
        material = store.materials.get(material_id)
        parse_result = store.parse_results.get(material_id)
        if not material:
            continue
        diagnostic = parse_diagnostic_snapshot(material.to_dict(), parse_result.to_dict() if parse_result else {})
        if material.material_type == "unknown":
            unknown_materials += 1
        if diagnostic["needs_manual_review"]:
            manual_review_materials += 1
        if diagnostic["quality_level"] == "low":
            low_quality_materials += 1
        reason_code = str(diagnostic.get("manual_review_reason_code", "") or diagnostic.get("unknown_reason_code", "") or diagnostic.get("parse_reason_code", "") or "").strip()
        if reason_code:
            manual_review_reasons[reason_code] += 1

    pending_cases = sum(
        1
        for case_id in submission.case_ids
        if case_id in store.cases and getattr(store.cases[case_id], "status", "") == "awaiting_manual_review"
    )
    retryable_jobs = sum(
        1
        for job in store.jobs.values()
        if getattr(job, "scope_id", "") == submission_id
        and getattr(job, "retryable", False)
        and str(getattr(job, "status", "") or "").strip().lower() in {"failed", "interrupted"}
    )
    return {
        "materials_total": len(submission.material_ids),
        "unknown_materials": unknown_materials,
        "manual_review_materials": manual_review_materials,
        "low_quality_materials": low_quality_materials,
        "pending_cases": pending_cases,
        "corrections_total": len(submission.correction_ids),
        "jobs_retryable": retryable_jobs,
        "manual_review_reasons": dict(manual_review_reasons),
    }


def build_correction_analysis(before_metrics: dict[str, Any], after_metrics: dict[str, Any]) -> dict[str, Any]:
    unknown_delta = int(after_metrics.get("unknown_materials", 0)) - int(before_metrics.get("unknown_materials", 0))
    manual_review_delta = int(after_metrics.get("manual_review_materials", 0)) - int(before_metrics.get("manual_review_materials", 0))
    low_quality_delta = int(after_metrics.get("low_quality_materials", 0)) - int(before_metrics.get("low_quality_materials", 0))
    pending_cases_delta = int(after_metrics.get("pending_cases", 0)) - int(before_metrics.get("pending_cases", 0))

    if unknown_delta < 0:
        outcome_code = "reduced_unknown_materials"
    elif manual_review_delta < 0:
        outcome_code = "reduced_manual_review_load"
    elif pending_cases_delta < 0 or low_quality_delta < 0:
        outcome_code = "refreshed_review_output"
    elif before_metrics != after_metrics:
        outcome_code = "awaiting_followup_validation"
    else:
        outcome_code = "no_material_change_detected"

    return {
        "metrics_before": dict(before_metrics),
        "metrics_after": dict(after_metrics),
        "delta": {
            "unknown_materials": unknown_delta,
            "manual_review_materials": manual_review_delta,
            "low_quality_materials": low_quality_delta,
            "pending_cases": pending_cases_delta,
        },
        "outcome_code": outcome_code,
        "outcome_label": label_for_correction_outcome(outcome_code),
    }

