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

    assert {"status", "review_stage", "review_profile_revision", "review_profile_preset", "internal_owner", "internal_updated_at"}.issubset(submission_columns)
    assert {"needs_manual_review", "manual_review_reason_code", "unknown_reason", "quality_level"}.issubset(parse_columns)
    assert {"job_type", "status", "error_code", "retryable", "retry_count"}.issubset(job_columns)
    assert {"correction_type", "reason_code", "outcome_code", "unknown_delta", "manual_review_delta"}.issubset(correction_columns)


@pytest.mark.unit
@pytest.mark.contract
def test_list_submission_registry_uses_structured_filters(tmp_path):
    Submission = require_symbol("app.core.domain.models", "Submission")
    runtime_store = require_symbol("app.core.services.runtime_store", "store")
    init_db = require_symbol("app.core.services.sqlite_repository", "init_db")
    save_submission_graph = require_symbol("app.core.services.sqlite_repository", "save_submission_graph")
    list_submission_registry = require_symbol("app.core.services.sqlite_repository", "list_submission_registry")

    db_path = tmp_path / "runtime" / "soft_review.db"
    original_sqlite_path = os.environ.get("SOFT_REVIEW_SQLITE_PATH")
    os.environ["SOFT_REVIEW_SQLITE_PATH"] = str(db_path)

    original_submissions = dict(runtime_store.submissions)
    try:
        runtime_store.submissions.clear()
        init_db()

        first = Submission(
            id="sub_registry_1",
            mode="single_case_package",
            filename="first.zip",
            storage_path="data/first.zip",
            status="completed",
            created_at="2026-05-02T09:00:00",
            internal_owner="alice",
            internal_status="assigned",
            internal_updated_at="2026-05-02T10:00:00",
        )
        second = Submission(
            id="sub_registry_2",
            mode="single_case_package",
            filename="second.zip",
            storage_path="data/second.zip",
            status="awaiting_manual_review",
            created_at="2026-05-02T11:00:00",
            internal_owner="bob",
            internal_status="blocked",
            internal_updated_at="2026-05-02T11:30:00",
        )
        runtime_store.add_submission(first)
        runtime_store.add_submission(second)
        save_submission_graph(first.id)
        save_submission_graph(second.id)

        filtered = list_submission_registry({"internal_status": "blocked", "owner": "bo", "status": "awaiting_manual_review"})
        assert [item.id for item in filtered] == ["sub_registry_2"]
        assert filtered[0].internal_owner == "bob"
        assert filtered[0].internal_updated_at == "2026-05-02T11:30:00"
    finally:
        runtime_store.submissions.clear()
        runtime_store.submissions.update(original_submissions)
        if original_sqlite_path is None:
            os.environ.pop("SOFT_REVIEW_SQLITE_PATH", None)
        else:
            os.environ["SOFT_REVIEW_SQLITE_PATH"] = original_sqlite_path
