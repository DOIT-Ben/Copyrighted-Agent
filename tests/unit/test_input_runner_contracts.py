from __future__ import annotations

import pytest

from tests.helpers.contracts import require_symbol


@pytest.mark.unit
@pytest.mark.contract
def test_input_runner_metrics_include_unknown_and_review_counts():
    metrics_from_result = require_symbol("app.tools.input_runner", "_metrics_from_result")

    metrics = metrics_from_result(
        {
            "materials": [
                {"material_type": "agreement"},
                {"material_type": "unknown"},
            ],
            "cases": [{"id": "case_1"}],
            "reports": [{"id": "rep_1"}],
            "parse_results": [
                {
                    "metadata_json": {
                        "privacy": {"total_replacements": 3},
                        "triage": {"needs_manual_review": True, "quality_review_reason_code": "noise_too_high"},
                        "parse_quality": {"quality_level": "low", "review_reason_code": "noise_too_high"},
                    }
                },
                {
                    "metadata_json": {
                        "privacy": {"total_replacements": 1},
                        "triage": {"needs_manual_review": False, "quality_review_reason_code": "noise_too_high"},
                        "parse_quality": {"quality_level": "medium", "review_reason_code": "noise_too_high"},
                    }
                },
            ],
        }
    )

    assert metrics["materials"] == 2
    assert metrics["cases"] == 1
    assert metrics["reports"] == 1
    assert metrics["unknown"] == 1
    assert metrics["needs_review"] == 1
    assert metrics["low_quality"] == 1
    assert metrics["redactions"] == 4
    assert metrics["review_reasons"] == {"noise_too_high": 2}
    assert metrics["legacy_doc_buckets"] == {}
