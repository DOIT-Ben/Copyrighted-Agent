from __future__ import annotations

from pathlib import Path
import zipfile

from app.core.domain.enums import MaterialType
from app.core.domain.models import Case, Correction, ReportArtifact, ReviewResult
from app.core.privacy.desensitization import build_ai_safe_case_payload
from app.core.reports.renderers import render_case_report_markdown
from app.core.reviewers.ai.service import generate_case_ai_review, resolve_case_ai_provider
from app.core.reviewers.rules.cross_material import review_case_consistency
from app.core.reviewers.rules.document import review_document_text
from app.core.reviewers.rules.info_form import review_info_form_text
from app.core.reviewers.rules.online_filing import review_online_filing_payload
from app.core.reviewers.rules.source_code import review_source_code_text
from app.core.reviewers.rules.agreement import review_agreement_text
from app.core.services.app_config import load_app_config
from app.core.services.app_logging import log_event
from app.core.services.online_filing import normalize_online_filing
from app.core.services.review_dimensions import build_case_review_dimensions
from app.core.services.review_profile import bump_review_profile_revision, normalize_review_profile
from app.core.services.review_rulebook import reset_profile_dimension_rule, update_profile_dimension_rule
from app.core.services.submission_insights import (
    build_correction_analysis,
    label_for_correction_outcome,
    label_for_correction_reason,
    submission_quality_snapshot,
)
from app.core.services.sqlite_repository import save_submission_graph
from app.core.services.runtime_store import store
from app.core.utils.text import ensure_dir, now_iso, slug_id, summarize_severity


def _submission_runtime_dir(submission_id: str) -> Path:
    submission = store.submissions.get(submission_id)
    if submission:
        for material_id in submission.material_ids:
            parse_result = store.parse_results.get(material_id)
            if parse_result and getattr(parse_result, "raw_text_path", ""):
                return Path(parse_result.raw_text_path).resolve().parents[2]
    return ensure_dir(Path(load_app_config().data_root) / "submissions" / submission_id)


def _submission_for_material(material_id: str):
    material = store.materials.get(material_id)
    if not material:
        raise ValueError(f"Material not found: {material_id}")
    submission = store.submissions.get(material.submission_id)
    if not submission:
        raise ValueError(f"Submission not found: {material.submission_id}")
    return material, submission


def _submission_for_case(case_id: str):
    case = store.cases.get(case_id)
    if not case:
        raise ValueError(f"Case not found: {case_id}")
    submission = store.submissions.get(case.source_submission_id)
    if not submission:
        raise ValueError(f"Submission not found: {case.source_submission_id}")
    return case, submission


def _sync_submission_status(submission_id: str) -> None:
    submission = store.submissions.get(submission_id)
    if not submission:
        return
    cases = [store.cases[item_id] for item_id in submission.case_ids if item_id in store.cases]
    if not cases:
        return
    if any(case.status == "awaiting_manual_review" for case in cases):
        submission.status = "awaiting_manual_review"
        if any(getattr(case, "review_stage", "") == "desensitized_uploaded" for case in cases):
            submission.review_stage = "desensitized_uploaded"
        else:
            submission.review_stage = "desensitized_ready"
        return
    if all(case.status in {"completed", "grouped"} for case in cases):
        submission.status = "completed"
        submission.review_stage = "review_completed"


def _desensitized_entry_candidates(material_id: str, original_filename: str) -> list[str]:
    filename = str(original_filename or "").replace("\\", "/").split("/")[-1]
    return [
        f"artifacts/{material_id}/desensitized.txt",
        f"{material_id}/desensitized.txt",
        f"{material_id}.desensitized.txt",
        f"{filename}.desensitized.txt",
        filename,
    ]


def _material_review_bucket(material_type: str, text: str) -> dict:
    if material_type == MaterialType.AGREEMENT.value:
        return review_agreement_text(text)
    if material_type == MaterialType.SOFTWARE_DOC.value:
        return review_document_text(text)
    if material_type == MaterialType.SOURCE_CODE.value:
        return review_source_code_text(text)
    if material_type == MaterialType.INFO_FORM.value:
        return review_info_form_text(text)
    return {"issues": []}


def _case_materials(case_id: str) -> list:
    case = store.cases.get(case_id)
    if not case:
        return []
    return [store.materials[item_id] for item_id in case.material_ids if item_id in store.materials]


def _infer_case_identity(materials: list, fallback_name: str = "Manual Case") -> tuple[str, str, str]:
    software_name = ""
    version = ""
    company_name = ""

    for material in materials:
        if not software_name:
            software_name = material.detected_software_name or material.metadata.get("software_name", "")
        if not version:
            version = material.detected_version or material.metadata.get("version", "")
        if not company_name:
            company_name = material.metadata.get("company_name", "")
        if software_name and version and company_name:
            break

    software_name = software_name or fallback_name
    return software_name, version, company_name


def _collect_case_issues(materials: list, consistency_issues: list[dict]) -> list[dict]:
    combined: list[dict] = [dict(item) for item in list(consistency_issues or [])]
    for material in materials:
        for issue in list(getattr(material, "issues", []) or []):
            payload = dict(issue or {})
            payload.setdefault("material_id", material.id)
            payload.setdefault("material_name", material.original_filename)
            payload.setdefault("material_type", material.material_type)
            combined.append(payload)
    return combined


def _submission_metrics(submission_id: str) -> dict:
    return submission_quality_snapshot(submission_id)


def _effect_analysis(submission_id: str, before_metrics: dict) -> tuple[str, dict]:
    analysis = build_correction_analysis(before_metrics, _submission_metrics(submission_id))
    return str(analysis.get("outcome_code", "") or ""), analysis


def _record_correction(
    submission_id: str,
    correction_type: str,
    *,
    material_id: str = "",
    case_id: str = "",
    reason_code: str = "",
    outcome_code: str = "",
    original_value: dict | None = None,
    corrected_value: dict | None = None,
    analysis: dict | None = None,
    note: str = "",
    corrected_by: str = "local",
) -> Correction:
    normalized_reason_code = str(reason_code or "").strip()
    normalized_outcome_code = str(outcome_code or "").strip()
    correction = Correction(
        id=slug_id("cor"),
        submission_id=submission_id,
        correction_type=correction_type,
        material_id=material_id,
        case_id=case_id,
        reason_code=normalized_reason_code,
        reason_label=label_for_correction_reason(normalized_reason_code),
        outcome_code=normalized_outcome_code,
        outcome_label=label_for_correction_outcome(normalized_outcome_code),
        original_value=original_value or {},
        corrected_value=corrected_value or {},
        analysis=dict(analysis or {}),
        note=note,
        corrected_by=corrected_by,
        corrected_at=now_iso(),
    )
    store.add_correction(correction)
    submission = store.submissions.get(submission_id)
    if submission is not None:
        submission.correction_ids.append(correction.id)
    return correction


def _write_case_report(case: Case, report_path: Path, report_content: str) -> ReportArtifact:
    ensure_dir(report_path.parent)
    report_path.write_text(report_content, encoding="utf-8")
    if case.report_id and case.report_id in store.report_artifacts:
        report = store.report_artifacts[case.report_id]
        report.storage_path = str(report_path)
        report.content = report_content
        report.created_at = now_iso()
        return report
    report = ReportArtifact(
        id=slug_id("rep"),
        scope_type="case",
        scope_id=case.id,
        report_type="case_markdown",
        file_format="md",
        storage_path=str(report_path),
        created_at=now_iso(),
        content=report_content,
    )
    store.add_report_artifact(report)
    case.report_id = report.id
    submission = store.submissions.get(case.source_submission_id)
    if submission and report.id not in submission.report_ids:
        submission.report_ids.append(report.id)
    return report


def _compose_case_review_payload(
    case: Case,
    materials: list,
    combined_issues: list[dict],
    ai_review: dict,
    review_profile: dict,
) -> dict:
    rule_conclusion = str(ai_review.get("rule_summary") or ai_review.get("conclusion") or "").strip()
    ai_summary = str(ai_review.get("ai_note") or ai_review.get("summary") or "").strip()
    review_dimensions = build_case_review_dimensions(
        case,
        materials,
        cross_material_issues=combined_issues,
        ai_resolution=str(ai_review.get("resolution", "explicit_mock") or ""),
        review_profile=review_profile,
    )
    return {
        "review": {
            "severity_summary_json": summarize_severity(combined_issues),
            "issues_json": combined_issues,
            "score": max(0.0, 100.0 - len(combined_issues) * 12.5),
            "conclusion": rule_conclusion or "规则审查已完成",
            "rule_conclusion": rule_conclusion or "规则审查已完成",
            "ai_summary": ai_summary,
            "ai_provider": ai_review.get("provider", "mock"),
            "ai_resolution": ai_review.get("resolution", "explicit_mock"),
            "review_profile_snapshot": dict(review_profile),
            "prompt_snapshot_json": dict(ai_review.get("prompt_snapshot") or {}),
        },
        "report": {
            "case_name": case.case_name,
            "materials": [],
            "cross_material_issues": combined_issues,
            "review_dimensions": review_dimensions,
            "rule_conclusion": rule_conclusion or "规则引擎未返回额外结论",
            "ai_summary": ai_summary or "当前没有额外 AI 补充说明",
            "ai_provider": ai_review.get("provider", "mock"),
            "ai_resolution": ai_review.get("resolution", "explicit_mock"),
            "review_profile": dict(review_profile),
        },
    }


def _rebuild_case(case_id: str) -> dict:
    case, submission = _submission_for_case(case_id)
    review_profile = normalize_review_profile(getattr(submission, "review_profile", {}))
    materials = _case_materials(case_id)
    if not materials:
        return {"case": case.to_dict(), "review_result": None, "report": None}

    software_name, version, company_name = _infer_case_identity(materials, fallback_name=case.case_name)
    case.case_name = software_name
    case.software_name = software_name
    case.version = version
    case.company_name = company_name

    info_form = next((item for item in materials if item.material_type == MaterialType.INFO_FORM.value), None)
    source_code = next((item for item in materials if item.material_type == MaterialType.SOURCE_CODE.value), None)
    software_doc = next((item for item in materials if item.material_type == MaterialType.SOFTWARE_DOC.value), None)
    agreement = next((item for item in materials if item.material_type == MaterialType.AGREEMENT.value), None)
    online_filing = normalize_online_filing(getattr(case, "online_filing", {}) or {})

    consistency = review_case_consistency(
        info_form.metadata if info_form else {},
        source_code.metadata if source_code else {},
        software_doc.metadata if software_doc else {},
        agreement.metadata if agreement else {},
        online_filing,
    )
    online_filing_review = review_online_filing_payload(
        online_filing,
        case_payload=case.to_dict(),
        info_form=info_form.metadata if info_form else {},
        agreement=agreement.metadata if agreement else {},
    )
    combined_issues = _collect_case_issues(materials, consistency.get("issues", []))
    combined_issues.extend(list(online_filing_review.get("issues", [])))
    ai_provider = resolve_case_ai_provider()
    ai_payload = {
        "software_name": case.software_name,
        "version": case.version,
        "company_name": case.company_name,
        "online_filing": online_filing if online_filing.get("has_data") else {},
    }
    if ai_provider != "mock":
        ai_payload = build_ai_safe_case_payload(ai_payload)
    ai_review = generate_case_ai_review(
        ai_payload,
        {"issues": combined_issues},
        provider=ai_provider,
        review_profile=review_profile,
    )
    review_payload = _compose_case_review_payload(case, materials, combined_issues, ai_review, review_profile)

    if case.review_result_id and case.review_result_id in store.review_results:
        review_result = store.review_results[case.review_result_id]
        review_result.reviewer_type = "hybrid"
        review_result.severity_summary_json = review_payload["review"]["severity_summary_json"]
        review_result.issues_json = review_payload["review"]["issues_json"]
        review_result.score = review_payload["review"]["score"]
        review_result.conclusion = review_payload["review"]["conclusion"]
        review_result.rule_conclusion = review_payload["review"]["rule_conclusion"]
        review_result.ai_summary = review_payload["review"]["ai_summary"]
        review_result.ai_provider = review_payload["review"]["ai_provider"]
        review_result.ai_resolution = review_payload["review"]["ai_resolution"]
        review_result.review_profile_snapshot = review_payload["review"]["review_profile_snapshot"]
        review_result.prompt_snapshot_json = review_payload["review"]["prompt_snapshot_json"]
        review_result.created_at = now_iso()
    else:
        review_result = ReviewResult(
            id=slug_id("rev"),
            scope_type="case",
            scope_id=case.id,
            reviewer_type="hybrid",
            severity_summary_json=review_payload["review"]["severity_summary_json"],
            issues_json=review_payload["review"]["issues_json"],
            score=review_payload["review"]["score"],
            conclusion=review_payload["review"]["conclusion"],
            created_at=now_iso(),
            rule_conclusion=review_payload["review"]["rule_conclusion"],
            ai_summary=review_payload["review"]["ai_summary"],
            ai_provider=review_payload["review"]["ai_provider"],
            ai_resolution=review_payload["review"]["ai_resolution"],
            review_profile_snapshot=review_payload["review"]["review_profile_snapshot"],
            prompt_snapshot_json=review_payload["review"]["prompt_snapshot_json"],
        )
        store.add_review_result(review_result)
        case.review_result_id = review_result.id

    report_data = review_payload["report"]
    report_data["materials"] = [item.original_filename for item in materials]
    report_content = render_case_report_markdown(report_data)
    report_path = _submission_runtime_dir(submission.id) / "reports" / f"{case.id}.md"
    report = _write_case_report(case, report_path, report_content)
    case.status = "completed"
    return {"case": case.to_dict(), "review_result": review_result.to_dict(), "report": report.to_dict()}


def update_case_online_filing(
    case_id: str,
    payload: dict | None,
    *,
    corrected_by: str = "local",
    note: str = "",
) -> dict:
    case, submission = _submission_for_case(case_id)
    before_metrics = _submission_metrics(submission.id)
    original_value = normalize_online_filing(getattr(case, "online_filing", {}) or {})
    normalized = normalize_online_filing(payload)
    case.online_filing = normalized
    rebuilt = _rebuild_case(case.id)
    outcome_code, analysis = _effect_analysis(submission.id, before_metrics)
    correction = _record_correction(
        submission.id,
        "update_case_online_filing",
        case_id=case.id,
        reason_code="online_filing_enriched",
        outcome_code=outcome_code,
        original_value={"online_filing": original_value},
        corrected_value={"online_filing": normalized},
        analysis=analysis,
        note=note or "online_filing_updated",
        corrected_by=corrected_by,
    )
    save_submission_graph(submission.id)
    log_event(
        "update_case_online_filing",
        {"submission_id": submission.id, "case_id": case.id, "has_data": normalized.get("has_data", False), "corrected_by": corrected_by},
    )
    return {
        "correction": correction.to_dict(),
        "case": rebuilt["case"],
        "review_result": rebuilt["review_result"],
        "report": rebuilt["report"],
    }


def _remove_case_if_empty(case_id: str) -> None:
    case = store.cases.get(case_id)
    if not case or case.material_ids:
        return
    submission = store.submissions.get(case.source_submission_id)
    if submission and case.id in submission.case_ids:
        submission.case_ids.remove(case.id)
    if case.review_result_id:
        store.review_results.pop(case.review_result_id, None)
    if case.report_id:
        store.report_artifacts.pop(case.report_id, None)
        if submission and case.report_id in submission.report_ids:
            submission.report_ids.remove(case.report_id)
    store.cases.pop(case.id, None)


def change_material_type(material_id: str, new_material_type: str, corrected_by: str = "local", note: str = "") -> dict:
    if new_material_type not in {item.value for item in MaterialType}:
        raise ValueError(f"Unsupported material type: {new_material_type}")

    material, submission = _submission_for_material(material_id)
    before_metrics = _submission_metrics(submission.id)
    original_value = {"material_type": material.material_type}
    material.material_type = new_material_type
    material.metadata = {
        **material.metadata,
        "correction": {
            "corrected_type": new_material_type,
            "corrected_by": corrected_by,
            "corrected_at": now_iso(),
            "note": note,
        },
    }

    if material.case_id:
        _rebuild_case(material.case_id)
    outcome_code, analysis = _effect_analysis(submission.id, before_metrics)
    correction = _record_correction(
        submission.id,
        "change_material_type",
        material_id=material.id,
        case_id=material.case_id or "",
        reason_code="manual_material_reclassified",
        outcome_code=outcome_code,
        original_value=original_value,
        corrected_value={"material_type": new_material_type},
        analysis=analysis,
        note=note,
        corrected_by=corrected_by,
    )
    save_submission_graph(submission.id)
    log_event(
        "change_material_type",
        {"submission_id": submission.id, "material_id": material.id, "material_type": new_material_type, "corrected_by": corrected_by},
    )

    return {"correction": correction.to_dict(), "material": material.to_dict()}


def assign_material_to_case(material_id: str, case_id: str, corrected_by: str = "local", note: str = "") -> dict:
    material, submission = _submission_for_material(material_id)
    case, _ = _submission_for_case(case_id)
    if material.submission_id != case.source_submission_id:
        raise ValueError("Material and case must belong to the same submission")
    before_metrics = _submission_metrics(submission.id)

    original_case_id = material.case_id or ""
    if original_case_id and original_case_id in store.cases:
        original_case = store.cases[original_case_id]
        if material.id in original_case.material_ids:
            original_case.material_ids.remove(material.id)
        _remove_case_if_empty(original_case_id)

    if material.id not in case.material_ids:
        case.material_ids.append(material.id)
    material.case_id = case.id

    rebuilt = _rebuild_case(case.id)
    outcome_code, analysis = _effect_analysis(submission.id, before_metrics)
    correction = _record_correction(
        submission.id,
        "assign_material_to_case",
        material_id=material.id,
        case_id=case.id,
        reason_code="manual_case_regrouped",
        outcome_code=outcome_code,
        original_value={"case_id": original_case_id},
        corrected_value={"case_id": case.id},
        analysis=analysis,
        note=note,
        corrected_by=corrected_by,
    )
    save_submission_graph(submission.id)
    log_event(
        "assign_material_to_case",
        {"submission_id": submission.id, "material_id": material.id, "case_id": case.id, "corrected_by": corrected_by},
    )
    return {
        "correction": correction.to_dict(),
        "material": material.to_dict(),
        "case": rebuilt["case"],
        "review_result": rebuilt["review_result"],
        "report": rebuilt["report"],
    }


def create_case_from_materials(
    submission_id: str,
    material_ids: list[str],
    case_name: str = "",
    version: str = "",
    company_name: str = "",
    corrected_by: str = "local",
    note: str = "",
) -> dict:
    submission = store.submissions.get(submission_id)
    if not submission:
        raise ValueError(f"Submission not found: {submission_id}")
    before_metrics = _submission_metrics(submission_id)
    materials = [store.materials[item_id] for item_id in material_ids if item_id in store.materials]
    if not materials:
        raise ValueError("No valid materials selected")

    software_name = case_name or _infer_case_identity(materials, fallback_name="Manual Case")[0]
    new_case = Case(
        id=slug_id("case"),
        case_name=software_name,
        software_name=software_name,
        version=version or _infer_case_identity(materials, fallback_name=software_name)[1],
        company_name=company_name or _infer_case_identity(materials, fallback_name=software_name)[2],
        status="grouped",
        source_submission_id=submission_id,
        created_at=now_iso(),
        material_ids=[],
    )
    store.add_case(new_case)
    if new_case.id not in submission.case_ids:
        submission.case_ids.append(new_case.id)

    for material in materials:
        if material.case_id and material.case_id in store.cases:
            old_case = store.cases[material.case_id]
            if material.id in old_case.material_ids:
                old_case.material_ids.remove(material.id)
            _remove_case_if_empty(old_case.id)
        material.case_id = new_case.id
        new_case.material_ids.append(material.id)

    rebuilt = _rebuild_case(new_case.id)
    outcome_code, analysis = _effect_analysis(submission_id, before_metrics)
    correction = _record_correction(
        submission_id,
        "create_case_from_materials",
        case_id=new_case.id,
        reason_code="manual_case_created",
        outcome_code=outcome_code,
        original_value={"material_ids": []},
        corrected_value={"material_ids": list(material_ids), "case_name": new_case.case_name},
        analysis=analysis,
        note=note,
        corrected_by=corrected_by,
    )
    save_submission_graph(submission_id)
    log_event(
        "create_case_from_materials",
        {"submission_id": submission_id, "case_id": new_case.id, "material_ids": material_ids, "corrected_by": corrected_by},
    )
    return {
        "correction": correction.to_dict(),
        "case": rebuilt["case"],
        "review_result": rebuilt["review_result"],
        "report": rebuilt["report"],
    }


def merge_cases(source_case_id: str, target_case_id: str, corrected_by: str = "local", note: str = "") -> dict:
    source_case, submission = _submission_for_case(source_case_id)
    target_case, _ = _submission_for_case(target_case_id)
    if source_case.id == target_case.id:
        raise ValueError("Source and target case must be different")
    if source_case.source_submission_id != target_case.source_submission_id:
        raise ValueError("Cases must belong to the same submission")
    before_metrics = _submission_metrics(submission.id)

    moved_materials = list(source_case.material_ids)
    for material_id in moved_materials:
        material = store.materials.get(material_id)
        if not material:
            continue
        material.case_id = target_case.id
        if material_id not in target_case.material_ids:
            target_case.material_ids.append(material_id)
    source_case.material_ids = []

    rebuilt = _rebuild_case(target_case.id)
    _remove_case_if_empty(source_case.id)
    outcome_code, analysis = _effect_analysis(submission.id, before_metrics)
    correction = _record_correction(
        submission.id,
        "merge_cases",
        case_id=target_case.id,
        reason_code="manual_case_merged",
        outcome_code=outcome_code,
        original_value={"source_case_id": source_case.id, "target_case_id": target_case.id},
        corrected_value={"merged_case_id": source_case.id},
        analysis=analysis,
        note=note,
        corrected_by=corrected_by,
    )
    save_submission_graph(submission.id)
    log_event(
        "merge_cases",
        {"submission_id": submission.id, "source_case_id": source_case.id, "target_case_id": target_case.id, "corrected_by": corrected_by},
    )
    return {
        "correction": correction.to_dict(),
        "case": rebuilt["case"],
        "review_result": rebuilt["review_result"],
        "report": rebuilt["report"],
    }


def rerun_case_review(case_id: str, corrected_by: str = "local", note: str = "", review_profile: dict | None = None) -> dict:
    case, submission = _submission_for_case(case_id)
    before_metrics = _submission_metrics(submission.id)
    original_review_profile = normalize_review_profile(getattr(submission, "review_profile", {}))
    if review_profile is not None:
        submission.review_profile = normalize_review_profile(review_profile)
    rebuilt = _rebuild_case(case.id)
    _sync_submission_status(submission.id)
    outcome_code, analysis = _effect_analysis(submission.id, before_metrics)
    correction = _record_correction(
        submission.id,
        "rerun_case_review",
        case_id=case.id,
        reason_code="manual_review_rerun",
        outcome_code=outcome_code,
        original_value={"review_result_id": case.review_result_id, "review_profile": original_review_profile},
        corrected_value={"review_result_id": case.review_result_id, "review_profile": normalize_review_profile(getattr(submission, "review_profile", {}))},
        analysis=analysis,
        note=note,
        corrected_by=corrected_by,
    )
    save_submission_graph(submission.id)
    log_event("rerun_case_review", {"submission_id": submission.id, "case_id": case.id, "corrected_by": corrected_by})
    return {
        "correction": correction.to_dict(),
        "case": rebuilt["case"],
        "review_result": rebuilt["review_result"],
        "report": rebuilt["report"],
    }


def update_submission_review_dimension_rule(
    submission_id: str,
    dimension_key: str,
    *,
    title: str = "",
    objective: str = "",
    checkpoints: str = "",
    evidence_targets: str = "",
    common_failures: str = "",
    operator_notes: str = "",
    llm_focus: str = "",
    rules: list[dict] | None = None,
    corrected_by: str = "local",
    note: str = "",
) -> dict:
    submission = store.submissions.get(submission_id)
    if not submission:
        raise ValueError(f"Submission not found: {submission_id}")

    original_review_profile = normalize_review_profile(getattr(submission, "review_profile", {}))
    updated_review_profile = update_profile_dimension_rule(
        original_review_profile,
        dimension_key,
        {
            "title": title,
            "objective": objective,
            "checkpoints": checkpoints,
            "evidence_targets": evidence_targets,
            "common_failures": common_failures,
            "operator_notes": operator_notes,
            "llm_focus": llm_focus,
            "rules": list(rules or []),
        },
    )
    submission.review_profile = bump_review_profile_revision(
        normalize_review_profile(updated_review_profile),
        updated_by=corrected_by,
        change_note=note or f"updated:{dimension_key}",
        last_dimension_key=dimension_key,
        change_type="dimension_rule_updated",
    )
    correction = _record_correction(
        submission.id,
        "update_review_dimension_rule",
        reason_code="rule_dimension_tuned",
        outcome_code="stabilized_review_configuration",
        original_value={"dimension_key": dimension_key, "review_profile": original_review_profile},
        corrected_value={"dimension_key": dimension_key, "review_profile": submission.review_profile},
        analysis={
            "metrics_before": _submission_metrics(submission.id),
            "metrics_after": _submission_metrics(submission.id),
            "delta": {},
            "outcome_code": "stabilized_review_configuration",
            "outcome_label": label_for_correction_outcome("stabilized_review_configuration"),
        },
        note=note or f"updated:{dimension_key}",
        corrected_by=corrected_by,
    )
    save_submission_graph(submission.id)
    log_event(
        "update_review_dimension_rule",
        {"submission_id": submission.id, "dimension_key": dimension_key, "corrected_by": corrected_by},
    )
    return {"correction": correction.to_dict(), "review_profile": submission.review_profile}


def reset_submission_review_dimension_rule(
    submission_id: str,
    dimension_key: str,
    *,
    corrected_by: str = "local",
    note: str = "",
) -> dict:
    submission = store.submissions.get(submission_id)
    if not submission:
        raise ValueError(f"Submission not found: {submission_id}")

    original_review_profile = normalize_review_profile(getattr(submission, "review_profile", {}))
    updated_review_profile = reset_profile_dimension_rule(original_review_profile, dimension_key)
    submission.review_profile = bump_review_profile_revision(
        normalize_review_profile(updated_review_profile),
        updated_by=corrected_by,
        change_note=note or f"reset:{dimension_key}",
        last_dimension_key=dimension_key,
        change_type="dimension_rule_reset",
    )
    correction = _record_correction(
        submission.id,
        "reset_review_dimension_rule",
        reason_code="rule_dimension_reset",
        outcome_code="stabilized_review_configuration",
        original_value={"dimension_key": dimension_key, "review_profile": original_review_profile},
        corrected_value={"dimension_key": dimension_key, "review_profile": submission.review_profile},
        analysis={
            "metrics_before": _submission_metrics(submission.id),
            "metrics_after": _submission_metrics(submission.id),
            "delta": {},
            "outcome_code": "stabilized_review_configuration",
            "outcome_label": label_for_correction_outcome("stabilized_review_configuration"),
        },
        note=note or f"reset:{dimension_key}",
        corrected_by=corrected_by,
    )
    save_submission_graph(submission.id)
    log_event(
        "reset_review_dimension_rule",
        {"submission_id": submission.id, "dimension_key": dimension_key, "corrected_by": corrected_by},
    )
    return {"correction": correction.to_dict(), "review_profile": submission.review_profile}


def continue_case_review_from_desensitized(case_id: str, corrected_by: str = "local", note: str = "") -> dict:
    case, submission = _submission_for_case(case_id)
    before_metrics = _submission_metrics(submission.id)
    original_value = {"status": case.status, "review_result_id": case.review_result_id, "report_id": case.report_id}
    case.review_stage = "review_processing"
    rebuilt = _rebuild_case(case.id)
    case.review_stage = "review_completed"
    _sync_submission_status(submission.id)
    outcome_code, analysis = _effect_analysis(submission.id, before_metrics)
    correction = _record_correction(
        submission.id,
        "continue_case_review_from_desensitized",
        case_id=case.id,
        reason_code="desensitized_review_continued",
        outcome_code=outcome_code,
        original_value=original_value,
        corrected_value={"status": "completed"},
        analysis=analysis,
        note=note,
        corrected_by=corrected_by,
    )
    save_submission_graph(submission.id)
    log_event(
        "continue_case_review_from_desensitized",
        {"submission_id": submission.id, "case_id": case.id, "corrected_by": corrected_by},
    )
    return {
        "correction": correction.to_dict(),
        "case": rebuilt["case"],
        "review_result": rebuilt["review_result"],
        "report": rebuilt["report"],
    }


def upload_desensitized_package(
    submission_id: str,
    package_path: str | Path,
    corrected_by: str = "local",
    note: str = "",
) -> dict:
    submission = store.submissions.get(submission_id)
    if not submission:
        raise ValueError(f"Submission not found: {submission_id}")

    archive_path = Path(package_path)
    if archive_path.suffix.lower() != ".zip":
        raise ValueError("Desensitized package must be a zip file")
    if not archive_path.exists():
        raise ValueError(f"Desensitized package not found: {archive_path}")

    before_metrics = _submission_metrics(submission.id)
    matched_materials: list[str] = []
    with zipfile.ZipFile(archive_path, "r") as archive:
        names = set(archive.namelist())
        for material_id in submission.material_ids:
            material = store.materials.get(material_id)
            parse_result = store.parse_results.get(material_id)
            if not material or not parse_result:
                continue
            matched_name = next(
                (candidate for candidate in _desensitized_entry_candidates(material.id, material.original_filename) if candidate in names),
                "",
            )
            if not matched_name:
                continue
            text = archive.read(matched_name).decode("utf-8", errors="ignore")
            Path(parse_result.desensitized_text_path).write_text(text, encoding="utf-8")
            material.content = text
            material.metadata = {
                **material.metadata,
                "desensitized_upload": {
                    "file_name": archive_path.name,
                    "matched_entry": matched_name,
                    "uploaded_by": corrected_by,
                    "uploaded_at": now_iso(),
                    "note": note,
                },
            }
            matched_materials.append(material.id)

    if not matched_materials:
        raise ValueError("No desensitized artifacts in the zip matched this submission")

    original_stage = getattr(submission, "review_stage", "desensitized_ready")
    for case_id in submission.case_ids:
        case = store.cases.get(case_id)
        if case and case.status == "awaiting_manual_review":
            case.review_stage = "desensitized_uploaded"

    submission.review_stage = "desensitized_uploaded"
    _sync_submission_status(submission.id)
    outcome_code, analysis = _effect_analysis(submission.id, before_metrics)
    correction = _record_correction(
        submission.id,
        "upload_desensitized_package",
        reason_code="desensitized_package_uploaded",
        outcome_code=outcome_code,
        original_value={"review_stage": original_stage},
        corrected_value={"review_stage": "desensitized_uploaded", "matched_material_ids": matched_materials},
        analysis=analysis,
        note=note or archive_path.name,
        corrected_by=corrected_by,
    )
    save_submission_graph(submission.id)
    log_event(
        "upload_desensitized_package",
        {"submission_id": submission.id, "matched_material_count": len(matched_materials), "corrected_by": corrected_by},
    )
    return {"correction": correction.to_dict(), "matched_material_ids": matched_materials, "submission": submission.to_dict()}


def update_submission_internal_state(
    submission_id: str,
    *,
    owner: str = "",
    internal_status: str = "",
    next_step: str = "",
    note: str = "",
    updated_by: str = "operator_ui",
) -> dict:
    submission = store.submissions.get(submission_id)
    if not submission:
        raise ValueError(f"Submission not found: {submission_id}")

    allowed_statuses = {
        "unassigned",
        "in_review",
        "waiting_materials",
        "fixing",
        "ready_to_deliver",
        "delivered",
        "blocked",
    }
    normalized_status = str(internal_status or "unassigned").strip() or "unassigned"
    if normalized_status not in allowed_statuses:
        normalized_status = "unassigned"

    original_value = {
        "internal_owner": getattr(submission, "internal_owner", ""),
        "internal_status": getattr(submission, "internal_status", "unassigned"),
        "internal_next_step": getattr(submission, "internal_next_step", ""),
        "internal_note": getattr(submission, "internal_note", ""),
    }
    updated_at = now_iso()
    submission.internal_owner = str(owner or "").strip()[:80]
    submission.internal_status = normalized_status
    submission.internal_next_step = str(next_step or "").strip()[:240]
    submission.internal_note = str(note or "").strip()[:500]
    submission.internal_updated_by = str(updated_by or "operator_ui").strip()[:80]
    submission.internal_updated_at = updated_at

    corrected_value = {
        "internal_owner": submission.internal_owner,
        "internal_status": submission.internal_status,
        "internal_next_step": submission.internal_next_step,
        "internal_note": submission.internal_note,
        "internal_updated_by": submission.internal_updated_by,
        "internal_updated_at": submission.internal_updated_at,
    }
    correction = _record_correction(
        submission_id,
        "update_internal_state",
        original_value=original_value,
        corrected_value=corrected_value,
        note=note or next_step or "更新内部处理状态",
        corrected_by=updated_by,
    )
    save_submission_graph(submission_id)
    log_event(
        "update_submission_internal_state",
        {"submission_id": submission_id, "internal_status": normalized_status, "owner": submission.internal_owner, "by": updated_by},
    )
    return {"submission": submission.to_dict(), "correction": correction.to_dict()}
