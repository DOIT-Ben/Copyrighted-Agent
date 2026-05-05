from __future__ import annotations

from app.core.services.business_review import business_level


def _render_issue_lines(issues: list[dict]) -> list[str]:
    if not issues:
        return ["- 未发现问题"]
    lines = []
    for issue in issues:
        severity = issue.get("severity", "minor")
        category = issue.get("category", "问题")
        desc = issue.get("desc", "")
        level, _ = business_level(issue)
        lines.append(f"- [{level} / {severity}] {category}: {desc}")
    return lines


def _render_business_issue_lines(issues: list[dict], target: str) -> list[str]:
    lines: list[str] = []
    for issue in issues:
        level, _ = business_level(issue)
        if level != target:
            continue
        category = issue.get("category", "问题")
        desc = issue.get("desc", "") or issue.get("message", "") or issue.get("detail", "")
        material = issue.get("material_name", "")
        if material:
            lines.append(f"- {category}: {desc}（材料：{material}）")
        else:
            lines.append(f"- {category}: {desc}")
    return lines or ["- 无"]


def _render_dimension_lines(dimensions: list[dict]) -> list[str]:
    if not dimensions:
        return ["- 暂无审查维度明细"]
    lines: list[str] = []
    for item in dimensions:
        lines.append(f"### {item.get('title', '审查维度')}")
        lines.append(f"- 状态: {item.get('status', '-')}")
        lines.append(f"- 检查对象: {item.get('scope', '-')}")
        lines.append(f"- 说明: {item.get('summary', '-')}")
        findings = list(item.get("findings", []) or [])
        if findings:
            lines.append("- 关键依据:")
            for finding in findings:
                lines.append(f"  - {finding}")
        lines.append("")
    return lines


def render_material_report_markdown(payload: dict) -> str:
    title = payload.get("material_name", "材料报告")
    material_type = payload.get("material_type", "unknown")
    issues = payload.get("issues", [])
    parse_quality = payload.get("parse_quality", {})
    triage = payload.get("triage", {})
    lines = [
        f"# {title}",
        "",
        f"- 材料类型: {material_type}",
        f"- parse_quality: {parse_quality.get('quality_level', 'unknown')} ({parse_quality.get('quality_score', 'n/a')})",
        f"- needs_manual_review: {triage.get('needs_manual_review', False)}",
    ]
    if parse_quality.get("review_reason_code"):
        lines.append(
            f"- parse_review_reason: {parse_quality.get('review_reason_code')} ({parse_quality.get('review_reason_label', '')})"
        )
    if parse_quality.get("legacy_doc_bucket"):
        lines.append(
            f"- legacy_doc_bucket: {parse_quality.get('legacy_doc_bucket')} ({parse_quality.get('legacy_doc_bucket_label', '')})"
        )
    if triage.get("unknown_reason"):
        lines.append(f"- unknown_reason: {triage.get('unknown_reason')}")
    lines.extend(["", "## 问题摘要", ""])
    lines.extend(_render_issue_lines(issues))
    return "\n".join(lines)


def render_case_report_markdown(payload: dict) -> str:
    case_name = payload.get("case_name", "项目报告")
    materials = payload.get("materials", [])
    issues = payload.get("cross_material_issues", [])
    dimensions = payload.get("review_dimensions", [])
    review_profile = dict(payload.get("review_profile", {}) or {})
    rule_conclusion = payload.get("rule_conclusion", "")
    ai_summary = payload.get("ai_summary", "")
    ai_provider = payload.get("ai_provider", "mock")
    ai_resolution = payload.get("ai_resolution", "explicit_mock")
    lines = [f"# {case_name}", "", "## 材料概览", ""]
    for item in materials:
        lines.append(f"- {item}")
    lines.extend(["", "## 规则结论", ""])
    lines.append(f"- {rule_conclusion or '规则引擎未返回额外结论'}")
    lines.extend(["", "## 审查维度", ""])
    lines.extend(_render_dimension_lines(dimensions))
    if review_profile:
        lines.extend(["", "## 审查配置", ""])
        lines.append(f"- focus_mode: {review_profile.get('focus_mode', 'balanced')}")
        lines.append(f"- strictness: {review_profile.get('strictness', 'standard')}")
        lines.append(f"- enabled_dimensions: {', '.join(list(review_profile.get('enabled_dimensions', []) or []))}")
        lines.append(f"- llm_instruction: {review_profile.get('llm_instruction', '') or '未补充'}")
    lines.extend(["", "## 问题级别归类", ""])
    lines.extend(["", "### 退回级问题", ""])
    lines.extend(_render_business_issue_lines(issues, "退回级问题"))
    lines.extend(["", "### 弱智问题", ""])
    lines.extend(_render_business_issue_lines(issues, "弱智问题"))
    lines.extend(["", "### 警告项", ""])
    lines.extend(_render_business_issue_lines(issues, "警告项"))
    lines.extend(["", "## 跨材料问题", ""])
    lines.extend(_render_issue_lines(issues))
    lines.extend(["", "## AI 补充说明", ""])
    lines.append(f"- provider: {ai_provider}")
    lines.append(f"- resolution: {ai_resolution}")
    lines.append(f"- summary: {ai_summary or '当前没有额外 AI 补充说明'}")
    return "\n".join(lines)


def render_submission_global_review_markdown(payload: dict) -> str:
    inventory = dict(payload.get("material_inventory", {}) or {})
    case_inventory = dict(payload.get("case_inventory", {}) or {})
    severity_counts = dict(payload.get("severity_counts", {}) or {})
    issues = list(payload.get("issues", []) or [])
    lines = [
        "# 整包全局审查报告",
        "",
        f"- 全局状态: {payload.get('status', 'unknown')}",
        f"- 全局得分: {payload.get('score', 'n/a')}",
        f"- 结论摘要: {payload.get('summary', '') or '-'}",
        f"- 材料总数: {inventory.get('total', 0)}",
        f"- 项目分组数: {case_inventory.get('total', 0)}",
        f"- 严重问题: {severity_counts.get('severe', 0)}",
        f"- 需复核问题: {severity_counts.get('moderate', 0)}",
        f"- 提醒项: {severity_counts.get('minor', 0)}",
        "",
        "## 材料清单",
        "",
    ]
    files = list(inventory.get("files", []) or [])
    if files:
        for item in files:
            name = item.get("file_name", "未知文件")
            material_type = item.get("material_type_label") or item.get("material_type", "unknown")
            identity = " ".join(
                part
                for part in [
                    str(item.get("detected_software_name", "") or "").strip(),
                    str(item.get("detected_version", "") or "").strip(),
                ]
                if part
            )
            suffix = f"；识别：{identity}" if identity else ""
            lines.append(
                f"- {name}: {material_type}；解析质量 {item.get('quality_level', 'unknown')}；问题 {item.get('issue_count', 0)} 个{suffix}"
            )
    else:
        lines.append("- 未发现可处理材料")

    lines.extend(["", "## 全局问题", ""])
    if issues:
        for issue in issues:
            lines.append(
                f"- [{issue.get('severity', 'minor')}] {issue.get('category', '全局审查')}: "
                f"{issue.get('desc', '')} 建议：{issue.get('suggestion', issue.get('suggest', ''))}"
            )
    else:
        lines.append("- 未发现全局问题")
    return "\n".join(lines)


def render_batch_report_markdown(payload: dict) -> str:
    submission_name = payload.get("submission_name", "批次报告")
    items = payload.get("items", [])
    lines = [f"# {submission_name}", "", "## 文件摘要", ""]
    for item in items:
        file_name = item.get("file_name", "未知文件")
        issue_count = len(item.get("issues", []))
        lines.append(f"- {file_name}: {issue_count} 个问题")
    return "\n".join(lines)
