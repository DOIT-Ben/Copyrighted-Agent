from __future__ import annotations

import json

from app.core.services.review_profile import (
    DIMENSION_CATALOG,
    FOCUS_MODE_LABELS,
    REVIEW_PROFILE_PRESETS,
    STRICTNESS_LABELS,
    normalize_review_profile,
)
from app.core.services.review_rulebook import dimension_rulebook_from_profile, format_rule_checkpoints
from app.core.utils.text import escape_html


def _inline_rule_editor(key: str, rule: dict) -> str:
    checkpoints = format_rule_checkpoints(list(rule.get("checkpoints", []) or []))
    return f"""
    <details class="dimension-rule-editor">
      <summary>导入前编辑规则</summary>
      <div class="dimension-rule-editor-body">
        <label class="field">
          <span>规则名称</span>
          <input type="text" name="rule_{escape_html(key)}_title" value="{escape_html(rule.get('title', ''))}">
        </label>
        <label class="field">
          <span>审查目标</span>
          <textarea name="rule_{escape_html(key)}_objective" rows="3">{escape_html(rule.get('objective', ''))}</textarea>
        </label>
        <label class="field">
          <span>检查点</span>
          <textarea name="rule_{escape_html(key)}_checkpoints" rows="5">{escape_html(checkpoints)}</textarea>
          <span class="field-hint">每行一条。提交 ZIP 后会保存到本批次。</span>
        </label>
        <label class="field">
          <span>LLM 关注点</span>
          <textarea name="rule_{escape_html(key)}_llm_focus" rows="3">{escape_html(rule.get('llm_focus', ''))}</textarea>
        </label>
      </div>
    </details>
    """


def render_review_profile_form_fields(
    profile: dict | None = None,
    *,
    submit_context: str = "import",
    submission_id: str = "",
    case_id: str = "",
) -> str:
    normalized = normalize_review_profile(profile)
    rulebook = dimension_rulebook_from_profile(normalized)
    focus_options = "".join(
        f'<option value="{escape_html(key)}"{" selected" if key == normalized["focus_mode"] else ""}>{escape_html(label)}</option>'
        for key, label in FOCUS_MODE_LABELS.items()
    )
    strictness_options = "".join(
        f'<option value="{escape_html(key)}"{" selected" if key == normalized["strictness"] else ""}>{escape_html(label)}</option>'
        for key, label in STRICTNESS_LABELS.items()
    )
    rule_suffix = f"?case_id={escape_html(case_id)}" if case_id else ""
    dimension_items = "".join(
        (
            '<div class="dimension-choice">'
            '<label class="dimension-choice-main">'
            f'<input type="checkbox" name="dimension_{escape_html(item["key"])}" value="1"'
            f'{" checked" if item["key"] in normalized["enabled_dimensions"] else ""}>'
            '<span>'
            f'<strong>{escape_html(item["title"])}</strong>'
            f'<small>{escape_html(item.get("description", ""))}</small>'
            "</span>"
            "</label>"
            + (
                '<a class="dimension-rule-link" '
                f'href="/submissions/{escape_html(submission_id)}/review-rules/{escape_html(item["key"])}{rule_suffix}">'
                "编辑规则</a>"
                if submission_id
                else ""
            )
            + _inline_rule_editor(item["key"], rulebook.get(item["key"], {}))
            + "</div>"
        )
        for item in DIMENSION_CATALOG
    )
    preset_items = "".join(
        (
            f'<button class="button-secondary button-compact review-profile-preset{" is-active" if item["key"] == normalized["preset_key"] else ""}" '
            'type="button" '
            f'data-review-preset="{escape_html(item["key"])}" '
            f"data-review-profile='{escape_html(json.dumps(dict(item['profile']), ensure_ascii=False))}'>"
            f"{escape_html(item['title'])}</button>"
        )
        for item in REVIEW_PROFILE_PRESETS
    )
    helper_copy = (
        "这组配置会直接影响本次导入后的审查维度展示和 LLM 补充研判。"
        if submit_context == "import"
        else "修改后会保存为当前批次的审查配置，并用于下一次重新审查。"
    )
    return f"""
    <div class="review-profile-box">
      <div class="review-profile-head">
        <strong>审查配置</strong>
        <small>{escape_html(helper_copy)}</small>
      </div>
      <div class="review-profile-preset-row">
        {preset_items}
      </div>
      <input type="hidden" name="review_profile_preset" value="{escape_html(normalized['preset_key'])}">
      <input type="hidden" name="review_dimensions_present" value="1">
      <div class="review-profile-grid">
        <label class="field">
          <span>审查侧重</span>
          <select name="focus_mode">{focus_options}</select>
        </label>
        <label class="field">
          <span>严格程度</span>
          <select name="strictness">{strictness_options}</select>
        </label>
      </div>
      <label class="field">
        <span>LLM 补充指令</span>
        <textarea name="llm_instruction" rows="3" placeholder="例如：重点关注申请主体、软件名称和版本号在不同材料中的一致性。">{escape_html(normalized["llm_instruction"])}</textarea>
        <span class="field-hint">用于补充审查重点。</span>
      </label>
      <div class="dimension-choice-grid">
        {dimension_items}
      </div>
    </div>
    """


__all__ = ["render_review_profile_form_fields"]
