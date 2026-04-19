from __future__ import annotations

from pathlib import Path
import zipfile

import pytest

from tests.helpers.contracts import get_value, require_symbol


def _write_zip(zip_path: Path, files: dict[str, str]) -> Path:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative_path, content in files.items():
            archive.writestr(relative_path, content)
    return zip_path


@pytest.mark.integration
@pytest.mark.contract
def test_mode_b_accepts_directory_input(tmp_path: Path):
    ingest_submission = require_symbol("app.core.pipelines.submission_pipeline", "ingest_submission")
    batch_dir = tmp_path / "agreements_batch_dir"
    batch_dir.mkdir(parents=True, exist_ok=True)
    (batch_dir / "project_a_agreement.txt").write_text(
        "软件名称：项目A\n甲方：公司甲\n乙方：公司乙\n本协议自双方签订之日起生效。",
        encoding="utf-8",
    )
    (batch_dir / "project_b_agreement.txt").write_text(
        "软件名称：项目B\n甲方：公司丙\n乙方：公司丁\n本协议自双方签订之日起生效。",
        encoding="utf-8",
    )
    (batch_dir / "project_c_agreement.txt").write_text(
        "软件名称：项目C\n甲方：公司戊\n乙方：公司己\n本协议自双方签订之日起生效。",
        encoding="utf-8",
    )

    result = ingest_submission(zip_path=batch_dir, mode="batch_same_material")
    materials = get_value(result, "materials", [])
    assert len(materials) == 3


@pytest.mark.integration
@pytest.mark.contract
def test_pipeline_persists_privacy_manifest(mode_a_zip_path):
    ingest_submission = require_symbol("app.core.pipelines.submission_pipeline", "ingest_submission")
    result = ingest_submission(zip_path=mode_a_zip_path, mode="single_case_package")
    parse_results = get_value(result, "parse_results", [])

    assert parse_results
    manifest_path = Path(parse_results[0]["privacy_manifest_path"])
    assert manifest_path.exists()
    assert "local_manual_redaction_v1" in manifest_path.read_text(encoding="utf-8")


@pytest.mark.integration
@pytest.mark.contract
def test_noisy_zip_entries_are_ignored(tmp_path: Path):
    ingest_submission = require_symbol("app.core.pipelines.submission_pipeline", "ingest_submission")
    zip_path = _write_zip(
        tmp_path / "zip_with_macos_noise.zip",
        {
            "__MACOSX/bundle/._agreement.txt": "noise",
            "bundle/.DS_Store": "noise",
            "bundle/agreement.txt": "软件名称：项目A\n甲方：公司甲\n乙方：公司乙\n本协议自双方签订之日起生效。",
        },
    )

    result = ingest_submission(zip_path=zip_path, mode="batch_same_material")
    materials = get_value(result, "materials", [])
    assert len(materials) == 1
