from __future__ import annotations

from app.core.services.review_profile import dimension_title, normalize_review_profile
from app.core.services.review_rulebook import default_dimension_rule, dimension_rulebook_from_profile, format_rule_checkpoints
from app.core.utils.text import escape_html
from app.web.view_helpers import icon, layout, link, list_pairs, panel, pill, table


def _summary_tile(label: str, value: str, note: str) -> str:
    return (
        '<div class="summary-tile">'
        f"<span>{escape_html(label)}</span>"
        f"<strong>{escape_html(value)}</strong>"
        f"<small>{escape_html(note)}</small>"
        "</div>"
    )


def _checkpoint_list(title: str, checkpoints: list[str]) -> str:
    items = "".join(f"<li>{escape_html(item)}</li>" for item in checkpoints)
    return f'<div class="rule-checkpoint-list"><strong>{escape_html(title)}</strong><ul>{items}</ul></div>'


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
    is_enabled = dimension_key in review_profile.get("enabled_dimensions", [])

    case_options = "".join(
        f'<option value="{escape_html(case.get("id", ""))}"{" selected" if case.get("id", "") == selected_case_id else ""}>'
        f'{escape_html(case.get("case_name", "") or case.get("software_name", "") or case.get("id", ""))}</option>'
        for case in cases
    ) or '<option value="">暂无项目</option>'

    checkpoints_text = format_rule_checkpoints(rule_entry.get("checkpoints", []))
    summary_tiles = "".join(
        [
            _summary_tile("维度", rule_entry.get("title", dimension_title(dimension_key)), "当前可编辑的审查重点"),
            _summary_tile("状态", "已启用" if is_enabled else "未启用", "是否参与当前批次审查"),
            _summary_tile("检查点", str(len(rule_entry.get("checkpoints", []) or [])), "会拼入 LLM 提示词"),
        ]
    )

    prompt_preview_pairs = [
        ("规则名称", escape_html(rule_entry.get("title", dimension_title(dimension_key)))),
        ("审查目标", escape_html(rule_entry.get("objective", "") or "-")),
        ("LLM 关注点", escape_html(rule_entry.get("llm_focus", "") or "-")),
    ]
    compare_rows = [
        ["规则名称", escape_html(default_rule.get("title", "")), escape_html(rule_entry.get("title", ""))],
        ["审查目标", escape_html(default_rule.get("objective", "")), escape_html(rule_entry.get("objective", ""))],
        ["LLM 关注点", escape_html(default_rule.get("llm_focus", "")), escape_html(rule_entry.get("llm_focus", ""))],
        [
            "检查点数量",
            escape_html(str(len(default_rule.get("checkpoints", []) or []))),
            escape_html(str(len(rule_entry.get("checkpoints", []) or []))),
        ],
    ]

    editor_body = f"""
    <form class="operator-form rule-editor-form" action="/submissions/{escape_html(submission_id)}/review-rules/{escape_html(dimension_key)}" method="post">
      <label class="field">
        <span>规则名称</span>
        <input type="text" name="title" value="{escape_html(rule_entry.get('title', ''))}" required>
      </label>
      <label class="field">
        <span>审查目标</span>
        <textarea name="objective" rows="4" required>{escape_html(rule_entry.get('objective', ''))}</textarea>
      </label>
      <label class="field">
        <span>检查点</span>
        <textarea name="checkpoints" rows="10" required>{escape_html(checkpoints_text)}</textarea>
        <span class="field-hint">每行一条规则。保存后会同步到当前批次的提示词规则里。</span>
      </label>
      <label class="field">
        <span>LLM 关注点</span>
        <textarea name="llm_focus" rows="4">{escape_html(rule_entry.get('llm_focus', ''))}</textarea>
      </label>
      <label class="field">
        <span>保存后重跑项目</span>
        <select name="case_id">{case_options}</select>
      </label>
      <label class="field">
        <span>备注</span>
        <input type="text" name="note" placeholder="记录这次规则调整原因">
      </label>
      <div class="inline-actions rule-editor-actions">
        <button class="button-primary" type="submit" name="action" value="save">{icon("check", "icon icon-sm")}保存规则</button>
        <button class="button-secondary" type="submit" name="action" value="save_and_rerun">{icon("refresh", "icon icon-sm")}保存并重跑</button>
        <button class="button-secondary" type="submit" name="action" value="restore_default">{icon("refresh", "icon icon-sm")}恢复默认</button>
        <a class="button-secondary" href="/submissions/{escape_html(submission_id)}/operator">{icon("wrench", "icon icon-sm")}人工干预台</a>
      </div>
    </form>
    """

    preview_body = (
        list_pairs(prompt_preview_pairs, css_class="dossier-list dossier-list-single")
        + _checkpoint_list("当前检查点", rule_entry.get("checkpoints", []))
    )
    default_preview_body = _checkpoint_list("默认检查点", default_rule.get("checkpoints", []))

    content = f"""
    <section class="dashboard-grid rule-layout">
      {panel('规则概览', f'<div class="summary-grid">{summary_tiles}</div>', extra_class='span-12 panel-soft', icon_name='shield', panel_id='rule-summary')}
      {panel('编辑规则', editor_body, extra_class='span-7 rule-editor-panel', icon_name='wrench', panel_id='rule-editor')}
      {panel('提示词预览', preview_body, extra_class='span-5 rule-preview-panel', icon_name='search', panel_id='rule-preview')}
      {panel('默认对照', table(['字段', '默认规则', '当前规则'], compare_rows) + default_preview_body, extra_class='span-12', icon_name='layers', panel_id='rule-compare')}
    </section>
    """

    return layout(
        title=f"{dimension_title(dimension_key)} - 审查规则",
        active_nav="submissions",
        header_tag="审查规则",
        header_title=rule_entry.get("title", dimension_title(dimension_key)),
        header_subtitle="编辑这个维度的审查目标、检查点和 LLM 关注点。",
        header_meta="".join(
            [
                pill("已启用" if is_enabled else "未启用", "success" if is_enabled else "warning"),
                link(f"/submissions/{submission_id}", "返回批次", css_class="button-secondary button-compact"),
            ]
        ),
        content=content,
        header_note="",
        page_links=[
            ("#rule-editor", "编辑规则", "wrench"),
            ("#rule-preview", "提示词预览", "search"),
            ("#rule-compare", "默认对照", "layers"),
        ],
    )


__all__ = ["render_review_rule_detail_page"]
