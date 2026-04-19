from __future__ import annotations

import pytest

from tests.helpers.contracts import renderable_text, require_symbol


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.review
@pytest.mark.ai
def test_ai_review_service_supports_mock_provider():
    generate_case_ai_review = require_symbol(
        "app.core.reviewers.ai.service",
        "generate_case_ai_review",
    )
    result = generate_case_ai_review(
        case_payload={"software_name": "极光关节运动分析系统", "version": "V1.0"},
        rule_results={"issues": [{"severity": "moderate", "desc": "版本号不一致"}]},
        provider="mock",
    )
    text = renderable_text(result)
    assert text


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.review
@pytest.mark.ai
def test_ai_review_returns_structured_summary_fields():
    generate_case_ai_review = require_symbol(
        "app.core.reviewers.ai.service",
        "generate_case_ai_review",
    )
    result = generate_case_ai_review(
        case_payload={"software_name": "极光关节运动分析系统", "version": "V1.0"},
        rule_results={"issues": [{"severity": "moderate", "desc": "版本号不一致"}]},
        provider="mock",
    )
    text = renderable_text(result)
    assert "结论" in text or "conclusion" in text

