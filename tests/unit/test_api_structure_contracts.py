from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.unit
@pytest.mark.contract
def test_api_main_stays_a_thin_app_entrypoint():
    main_source = Path("app/api/main.py").read_text(encoding="utf-8")

    assert len(main_source.splitlines()) <= 80
    assert "from app.api.routes import register_routes" in main_source
    assert "from app.api.startup import prepare_runtime" in main_source
    assert "register_routes(app)" in main_source
    assert "prepare_runtime(testing=testing)" in main_source
    assert "register_upload_routes" not in main_source
    assert "register_download_routes" not in main_source
    assert "recover_interrupted_jobs" not in main_source
    assert "load_all_into_store" not in main_source


@pytest.mark.unit
@pytest.mark.contract
def test_api_routes_module_is_the_route_registration_composition_root():
    routes_source = Path("app/api/routes.py").read_text(encoding="utf-8")

    expected_registrars = (
        "register_page_routes",
        "register_static_routes",
        "register_upload_routes",
        "register_api_read_routes",
        "register_rule_routes",
        "register_job_retry_routes",
        "register_correction_api_routes",
        "register_correction_page_routes",
        "register_download_routes",
    )

    assert "def register_routes(app: FastAPI) -> None:" in routes_source
    for registrar in expected_registrars:
        assert registrar in routes_source
