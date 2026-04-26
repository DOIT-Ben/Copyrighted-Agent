from __future__ import annotations

import json
from pathlib import Path

from app.core.domain.enums import MaterialType, ReviewStrategy, SubmissionMode
from app.core.domain.models import Case, Job, Material, ParseResult, ReportArtifact, ReviewResult, Submission
from app.core.parsers.service import parse_material
from app.core.privacy.desensitization import build_ai_safe_case_payload
from app.core.reports.renderers import (
    render_batch_report_markdown,
    render_case_report_markdown,
    render_material_report_markdown,
)
from app.core.reviewers.ai.service import generate_case_ai_review, resolve_case_ai_provider
from app.core.services.app_config import load_app_config
from app.core.reviewers.rules.agreement import review_agreement_text
from app.core.reviewers.rules.cross_material import review_case_consistency
from app.core.reviewers.rules.document import review_document_text
from app.core.reviewers.rules.info_form import review_info_form_text
from app.core.reviewers.rules.online_filing import review_online_filing_payload
from app.core.reviewers.rules.source_code import review_source_code_text
from app.core.services.app_logging import log_event
from app.core.services.evidence_anchors import attach_issue_evidence_anchors
from app.core.services.input_intake import stage_directory_input
from app.core.services.material_classifier import classify_material
from app.core.services.online_filing import normalize_online_filing
from app.core.services.review_dimensions import build_case_review_dimensions
from app.core.services.review_profile import normalize_review_profile
from app.core.services.sqlite_repository import save_submission_graph
from app.core.services.runtime_store import store
from app.core.services.zip_ingestion import safe_extract_zip
from app.core.utils.text import ensure_dir, now_iso, slug_id, summarize_severity


ALLOWED_FILE_SUFFIXES = {".doc", ".docx", ".pdf", ".txt", ".md"}


def _runtime_root() -> Path:
    return ensure_dir(Path(load_app_config().data_root))


def _write_text(path: Path, content: str) -> Path:
    ensure_dir(path.parent)
    path.write_text(content, encoding="utf-8")
    return path


def _update_job(
    job: Job,
    *,
    status: str | None = None,
    progress: int | None = None,
    stage: str | None = None,
    detail: str | None = None,
    finished: bool = False,
    persist_submission_id: str = "",
) -> None:
    if status is not None:
        job.status = status
    if progress is not None:
        job.progress = progress
    if stage is not None:
        job.stage = stage
    if detail is not None:
        job.detail = detail
    if finished:
        job.finished_at = now_iso()
    if persist_submission_id:
        save_submission_graph(persist_submission_id)


def _prepare_input_source(source_path: Path, submission_dir: Path) -> tuple[str, list[Path]]:
    extracted_dir = submission_dir / "extracted"
    if source_path.is_dir():
        staged_files = stage_directory_input(source_path, extracted_dir)
        return str(extracted_dir), staged_files
    if source_path.suffix.lower() != ".zip":
        raise ValueError(f"Unsupported input source: {source_path}")
    archive_target = submission_dir / source_path.name
    archive_target.write_bytes(source_path.read_bytes())
    return str(archive_target), safe_extract_zip(archive_target, extracted_dir)


def _review_by_material_type(material_type: str, text: str) -> dict:
    if material_type == MaterialType.AGREEMENT.value:
        return review_agreement_text(text)
    if material_type == MaterialType.SOFTWARE_DOC.value:
        return review_document_text(text)
    if material_type == MaterialType.SOURCE_CODE.value:
        return review_source_code_text(text)
    if material_type == MaterialType.INFO_FORM.value:
        return review_info_form_text(text)
    return {"issues": []}


def _build_case_ai_payload(case: Case, case_materials: list[Material]) -> dict:
    material_type_counts: dict[str, int] = {}
    material_inventory: list[dict[str, str]] = []
    for material in case_materials:
        material_type_counts[material.material_type] = material_type_counts.get(material.material_type, 0) + 1
        parse_quality = dict(material.metadata.get("parse_quality") or {})
        triage = dict(material.metadata.get("triage") or {})
        material_inventory.append(
            {
                "material_type": material.material_type,
                "file_ext": material.file_ext,
                "parse_status": material.parse_status,
                "review_status": material.review_status,
                "quality_level": str(parse_quality.get("quality_level", "") or ""),
                "quality_reason_code": str(
                    triage.get("quality_review_reason_code")
                    or parse_quality.get("review_reason_code")
                    or parse_quality.get("quality_reason")
                    or ""
                ),
                "legacy_doc_bucket": str(parse_quality.get("legacy_doc_bucket", "") or ""),
            }
        )
    return {
        "software_name": case.software_name,
        "version": case.version,
        "company_name": case.company_name,
        "online_filing": normalize_online_filing(getattr(case, "online_filing", {}) or {}),
        "material_count": len(case_materials),
        "material_type_counts": material_type_counts,
        "material_inventory": material_inventory,
    }


def _collect_case_issues(materials: list[Material], consistency_issues: list[dict]) -> list[dict]:
    combined: list[dict] = [dict(item) for item in list(consistency_issues or [])]
    for material in materials:
        for issue in list(material.issues or []):
            payload = dict(issue or {})
            payload.setdefault("material_id", material.id)
            payload.setdefault("material_name", material.original_filename)
            payload.setdefault("material_type", material.material_type)
            combined.append(payload)
    return combined


def _select_classification(first_pass: dict, second_pass: dict | None, parse_quality: dict) -> dict:
    selected = dict(first_pass)

    if not parse_quality.get("is_text_usable", False):
        if second_pass and second_pass.get("material_type") != MaterialType.UNKNOWN.value:
            return {
                "material_type": MaterialType.UNKNOWN.value,
                "confidence": 0.0,
                "reason": "low_quality_content_blocked",
            }
        if selected.get("reason") == "content":
            return {
                "material_type": MaterialType.UNKNOWN.value,
                "confidence": 0.0,
                "reason": "low_quality_content_blocked",
            }
        return selected

    if not second_pass:
        return selected

    if second_pass.get("material_type") != MaterialType.UNKNOWN.value:
        if selected.get("material_type") == MaterialType.UNKNOWN.value:
            return dict(second_pass)
        if float(second_pass.get("confidence", 0.0)) >= float(selected.get("confidence", 0.0)):
            return dict(second_pass)

    return selected


def _unknown_reason(classification: dict, parse_quality: dict) -> str:
    if classification.get("material_type") != MaterialType.UNKNOWN.value:
        return ""
    if classification.get("reason") == "low_quality_content_blocked":
        return "blocked_low_quality_content_signal"
    if not parse_quality.get("is_text_usable", False):
        if "ole_binary_header" in parse_quality.get("quality_flags", []):
            return "binary_doc_parse_failed"
        return str(parse_quality.get("quality_reason", "text_not_usable"))
    return "no_matching_rule"


def _build_triage(classification: dict, parse_quality: dict) -> dict:
    unknown_reason = _unknown_reason(classification, parse_quality)
    needs_manual_review = bool(
        classification.get("material_type") == MaterialType.UNKNOWN.value
        or parse_quality.get("quality_level") == "low"
        or float(classification.get("confidence", 0.0)) < 0.85
    )
    return {
        "needs_manual_review": needs_manual_review,
        "unknown_reason": unknown_reason,
        "quality_review_reason_code": parse_quality.get("review_reason_code", ""),
        "quality_review_reason_label": parse_quality.get("review_reason_label", ""),
        "legacy_doc_bucket": parse_quality.get("legacy_doc_bucket", ""),
        "legacy_doc_bucket_label": parse_quality.get("legacy_doc_bucket_label", ""),
        "review_recommendation": "manual_triage" if needs_manual_review else "auto_ok",
    }


def _build_case_review_record(
    case: Case,
    case_materials: list[Material],
    combined_issues: list[dict],
    ai_review: dict,
    review_profile: dict,
) -> dict:
    rule_conclusion = str(ai_review.get("rule_summary") or ai_review.get("conclusion") or "").strip()
    ai_summary = str(ai_review.get("ai_note") or ai_review.get("summary") or "").strip()
    review_dimensions = build_case_review_dimensions(
        case,
        case_materials,
        cross_material_issues=combined_issues,
        ai_resolution=str(ai_review.get("resolution", "explicit_mock") or ""),
        review_profile=review_profile,
    )
    report_payload = {
        "case_name": case.case_name,
        "materials": [],
        "cross_material_issues": combined_issues,
        "review_dimensions": review_dimensions,
        "review_profile": dict(review_profile),
        "rule_conclusion": rule_conclusion or "规则引擎未返回额外结论",
        "ai_summary": ai_summary or "当前没有额外 AI 补充说明",
        "ai_provider": ai_review.get("provider", "mock"),
        "ai_resolution": ai_review.get("resolution", "explicit_mock"),
    }
    review_payload = {
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
    }
    return {"report_payload": report_payload, "review_payload": review_payload}


def ingest_submission(
    zip_path: str | Path,
    mode: str,
    created_by: str = "local",
    review_strategy: str = ReviewStrategy.AUTO_REVIEW.value,
    review_profile: dict | None = None,
    *,
    submission_id: str = "",
    job_id: str = "",
) -> dict:
    source_path = Path(zip_path)
    if mode not in {item.value for item in SubmissionMode}:
        raise ValueError(f"Unsupported submission mode: {mode}")
    if review_strategy not in {item.value for item in ReviewStrategy}:
        raise ValueError(f"Unsupported review strategy: {review_strategy}")
    normalized_review_profile = normalize_review_profile(review_profile)
    log_event(
        "ingest_submission_started",
        {
            "source_path": str(source_path),
            "mode": mode,
            "created_by": created_by,
            "review_strategy": review_strategy,
            "review_profile": normalized_review_profile,
        },
    )

    runtime_root = _runtime_root()
    submission_id = submission_id or slug_id("sub")
    submission_dir = ensure_dir(runtime_root / "submissions" / submission_id)
    job = store.jobs.get(job_id) if job_id else None
    if job:
        job.scope_id = submission_id
        _update_job(
            job,
            status="running",
            progress=6,
            stage="正在登记批次",
            detail="系统已接收文件，正在创建批次记录。",
        )
    else:
        job = Job(
            id=job_id or slug_id("job"),
            job_type="ingest_submission",
            scope_type="submission",
            scope_id=submission_id,
            status="running",
            progress=6,
            stage="正在登记批次",
            detail="系统已接收文件，正在创建批次记录。",
            started_at=now_iso(),
        )
        store.add_job(job)

    submission = Submission(
        id=submission_id,
        mode=mode,
        filename=source_path.name,
        storage_path=str(source_path),
        status="processing",
        created_at=now_iso(),
        review_strategy=review_strategy,
        review_stage="intake_processing",
        created_by=created_by,
        review_profile=normalized_review_profile,
    )
    store.add_submission(submission)
    _update_job(
        job,
        progress=12,
        stage="正在解压文件",
        detail="批次已创建，正在解压 ZIP 并识别可处理文件。",
        persist_submission_id=submission_id,
    )
    storage_path, extracted_files = _prepare_input_source(source_path, submission_dir)
    submission.storage_path = storage_path
    allowed_files = [item for item in sorted(extracted_files) if item.suffix.lower() in ALLOWED_FILE_SUFFIXES]
    _update_job(
        job,
        progress=18,
        stage="正在解析材料",
        detail=f"已发现 {len(allowed_files)} 份可处理材料，开始解析与分类。",
        persist_submission_id=submission_id,
    )

    materials: list[Material] = []
    parse_results: list[ParseResult] = []

    total_files = len(allowed_files)
    for index, file_path in enumerate(allowed_files, start=1):
        parse_progress = 18 if total_files <= 0 else min(64, 18 + round((index / total_files) * 46))
        _update_job(
            job,
            progress=parse_progress,
            stage="正在解析材料",
            detail=f"正在处理第 {index}/{total_files} 份材料：{file_path.name}",
            persist_submission_id=submission_id,
        )
        parse_hint = file_path.read_text(encoding="utf-8", errors="ignore") if file_path.suffix.lower() in {".txt", ".md"} else ""
        first_pass_classification = classify_material(file_name=file_path.name, content=parse_hint, directory_hint=file_path.parent.name)
        parsed = parse_material(file_path=file_path, material_type=first_pass_classification["material_type"])
        second_pass_classification: dict | None = None
        if first_pass_classification["material_type"] == MaterialType.UNKNOWN.value or first_pass_classification.get("confidence", 0.0) < 0.9:
            second_pass_classification = classify_material(
                file_name=file_path.name,
                content=parsed["clean_text"],
                directory_hint=file_path.parent.name,
            )
        classification = _select_classification(
            first_pass=first_pass_classification,
            second_pass=second_pass_classification,
            parse_quality=parsed["quality"],
        )
        review = _review_by_material_type(classification["material_type"], parsed["clean_text"])
        review["issues"] = attach_issue_evidence_anchors(review.get("issues", []), parsed["desensitized_text"])
        review_metadata = dict(review.get("metadata", {}) or {})
        triage = _build_triage(classification, parsed["quality"])
        material_metadata = {
            **parsed["metadata"],
            **review_metadata,
            "classification": {
                **classification,
                "first_pass_result": first_pass_classification["material_type"],
                "second_pass_result": (
                    second_pass_classification["material_type"] if second_pass_classification else first_pass_classification["material_type"]
                ),
                "first_pass_reason": first_pass_classification.get("reason", ""),
                "second_pass_reason": second_pass_classification.get("reason", "") if second_pass_classification else "",
                "selected_result": classification["material_type"],
            },
            "privacy": parsed["privacy"]["summary"],
            "triage": triage,
        }

        material = Material(
            id=slug_id("mat"),
            case_id=None,
            submission_id=submission_id,
            material_type=classification["material_type"],
            original_filename=file_path.name,
            storage_path=str(file_path),
            file_ext=file_path.suffix.lower(),
            parse_status="completed",
            review_status="completed",
            detected_software_name=parsed["metadata"].get("software_name", ""),
            detected_version=parsed["metadata"].get("version", ""),
            content=parsed["desensitized_text"],
            metadata=material_metadata,
            issues=review.get("issues", []),
        )
        store.add_material(material)
        submission.material_ids.append(material.id)
        materials.append(material)

        parse_dir = ensure_dir(submission_dir / "parsed" / material.id)
        privacy_manifest = {
            **parsed["privacy"],
            "material_id": material.id,
            "material_type": material.material_type,
            "original_filename": material.original_filename,
        }
        parse_result = ParseResult(
            material_id=material.id,
            raw_text_path=str(_write_text(parse_dir / "raw.txt", parsed["raw_text"])),
            clean_text_path=str(_write_text(parse_dir / "clean.txt", parsed["clean_text"])),
            desensitized_text_path=str(_write_text(parse_dir / "desensitized.txt", parsed["desensitized_text"])),
            privacy_manifest_path=str(
                _write_text(parse_dir / "privacy.json", json.dumps(privacy_manifest, ensure_ascii=False, indent=2))
            ),
            metadata_json=material_metadata,
            parser_name=parsed["parser_name"],
        )
        store.add_parse_result(parse_result)
        parse_results.append(parse_result)

        material_report_content = render_material_report_markdown(
            {
                "material_name": material.original_filename,
                "material_type": material.material_type,
                "issues": material.issues,
                "parse_quality": parsed["quality"],
                "triage": triage,
            }
        )
        report_artifact = ReportArtifact(
            id=slug_id("rep"),
            scope_type="material",
            scope_id=material.id,
            report_type="material_markdown",
            file_format="md",
            storage_path=str(_write_text(submission_dir / "reports" / f"{material.id}.md", material_report_content)),
            created_at=now_iso(),
            content=material_report_content,
        )
        store.add_report_artifact(report_artifact)
        material.report_id = report_artifact.id

    cases: list[Case] = []
    reports: list[ReportArtifact] = []
    review_results: list[ReviewResult] = []
    _update_job(
        job,
        progress=72,
        stage="正在整理项目",
        detail="材料解析完成，正在归并项目并准备生成审查结果。",
        persist_submission_id=submission_id,
    )

    if mode == SubmissionMode.SINGLE_CASE_PACKAGE.value:
        info_form = next((item for item in materials if item.material_type == MaterialType.INFO_FORM.value), None)
        source_code = next((item for item in materials if item.material_type == MaterialType.SOURCE_CODE.value), None)
        software_doc = next((item for item in materials if item.material_type == MaterialType.SOFTWARE_DOC.value), None)
        agreements = [item for item in materials if item.material_type == MaterialType.AGREEMENT.value]
        agreement = agreements[0] if agreements else None

        case_name = (
            (info_form.detected_software_name if info_form else "")
            or (software_doc.detected_software_name if software_doc else "")
            or (source_code.detected_software_name if source_code else "")
            or source_path.stem
        )
        case_version = (
            (info_form.detected_version if info_form else "")
            or (software_doc.detected_version if software_doc else "")
            or (source_code.detected_version if source_code else "")
        )
        company_name = (info_form.metadata.get("company_name") if info_form else "") or ""
        waiting_manual_review = review_strategy == ReviewStrategy.MANUAL_DESENSITIZED_REVIEW.value

        case = Case(
            id=slug_id("case"),
            case_name=case_name or "未命名软著项目",
            software_name=case_name or "未命名软著项目",
            version=case_version or "",
            company_name=company_name,
            status="awaiting_manual_review" if waiting_manual_review else "completed",
            source_submission_id=submission_id,
            created_at=now_iso(),
            material_ids=[item.id for item in materials],
            review_stage="desensitized_ready" if waiting_manual_review else "review_completed",
        )
        for item in materials:
            item.case_id = case.id
        store.add_case(case)
        submission.case_ids.append(case.id)
        cases.append(case)

        if waiting_manual_review:
            _update_job(
                job,
                progress=86,
                stage="正在生成脱敏交付",
                detail="已完成脱敏准备，等待人工确认后继续正式审查。",
                persist_submission_id=submission_id,
            )
            log_event(
                "submission_review_deferred",
                {"submission_id": submission.id, "case_id": case.id, "review_strategy": review_strategy},
            )
        else:
            _update_job(
                job,
                progress=86,
                stage="正在生成审查结果",
                detail="项目已归并完成，正在输出审查结论与报告。",
                persist_submission_id=submission_id,
            )
            consistency = review_case_consistency(
                info_form.metadata if info_form else {},
                source_code.metadata if source_code else {},
                software_doc.metadata if software_doc else {},
                agreement.metadata if agreement else {},
                normalize_online_filing(getattr(case, "online_filing", {}) or {}),
            )
            combined_issues = _collect_case_issues(materials, consistency.get("issues", []))
            combined_issues.extend(
                list(
                    review_online_filing_payload(
                        getattr(case, "online_filing", {}) or {},
                        case_payload=case.to_dict(),
                        info_form=info_form.metadata if info_form else {},
                        agreement=agreement.metadata if agreement else {},
                    ).get("issues", [])
                )
            )
            ai_provider = resolve_case_ai_provider()
            ai_case_payload = _build_case_ai_payload(case, materials)
            if ai_provider != "mock":
                ai_case_payload = build_ai_safe_case_payload(ai_case_payload)
            ai_review = generate_case_ai_review(
                ai_case_payload,
                {"issues": combined_issues},
                provider=ai_provider,
                review_profile=normalized_review_profile,
            )
            review_record = _build_case_review_record(
                case,
                materials,
                combined_issues,
                ai_review,
                normalized_review_profile,
            )
            review_result = ReviewResult(
                id=slug_id("rev"),
                scope_type="case",
                scope_id=case.id,
                reviewer_type="hybrid",
                severity_summary_json=review_record["review_payload"]["severity_summary_json"],
                issues_json=review_record["review_payload"]["issues_json"],
                score=review_record["review_payload"]["score"],
                conclusion=review_record["review_payload"]["conclusion"],
                created_at=now_iso(),
                rule_conclusion=review_record["review_payload"]["rule_conclusion"],
                ai_summary=review_record["review_payload"]["ai_summary"],
                ai_provider=review_record["review_payload"]["ai_provider"],
                ai_resolution=review_record["review_payload"]["ai_resolution"],
                review_profile_snapshot=review_record["review_payload"]["review_profile_snapshot"],
                prompt_snapshot_json=review_record["review_payload"]["prompt_snapshot_json"],
            )
            store.add_review_result(review_result)
            case.review_result_id = review_result.id
            review_results.append(review_result)

            case_report_payload = review_record["report_payload"]
            case_report_payload["materials"] = [
                item.original_filename for item in materials
            ] + [item.original_filename for item in agreements if item not in materials]
            case_report_content = render_case_report_markdown(case_report_payload)
            case_report = ReportArtifact(
                id=slug_id("rep"),
                scope_type="case",
                scope_id=case.id,
                report_type="case_markdown",
                file_format="md",
                storage_path=str(_write_text(submission_dir / "reports" / f"{case.id}.md", case_report_content)),
                created_at=now_iso(),
                content=case_report_content,
            )
            store.add_report_artifact(case_report)
            case.report_id = case_report.id
            submission.report_ids.append(case_report.id)
            reports.append(case_report)
    else:
        _update_job(
            job,
            progress=86,
            stage="正在生成批次报告",
            detail="批量归档已完成，正在整理材料汇总与批次报告。",
            persist_submission_id=submission_id,
        )
        groups: dict[tuple[str, str], list[Material]] = {}
        for material in materials:
            key = (material.detected_software_name, material.detected_version)
            if key == ("", ""):
                continue
            groups.setdefault(key, []).append(material)
        for (software_name, version), items in groups.items():
            case = Case(
                id=slug_id("case"),
                case_name=software_name or "批量归档项目",
                software_name=software_name or "批量归档项目",
                version=version,
                company_name="",
                status="grouped",
                source_submission_id=submission_id,
                created_at=now_iso(),
                material_ids=[item.id for item in items],
            )
            for item in items:
                item.case_id = case.id
            store.add_case(case)
            submission.case_ids.append(case.id)
            cases.append(case)

        batch_report_content = render_batch_report_markdown(
            {
                "submission_name": submission.filename,
                "material_type": materials[0].material_type if materials else "unknown",
                "items": [{"file_name": item.original_filename, "issues": item.issues} for item in materials],
            }
        )
        batch_report = ReportArtifact(
            id=slug_id("rep"),
            scope_type="submission",
            scope_id=submission.id,
            report_type="batch_markdown",
            file_format="md",
            storage_path=str(_write_text(submission_dir / "reports" / "batch.md", batch_report_content)),
            created_at=now_iso(),
            content=batch_report_content,
        )
        store.add_report_artifact(batch_report)
        submission.report_ids.append(batch_report.id)
        reports.append(batch_report)

    submission.status = (
        "awaiting_manual_review"
        if review_strategy == ReviewStrategy.MANUAL_DESENSITIZED_REVIEW.value and mode == SubmissionMode.SINGLE_CASE_PACKAGE.value
        else "completed"
    )
    submission.review_stage = (
        "desensitized_ready"
        if review_strategy == ReviewStrategy.MANUAL_DESENSITIZED_REVIEW.value and mode == SubmissionMode.SINGLE_CASE_PACKAGE.value
        else "review_completed"
    )
    _update_job(
        job,
        status="completed",
        progress=100,
        stage="结果已生成",
        detail=(
            "脱敏件已准备完成，可进入批次详情继续审查。"
            if review_strategy == ReviewStrategy.MANUAL_DESENSITIZED_REVIEW.value and mode == SubmissionMode.SINGLE_CASE_PACKAGE.value
            else "批次解析与审查已完成，正在进入结果页面。"
        ),
        finished=True,
    )
    save_submission_graph(submission.id)
    log_event(
        "ingest_submission_completed",
        {
            "submission_id": submission.id,
            "mode": submission.mode,
            "review_strategy": submission.review_strategy,
            "material_count": len(submission.material_ids),
            "case_count": len(submission.case_ids),
            "report_count": len(submission.report_ids),
        },
    )

    return {
        "submission": submission.to_dict(),
        "cases": [case.to_dict() for case in cases],
        "materials": [material.to_dict() for material in materials],
        "reports": [report.to_dict() for report in reports],
        "jobs": [job.to_dict()],
        "parse_results": [item.to_dict() for item in parse_results],
        "review_results": [item.to_dict() for item in review_results],
    }
