from __future__ import annotations

from pathlib import Path

from app.core.domain.enums import MaterialType
from app.core.domain.models import Case, Correction, ReportArtifact, ReviewResult
from app.core.privacy.desensitization import build_ai_safe_case_payload
from app.core.reports.renderers import render_case_report_markdown
from app.core.reviewers.ai.service import generate_case_ai_review, resolve_case_ai_provider
from app.core.reviewers.rules.cross_material import review_case_consistency
from app.core.reviewers.rules.document import review_document_text
from app.core.reviewers.rules.info_form import review_info_form_text
from app.core.reviewers.rules.source_code import review_source_code_text
from app.core.reviewers.rules.agreement import review_agreement_text
from app.core.services.app_config import load_app_config
from app.core.services.app_logging import log_event
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


def _record_correction(
    submission_id: str,
    correction_type: str,
    *,
    material_id: str = "",
    case_id: str = "",
    original_value: dict | None = None,
    corrected_value: dict | None = None,
    note: str = "",
    corrected_by: str = "local",
) -> Correction:
    correction = Correction(
        id=slug_id("cor"),
        submission_id=submission_id,
        correction_type=correction_type,
        material_id=material_id,
        case_id=case_id,
        original_value=original_value or {},
        corrected_value=corrected_value or {},
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


def _compose_case_review_payload(case: Case, combined_issues: list[dict], ai_review: dict) -> dict:
    rule_conclusion = str(ai_review.get("rule_summary") or ai_review.get("conclusion") or "").strip()
    ai_summary = str(ai_review.get("ai_note") or ai_review.get("summary") or "").strip()
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
        },
        "report": {
            "case_name": case.case_name,
            "materials": [],
            "cross_material_issues": combined_issues,
            "rule_conclusion": rule_conclusion or "规则引擎未返回额外结论",
            "ai_summary": ai_summary or "当前没有额外 AI 补充说明",
            "ai_provider": ai_review.get("provider", "mock"),
            "ai_resolution": ai_review.get("resolution", "explicit_mock"),
        },
    }


def _rebuild_case(case_id: str) -> dict:
    case, submission = _submission_for_case(case_id)
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

    consistency = review_case_consistency(
        info_form.metadata if info_form else {},
        source_code.metadata if source_code else {},
        software_doc.metadata if software_doc else {},
    )
    combined_issues = consistency.get("issues", [])
    ai_provider = resolve_case_ai_provider()
    ai_payload = {
        "software_name": case.software_name,
        "version": case.version,
        "company_name": case.company_name,
    }
    if ai_provider != "mock":
        ai_payload = build_ai_safe_case_payload(ai_payload)
    ai_review = generate_case_ai_review(ai_payload, {"issues": combined_issues}, provider=ai_provider)
    review_payload = _compose_case_review_payload(case, combined_issues, ai_review)

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

    correction = _record_correction(
        submission.id,
        "change_material_type",
        material_id=material.id,
        case_id=material.case_id or "",
        original_value=original_value,
        corrected_value={"material_type": new_material_type},
        note=note,
        corrected_by=corrected_by,
    )

    if material.case_id:
        _rebuild_case(material.case_id)
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

    original_case_id = material.case_id or ""
    if original_case_id and original_case_id in store.cases:
        original_case = store.cases[original_case_id]
        if material.id in original_case.material_ids:
            original_case.material_ids.remove(material.id)
        _remove_case_if_empty(original_case_id)

    if material.id not in case.material_ids:
        case.material_ids.append(material.id)
    material.case_id = case.id

    correction = _record_correction(
        submission.id,
        "assign_material_to_case",
        material_id=material.id,
        case_id=case.id,
        original_value={"case_id": original_case_id},
        corrected_value={"case_id": case.id},
        note=note,
        corrected_by=corrected_by,
    )

    rebuilt = _rebuild_case(case.id)
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

    correction = _record_correction(
        submission_id,
        "create_case_from_materials",
        case_id=new_case.id,
        original_value={"material_ids": []},
        corrected_value={"material_ids": list(material_ids), "case_name": new_case.case_name},
        note=note,
        corrected_by=corrected_by,
    )
    rebuilt = _rebuild_case(new_case.id)
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

    moved_materials = list(source_case.material_ids)
    for material_id in moved_materials:
        material = store.materials.get(material_id)
        if not material:
            continue
        material.case_id = target_case.id
        if material_id not in target_case.material_ids:
            target_case.material_ids.append(material_id)
    source_case.material_ids = []

    correction = _record_correction(
        submission.id,
        "merge_cases",
        case_id=target_case.id,
        original_value={"source_case_id": source_case.id, "target_case_id": target_case.id},
        corrected_value={"merged_case_id": source_case.id},
        note=note,
        corrected_by=corrected_by,
    )

    rebuilt = _rebuild_case(target_case.id)
    _remove_case_if_empty(source_case.id)
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


def rerun_case_review(case_id: str, corrected_by: str = "local", note: str = "") -> dict:
    case, submission = _submission_for_case(case_id)
    correction = _record_correction(
        submission.id,
        "rerun_case_review",
        case_id=case.id,
        original_value={"review_result_id": case.review_result_id},
        corrected_value={"review_result_id": case.review_result_id},
        note=note,
        corrected_by=corrected_by,
    )
    rebuilt = _rebuild_case(case.id)
    save_submission_graph(submission.id)
    log_event("rerun_case_review", {"submission_id": submission.id, "case_id": case.id, "corrected_by": corrected_by})
    return {
        "correction": correction.to_dict(),
        "case": rebuilt["case"],
        "review_result": rebuilt["review_result"],
        "report": rebuilt["report"],
    }
