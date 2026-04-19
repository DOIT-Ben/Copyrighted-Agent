from __future__ import annotations

import pytest

from tests.helpers.contracts import get_field_names, require_symbol


@pytest.mark.unit
@pytest.mark.contract
def test_submission_mode_enum_contains_supported_modes():
    SubmissionMode = require_symbol("app.core.domain.enums", "SubmissionMode")
    values = {item.value for item in SubmissionMode}
    assert {"single_case_package", "batch_same_material"} <= values


@pytest.mark.unit
@pytest.mark.contract
def test_material_type_enum_contains_required_values():
    MaterialType = require_symbol("app.core.domain.enums", "MaterialType")
    values = {item.value for item in MaterialType}
    assert {"info_form", "source_code", "software_doc", "agreement", "unknown"} <= values


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.parametrize(
    ("module_name", "symbol_name", "expected_fields"),
    [
        (
            "app.core.domain.models",
            "Submission",
            {"id", "mode", "filename", "storage_path", "status", "created_at"},
        ),
        (
            "app.core.domain.models",
            "Case",
            {"id", "case_name", "software_name", "version", "company_name", "status"},
        ),
        (
            "app.core.domain.models",
            "Material",
            {
                "id",
                "case_id",
                "submission_id",
                "material_type",
                "original_filename",
                "storage_path",
                "file_ext",
                "parse_status",
                "review_status",
            },
        ),
        (
            "app.core.domain.models",
            "ParseResult",
            {"material_id", "raw_text_path", "clean_text_path", "desensitized_text_path", "metadata_json"},
        ),
        (
            "app.core.domain.models",
            "ReviewResult",
            {"id", "scope_type", "scope_id", "reviewer_type", "issues_json", "conclusion"},
        ),
        (
            "app.core.domain.models",
            "ReportArtifact",
            {"id", "scope_type", "scope_id", "report_type", "file_format", "storage_path"},
        ),
        (
            "app.core.domain.models",
            "Job",
            {"id", "job_type", "scope_type", "scope_id", "status", "progress"},
        ),
    ],
)
def test_core_domain_models_expose_minimum_required_fields(module_name, symbol_name, expected_fields):
    model_cls = require_symbol(module_name, symbol_name)
    assert expected_fields <= get_field_names(model_cls)

