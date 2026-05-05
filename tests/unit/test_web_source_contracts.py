from __future__ import annotations

from pathlib import Path

import pytest

from tests.helpers.contracts import require_symbol


EXPECTED_EXPORT_MAP = {
    "render_app_script": "app.web.view_helpers",
    "render_case_detail": "app.web.page_case",
    "render_home_page": "app.web.page_home",
    "render_ops_page": "app.web.page_ops",
    "render_report_page": "app.web.page_report",
    "render_stylesheet": "app.web.view_helpers",
    "render_submission_detail": "app.web.page_submission",
    "render_submissions_index": "app.web.page_submission",
}

CANONICAL_LOCALIZED_TERMS = (
    "\u8f6f\u8457",
    "\u5bfc\u5165",
    "\u7f3a\u5c11",
    "\u4ec5\u652f\u6301",
    "\u6a21\u5f0f",
    "\u6587\u4ef6",
)


def _build_known_mojibake_markers() -> tuple[str, ...]:
    markers: set[str] = set()
    for term in CANONICAL_LOCALIZED_TERMS:
        utf8_bytes = term.encode("utf-8")
        for encoding in ("gbk", "cp936", "latin-1"):
            marker = utf8_bytes.decode(encoding, errors="ignore")
            if marker and marker != term:
                markers.add(marker)
    return tuple(sorted(markers))


@pytest.mark.unit
@pytest.mark.contract
def test_pages_barrel_exports_expected_renderers():
    pages_module = __import__("app.web.pages", fromlist=["__all__"])
    assert set(getattr(pages_module, "__all__", [])) == set(EXPECTED_EXPORT_MAP)

    for export_name, module_name in EXPECTED_EXPORT_MAP.items():
        exported_symbol = require_symbol("app.web.pages", export_name)
        direct_symbol = require_symbol(module_name, export_name)
        assert exported_symbol is direct_symbol


@pytest.mark.unit
@pytest.mark.contract
def test_app_web_readme_documents_module_map_and_windows_guardrail():
    readme_path = Path("app/web/README.md")
    readme_text = readme_path.read_text(encoding="utf-8")

    assert "view_helpers.py" in readme_text
    assert "pages.py" in readme_text
    assert "apply_patch" in readme_text
    assert "unicode_escape" in readme_text
    assert "PowerShell" in readme_text


@pytest.mark.unit
@pytest.mark.contract
def test_active_web_source_files_avoid_known_mojibake_markers():
    source_paths = sorted(Path("app/web").glob("*.py")) + [Path("app/api/main.py")]
    markers = _build_known_mojibake_markers()

    for path in source_paths:
        text = path.read_text(encoding="utf-8")
        assert "\ufffd" not in text, str(path)
        for marker in markers:
            assert marker not in text, f"{path} contains suspicious mojibake marker: {marker}"
