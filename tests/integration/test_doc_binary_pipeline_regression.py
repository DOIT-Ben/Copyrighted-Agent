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
def test_legacy_doc_can_be_classified_from_extracted_utf16le_content(tmp_path: Path):
    ingest_submission = require_symbol("app.core.pipelines.submission_pipeline", "ingest_submission")
    zip_path = _write_zip(
        tmp_path / "legacy_doc_content_recovery.zip",
        {
            "bundle/generic.doc": (
                b"\xd0\xcf\x11\xe0"
                + (
                    "甲方：江西中医药大学\n"
                    "乙方：杭州极光灵愈人工智能科技有限公司\n"
                    "经双方友好协商，就合作开发“居家康复陪伴机器人”V1.0达成以下协议。\n"
                    "本协议自双方签订之日起生效。\n"
                ).encode("utf-16-le")
            ),
        },
    )

    result = ingest_submission(zip_path=zip_path, mode="single_case_package")
    materials = get_value(result, "materials", [])
    parse_results = get_value(result, "parse_results", [])

    assert len(materials) == 1
    assert materials[0]["material_type"] == "agreement"
    assert parse_results[0]["metadata_json"]["parse_quality"]["quality_level"] in {"high", "medium"}
    assert parse_results[0]["metadata_json"]["triage"]["needs_manual_review"] is False
    assert isinstance(parse_results[0]["metadata_json"].get("page_segments", []), list)
