from __future__ import annotations

from pathlib import Path

import pytest


UTF8_TARGETS = [
    Path("README.md"),
    Path("app/web/README.md"),
    Path("docs/ENCODING.md"),
    Path("docs/PROJECT_STRUCTURE.md"),
    Path("docs/dev/221-encoding-governance-audit-log.md"),
    Path("app/web/page_home.py"),
    Path("app/web/static/app.js"),
    Path("app/web/static/styles.css"),
    Path(".github/workflows/ci.yml"),
    Path(".gitattributes"),
    Path("pyproject.toml"),
]

MOJIBAKE_MARKERS = (
    "\ufffd",
    "鍒嗘",
    "鎵规",
    "瀵煎",
    "鏌ョ",
    "绯荤",
)


@pytest.mark.non_functional
@pytest.mark.contract
def test_key_docs_are_utf8_readable():
    for target in UTF8_TARGETS:
        text = target.read_text(encoding="utf-8")
        assert text.strip(), f"{target} should not be empty"
        for marker in MOJIBAKE_MARKERS:
            assert marker not in text, f"{target} contains suspicious mojibake marker: {marker}"


@pytest.mark.non_functional
@pytest.mark.contract
def test_encoding_guardrail_documents_windows_safe_workflow():
    text = Path("docs/ENCODING.md").read_text(encoding="utf-8")
    assert "UTF-8" in text
    assert "PowerShell" in text
    assert "unicode_escape" in text
    assert "apply_patch" in text
