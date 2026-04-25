from __future__ import annotations

import os
import sqlite3

import pytest

from tests.helpers.contracts import require_symbol


@pytest.mark.unit
@pytest.mark.contract
def test_sqlite_repository_initializes_required_tables_and_submission_indexes(tmp_path):
    init_db = require_symbol("app.core.services.sqlite_repository", "init_db")

    db_path = tmp_path / "runtime" / "soft_review.db"
    original_sqlite_path = os.environ.get("SOFT_REVIEW_SQLITE_PATH")
    os.environ["SOFT_REVIEW_SQLITE_PATH"] = str(db_path)

    try:
        init_db()
        with sqlite3.connect(db_path) as connection:
            table_rows = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
            index_rows = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
    finally:
        if original_sqlite_path is None:
            os.environ.pop("SOFT_REVIEW_SQLITE_PATH", None)
        else:
            os.environ["SOFT_REVIEW_SQLITE_PATH"] = original_sqlite_path

    tables = {row[0] for row in table_rows}
    indexes = {row[0] for row in index_rows}

    assert {
        "submissions",
        "cases",
        "materials",
        "parse_results",
        "review_results",
        "report_artifacts",
        "jobs",
        "corrections",
    }.issubset(tables)
    assert {
        "idx_cases_submission_id",
        "idx_materials_submission_id",
        "idx_parse_results_submission_id",
        "idx_review_results_submission_id",
        "idx_report_artifacts_submission_id",
        "idx_jobs_submission_id",
        "idx_corrections_submission_id",
    }.issubset(indexes)
