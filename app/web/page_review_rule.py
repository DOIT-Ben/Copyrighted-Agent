from __future__ import annotations

from app.core.services.review_profile import DIMENSION_CATALOG, dimension_title, list_review_rule_history, normalize_review_profile
from app.core.services.review_rulebook import (
    default_dimension_rule,
    dimension_rulebook_from_profile,
    format_rule_checkpoints,
    format_rule_guidance_lines,
)
from app.core.utils.text import escape_html
from app.web.view_helpers import contract_markers, icon, layout, link, list_pairs, panel, pill, table


def _summary_tile(label: str, value: str, note: str) -> str:
    return (
        '<div class="rule-summary-tile">'
        f'<span class="rule-summary-tile-label">{escape_html(label)}</span>'
        f'<strong class="rule-summary-tile-value">{escape_html(value)}</strong>'
        f'<small class="rule-summary-tile-note">{escape_html(note)}</small>'
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
    current_sev = item.get("severity", "moderate")
    _sev_label = {"severe": "严重", "moderate": "中等", "minor": "轻微"}
    severity_pills = "".join(
        f'<label class="sev-pill sev-{escape_html(level)}">'
        f'<input type="radio" name="{escape_html(base)}_severity" value="{escape_html(level)}"{" checked" if level == current_sev else ""}>'
        f'<span>{_sev_label.get(level, level)}</span>'
        f'</label>'
        for level in ["severe", "moderate", "minor"]
    )
    return f"""
    <article class="rule-item-row">
      <div class="rule-item-row-main">
        <label class="rule-item-toggle">
          <input type="checkbox" name="{escape_html(base)}_enabled" value="1"{checked}>
          <span class="toggle-track"><span class="toggle-thumb"></span></span>
        </label>
        <div class="rule-item-meta">
          <strong>{escape_html(item.get("title", ""))}</strong>
          <small>{escape_html(item.get("category", ""))}</small>
        </div>
        <div class="rule-item-severity">{severity_pills}</div>
      </div>
      <details class="rule-item-detail">
        <summary class="rule-item-detail-toggle">编辑名称与说明</summary>
        <div class="rule-item-detail-body">
          <label class="field">
            <span>规则名称</span>
            <input type="text" name="{escape_html(base)}_title" value="{escape_html(item.get('title', ''))}">
          </label>
          <label class="field">
            <span>检查说明</span>
            <textarea name="{escape_html(base)}_prompt_hint" rows="3">{escape_html(item.get('prompt_hint', ''))}</textarea>
          </label>
        </div>
      </details>
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


def render_global_rule_detail_page(dimension_key: str) -> str:
    from app.core.services.review_profile import default_review_profile, _load_global_review_profile

    global_profile = _load_global_review_profile()
    if global_profile:
        profile = normalize_review_profile(global_profile)
    else:
        profile = default_review_profile()

    rulebook = dimension_rulebook_from_profile(profile)
    if dimension_key not in rulebook:
        raise ValueError(f"Unsupported dimension key: {dimension_key}")

    rule_entry = rulebook[dimension_key]
    default_rule = default_dimension_rule(dimension_key)
    rulebook_meta = dict(profile.get("rulebook_meta", {}) or {})
    is_enabled = dimension_key in profile.get("enabled_dimensions", [])

    checkpoints_text = format_rule_checkpoints(rule_entry.get("checkpoints", []))
    evidence_text = format_rule_guidance_lines(rule_entry.get("evidence_targets", []))

    rule_items_html = "".join(_rule_item_editor(dimension_key, item) for item in rule_entry.get("rules", []))

    content = f"""
    <section class="dashboard-grid">
      {panel('规则配置',
        f'<div class="summary-grid">'
        + _summary_tile('维度', dimension_title(dimension_key), '')
        + _summary_tile('状态', '启用' if is_enabled else '停用', '')
        + _summary_tile('规则项', str(len(rule_entry.get('rules', []))), '')
        + '</div>'
        + f'<form class="admin-form" action="/api/global-rules/{escape_html(dimension_key)}" method="post">'
        f'<div class="rule-item-list">{rule_items_html}</div>'
        '<div class="inline-actions">'
        f'<button class="button-primary" type="submit">{icon("check", "icon icon-sm")}保存</button>'
        f'<a class="button-secondary" href="/">{icon("x", "icon icon-sm")}返回</a>'
        '</div>'
        '</form>',
        kicker='', extra_class='span-12', icon_name='edit', description='', panel_id='rule-editor')}
    </section>
    """

    return layout(
        title=f"规则配置 - {dimension_title(dimension_key)}",
        active_nav="home",
        header_tag="",
        header_title=f"规则配置",
        header_subtitle=dimension_title(dimension_key),
        header_meta=pill("全局", "info"),
        content=content,
        header_note="",
        page_links=[
            ("/", "返回", "home"),
        ],
    )


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

    _dimension_keys = [item["key"] for item in DIMENSION_CATALOG]
    _cur_idx = _dimension_keys.index(dimension_key) if dimension_key in _dimension_keys else -1
    _prev_key = _dimension_keys[_cur_idx - 1] if _cur_idx > 0 else None
    _next_key = _dimension_keys[_cur_idx + 1] if 0 <= _cur_idx < len(_dimension_keys) - 1 else None
    _prev_url = f"/submissions/{submission_id}/review-rules/{_prev_key}" if _prev_key else ""
    _next_url = f"/submissions/{submission_id}/review-rules/{_next_key}" if _next_key else ""
    _prev_title = dimension_title(_prev_key) if _prev_key else ""
    _next_title = dimension_title(_next_key) if _next_key else ""
    _dim_progress = f"{_cur_idx + 1} / {len(_dimension_keys)}" if _cur_idx >= 0 else ""

    rule_item_editors = "".join(_rule_item_editor(dimension_key, item) for item in list(rule_entry.get("rules", []) or []))

    rule_count = len(rule_entry.get("rules", []) or [])
    editor_body = f"""
    <form class="admin-form rule-editor-form" action="/submissions/{escape_html(submission_id)}/review-rules/{escape_html(dimension_key)}" method="post">
      <div class="summary-grid">
        {_summary_tile("维度", rule_entry.get("title", dimension_title(dimension_key)), f"{_dim_progress}")}
        {_summary_tile("规则版本", f"r{int(rulebook_meta.get('revision', 1) or 1)}", "rule-version")}
        {_summary_tile("状态", "启用" if is_enabled else "停用", "")}
        {_summary_tile("规则项", str(rule_count), "")}
      </div>
      <div class="inline-actions rule-editor-primary-actions">
        <button class="button-primary" type="submit" name="action" value="save">{icon("check", "icon icon-sm")}保存</button>
        <button class="button-secondary" type="submit" name="action" value="save_and_rerun">{icon("refresh", "icon icon-sm")}重跑</button>
        <button class="button-secondary" type="submit" name="action" value="restore_default">{icon("refresh", "icon icon-sm")}恢复</button>
        {'<a href="' + escape_html(_prev_url) + '" class="button-secondary">' + icon("chevron-left", "icon icon-sm") + '</a>' if _prev_key else ''}
        {'<a href="' + escape_html(_next_url) + '" class="button-secondary">' + icon("chevron-right", "icon icon-sm") + '</a>' if _next_key else ''}
        '<a href="/submissions/' + escape_html(submission_id) + '" class="button-secondary">' + icon("x", "icon icon-sm") + '返回</a>'
      </div>
      <label class="field">
        <span>规则名称</span>
        <input type="text" name="title" value="{escape_html(rule_entry.get('title', ''))}" required>
      </label>
      <label class="field">
        <span>重跑项目</span>
        <select name="case_id">{case_options}</select>
      </label>
      <label class="field">
        <span>审查目标</span>
        <textarea name="objective" rows="3" required>{escape_html(rule_entry.get('objective', ''))}</textarea>
      </label>
      <label class="field">
        <span>规则项 ({rule_count})</span>
        <div class="rule-item-stack">{rule_item_editors}</div>
      </label>
      <label class="field">
        <span>检查点</span>
        <textarea name="checkpoints" rows="6" required>{escape_html(checkpoints_text)}</textarea>
      </label>
      <label class="field">
        <span>LLM 关注点</span>
        <textarea name="llm_focus" rows="6">{escape_html(rule_entry.get('llm_focus', ''))}</textarea>
      </label>
      <label class="field">
        <span>修改备注</span>
        <input type="text" name="note" placeholder="记录调整原因">
      </label>
    </form>
    """

    content = f"""
    <section class="dashboard-grid">
      {contract_markers("rule-focus-modal", "聚焦编辑")}
      {panel('规则编辑', editor_body, kicker='', extra_class='span-12', icon_name='edit', description='', panel_id='rule-editor')}
      {panel('规则版本历史', _rule_history_table(submission_id, dimension_key), kicker='', extra_class='span-12', icon_name='history', description='', panel_id='rule-history')}
    </section>
    """

    return layout(
        title=f"{dimension_title(dimension_key)} - 规则编辑",
        active_nav="submissions",
        header_tag="规则编辑",
        header_title=dimension_title(dimension_key),
        header_subtitle=f"{_dim_progress}",
        header_meta=pill("启用" if is_enabled else "停用", "success" if is_enabled else "warning"),
        content=content,
        header_note="",
        page_links=[
            ("/submissions", "返回", "layers"),
        ],
    )


__all__ = ["render_global_rule_detail_page", "render_review_rule_detail_page"]
