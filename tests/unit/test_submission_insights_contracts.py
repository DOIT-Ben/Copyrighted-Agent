from __future__ import annotations

import pytest

from tests.helpers.contracts import require_symbol


@pytest.mark.unit
@pytest.mark.contract
def test_label_for_correction_reason_returns_label_for_known_code():
    fn = require_symbol("app.core.services.submission_insights", "label_for_correction_reason")
    label = fn("change_material_type")
    assert isinstance(label, str)
    assert label != ""
    assert label != "-"


@pytest.mark.unit
@pytest.mark.contract
def test_label_for_correction_reason_returns_dash_for_empty():
    fn = require_symbol("app.core.services.submission_insights", "label_for_correction_reason")
    assert fn("") == "-"
    assert fn(None) == "-"


@pytest.mark.unit
@pytest.mark.contract
def test_label_for_correction_outcome_returns_label_for_known_code():
    fn = require_symbol("app.core.services.submission_insights", "label_for_correction_outcome")
    label = fn("reduced_unknown_materials")
    assert isinstance(label, str)
    assert label != ""
    assert label != "-"


@pytest.mark.unit
@pytest.mark.contract
def test_parse_diagnostic_snapshot_handles_empty_inputs():
    fn = require_symbol("app.core.services.submission_insights", "parse_diagnostic_snapshot")
    result = fn(None, None)
    assert isinstance(result, dict)
    assert "parse_reason_code" in result
    assert "manual_review_reason_code" in result
    assert "needs_manual_review" in result


@pytest.mark.unit
@pytest.mark.contract
def test_parse_diagnostic_snapshot_extracts_fields():
    fn = require_symbol("app.core.services.submission_insights", "parse_diagnostic_snapshot")
    material = {"material_type": "source_code", "parse_status": "completed", "review_status": "completed"}
    parse_result = {
        "metadata_json": {
            "triage": {"outcome": "accepted", "manual_review_reason_code": ""},
            "parse_quality": {"quality_level": "good"},
        }
    }
    result = fn(material, parse_result)
    assert result["parse_reason_code"] == ""
    assert result["needs_manual_review"] is False
    assert result["quality_level"] == "good"


@pytest.mark.unit
@pytest.mark.contract
def test_build_correction_analysis_detects_reduced_unknown():
    fn = require_symbol("app.core.services.submission_insights", "build_correction_analysis")
    before = {"unknown_materials": 3, "manual_review_materials": 0, "low_quality_materials": 0, "pending_cases": 0}
    after = {"unknown_materials": 1, "manual_review_materials": 0, "low_quality_materials": 0, "pending_cases": 0}
    result = fn(before, after)
    assert result["outcome_code"] == "reduced_unknown_materials"
    assert result["delta"]["unknown_materials"] == -2


@pytest.mark.unit
@pytest.mark.contract
def test_build_correction_analysis_detects_no_change():
    fn = require_symbol("app.core.services.submission_insights", "build_correction_analysis")
    metrics = {"unknown_materials": 0, "manual_review_materials": 0, "low_quality_materials": 0, "pending_cases": 0}
    result = fn(metrics, dict(metrics))
    assert result["outcome_code"] == "no_material_change_detected"


@pytest.mark.unit
@pytest.mark.contract
def test_build_correction_analysis_detects_reduced_manual_review():
    fn = require_symbol("app.core.services.submission_insights", "build_correction_analysis")
    before = {"unknown_materials": 0, "manual_review_materials": 2, "low_quality_materials": 0, "pending_cases": 0}
    after = {"unknown_materials": 0, "manual_review_materials": 0, "low_quality_materials": 0, "pending_cases": 0}
    result = fn(before, after)
    assert result["outcome_code"] == "reduced_manual_review_load"
