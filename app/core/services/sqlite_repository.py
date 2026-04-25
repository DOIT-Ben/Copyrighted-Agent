from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.core.domain.models import Case, Correction, Job, Material, ParseResult, ReportArtifact, ReviewResult, Submission
from app.core.services.app_config import load_app_config
from app.core.services.runtime_store import store
from app.core.utils.text import ensure_dir


DB_PATH = Path("data") / "runtime" / "soft_review.db"


def _db_path() -> Path:
    config = load_app_config()
    target = Path(config.sqlite_path or DB_PATH)
    ensure_dir(target.parent)
    return target


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(_db_path())
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with _connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS submissions (
                id TEXT PRIMARY KEY,
                submission_id TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS cases (
                id TEXT PRIMARY KEY,
                submission_id TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS materials (
                id TEXT PRIMARY KEY,
                submission_id TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS parse_results (
                id TEXT PRIMARY KEY,
                submission_id TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS review_results (
                id TEXT PRIMARY KEY,
                submission_id TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS report_artifacts (
                id TEXT PRIMARY KEY,
                submission_id TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                submission_id TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS corrections (
                id TEXT PRIMARY KEY,
                submission_id TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_cases_submission_id ON cases(submission_id);
            CREATE INDEX IF NOT EXISTS idx_materials_submission_id ON materials(submission_id);
            CREATE INDEX IF NOT EXISTS idx_parse_results_submission_id ON parse_results(submission_id);
            CREATE INDEX IF NOT EXISTS idx_review_results_submission_id ON review_results(submission_id);
            CREATE INDEX IF NOT EXISTS idx_report_artifacts_submission_id ON report_artifacts(submission_id);
            CREATE INDEX IF NOT EXISTS idx_jobs_submission_id ON jobs(submission_id);
            CREATE INDEX IF NOT EXISTS idx_corrections_submission_id ON corrections(submission_id);
            """
        )


def _upsert(connection: sqlite3.Connection, table: str, row_id: str, submission_id: str, payload: dict) -> None:
    connection.execute(
        f"""
        INSERT INTO {table} (id, submission_id, payload_json)
        VALUES (?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            submission_id = excluded.submission_id,
            payload_json = excluded.payload_json
        """,
        (row_id, submission_id, json.dumps(payload, ensure_ascii=False)),
    )


def _delete_submission_rows(connection: sqlite3.Connection, submission_id: str) -> None:
    for table in (
        "submissions",
        "cases",
        "materials",
        "parse_results",
        "review_results",
        "report_artifacts",
        "jobs",
        "corrections",
    ):
        connection.execute(f"DELETE FROM {table} WHERE submission_id = ?", (submission_id,))


def save_submission_graph(submission_id: str) -> None:
    submission = store.submissions.get(submission_id)
    if not submission:
        return

    init_db()
    with _connect() as connection:
        _delete_submission_rows(connection, submission_id)
        _upsert(connection, "submissions", submission.id, submission_id, submission.to_dict())

        for case_id in submission.case_ids:
            case = store.cases.get(case_id)
            if case:
                _upsert(connection, "cases", case.id, submission_id, case.to_dict())
                if case.review_result_id and case.review_result_id in store.review_results:
                    review_result = store.review_results[case.review_result_id]
                    _upsert(connection, "review_results", review_result.id, submission_id, review_result.to_dict())
                if case.report_id and case.report_id in store.report_artifacts:
                    report = store.report_artifacts[case.report_id]
                    _upsert(connection, "report_artifacts", report.id, submission_id, report.to_dict())

        for material_id in submission.material_ids:
            material = store.materials.get(material_id)
            if material:
                _upsert(connection, "materials", material.id, submission_id, material.to_dict())
                parse_result = store.parse_results.get(material.id)
                if parse_result:
                    _upsert(connection, "parse_results", parse_result.material_id, submission_id, parse_result.to_dict())
                if material.report_id and material.report_id in store.report_artifacts:
                    report = store.report_artifacts[material.report_id]
                    _upsert(connection, "report_artifacts", report.id, submission_id, report.to_dict())

        for report_id in submission.report_ids:
            report = store.report_artifacts.get(report_id)
            if report:
                _upsert(connection, "report_artifacts", report.id, submission_id, report.to_dict())

        for correction_id in submission.correction_ids:
            correction = store.corrections.get(correction_id)
            if correction:
                _upsert(connection, "corrections", correction.id, submission_id, correction.to_dict())

        for job in store.jobs.values():
            if getattr(job, "scope_id", "") == submission_id:
                _upsert(connection, "jobs", job.id, submission_id, job.to_dict())

        connection.commit()


def load_all_into_store() -> None:
    init_db()
    store.reset()
    with _connect() as connection:
        for row in connection.execute("SELECT payload_json FROM submissions ORDER BY rowid"):
            store.add_submission(Submission(**json.loads(row["payload_json"])))
        for row in connection.execute("SELECT payload_json FROM cases ORDER BY rowid"):
            store.add_case(Case(**json.loads(row["payload_json"])))
        for row in connection.execute("SELECT payload_json FROM materials ORDER BY rowid"):
            store.add_material(Material(**json.loads(row["payload_json"])))
        for row in connection.execute("SELECT payload_json FROM parse_results ORDER BY rowid"):
            store.add_parse_result(ParseResult(**json.loads(row["payload_json"])))
        for row in connection.execute("SELECT payload_json FROM review_results ORDER BY rowid"):
            store.add_review_result(ReviewResult(**json.loads(row["payload_json"])))
        for row in connection.execute("SELECT payload_json FROM report_artifacts ORDER BY rowid"):
            store.add_report_artifact(ReportArtifact(**json.loads(row["payload_json"])))
        for row in connection.execute("SELECT payload_json FROM jobs ORDER BY rowid"):
            store.add_job(Job(**json.loads(row["payload_json"])))
        for row in connection.execute("SELECT payload_json FROM corrections ORDER BY rowid"):
            store.add_correction(Correction(**json.loads(row["payload_json"])))


def clear_database() -> None:
    db_path = _db_path()
    if db_path.exists():
        try:
            db_path.unlink()
            return
        except PermissionError:
            pass

    init_db()
    with _connect() as connection:
        table_rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        for row in table_rows:
            connection.execute(f"DELETE FROM {row['name']}")
        connection.commit()
