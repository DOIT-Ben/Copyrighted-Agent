from __future__ import annotations

from app.core.services.review_profile import dimension_title, list_review_rule_history, normalize_review_profile
from app.core.services.review_rulebook import (
    default_dimension_rule,
    dimension_rulebook_from_profile,
    format_rule_checkpoints,
    format_rule_guidance_lines,
)
from app.core.utils.text import escape_html
from app.web.view_helpers import icon, layout, link, list_pairs, pill, table


def _summary_tile(label: str, value: str, note: str) -> str:
    del note
    return (
        '<div class="summary-tile">'
        f"<span>{escape_html(label)}</span>"
        f"<strong>{escape_html(value)}</strong>"
        "</div>"
    )


def _checkpoint_list(title: str, checkpoints: list[str]) -> str:
    items = "".join(f"<li>{escape_html(item)}</li>" for item in checkpoints) or "<li>-</li>"
    return f'<div class="rule-checkpoint-list"><strong>{escape_html(title)}</strong><ul>{items}</ul></div>'


def _guidance_list(title: str, items: list[str], note: str = "") -> str:
    rows = "".join(f"<li>{escape_html(item)}</li>" for item in items) or "<li>-</li>"
    note_html = f"<p>{escape_html(note)}</p>" if note else ""
    return f'<div class="rule-checkpoint-list"><strong>{escape_html(title)}</strong>{note_html}<ul>{rows}</ul></div>'


def _focus_section(title: str, body: str, *, open_by_default: bool = False, meta: str = "") -> str:
    open_attr = " open" if open_by_default else ""
    meta_html = f"<small>{escape_html(meta)}</small>" if meta else ""
    return (
        f'<details class="rule-focus-section"{open_attr}>'
        "<summary>"
        "<span>"
        f"<strong>{escape_html(title)}</strong>"
        f"{meta_html}"
        "</span>"
        f'{icon("search", "icon icon-sm")}'
        "</summary>"
        f'<div class="rule-focus-section-body">{body}</div>'
        "</details>"
    )


def _rule_items_table(rule_entry: dict) -> str:
    rows = [
        [
            pill("启用" if item.get("enabled", True) else "停用", "success" if item.get("enabled", True) else "warning"),
            escape_html(str(item.get("category", "") or "-")),
            escape_html(str(item.get("title", "") or "-")),
            escape_html(str(item.get("severity", "") or "-")),
            escape_html(str(item.get("prompt_hint", "") or "-")),
        ]
        for item in list(rule_entry.get("rules", []) or [])
    ]
    return table(["状态", "分类", "规则项", "级别", "检查说明"], rows) if rows else ""


def _rule_item_editor(dimension_key: str, item: dict) -> str:
    base = f"rule_{dimension_key}_item_{item.get('key', '')}"
    checked = " checked" if item.get("enabled", True) else ""
    severity_options = "".join(
        f'<option value="{escape_html(level)}"{" selected" if level == item.get("severity", "moderate") else ""}>{escape_html(level)}</option>'
        for level in ["severe", "moderate", "minor"]
    )
    return f"""
    <article class="rule-item-card">
      <label class="dimension-choice-main">
        <input type="checkbox" name="{escape_html(base)}_enabled" value="1"{checked}>
        <span>
          <strong>{escape_html(item.get("title", ""))}</strong>
          <small>{escape_html(item.get("category", ""))}</small>
        </span>
      </label>
      <div class="review-profile-grid compact-grid">
        <label class="field">
          <span>规则名称</span>
          <input type="text" name="{escape_html(base)}_title" value="{escape_html(item.get('title', ''))}">
        </label>
        <label class="field">
          <span>级别</span>
          <select name="{escape_html(base)}_severity">{severity_options}</select>
        </label>
      </div>
      <label class="field">
        <span>检查说明</span>
        <textarea name="{escape_html(base)}_prompt_hint" rows="3">{escape_html(item.get('prompt_hint', ''))}</textarea>
      </label>
    </article>
    """


def _rule_history_table(submission_id: str, dimension_key: str) -> str:
    history = list_review_rule_history(submission_id, dimension_key, limit=8)
    if not history:
        return "<p>暂无规则版本历史。</p>"
    rows = [
        [
            escape_html(f"r{int(item.get('revision', 1) or 1)}"),
            escape_html(str(item.get("change_type_label", "") or "-")),
            escape_html(str(item.get("updated_by", "") or "-")),
            escape_html(str(item.get("change_note", "") or "-")),
            escape_html(str(item.get("corrected_at", "") or "-")),
        ]
        for item in history
    ]
    return table(["版本", "变更类型", "修改人", "备注", "时间"], rows)


def render_review_rule_detail_page(
    submission: dict,
    cases: list[dict],
    dimension_key: str,
    *,
    selected_case_id: str = "",
) -> str:
    submission_id = str(submission.get("id", "") or "")
    review_profile = normalize_review_profile(submission.get("review_profile", {}))
    rulebook = dimension_rulebook_from_profile(review_profile)
    if dimension_key not in rulebook:
        raise ValueError(f"Unsupported dimension key: {dimension_key}")

    rule_entry = rulebook[dimension_key]
    default_rule = default_dimension_rule(dimension_key)
    rulebook_meta = dict(review_profile.get("rulebook_meta", {}) or {})
    is_enabled = dimension_key in review_profile.get("enabled_dimensions", [])

    case_options = "".join(
        f'<option value="{escape_html(case.get("id", ""))}"{" selected" if case.get("id", "") == selected_case_id else ""}>'
        f'{escape_html(case.get("case_name", "") or case.get("software_name", "") or case.get("id", ""))}</option>'
        for case in cases
    ) or '<option value="">暂无项目</option>'

    checkpoints_text = format_rule_checkpoints(rule_entry.get("checkpoints", []))
    evidence_text = format_rule_guidance_lines(rule_entry.get("evidence_targets", []))
    failure_text = format_rule_guidance_lines(rule_entry.get("common_failures", []))
    operator_notes_text = format_rule_guidance_lines(rule_entry.get("operator_notes", []))

    summary_tiles = "".join(
        [
            _summary_tile("维度", rule_entry.get("title", dimension_title(dimension_key)), "当前只编辑这个维度。"),
            _summary_tile("状态", "已启用" if is_enabled else "未启用", "决定是否参与当前批次审查。"),
            _summary_tile("规则项", str(len(rule_entry.get("rules", []) or [])), "这里只保留会直接影响判断的规则。"),
            _summary_tile("规则版本", f"r{int(rulebook_meta.get('revision', 1) or 1)}", "每次保存或恢复默认都会递增。"),
        ]
    )

    prompt_preview_pairs = [
        ("规则名称", str(rule_entry.get("title", dimension_title(dimension_key)))),
        ("审查目标", str(rule_entry.get("objective", "") or "-")),
        ("LLM 关注点", str(rule_entry.get("llm_focus", "") or "-")),
    ]
    compare_rows = [
        ["规则名称", escape_html(default_rule.get("title", "")), escape_html(rule_entry.get("title", ""))],
        ["审查目标", escape_html(default_rule.get("objective", "")), escape_html(rule_entry.get("objective", ""))],
        ["LLM 关注点", escape_html(default_rule.get("llm_focus", "")), escape_html(rule_entry.get("llm_focus", ""))],
        ["规则项数量", escape_html(str(len(default_rule.get("rules", []) or []))), escape_html(str(len(rule_entry.get("rules", []) or [])))],
    ]

    version_overview = list_pairs(
        [
            ("规则版本", f"r{int(rulebook_meta.get('revision', 1) or 1)}"),
            ("最近修改维度", dimension_title(str(rulebook_meta.get("last_dimension_key", "") or dimension_key))),
            ("最近修改人", str(rulebook_meta.get("updated_by", "") or "未记录")),
            ("最近备注", str(rulebook_meta.get("change_note", "") or "未记录")),
        ],
        css_class="dossier-list dossier-list-single",
    )
    rule_history_body = _rule_history_table(submission_id, dimension_key)
    rule_item_editors = "".join(_rule_item_editor(dimension_key, item) for item in list(rule_entry.get("rules", []) or []))

    editor_body = f"""
    <form class="operator-form rule-editor-form rule-focus-form" action="/submissions/{escape_html(submission_id)}/review-rules/{escape_html(dimension_key)}" method="post">
      <div class="rule-focus-form-grid">
        <label class="field">
          <span>规则名称</span>
          <input type="text" name="title" value="{escape_html(rule_entry.get('title', ''))}" required>
        </label>
        <label class="field">
          <span>保存后重跑项目</span>
          <select name="case_id">{case_options}</select>
        </label>
      </div>
      <label class="field">
        <span>审查目标</span>
        <textarea name="objective" rows="4" required>{escape_html(rule_entry.get('objective', ''))}</textarea>
      </label>
      <div class="rule-focus-stack">
        <div class="rule-focus-stack-head">
          <strong>规则项</strong>
          <small>只调整会直接影响判定的细分规则。</small>
        </div>
        <div class="rule-item-stack">
          {rule_item_editors}
        </div>
      </div>
      <div class="rule-focus-form-grid">
        <label class="field">
          <span>检查点摘要</span>
          <textarea name="checkpoints" rows="8" required>{escape_html(checkpoints_text)}</textarea>
        </label>
        <label class="field">
          <span>LLM 关注点</span>
          <textarea name="llm_focus" rows="8">{escape_html(rule_entry.get('llm_focus', ''))}</textarea>
        </label>
      </div>
      <div class="rule-focus-form-grid triple">
        <label class="field">
          <span>重点看哪些材料</span>
          <textarea name="evidence_targets" rows="6">{escape_html(evidence_text)}</textarea>
        </label>
        <label class="field">
          <span>常见退回点</span>
          <textarea name="common_failures" rows="6">{escape_html(failure_text)}</textarea>
        </label>
        <label class="field">
          <span>处理建议</span>
          <textarea name="operator_notes" rows="6">{escape_html(operator_notes_text)}</textarea>
        </label>
      </div>
      <label class="field">
        <span>备注</span>
        <input type="text" name="note" placeholder="记录这次规则调整原因">
      </label>
      <div class="inline-actions rule-editor-actions">
        <button class="button-primary" type="submit" name="action" value="save">{icon("check", "icon icon-sm")}保存规则</button>
        <button class="button-secondary" type="submit" name="action" value="save_and_rerun">{icon("refresh", "icon icon-sm")}保存并重跑</button>
        <button class="button-secondary" type="submit" name="action" value="restore_default">{icon("refresh", "icon icon-sm")}恢复默认</button>
      </div>
    </form>
    """

    preview_body = (
        list_pairs(prompt_preview_pairs, css_class="dossier-list dossier-list-single")
        + _checkpoint_list("当前检查点", rule_entry.get("checkpoints", []))
        + _guidance_list("重点看哪些材料", rule_entry.get("evidence_targets", []), "这些位置会带进提示词，也会在结果页作为回查线索。")
        + _guidance_list("常见退回点", rule_entry.get("common_failures", []))
        + _guidance_list("处理建议", rule_entry.get("operator_notes", []))
        + _rule_items_table(rule_entry)
    )
    default_preview_body = (
        table(["字段", "默认规则", "当前规则"], compare_rows)
        + _checkpoint_list("默认检查点", default_rule.get("checkpoints", []))
        + _guidance_list("默认重点材料", default_rule.get("evidence_targets", []))
        + _guidance_list("默认常见退回点", default_rule.get("common_failures", []))
        + _guidance_list("默认处理建议", default_rule.get("operator_notes", []))
    )

    side_body = "".join(
        [
            '<section class="rule-focus-side-panel" id="rule-version">',
            '<div class="rule-focus-side-head">',
            f'{icon("clock", "icon icon-sm")}',
            "<div><strong>规则版本</strong><small>历史与当前版本都收在这里。</small></div>",
            "</div>",
            version_overview,
            rule_history_body,
            "</section>",
            _focus_section("当前规则预览", preview_body, open_by_default=True, meta="先看效果，再决定改哪里"),
            _focus_section("默认规则对照", default_preview_body, meta="需要时再展开"),
        ]
    )

    content = f"""
    <section class="rule-focus-shell">
      <div class="rule-focus-backdrop"></div>
      <article class="rule-focus-modal">
        <header class="rule-focus-header" id="rule-summary">
          <div class="rule-focus-header-main">
            <span class="workspace-tag">聚焦编辑</span>
            <h2>{escape_html(rule_entry.get("title", dimension_title(dimension_key)))}</h2>
            <p>把规则编辑收成一个小窗，只保留当前维度的核心信息，减少上下文噪音。</p>
          </div>
          <div class="rule-focus-header-actions">
            {pill("已启用" if is_enabled else "未启用", "success" if is_enabled else "warning")}
            {link(f"/submissions/{submission_id}", "返回批次", css_class="button-secondary button-compact")}
            {link(f"/submissions/{submission_id}/operator", "返回人工台", css_class="button-secondary button-compact")}
          </div>
        </header>
        <div class="rule-focus-summary-grid">
          {summary_tiles}
        </div>
        <div class="rule-focus-layout" id="rule-editor">
          <section class="rule-focus-main">
            <div class="rule-focus-main-head">
              <strong>编辑规则</strong>
              <small>先改目标和规则项，再补材料提示与备注。</small>
            </div>
            {editor_body}
          </section>
          <aside class="rule-focus-side">
            {side_body}
          </aside>
        </div>
      </article>
    </section>
    """

    return layout(
        title=f"{dimension_title(dimension_key)} - 审查规则",
        active_nav="submissions",
        header_tag="审查规则",
        header_title="规则聚焦编辑",
        header_subtitle="这里不再把所有信息摊满一整页，而是把用户拉进一个更专注的编辑窗口。",
        header_meta="".join(
            [
                pill("规则版本", "info"),
                pill(f"r{int(rulebook_meta.get('revision', 1) or 1)}", "neutral"),
            ]
        ),
        content=content,
        header_note="",
        page_links=[
            ("#rule-summary", "规则摘要", "shield"),
            ("#rule-editor", "编辑窗口", "wrench"),
            ("#rule-version", "规则版本", "clock"),
        ],
    )


__all__ = ["render_review_rule_detail_page"]
