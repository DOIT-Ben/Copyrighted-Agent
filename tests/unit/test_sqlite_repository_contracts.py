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
        "idx_submissions_status",
        "idx_submissions_internal_status",
        "idx_parse_results_manual_review",
        "idx_jobs_retryable_status",
        "idx_corrections_reason_outcome",
    }.issubset(indexes)


@pytest.mark.unit
@pytest.mark.contract
def test_sqlite_repository_exposes_structured_columns(tmp_path):
    init_db = require_symbol("app.core.services.sqlite_repository", "init_db")

    db_path = tmp_path / "runtime" / "soft_review.db"
    original_sqlite_path = os.environ.get("SOFT_REVIEW_SQLITE_PATH")
    os.environ["SOFT_REVIEW_SQLITE_PATH"] = str(db_path)

    try:
        init_db()
        with sqlite3.connect(db_path) as connection:
            submission_columns = {row[1] for row in connection.execute("PRAGMA table_info(submissions)").fetchall()}
            parse_columns = {row[1] for row in connection.execute("PRAGMA table_info(parse_results)").fetchall()}
            job_columns = {row[1] for row in connection.execute("PRAGMA table_info(jobs)").fetchall()}
            correction_columns = {row[1] for row in connection.execute("PRAGMA table_info(corrections)").fetchall()}
    finally:
        if original_sqlite_path is None:
            os.environ.pop("SOFT_REVIEW_SQLITE_PATH", None)
        else:
            os.environ["SOFT_REVIEW_SQLITE_PATH"] = original_sqlite_path

    assert {"status", "review_stage", "review_profile_revision", "review_profile_preset"}.issubset(submission_columns)
    assert {"needs_manual_review", "manual_review_reason_code", "unknown_reason", "quality_level"}.issubset(parse_columns)
    assert {"job_type", "status", "error_code", "retryable", "retry_count"}.issubset(job_columns)
    assert {"correction_type", "reason_code", "outcome_code", "unknown_delta", "manual_review_delta"}.issubset(correction_columns)
