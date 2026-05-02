from __future__ import annotations

from pathlib import Path

import pytest


UTF8_TARGETS = [
    Path("README.md"),
    Path("app/web/README.md"),
    Path("docs/dev/221-encoding-governance-audit-log.md"),
]


@pytest.mark.non_functional
@pytest.mark.contract
def test_key_docs_are_utf8_readable():
    for target in UTF8_TARGETS:
        text = target.read_text(encoding="utf-8")
        assert text.strip(), f"{target} should not be empty"
