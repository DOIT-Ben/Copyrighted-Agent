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
          <span>规则名</span>
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


def _inline_rule_editor(key: str, rule: dict) -> str:
    checkpoints = format_rule_checkpoints(list(rule.get("checkpoints", []) or []))
    enabled_rule_count = sum(1 for item in list(rule.get("rules", []) or []) if item.get("enabled", True))
    rule_items = "".join(_rule_item_editor(key, item) for item in list(rule.get("rules", []) or []))
    return f"""
    <details class="dimension-rule-editor">
      <summary>
        <span>导入前编辑规则</span>
        <small>已启用 {enabled_rule_count} 项检查点，点开后进入右侧编辑面板</small>
      </summary>
      <div class="dimension-rule-editor-modal" role="dialog" aria-modal="true" aria-label="导入前编辑规则">
        <div class="dimension-rule-editor-backdrop"></div>
        <div class="dimension-rule-editor-window">
          <div class="dimension-rule-editor-window-head">
            <div class="dimension-rule-editor-window-copy">
              <span class="dimension-rule-editor-kicker">右侧编辑面板</span>
              <strong>{escape_html(rule.get("title", ""))}</strong>
              <small>只处理当前维度。先改规则项，再补检查点和提示语，避免在首页堆太多信息。</small>
            </div>
            <div class="dimension-rule-editor-window-meta">
              <span class="dimension-rule-editor-chip">规则项 {enabled_rule_count}</span>
              <span class="dimension-rule-editor-close">再次点击入口即可收起</span>
            </div>
          </div>
          <div class="dimension-rule-editor-body">
            <div class="dimension-rule-editor-grid">
              <label class="field">
                <span>规则名称</span>
                <input type="text" name="rule_{escape_html(key)}_title" value="{escape_html(rule.get('title', ''))}">
              </label>
              <label class="field">
                <span>审查目标</span>
                <textarea name="rule_{escape_html(key)}_objective" rows="3">{escape_html(rule.get('objective', ''))}</textarea>
              </label>
            </div>
            <div class="dimension-rule-editor-section">
              <div class="dimension-rule-editor-section-head">
                <strong>规则项</strong>
                <small>这里决定导入后会重点命中哪些判断条件。</small>
              </div>
              <div class="rule-item-stack">
                {rule_items}
              </div>
            </div>
            <div class="dimension-rule-editor-grid dimension-rule-editor-grid-wide">
              <label class="field">
                <span>检查点摘要</span>
                <textarea name="rule_{escape_html(key)}_checkpoints" rows="5">{escape_html(checkpoints)}</textarea>
              </label>
              <label class="field">
                <span>LLM 关注点</span>
                <textarea name="rule_{escape_html(key)}_llm_focus" rows="5">{escape_html(rule.get('llm_focus', ''))}</textarea>
              </label>
            </div>
          </div>
        </div>
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
                "查看完整规则</a>"
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
        "只保留本次审查需要关注的重点，详细规则按需打开小窗即可。"
        if submit_context == "import"
        else "修改后会保存到当前批次，并用于下一次重跑审查。"
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
      <details class="review-profile-fold" open>
        <summary>
          <span>调整本次审查要求</span>
          <small>可切换预设、勾选维度和补充 LLM 指令</small>
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
            <span>LLM 补充指令</span>
            <textarea name="llm_instruction" rows="3" placeholder="例如：重点关注申请人排序一致性、协议日期逻辑和源码脱敏。">{escape_html(normalized["llm_instruction"])}</textarea>
          </label>
          <div class="dimension-choice-grid">
            {dimension_items}
          </div>
        </div>
      </details>
      <div class="review-profile-footnote">
        <span>详细规则只会影响当前这次导入或重跑。</span>
      </div>
    </div>
    """


__all__ = ["render_review_profile_form_fields"]
