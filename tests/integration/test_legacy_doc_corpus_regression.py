from __future__ import annotations

from pathlib import Path

import pytest

from tests.helpers.contracts import require_symbol


CORPUS_ROOT = Path("tests") / "fixtures" / "legacy_doc_corpus"


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.parametrize(
    ("relative_path", "material_type", "expected_bucket", "expected_reason"),
    [
        ("usable_text/agreement_2505.doc", "agreement", "usable_text", "clean_text_ready"),
        ("partial_fragments/info_form.doc", "info_form", "usable_text", "clean_text_ready"),
        ("binary_noise/source_code_2502.doc", "source_code", "usable_text", "clean_text_ready"),
    ],
)
def test_legacy_doc_corpus_samples_keep_expected_quality_buckets(
    relative_path: str,
    material_type: str,
    expected_bucket: str,
    expected_reason: str,
):
    parse_material = require_symbol("app.core.parsers.service", "parse_material")

    file_path = CORPUS_ROOT / relative_path
    assert file_path.exists(), f"missing corpus sample: {file_path}"

    result = parse_material(file_path=file_path, material_type=material_type)
    quality = result["quality"]

    assert quality["legacy_doc_bucket"] == expected_bucket
    assert quality["review_reason_code"] == expected_reason
