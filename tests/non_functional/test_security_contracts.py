from __future__ import annotations

from pathlib import Path

import pytest

from tests.helpers.contracts import require_symbol


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.security
@pytest.mark.zip
def test_safe_extract_zip_blocks_zip_slip_entries(zip_with_zip_slip_path, tmp_path: Path):
    safe_extract_zip = require_symbol("app.core.services.zip_ingestion", "safe_extract_zip")
    with pytest.raises(Exception):
        safe_extract_zip(zip_path=zip_with_zip_slip_path, destination=tmp_path)


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.security
@pytest.mark.zip
def test_safe_extract_zip_rejects_executable_files(zip_with_executable_path, tmp_path: Path):
    safe_extract_zip = require_symbol("app.core.services.zip_ingestion", "safe_extract_zip")
    with pytest.raises(Exception):
        safe_extract_zip(zip_path=zip_with_executable_path, destination=tmp_path)


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.security
@pytest.mark.zip
def test_safe_extract_zip_sanitizes_windows_unsafe_filenames(zip_with_windows_unsafe_names_path, tmp_path: Path):
    safe_extract_zip = require_symbol("app.core.services.zip_ingestion", "safe_extract_zip")
    extracted = safe_extract_zip(zip_path=zip_with_windows_unsafe_names_path, destination=tmp_path)
    invalid_chars = '<>:"\\|?*'
    assert extracted
    assert all(not any(char in path.name for char in invalid_chars) for path in extracted)
