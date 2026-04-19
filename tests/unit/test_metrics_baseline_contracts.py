from __future__ import annotations

import os
import pytest

from tests.helpers.contracts import require_symbol


@pytest.mark.unit
@pytest.mark.contract
def test_metrics_baseline_can_parse_target_spec():
    parse_target_spec = require_symbol("app.tools.metrics_baseline", "parse_target_spec")

    target = parse_target_spec("mode_a_real|single_case_package|input\\软著材料")

    assert target["label"] == "mode_a_real"
    assert target["mode"] == "single_case_package"
    assert target["path"] == "input\\软著材料"


@pytest.mark.unit
@pytest.mark.contract
def test_metrics_baseline_compare_reports_numeric_deltas():
    compare_baseline_snapshots = require_symbol("app.tools.metrics_baseline", "compare_baseline_snapshots")

    current = {
        "targets": [
            {
                "label": "mode_a_real",
                "aggregate": {"materials": 24, "unknown": 0, "needs_review": 10, "low_quality": 10, "redactions": 239},
            }
        ]
    }
    previous = {
        "targets": [
            {
                "label": "mode_a_real",
                "aggregate": {"materials": 24, "unknown": 1, "needs_review": 10, "low_quality": 10, "redactions": 220},
            }
        ]
    }

    comparison = compare_baseline_snapshots(current, previous)
    target = comparison["comparisons"][0]

    assert target["label"] == "mode_a_real"
    assert target["delta"]["unknown"] == -1
    assert target["delta"]["redactions"] == 19


@pytest.mark.unit
@pytest.mark.contract
def test_metrics_baseline_markdown_renderer_mentions_deltas():
    render_baseline_markdown = require_symbol("app.tools.metrics_baseline", "render_baseline_markdown")

    markdown = render_baseline_markdown(
        {
            "generated_at": "2026-04-19T22:00:00",
            "targets": [
                {
                    "label": "mode_b_real",
                    "mode": "batch_same_material",
                    "path": "input\\合作协议",
                    "aggregate": {"materials": 11, "unknown": 0, "needs_review": 2, "low_quality": 2, "redactions": 149},
                    "entries": [],
                }
            ],
        },
        {
            "comparisons": [
                {
                    "label": "mode_b_real",
                    "delta": {"materials": 0, "unknown": 0, "needs_review": -1, "low_quality": -1, "redactions": 5},
                    "has_previous": True,
                }
            ]
        },
    )

    assert "mode_b_real" in markdown
    assert "needs_review" in markdown
    assert "-1" in markdown or "+-1" in markdown


@pytest.mark.unit
@pytest.mark.contract
def test_metrics_baseline_can_find_latest_snapshot_in_directory(tmp_path):
    find_latest_baseline_json = require_symbol("app.tools.metrics_baseline", "find_latest_baseline_json")

    older = tmp_path / "baseline_old.json"
    newer = tmp_path / "baseline_new.json"
    older.write_text('{"snapshot":{"generated_at":"2026-04-19T22:00:00","targets":[]}}', encoding="utf-8")
    newer.write_text('{"snapshot":{"generated_at":"2026-04-19T23:00:00","targets":[]}}', encoding="utf-8")
    os.utime(older, (1, 1))
    os.utime(newer, (2, 2))

    latest = find_latest_baseline_json(tmp_path)

    assert latest is not None
    assert latest.name == "baseline_new.json"


@pytest.mark.unit
@pytest.mark.contract
def test_metrics_baseline_builds_timestamped_archive_paths():
    build_archive_output_paths = require_symbol("app.tools.metrics_baseline", "build_archive_output_paths")

    paths = build_archive_output_paths("docs/dev/history", archive_stem="real-sample-baseline", generated_at="2026-04-19T23:02:13")

    assert str(paths["json"]).endswith("real-sample-baseline_20260419_230213.json")
    assert str(paths["markdown"]).endswith("real-sample-baseline_20260419_230213.md")
