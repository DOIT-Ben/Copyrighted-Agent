from __future__ import annotations

import os

import pytest

from tests.helpers.contracts import require_symbol


@pytest.mark.unit
@pytest.mark.contract
def test_load_app_config_uses_safe_defaults():
    load_app_config = require_symbol("app.core.services.app_config", "load_app_config")
    config = load_app_config(config_path="config/does-not-exist.json")

    assert config.host == "127.0.0.1"
    assert config.port == 8000
    assert config.ai_enabled is False
    assert config.ai_provider == "mock"


@pytest.mark.unit
@pytest.mark.contract
def test_load_app_config_allows_env_override():
    load_app_config = require_symbol("app.core.services.app_config", "load_app_config")
    original_provider = os.environ.get("SOFT_REVIEW_AI_PROVIDER")
    original_enabled = os.environ.get("SOFT_REVIEW_AI_ENABLED")
    try:
        os.environ["SOFT_REVIEW_AI_PROVIDER"] = "safe_stub"
        os.environ["SOFT_REVIEW_AI_ENABLED"] = "true"
        config = load_app_config(config_path="config/does-not-exist.json")
    finally:
        if original_provider is None:
            os.environ.pop("SOFT_REVIEW_AI_PROVIDER", None)
        else:
            os.environ["SOFT_REVIEW_AI_PROVIDER"] = original_provider
        if original_enabled is None:
            os.environ.pop("SOFT_REVIEW_AI_ENABLED", None)
        else:
            os.environ["SOFT_REVIEW_AI_ENABLED"] = original_enabled

    assert config.ai_provider == "safe_stub"
    assert config.ai_enabled is True
