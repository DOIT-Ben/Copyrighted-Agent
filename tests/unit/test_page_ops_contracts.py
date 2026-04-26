from __future__ import annotations

import pytest

from tests.helpers.contracts import require_symbol


@pytest.mark.unit
@pytest.mark.contract
def test_ops_callout_prefers_summary_for_pass_state():
    ops_callout_text = require_symbol("app.web.page_ops", "_ops_callout_text")

    result = ops_callout_text(
        "pass",
        "Release gate is satisfied for the current environment.",
        "",
        "先清掉阻塞项，再继续真实联调。",
    )

    assert result == "Release gate is satisfied for the current environment."


@pytest.mark.unit
@pytest.mark.contract
def test_ops_callout_prefers_action_for_warning_state():
    ops_callout_text = require_symbol("app.web.page_ops", "_ops_callout_text")

    result = ops_callout_text(
        "warning",
        "Provider readiness is incomplete.",
        "Complete provider readiness before retrying the release gate.",
        "先确认 provider、endpoint、API key 和脱敏边界。",
    )

    assert result == "Complete provider readiness before retrying the release gate."


@pytest.mark.unit
@pytest.mark.contract
def test_closeout_action_list_has_positive_empty_state_copy():
    closeout_action_list = require_symbol("app.web.page_ops", "_closeout_action_list")

    result = closeout_action_list([])

    assert "当前没有额外动作" in result
    assert "继续交付" in result
