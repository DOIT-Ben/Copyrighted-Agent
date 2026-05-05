from __future__ import annotations

from pathlib import Path

import pytest


UTF8_TARGETS = [
    Path("README.md"),
    Path("app/web/README.md"),
    Path("docs/ENCODING.md"),
    Path("docs/PROJECT_STRUCTURE.md"),
    Path("docs/dev/221-encoding-governance-audit-log.md"),
    Path(".github/workflows/ci.yml"),
    Path(".gitattributes"),
    Path("pyproject.toml"),
]


@pytest.mark.non_functional
@pytest.mark.contract
def test_key_docs_are_utf8_readable():
    for target in UTF8_TARGETS:
        text = target.read_text(encoding="utf-8")
        assert text.strip(), f"{target} should not be empty"


@pytest.mark.non_functional
@pytest.mark.contract
def test_encoding_guardrail_documents_windows_safe_workflow():
    text = Path("docs/ENCODING.md").read_text(encoding="utf-8")
    assert "UTF-8" in text
    assert "PowerShell" in text
    assert "unicode_escape" in text
    assert "apply_patch" in text
