from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from app.core.domain.enums import MaterialType, ReviewStrategy, SubmissionMode
from app.core.domain.models import Case, Material, ReportArtifact, ReviewResult, Submission
from app.core.reports.renderers import render_submission_global_review_markdown
from app.core.services.app_config import load_app_config
from app.core.services.runtime_store import store
from app.core.utils.text import ensure_dir, now_iso, slug_id, summarize_severity


CORE_SINGLE_CASE_TYPES = (
    MaterialType.INFO_FORM.value,
    MaterialType.SOURCE_CODE.value,
    MaterialType.SOFTWARE_DOC.value,
)

MATERIAL_TYPE_LABELS = {
    MaterialType.INFO_FORM.value: "信息采集表",
    MaterialType.SOURCE_CODE.value: "源代码",
    MaterialType.SOFTWARE_DOC.value: "软件说明文档",
    MaterialType.AGREEMENT.value: "协议/权属材料",
    MaterialType.UNKNOWN.value: "未识别材料",
}


def _issue(
    *,
    severity: str,
    category: str,
    rule_key: str,
    desc: str,
    suggestion: str,
    **extra: Any,
) -> dict[str, Any]:
    payload = {
        "severity": severity,
        "category": category,
        "rule_key": rule_key,
        "desc": desc,
        "suggestion": suggestion,
    }
    payload.update({key: value for key, value in extra.items() if value not in (None, "", [])})
    return payload


def _material_quality(material: Material) -> tuple[dict[str, Any], dict[str, Any]]:
    metadata = dict(material.metadata or {})
    parse_quality = dict(metadata.get("parse_quality") or {})
    triage = dict(metadata.get("triage") or {})
    return parse_quality, triage


def _identity_key(material: Material) -> tuple[str, str]:
    return (
        str(material.detected_software_name or "").strip(),
        str(material.detected_version or "").strip(),
    )


def _identity_label(key: tuple[str, str]) -> str:
    name, version = key
    if name and version:
        return f"{name} {version}"
    return name or version or "未提取名称/版本"


def _severity_counts(issues: list[dict[str, Any]]) -> dict[str, int]:
    counter = Counter(str(issue.get("severity", "minor") or "minor").lower() for issue in issues)
    return {
        "severe": int(counter.get("severe", 0)),
        "moderate": int(counter.get("moderate", 0)),
        "minor": int(counter.get("minor", 0)),
    }


def _review_status(issues: list[dict[str, Any]]) -> str:
    counts = _severity_counts(issues)
    if counts["severe"]:
        return "blocked"
    if counts["moderate"]:
        return "needs_review"
    return "ready"


def _score_from_issues(issues: list[dict[str, Any]]) -> float:
    counts = _severity_counts(issues)
    score = 100.0 - counts["severe"] * 18.0 - counts["moderate"] * 10.0 - counts["minor"] * 4.0
    return max(0.0, round(score, 2))


def _build_inventory(materials: list[Material]) -> dict[str, Any]:
    type_counts = Counter(material.material_type for material in materials)
    quality_counts: Counter[str] = Counter()
    manual_review_count = 0
    unknown_count = 0
    low_quality_count = 0
    files: list[dict[str, Any]] = []

    for material in materials:
        parse_quality, triage = _material_quality(material)
        quality_level = str(parse_quality.get("quality_level", "") or "unknown")
        quality_counts[quality_level] += 1
        needs_manual_review = bool(triage.get("needs_manual_review"))
        manual_review_count += 1 if needs_manual_review else 0
        unknown_count += 1 if material.material_type == MaterialType.UNKNOWN.value else 0
        low_quality_count += 1 if quality_level == "low" else 0
        files.append(
            {
                "id": material.id,
                "file_name": material.original_filename,
                "material_type": material.material_type,
                "material_type_label": MATERIAL_TYPE_LABELS.get(material.material_type, material.material_type),
                "detected_software_name": material.detected_software_name,
                "detected_version": material.detected_version,
                "quality_level": quality_level,
                "needs_manual_review": needs_manual_review,
                "issue_count": len(material.issues or []),
            }
        )

    return {
        "total": len(materials),
        "type_counts": dict(type_counts),
        "quality_counts": dict(quality_counts),
        "unknown_count": unknown_count,
        "low_quality_count": low_quality_count,
        "manual_review_count": manual_review_count,
        "files": files,
    }


def _material_quality_issues(materials: list[Material]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for material in materials:
        parse_quality, triage = _material_quality(material)
        if material.material_type == MaterialType.UNKNOWN.value:
            issues.append(
                _issue(
                    severity="severe",
                    category="材料识别",
                    rule_key="submission_unknown_material",
                    desc=f"{material.original_filename} 未能稳定识别材料类型。",
                    suggestion="先人工确认材料类型，必要时重新上传命名清晰、可解析的文件。",
                    material_id=material.id,
                    material_name=material.original_filename,
                    material_type=material.material_type,
                    unknown_reason=triage.get("unknown_reason", ""),
                )
            )
        if parse_quality.get("quality_level") == "low":
            issues.append(
                _issue(
                    severity="severe",
                    category="解析质量",
                    rule_key="submission_low_quality_material",
                    desc=f"{material.original_filename} 的解析质量较低，整包结论可能不可靠。",
                    suggestion="补充可复制文本版 PDF/DOCX，或先完成人工复核后再出具最终结论。",
                    material_id=material.id,
                    material_name=material.original_filename,
                    material_type=material.material_type,
                    quality_reason=parse_quality.get("review_reason_code") or parse_quality.get("quality_reason", ""),
                )
            )
        elif triage.get("needs_manual_review"):
            issues.append(
                _issue(
                    severity="moderate",
                    category="人工复核",
                    rule_key="submission_manual_review_material",
                    desc=f"{material.original_filename} 需要人工确认后再纳入最终判断。",
                    suggestion="优先处理待复核队列，确认类型、解析质量和归属项目。",
                    material_id=material.id,
                    material_name=material.original_filename,
                    material_type=material.material_type,
                    manual_review_reason=triage.get("manual_review_reason_code", ""),
                )
            )
    return issues


def _single_case_issues(materials: list[Material]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    type_counts = Counter(material.material_type for material in materials)

    for material_type in CORE_SINGLE_CASE_TYPES:
        if type_counts.get(material_type, 0):
            continue
        label = MATERIAL_TYPE_LABELS.get(material_type, material_type)
        issues.append(
            _issue(
                severity="severe",
                category="材料完整性",
                rule_key=f"submission_missing_{material_type}",
                desc=f"单案压缩包缺少核心材料：{label}。",
                suggestion="补齐核心材料后再提交审查，否则无法形成完整软著申报判断。",
                material_type=material_type,
            )
        )

    if not type_counts.get(MaterialType.AGREEMENT.value, 0):
        issues.append(
            _issue(
                severity="minor",
                category="权属材料",
                rule_key="submission_missing_agreement_optional",
                desc="未发现协议/权属材料，若申报场景涉及合作开发、委托开发或转让，可能缺少权属依据。",
                suggestion="确认开发方式；如涉及多主体或非原创独立开发，建议补充相应协议材料。",
                material_type=MaterialType.AGREEMENT.value,
            )
        )

    for material_type, count in sorted(type_counts.items()):
        if material_type == MaterialType.UNKNOWN.value or count <= 1:
            continue
        label = MATERIAL_TYPE_LABELS.get(material_type, material_type)
        issues.append(
            _issue(
                severity="moderate",
                category="材料归并",
                rule_key="submission_duplicate_material_type",
                desc=f"单案压缩包内发现 {count} 份{label}，当前案件审查可能只以首个同类材料作为主材料。",
                suggestion="确认是否为补充件、重复件或误放材料；必要时拆包或标记主材料。",
                material_type=material_type,
                count=count,
            )
        )

    identity_groups: dict[tuple[str, str], list[Material]] = defaultdict(list)
    for material in materials:
        key = _identity_key(material)
        if key != ("", ""):
            identity_groups[key].append(material)
    if len(identity_groups) > 1:
        groups = [
            {
                "identity": _identity_label(key),
                "material_names": [item.original_filename for item in items],
            }
            for key, items in identity_groups.items()
        ]
        issues.append(
            _issue(
                severity="moderate",
                category="整包一致性",
                rule_key="submission_mixed_identity_groups",
                desc="单案压缩包中提取到多个软件名称/版本组合，可能混入了不同项目材料。",
                suggestion="按软件名称和版本重新核对材料归属；不同项目建议拆成独立压缩包。",
                groups=groups,
            )
        )

    return issues


def _batch_issues(materials: list[Material], cases: list[Case]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    grouped_material_ids = {material_id for case in cases for material_id in case.material_ids}
    ungrouped = [material for material in materials if material.id not in grouped_material_ids]
    if materials and not cases:
        issues.append(
            _issue(
                severity="severe",
                category="批量分组",
                rule_key="submission_batch_no_groups",
                desc="批量材料未形成任何项目分组，系统无法按软件名称/版本输出整包清单。",
                suggestion="检查文件名、首页标题或材料内容中的软件名称与版本号是否可提取。",
            )
        )
    if ungrouped:
        issues.append(
            _issue(
                severity="severe",
                category="批量分组",
                rule_key="submission_batch_ungrouped_materials",
                desc=f"有 {len(ungrouped)} 份材料未能归入任何软件名称/版本分组。",
                suggestion="先人工确认未分组材料所属项目，避免批量申报漏项或串项。",
                material_names=[material.original_filename for material in ungrouped],
            )
        )

    group_sizes = [len(case.material_ids) for case in cases]
    if cases and any(size > 1 for size in group_sizes):
        duplicate_groups = [
            {"case_name": case.case_name, "version": case.version, "material_count": len(case.material_ids)}
            for case in cases
            if len(case.material_ids) > 1
        ]
        issues.append(
            _issue(
                severity="minor",
                category="批量分组",
                rule_key="submission_batch_multi_material_groups",
                desc="批量同类材料模式下，部分项目分组包含多份材料。",
                suggestion="确认这些材料是否确实属于同一软件版本，避免将同名不同项目合并。",
                groups=duplicate_groups,
            )
        )
    return issues


def _case_review_issues(review_results: list[ReviewResult]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    case_results = [item for item in review_results if item.scope_type == "case"]
    severe_case_count = 0
    moderate_case_count = 0
    for result in case_results:
        counts = _severity_counts(list(result.issues_json or []))
        severe_case_count += 1 if counts["severe"] else 0
        moderate_case_count += 1 if counts["moderate"] and not counts["severe"] else 0
    if severe_case_count:
        issues.append(
            _issue(
                severity="severe",
                category="案件审查",
                rule_key="submission_case_blockers_present",
                desc=f"已有 {severe_case_count} 个项目存在退回级审查问题。",
                suggestion="先处理项目报告中的退回级问题，再判断整包是否可交付。",
                case_count=severe_case_count,
            )
        )
    if moderate_case_count:
        issues.append(
            _issue(
                severity="moderate",
                category="案件审查",
                rule_key="submission_case_warnings_present",
                desc=f"已有 {moderate_case_count} 个项目存在需关注审查问题。",
                suggestion="结合业务场景确认是否需要补正，避免弱智问题进入最终申报材料。",
                case_count=moderate_case_count,
            )
        )
    return issues


def build_submission_global_review(
    submission: Submission,
    materials: list[Material],
    cases: list[Case],
    review_results: list[ReviewResult],
    *,
    mode: str,
    review_strategy: str,
) -> dict[str, Any]:
    """Build a deterministic submission-level review over the whole package."""

    issues: list[dict[str, Any]] = []
    inventory = _build_inventory(materials)

    if not materials:
        issues.append(
            _issue(
                severity="severe",
                category="材料完整性",
                rule_key="submission_no_processable_materials",
                desc="压缩包内没有可处理的软著材料。",
                suggestion="请上传包含 DOC/DOCX/PDF/TXT/MD 的材料包，并确认文件未损坏。",
            )
        )

    issues.extend(_material_quality_issues(materials))

    if mode == SubmissionMode.SINGLE_CASE_PACKAGE.value:
        issues.extend(_single_case_issues(materials))
    elif mode == SubmissionMode.BATCH_SAME_MATERIAL.value:
        issues.extend(_batch_issues(materials, cases))

    if review_strategy == ReviewStrategy.MANUAL_DESENSITIZED_REVIEW.value:
        issues.append(
            _issue(
                severity="moderate",
                category="审查阶段",
                rule_key="submission_waiting_manual_desensitized_review",
                desc="当前批次采用先脱敏后继续审查策略，尚未形成最终业务结论。",
                suggestion="先确认脱敏交付件，再继续正式审查并刷新全局结论。",
            )
        )

    issues.extend(_case_review_issues(review_results))

    status = _review_status(issues)
    severity_counts = _severity_counts(issues)
    score = _score_from_issues(issues)
    if status == "ready":
        summary = "整包材料结构稳定，未发现阻断提交的全局问题。"
    elif status == "needs_review":
        summary = "整包基本可审，但仍存在需要人工确认的全局风险。"
    else:
        summary = "整包存在阻断性问题，建议先补齐、拆分或人工复核后再提交。"

    return {
        "schema_version": 1,
        "submission_id": submission.id,
        "mode": mode,
        "review_strategy": review_strategy,
        "status": status,
        "score": score,
        "summary": summary,
        "severity_counts": severity_counts,
        "issue_count": len(issues),
        "issues": issues,
        "material_inventory": inventory,
        "case_inventory": {
            "total": len(cases),
            "items": [
                {
                    "id": case.id,
                    "case_name": case.case_name,
                    "software_name": case.software_name,
                    "version": case.version,
                    "material_count": len(case.material_ids),
                    "status": case.status,
                }
                for case in cases
            ],
        },
    }


def _submission_runtime_dir(submission_id: str) -> Path:
    submission = store.submissions.get(submission_id)
    if submission:
        for material_id in submission.material_ids:
            parse_result = store.parse_results.get(material_id)
            if parse_result and getattr(parse_result, "raw_text_path", ""):
                return Path(parse_result.raw_text_path).resolve().parents[2]
    return ensure_dir(Path(load_app_config().data_root) / "submissions" / submission_id)


def _should_write_global_report(submission: Submission) -> bool:
    return not (
        submission.review_strategy == ReviewStrategy.MANUAL_DESENSITIZED_REVIEW.value
        and submission.status == "awaiting_manual_review"
    )


def upsert_submission_global_review(submission_id: str, *, write_report: bool | None = None) -> dict[str, Any]:
    submission = store.submissions.get(submission_id)
    if not submission:
        raise ValueError(f"Submission not found: {submission_id}")

    materials = [store.materials[item_id] for item_id in submission.material_ids if item_id in store.materials]
    cases = [store.cases[item_id] for item_id in submission.case_ids if item_id in store.cases]
    review_results = [
        item
        for item in store.review_results.values()
        if item.scope_type == "case" and item.scope_id in {case.id for case in cases}
    ]
    global_review = build_submission_global_review(
        submission,
        materials,
        cases,
        review_results,
        mode=submission.mode,
        review_strategy=submission.review_strategy,
    )

    profile = dict(submission.review_profile or {})
    previous = dict(profile.get("submission_global_review", {}) or {})
    review_result_id = str(previous.get("review_result_id", "") or "")
    if review_result_id and review_result_id in store.review_results:
        review_result = store.review_results[review_result_id]
        review_result.reviewer_type = "global_rules"
        review_result.severity_summary_json = summarize_severity(global_review["issues"])
        review_result.issues_json = global_review["issues"]
        review_result.score = global_review["score"]
        review_result.conclusion = global_review["summary"]
        review_result.created_at = now_iso()
        review_result.rule_conclusion = global_review["summary"]
        review_result.ai_summary = ""
        review_result.ai_provider = "rules"
        review_result.ai_resolution = "not_applicable"
        review_result.review_profile_snapshot = dict(profile)
        review_result.prompt_snapshot_json = {}
    else:
        review_result = ReviewResult(
            id=slug_id("rev"),
            scope_type="submission",
            scope_id=submission.id,
            reviewer_type="global_rules",
            severity_summary_json=summarize_severity(global_review["issues"]),
            issues_json=global_review["issues"],
            score=global_review["score"],
            conclusion=global_review["summary"],
            created_at=now_iso(),
            rule_conclusion=global_review["summary"],
            ai_summary="",
            ai_provider="rules",
            ai_resolution="not_applicable",
            review_profile_snapshot=dict(profile),
            prompt_snapshot_json={},
        )
        store.add_review_result(review_result)
    global_review["review_result_id"] = review_result.id

    should_write_report = _should_write_global_report(submission) if write_report is None else bool(write_report)
    if should_write_report:
        report_content = render_submission_global_review_markdown(global_review)
        report_id = str(previous.get("report_id", "") or "")
        if report_id and report_id in store.report_artifacts:
            report = store.report_artifacts[report_id]
            report.storage_path = str(_submission_runtime_dir(submission.id) / "reports" / "submission_global_review.md")
            report.content = report_content
            report.created_at = now_iso()
        else:
            report = ReportArtifact(
                id=slug_id("rep"),
                scope_type="submission",
                scope_id=submission.id,
                report_type="submission_global_review_markdown",
                file_format="md",
                storage_path=str(_submission_runtime_dir(submission.id) / "reports" / "submission_global_review.md"),
                created_at=now_iso(),
                content=report_content,
            )
            store.add_report_artifact(report)
        ensure_dir(Path(report.storage_path).parent)
        Path(report.storage_path).write_text(report.content, encoding="utf-8")
        if report.id not in submission.report_ids:
            submission.report_ids.append(report.id)
        global_review["report_id"] = report.id
    elif previous.get("report_id"):
        global_review["report_id"] = previous.get("report_id")

    profile["submission_global_review"] = global_review
    submission.review_profile = profile
    return global_review


__all__ = ["build_submission_global_review", "upsert_submission_global_review"]
