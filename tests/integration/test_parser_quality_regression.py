from __future__ import annotations

from pathlib import Path
import zipfile

import pytest

from tests.helpers.contracts import get_value, require_symbol


def _write_zip(zip_path: Path, files: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative_path, content in files.items():
            archive.writestr(relative_path, content)
    return zip_path


@pytest.mark.integration
@pytest.mark.contract
def test_low_quality_binary_doc_is_not_auto_classified_from_noisy_content(tmp_path: Path):
    ingest_submission = require_symbol("app.core.pipelines.submission_pipeline", "ingest_submission")
    zip_path = _write_zip(
        tmp_path / "binary_doc_quality_gate.zip",
        {
            "bundle/generic.doc": b"\xd0\xcf\x11\xe0def sample():\n    return 1\n",
        },
    )

    result = ingest_submission(zip_path=zip_path, mode="single_case_package")
    materials = get_value(result, "materials", [])
    parse_results = get_value(result, "parse_results", [])

    assert len(materials) == 1
    assert materials[0]["material_type"] == "unknown"
    assert parse_results[0]["metadata_json"]["parse_quality"]["quality_level"] == "low"
    assert parse_results[0]["metadata_json"]["triage"]["unknown_reason"] == "blocked_low_quality_content_signal"
