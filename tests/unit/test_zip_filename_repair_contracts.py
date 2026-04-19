from __future__ import annotations

import pytest

from tests.helpers.contracts import require_symbol


@pytest.mark.unit
@pytest.mark.contract
def test_repair_member_name_recovers_utf8_mojibake():
    repair_member_name = require_symbol("app.core.services.zip_ingestion", "_repair_member_name")
    original = "\u8f6f\u8457\u7533\u8bf7/\u4fe1\u606f\u91c7\u96c6\u8868.doc"
    garbled = original.encode("utf-8").decode("cp437")
    assert repair_member_name(garbled) == original


@pytest.mark.unit
@pytest.mark.contract
def test_repair_member_name_recovers_gbk_mojibake():
    repair_member_name = require_symbol("app.core.services.zip_ingestion", "_repair_member_name")
    original = "\u8d44\u6599/\u5408\u4f5c\u534f\u8bae.doc"
    garbled = original.encode("gbk").decode("cp437")
    assert repair_member_name(garbled) == original
