from __future__ import annotations


def _render_issue_lines(issues: list[dict]) -> list[str]:
    if not issues:
        return ["- 未发现问题"]
    lines = []
    for issue in issues:
        severity = issue.get("severity", "minor")
        category = issue.get("category", "问题")
        desc = issue.get("desc", "")
        lines.append(f"- [{severity}] {category}: {desc}")
    return lines


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
    lines.extend(["", "## 跨材料问题", ""])
    lines.extend(_render_issue_lines(issues))
    lines.extend(["", "## AI 补充说明", ""])
    lines.append(f"- provider: {ai_provider}")
    lines.append(f"- resolution: {ai_resolution}")
    lines.append(f"- summary: {ai_summary or '当前没有额外 AI 补充说明'}")
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
