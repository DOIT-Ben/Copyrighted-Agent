from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.unit
@pytest.mark.contract
def test_legacy_web_start_scripts_delegate_to_uv_entrypoint():
    mock_script = Path("scripts/start_mock_web.ps1").read_text(encoding="utf-8")
    real_script = Path("scripts/start_real_web.ps1").read_text(encoding="utf-8")

    assert "start_uv_web.ps1" in mock_script
    assert "start_uv_web.ps1" in real_script
    assert "-Mock" in mock_script
    assert "-Endpoint $Endpoint" in real_script
    assert "py -m app.api.main" not in mock_script
    assert "py -m app.api.main" not in real_script
