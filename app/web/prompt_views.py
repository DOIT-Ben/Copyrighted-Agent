from __future__ import annotations

from app.core.utils.text import escape_html


def _dimension_cards(dimensions: list[dict]) -> str:
    if not dimensions:
        return ""
    cards = "".join(
        (
            '<article class="prompt-dimension-card">'
            f'<strong>{escape_html(str(item.get("title", "") or item.get("key", "-")))}</strong>'
            f'<p>{escape_html(str(item.get("objective", "") or "-"))}</p>'
            "</article>"
        )
        for item in dimensions
    )
    return f'<div class="prompt-dimension-grid">{cards}</div>'


def render_prompt_snapshot(snapshot: dict | None) -> str:
    payload = dict(snapshot or {})
    if not payload:
        return ""

    summary = dict(payload.get("review_profile_summary") or {})
    dimensions = list(payload.get("active_dimensions") or [])
    enabled_text = "、".join(str(item.get("title", "") or item.get("key", "-")) for item in dimensions) or "-"
    instruction_text = str(summary.get("llm_instruction", "") or "").strip() or "未补充"
    system_prompt = str(payload.get("system_prompt", "") or "").strip()
    user_prompt = str(payload.get("user_prompt", "") or "").strip()

    summary_pairs = (
        '<div class="dossier-list dossier-list-single">'
        f'<div><span>启用维度</span><strong>{escape_html(enabled_text)}</strong></div>'
        f'<div><span>审查侧重</span><strong>{escape_html(str(summary.get("focus_mode", "-") or "-"))}</strong></div>'
        f'<div><span>严格程度</span><strong>{escape_html(str(summary.get("strictness", "-") or "-"))}</strong></div>'
        f'<div><span>补充指令</span><strong>{escape_html(instruction_text)}</strong></div>'
        "</div>"
    )

    prompt_previews = (
        '<div class="report-source prompt-source">'
        '<details>'
        "<summary>查看本次发送给 LLM 的完整提示词</summary>"
        '<div class="prompt-stack">'
        '<div class="report-panel"><pre>'
        + escape_html(system_prompt or "No system prompt")
        + "</pre></div>"
        '<div class="report-panel"><pre>'
        + escape_html(user_prompt or "No user prompt")
        + "</pre></div>"
        "</div>"
        "</details>"
        "</div>"
    )

    return summary_pairs + _dimension_cards(dimensions) + prompt_previews


__all__ = ["render_prompt_snapshot"]
