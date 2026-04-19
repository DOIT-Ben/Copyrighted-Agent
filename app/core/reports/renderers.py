from __future__ import annotations


def _render_issue_lines(issues: list[dict]) -> list[str]:
    if not issues:
        return ["- \u672a\u53d1\u73b0\u95ee\u9898"]
    lines = []
    for issue in issues:
        severity = issue.get("severity", "minor")
        category = issue.get("category", "\u95ee\u9898")
        desc = issue.get("desc", "")
        lines.append(f"- [{severity}] {category}: {desc}")
    return lines


def render_material_report_markdown(payload: dict) -> str:
    title = payload.get("material_name", "\u6750\u6599\u62a5\u544a")
    material_type = payload.get("material_type", "unknown")
    issues = payload.get("issues", [])
    parse_quality = payload.get("parse_quality", {})
    triage = payload.get("triage", {})
    lines = [
        f"# {title}",
        "",
        f"- \u6750\u6599\u7c7b\u578b: {material_type}",
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
    lines.extend(["", "## \u95ee\u9898\u6458\u8981", ""])
    lines.extend(_render_issue_lines(issues))
    return "\n".join(lines)


def render_case_report_markdown(payload: dict) -> str:
    case_name = payload.get("case_name", "\u9879\u76ee\u62a5\u544a")
    materials = payload.get("materials", [])
    issues = payload.get("cross_material_issues", [])
    rule_conclusion = payload.get("rule_conclusion", "")
    ai_summary = payload.get("ai_summary", "")
    ai_provider = payload.get("ai_provider", "mock")
    ai_resolution = payload.get("ai_resolution", "explicit_mock")
    lines = [f"# {case_name}", "", "## \u6750\u6599\u6982\u89c8", ""]
    for item in materials:
        lines.append(f"- {item}")
    lines.extend(["", "## \u89c4\u5219\u7ed3\u8bba", ""])
    lines.append(f"- {rule_conclusion or '规则引擎未返回额外结论'}")
    lines.extend(["", "## \u8de8\u6750\u6599\u95ee\u9898", ""])
    lines.extend(_render_issue_lines(issues))
    lines.extend(["", "## AI \u8865\u5145\u8bf4\u660e", ""])
    lines.append(f"- provider: {ai_provider}")
    lines.append(f"- resolution: {ai_resolution}")
    lines.append(f"- summary: {ai_summary or '当前没有额外 AI 补充说明'}")
    return "\n".join(lines)


def render_batch_report_markdown(payload: dict) -> str:
    submission_name = payload.get("submission_name", "\u6279\u6b21\u62a5\u544a")
    items = payload.get("items", [])
    lines = [f"# {submission_name}", "", "## \u6587\u4ef6\u6458\u8981", ""]
    for item in items:
        file_name = item.get("file_name", "\u672a\u77e5\u6587\u4ef6")
        issue_count = len(item.get("issues", []))
        lines.append(f"- {file_name}: {issue_count} \u4e2a\u95ee\u9898")
    return "\n".join(lines)
