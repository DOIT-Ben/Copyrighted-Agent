from __future__ import annotations

import pytest

from tests.helpers.contracts import get_value, require_symbol


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.zip
def test_mode_b_batch_zip_does_not_force_everything_into_one_case(mode_b_zip_path):
    ingest_submission = require_symbol(
        "app.core.pipelines.submission_pipeline",
        "ingest_submission",
    )
    result = ingest_submission(zip_path=mode_b_zip_path, mode="batch_same_material")
    materials = get_value(result, "materials", [])
    cases = get_value(result, "cases", [])
    assert len(materials) == 3
    assert len(cases) <= 3


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.zip
def test_mode_b_can_leave_low_confidence_materials_unassigned(mode_b_ambiguous_zip_path):
    ingest_submission = require_symbol(
        "app.core.pipelines.submission_pipeline",
        "ingest_submission",
    )
    result = ingest_submission(zip_path=mode_b_ambiguous_zip_path, mode="batch_same_material")
    materials = get_value(result, "materials", [])
    unassigned = [item for item in materials if get_value(item, "case_id", None) in (None, "", 0)]
    assert unassigned

