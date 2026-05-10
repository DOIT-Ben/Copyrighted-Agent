from __future__ import annotations

from urllib.parse import urlencode, urlsplit

from fastapi import HTTPException

from app.core.services.runtime_store import store
from app.core.services.submission_insights import parse_diagnostic_snapshot, submission_quality_snapshot

SUBMISSION_NOTICE_MAP = {
    "job_retried": {
        "title": "任务已重新发起",
        "message": "系统已经基于原始上传文件重新创建处理任务，可继续查看新的批次详情。",
        "tone": "success",
        "icon_name": "refresh",
        "meta": ["已生成新任务", "可继续跟踪处理链路"],
    },
    "internal_state_updated": {
        "title": "内部处理状态已更新",
        "message": "负责人、内部状态和下一步备注已经保存，批次页面已刷新。",
        "tone": "success",
        "icon_name": "wrench",
        "meta": ["内部状态已保存", "操作已留痕"],
    },
    "material_type_updated": {
        "title": "材料类型已更新",
        "message": "选中的材料类型已经完成修正，相关留痕已写入更正审计。",
        "tone": "success",
        "icon_name": "check",
        "meta": ["已记录留痕", "批次页面已刷新"],
    },
    "material_assigned": {
        "title": "材料已归入项目",
        "message": "选中的材料已移动到目标项目，项目分组结果已刷新。",
        "tone": "success",
        "icon_name": "merge",
        "meta": ["项目分组已更新", "人工操作已留痕"],
    },
    "case_created": {
        "title": "新项目已创建",
        "message": "系统已基于选中的材料创建新项目。",
        "tone": "success",
        "icon_name": "lock",
        "meta": ["项目分组已更新", "审查链路已保留"],
    },
    "cases_merged": {
        "title": "项目已合并",
        "message": "源项目已并入目标项目，当前批次页已呈现新的聚合结果。",
        "tone": "success",
        "icon_name": "merge",
        "meta": ["分组结果已更新", "审计链路已保留"],
    },
    "case_review_rerun": {
        "title": "项目审查已重跑",
        "message": "选中的项目已重新审查，新的报告和 AI 信号会同步显示。",
        "tone": "info",
        "icon_name": "refresh",
        "meta": ["审查结果已刷新", "导出中心可能更新"],
    },
    "case_review_continued": {
        "title": "脱敏后继续审查已启动",
        "message": "系统已基于脱敏产物继续完成项目审查，报告和结果已刷新。",
        "tone": "success",
        "icon_name": "check",
        "meta": ["脱敏流程已闭环", "可立即查看报告"],
    },
    "desensitized_package_uploaded": {
        "title": "脱敏包已导入",
        "message": "系统已接收你上传的脱敏包，当前批次可继续进入正式审查。",
        "tone": "success",
        "icon_name": "upload",
        "meta": ["脱敏文件已回传", "可进入下一步审查"],
    },
}


def submission_notice_payload(code: str) -> dict | None:
    return SUBMISSION_NOTICE_MAP.get(str(code or "").strip())


def submission_notice_location(submission_id: str, code: str, *, focus: str = "") -> str:
    base = f"/submissions/{submission_id}"
    query = urlencode({"notice": code}) if code else ""
    fragment = f"#{focus}" if focus else ""
    if not query:
        return f"{base}{fragment}"
    return f"{base}?{query}{fragment}"


def safe_submission_return_target(value: str) -> str:
    target = str(value or "").strip()
    if not target:
        return ""
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc:
        return ""
    if parsed.path == "/submissions" or (parsed.path.startswith("/submissions/") and parsed.path.endswith("/exports")):
        suffix = f"?{parsed.query}" if parsed.query else ""
        fragment = f"#{parsed.fragment}" if parsed.fragment else ""
        return f"{parsed.path}{suffix}{fragment}"
    return ""


def submission_context(submission_id: str) -> tuple[dict, list[dict], list[dict], list[dict], list[dict]]:
    submission = store.submissions.get(submission_id)
    if not submission:
        raise HTTPException(404, "未找到批次")
    materials = [store.materials[item_id].to_dict() for item_id in submission.material_ids if item_id in store.materials]
    cases = [store.cases[item_id].to_dict() for item_id in submission.case_ids if item_id in store.cases]
    reports = [store.report_artifacts[item_id].to_dict() for item_id in submission.report_ids if item_id in store.report_artifacts]
    parse_results = [store.parse_results[item_id].to_dict() for item_id in submission.material_ids if item_id in store.parse_results]
    return submission.to_dict(), materials, cases, reports, parse_results


def submission_diagnostics_payload(submission_id: str) -> dict:
    submission = store.submissions.get(submission_id)
    if not submission:
        raise HTTPException(404, "未找到批次")
    diagnostics: list[dict] = []
    for material_id in submission.material_ids:
        material = store.materials.get(material_id)
        parse_result = store.parse_results.get(material_id)
        if not material:
            continue
        diagnostics.append(
            {
                "material_id": material.id,
                "original_filename": material.original_filename,
                "material_type": material.material_type,
                **parse_diagnostic_snapshot(material.to_dict(), parse_result.to_dict() if parse_result else {}),
            }
        )
    return {
        "submission_id": submission_id,
        "summary": submission_quality_snapshot(submission_id),
        "diagnostics": diagnostics,
    }
