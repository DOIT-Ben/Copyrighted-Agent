from __future__ import annotations

import json

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
    review_results = get_value(result, "review_results", [])
    prompt_snapshot = get_value(review_results[0], "prompt_snapshot_json", {})
    user_prompt = get_value(prompt_snapshot, "user_prompt", "")
    prompt_payload = json.loads(user_prompt.split("Desensitized case payload JSON:\n", 1)[1].split("\n\nRule results JSON:", 1)[0])
    assert prompt_payload["material_count"] == len(materials)
    assert prompt_payload["material_type_counts"].get("agreement", 0) <= len(
        [item for item in materials if item["material_type"] == "agreement"]
    )


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
