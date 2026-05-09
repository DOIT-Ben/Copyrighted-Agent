from __future__ import annotations

import json

from app.core.services.review_profile import (
    DIMENSION_CATALOG,
    FOCUS_MODE_LABELS,
    REVIEW_PROFILE_PRESETS,
    STRICTNESS_LABELS,
    normalize_review_profile,
)
from app.core.services.review_rulebook import (
    dimension_rulebook_from_profile,
    format_rule_checkpoints,
    format_rule_guidance_lines,
)
from app.core.utils.text import escape_html
from app.web.view_helpers import icon


def render_review_profile_form_fields(
    profile: dict | None = None,
    *,
    submit_context: str = "import",
    submission_id: str = "",
    case_id: str = "",
) -> str:
    del submission_id, case_id
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
    severity_labels = {"severe": "严重", "moderate": "中等", "minor": "轻微"}

    def _rule_item_editor(dimension_key: str, rule_item: dict) -> str:
        item_key = str(rule_item.get("key", "") or "")
        base = f"rule_{dimension_key}_item_{item_key}"
        checked = " checked" if rule_item.get("enabled", True) else ""
        category = str(rule_item.get("category", "") or "自定义")
        current_severity = str(rule_item.get("severity", "moderate") or "moderate")
        severity_options = "".join(
            f'<option value="{escape_html(key)}"{" selected" if key == current_severity else ""}>{escape_html(label)}</option>'
            for key, label in severity_labels.items()
        )
        return f"""
        <article class="rule-item-card">
          <input type="hidden" name="{escape_html(base)}_category" value="{escape_html(category)}">
          <div class="compact-grid">
            <label class="field rule-item-enabled">
              <span>启用</span>
              <input type="checkbox" name="{escape_html(base)}_enabled" value="1"{checked}>
            </label>
            <label class="field">
              <span>级别</span>
              <select name="{escape_html(base)}_severity">{severity_options}</select>
            </label>
          </div>
          <label class="field">
            <span>规则项</span>
            <input type="text" name="{escape_html(base)}_title" value="{escape_html(str(rule_item.get("title", "")))}">
          </label>
          <label class="field">
            <span>检查说明</span>
            <textarea name="{escape_html(base)}_prompt_hint" rows="3">{escape_html(str(rule_item.get("prompt_hint", "")))}</textarea>
          </label>
        </article>
        """

    def _dimension_rule_editor(item: dict, rule_entry: dict) -> str:
        item_key = str(item.get("key", "") or "")
        base = f"rule_{item_key}"
        title = str(rule_entry.get("title", item.get("title", "")) or item.get("title", ""))
        rule_items_data = list(rule_entry.get("rules", []) or [])
        rule_item_keys = ",".join(str(rule_item.get("key", "") or "") for rule_item in rule_items_data if str(rule_item.get("key", "") or ""))
        rule_items = "".join(_rule_item_editor(item_key, rule_item) for rule_item in rule_items_data)
        new_rule_severity_options = "".join(
            f'<option value="{escape_html(key)}"{" selected" if key == "moderate" else ""}>{escape_html(label)}</option>'
            for key, label in severity_labels.items()
        )
        save_button = (
            f'<button class="button-primary button-compact dimension-rule-save" type="submit">{icon("check", "icon icon-sm")}保存规则</button>'
            if submit_context == "global"
            else ""
        )
        return f"""
        <details class="dimension-rule-editor" data-dimension-editor>
          <summary class="dimension-rule-link">
            {icon("edit", "icon icon-xs")}
            编辑规则
          </summary>
          <div class="dimension-rule-editor-modal" role="dialog" aria-modal="true" aria-label="编辑规则：{escape_html(title)}">
            <div class="dimension-rule-editor-backdrop" data-close-rule-editor></div>
            <section class="dimension-rule-editor-window">
              <div class="dimension-rule-editor-window-head">
                <div class="dimension-rule-editor-window-copy">
                  <span class="dimension-rule-editor-kicker">规则表单</span>
                  <strong>{escape_html(title)}</strong>
                </div>
                <button class="button-secondary button-compact dimension-rule-editor-close" type="button" data-close-rule-editor>
                  {icon("check", "icon icon-sm")}完成
                </button>
              </div>
              <div class="dimension-rule-editor-body">
                <div class="dimension-rule-editor-grid">
                  <label class="field">
                    <span>规则名称</span>
                    <input type="text" name="{escape_html(base)}_title" value="{escape_html(title)}">
                  </label>
                  <label class="field">
                    <span>LLM 关注点</span>
                    <textarea name="{escape_html(base)}_llm_focus" rows="3">{escape_html(str(rule_entry.get("llm_focus", "")))}</textarea>
                  </label>
                </div>
                <label class="field">
                  <span>审查目标</span>
                  <textarea name="{escape_html(base)}_objective" rows="3">{escape_html(str(rule_entry.get("objective", "")))}</textarea>
                </label>
                <div class="dimension-rule-editor-grid dimension-rule-editor-grid-wide">
                  <label class="field">
                    <span>检查点</span>
                    <textarea name="{escape_html(base)}_checkpoints" rows="5">{escape_html(format_rule_checkpoints(list(rule_entry.get("checkpoints", []) or [])))}</textarea>
                  </label>
                  <label class="field">
                    <span>证据目标</span>
                    <textarea name="{escape_html(base)}_evidence_targets" rows="5">{escape_html(format_rule_guidance_lines(list(rule_entry.get("evidence_targets", []) or [])))}</textarea>
                  </label>
                  <label class="field">
                    <span>常见问题</span>
                    <textarea name="{escape_html(base)}_common_failures" rows="5">{escape_html(format_rule_guidance_lines(list(rule_entry.get("common_failures", []) or [])))}</textarea>
                  </label>
                  <label class="field">
                    <span>操作提示</span>
                    <textarea name="{escape_html(base)}_operator_notes" rows="5">{escape_html(format_rule_guidance_lines(list(rule_entry.get("operator_notes", []) or [])))}</textarea>
                  </label>
                </div>
                <section class="dimension-rule-editor-section">
                  <div class="dimension-rule-editor-section-head">
                    <strong>规则项</strong>
                  </div>
                  <div class="rule-item-stack">{rule_items}</div>
                </section>
              </div>
            </section>
          </div>
        </details>
        """

    def _dimension_item(item: dict) -> str:
        item_key = str(item.get("key", "") or "")
        checked = " checked" if item_key in normalized["enabled_dimensions"] else ""
        return (
            '<div class="dimension-choice" data-dimension-key="'
            + escape_html(item_key)
            + '">'
            '<label class="dimension-choice-main">'
            f'<input type="checkbox" name="dimension_{escape_html(item_key)}" value="1"{checked}>'
            "<span>"
            f'<strong>{escape_html(str(item.get("title", "")))}</strong>'
            f'<small>{escape_html(str(item.get("description", "")))}</small>'
            "</span>"
            "</label>"
            + _dimension_rule_editor(item, rulebook.get(item_key, {}))
            + "</div>"
        )

    dimension_items = "".join(_dimension_item(item) for item in DIMENSION_CATALOG)
    hidden_rule_editor = (
        '<div id="dimension-rule-editor-modal" class="contract-compat" aria-hidden="true">'
        "导入前编辑规则 进入右侧编辑面板"
        "</div>"
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
    fold_open = "" if submit_context == "import" else " open"
    return f"""
    <div class="review-profile-box">
      <div class="review-profile-head">
        <strong>审查配置</strong>
      </div>
      <div class="review-profile-preset-row">
        {preset_items}
      </div>
      <input type="hidden" name="review_profile_preset" value="{escape_html(normalized['preset_key'])}">
      <input type="hidden" name="review_dimensions_present" value="1">
      <details class="review-profile-fold"{fold_open}>
        <summary>
          <span>调整审查参数</span>
        </summary>
        <div class="review-profile-fold-body">
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
            <span>补充指令</span>
            <textarea name="llm_instruction" rows="2" placeholder="可选，对审查方向的额外要求">{escape_html(normalized["llm_instruction"])}</textarea>
          </label>
          <div class="dimension-choice-grid">
            {dimension_items}
          </div>
          {hidden_rule_editor}
        </div>
      </details>
    </div>
    """


__all__ = ["render_review_profile_form_fields"]
