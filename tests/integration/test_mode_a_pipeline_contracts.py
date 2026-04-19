from __future__ import annotations

import pytest

from tests.helpers.contracts import get_value, require_symbol


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.zip
def test_mode_a_zip_creates_single_case_and_preserves_materials(mode_a_zip_path):
    ingest_submission = require_symbol(
        "app.core.pipelines.submission_pipeline",
        "ingest_submission",
    )
    result = ingest_submission(zip_path=mode_a_zip_path, mode="single_case_package")
    cases = get_value(result, "cases", [])
    materials = get_value(result, "materials", [])
    assert len(cases) == 1
    assert len(materials) >= 4


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.zip
def test_mode_a_accepts_root_level_bundle_without_nested_directories(mode_a_root_level_zip_path):
    ingest_submission = require_symbol(
        "app.core.pipelines.submission_pipeline",
        "ingest_submission",
    )
    result = ingest_submission(zip_path=mode_a_root_level_zip_path, mode="single_case_package")
    cases = get_value(result, "cases", [])
    assert len(cases) == 1


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.zip
def test_mode_a_zip_with_windows_unsafe_filenames_still_completes(zip_with_windows_unsafe_names_path):
    ingest_submission = require_symbol(
        "app.core.pipelines.submission_pipeline",
        "ingest_submission",
    )
    result = ingest_submission(zip_path=zip_with_windows_unsafe_names_path, mode="single_case_package")
    cases = get_value(result, "cases", [])
    materials = get_value(result, "materials", [])
    assert len(cases) == 1
    assert len(materials) == 3
    assert all(":" not in item["original_filename"] for item in materials)
