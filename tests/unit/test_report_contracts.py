from __future__ import annotations

import pytest

from tests.helpers.contracts import renderable_text, require_symbol


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.report
def test_material_report_renderer_contains_title_and_issue_summary():
    render_material_report_markdown = require_symbol(
        "app.core.reports.renderers",
        "render_material_report_markdown",
    )
    report = render_material_report_markdown(
        {
            "material_name": "2501_合作协议.doc",
            "material_type": "agreement",
            "issues": [{"severity": "minor", "desc": "签定应改为签订"}],
            "parse_quality": {
                "quality_level": "low",
                "quality_score": 0.18,
                "review_reason_code": "noise_too_high",
                "review_reason_label": "噪音过多",
                "legacy_doc_bucket": "binary_noise",
                "legacy_doc_bucket_label": "纯噪音",
            },
        }
    )
    text = renderable_text(report)
    assert "合作协议" in text
    assert "签订" in text
    assert "binary_noise" in text or "纯噪音" in text


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.report
def test_case_report_renderer_contains_cross_material_section():
    render_case_report_markdown = require_symbol(
        "app.core.reports.renderers",
        "render_case_report_markdown",
    )
    report = render_case_report_markdown(
        {
            "case_name": "极光关节运动分析系统",
            "materials": ["信息采集表", "源代码", "软著文档", "合作协议"],
            "cross_material_issues": [{"severity": "moderate", "desc": "版本号不一致"}],
            "rule_conclusion": "规则引擎共发现 1 个问题",
            "ai_summary": "建议先统一版本号，再重跑综合审查。",
            "ai_provider": "safe_stub",
            "ai_resolution": "non_mock_safe_payload",
        }
    )
    text = renderable_text(report)
    assert "版本号不一致" in text
    assert "跨材料" in text or "综合" in text
    assert "AI" in text


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.report
def test_batch_report_renderer_contains_file_level_summary():
    render_batch_report_markdown = require_symbol(
        "app.core.reports.renderers",
        "render_batch_report_markdown",
    )
    report = render_batch_report_markdown(
        {
            "submission_name": "agreements_batch.zip",
            "material_type": "agreement",
            "items": [
                {"file_name": "项目A_合作协议.txt", "issues": []},
                {"file_name": "项目B_合作协议.txt", "issues": [{"severity": "minor", "desc": "措辞问题"}]},
            ],
        }
    )
    text = renderable_text(report)
    assert "项目A_合作协议.txt" in text
    assert "项目B_合作协议.txt" in text
