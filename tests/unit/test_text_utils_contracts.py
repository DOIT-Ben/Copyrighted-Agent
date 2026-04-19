from __future__ import annotations

import pytest

from tests.helpers.contracts import require_symbol


@pytest.mark.unit
@pytest.mark.contract
def test_clean_text_removes_non_printable_control_characters():
    clean_text = require_symbol("app.core.utils.text", "clean_text")

    cleaned = clean_text("软件名称\x07：测试系统\x0b\n版本号\x03：V1.0\n")

    assert "\x07" not in cleaned
    assert "\x0b" not in cleaned
    assert "\x03" not in cleaned
    assert "软件名称" in cleaned
    assert "版本号" in cleaned
