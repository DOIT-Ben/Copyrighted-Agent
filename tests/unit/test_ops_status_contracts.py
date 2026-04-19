from __future__ import annotations

import json
import os
import zipfile
from pathlib import Path

import pytest

from tests.helpers.contracts import require_symbol


@pytest.mark.unit
@pytest.mark.contract
def test_latest_runtime_backup_status_reads_manifest_from_newest_archive(tmp_path: Path):
    latest_runtime_backup_status = require_symbol("app.core.services.ops_status", "latest_runtime_backup_status")

    backups_root = tmp_path / "backups"
    backups_root.mkdir(parents=True, exist_ok=True)
    archive_path = backups_root / "runtime_backup_20260419_2300.zip"
    manifest = {
        "created_at": "2026-04-19T23:00:00",
        "entries": [{"archive_path": "runtime/sample.txt"}],
        "sqlite_snapshot": {"mode": "sqlite_backup_api"},
    }
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False))

    status = latest_runtime_backup_status(backups_root)

    assert status["status"] == "ok"
    assert status["file_name"] == archive_path.name
    assert status["entry_count"] == 1
    assert status["sqlite_snapshot_mode"] == "sqlite_backup_api"


@pytest.mark.unit
@pytest.mark.contract
def test_latest_metrics_baseline_status_aggregates_totals_from_snapshot_payload(tmp_path: Path):
    latest_metrics_baseline_status = require_symbol("app.core.services.ops_status", "latest_metrics_baseline_status")

    dev_root = tmp_path / "docs" / "dev"
    dev_root.mkdir(parents=True, exist_ok=True)
    baseline_path = dev_root / "real-sample-baseline.json"
    baseline_path.write_text(
        json.dumps(
            {
                "snapshot": {
                    "generated_at": "2026-04-19T23:10:00",
                    "targets": [
                        {
                            "label": "mode_a_real",
                            "mode": "single_case_package",
                            "path": "input\\软著材料",
                            "aggregate": {"materials": 24, "cases": 6, "reports": 6, "unknown": 0, "needs_review": 8, "low_quality": 8, "redactions": 239},
                        },
                        {
                            "label": "mode_b_real",
                            "mode": "batch_same_material",
                            "path": "input\\合作协议",
                            "aggregate": {"materials": 11, "cases": 10, "reports": 1, "unknown": 0, "needs_review": 2, "low_quality": 2, "redactions": 149},
                        },
                    ],
                },
                "comparison": {"comparisons": [{"label": "mode_a_real", "has_previous": True, "delta": {"needs_review": -2, "low_quality": -2}}]},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    status = latest_metrics_baseline_status(dev_root)

    assert status["status"] == "warning"
    assert status["target_count"] == 2
    assert status["totals"]["needs_review"] == 10
    assert status["totals"]["low_quality"] == 10
    assert status["comparison_available"] is True
    assert status["delta_totals"]["needs_review"] == -2


@pytest.mark.unit
@pytest.mark.contract
def test_list_metrics_baseline_history_returns_latest_first_with_delta_totals(tmp_path: Path):
    list_metrics_baseline_history = require_symbol("app.core.services.ops_status", "list_metrics_baseline_history")

    dev_root = tmp_path / "docs" / "dev"
    history_root = dev_root / "history"
    history_root.mkdir(parents=True, exist_ok=True)

    first = history_root / "real-sample-baseline_20260419_220000.json"
    second = history_root / "real-sample-baseline_20260419_230000.json"
    first.write_text(
        json.dumps({"snapshot": {"generated_at": "2026-04-19T22:00:00", "targets": [{"label": "mode_a", "aggregate": {"needs_review": 10, "low_quality": 10}}]}}, ensure_ascii=False),
        encoding="utf-8",
    )
    second.write_text(
        json.dumps(
            {
                "snapshot": {
                    "generated_at": "2026-04-19T23:00:00",
                    "targets": [{"label": "mode_a", "aggregate": {"needs_review": 0, "low_quality": 0}}],
                },
                "comparison": {"comparisons": [{"label": "mode_a", "has_previous": True, "delta": {"needs_review": -10, "low_quality": -10}}]},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    os.utime(first, (1, 1))
    os.utime(second, (2, 2))

    history = list_metrics_baseline_history(dev_root, limit=5)

    assert len(history) >= 2
    assert history[0]["file_name"] == second.name
    assert history[0]["delta_totals"]["needs_review"] == -10
    assert history[0]["totals"]["needs_review"] == 0
