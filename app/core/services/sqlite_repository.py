from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.core.domain.models import Case, Correction, Job, Material, ParseResult, ReportArtifact, ReviewResult, Submission
from app.core.services.app_config import load_app_config
from app.core.services.runtime_store import store
from app.core.utils.text import ensure_dir


DB_PATH = Path("data") / "runtime" / "soft_review.db"

TABLE_COLUMNS = {
    "submissions": {
        "status": "TEXT NOT NULL DEFAULT ''",
        "review_stage": "TEXT NOT NULL DEFAULT ''",
        "review_strategy": "TEXT NOT NULL DEFAULT ''",
        "internal_status": "TEXT NOT NULL DEFAULT ''",
        "created_at": "TEXT NOT NULL DEFAULT ''",
        "review_profile_revision": "INTEGER NOT NULL DEFAULT 1",
        "review_profile_preset": "TEXT NOT NULL DEFAULT ''",
    },
    "parse_results": {
        "needs_manual_review": "INTEGER NOT NULL DEFAULT 0",
        "manual_review_reason_code": "TEXT NOT NULL DEFAULT ''",
        "unknown_reason": "TEXT NOT NULL DEFAULT ''",
        "quality_level": "TEXT NOT NULL DEFAULT ''",
        "review_reason_code": "TEXT NOT NULL DEFAULT ''",
        "legacy_doc_bucket": "TEXT NOT NULL DEFAULT ''",
    },
    "jobs": {
        "job_type": "TEXT NOT NULL DEFAULT ''",
        "status": "TEXT NOT NULL DEFAULT ''",
        "error_code": "TEXT NOT NULL DEFAULT ''",
        "retryable": "INTEGER NOT NULL DEFAULT 0",
        "updated_at": "TEXT NOT NULL DEFAULT ''",
        "retry_count": "INTEGER NOT NULL DEFAULT 0",
        "provider": "TEXT NOT NULL DEFAULT ''",
    },
    "corrections": {
        "correction_type": "TEXT NOT NULL DEFAULT ''",
        "corrected_at": "TEXT NOT NULL DEFAULT ''",
        "corrected_by": "TEXT NOT NULL DEFAULT ''",
        "reason_code": "TEXT NOT NULL DEFAULT ''",
        "outcome_code": "TEXT NOT NULL DEFAULT ''",
        "unknown_delta": "INTEGER NOT NULL DEFAULT 0",
        "manual_review_delta": "INTEGER NOT NULL DEFAULT 0",
        "review_profile_revision": "INTEGER NOT NULL DEFAULT 0",
    },
}


def _db_path() -> Path:
    config = load_app_config()
    target = Path(config.sqlite_path or DB_PATH)
    ensure_dir(target.parent)
    return target


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(_db_path())
    connection.row_factory = sqlite3.Row
    return connection


def _table_info(connection: sqlite3.Connection, table: str) -> set[str]:
    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    return {str(row["name"]) for row in rows}


def _ensure_columns(connection: sqlite3.Connection) -> None:
    for table, columns in TABLE_COLUMNS.items():
        existing = _table_info(connection, table)
        for column_name, column_sql in columns.items():
            if column_name in existing:
                continue
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {column_name} {column_sql}")


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
        _ensure_columns(connection)
        connection.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_submissions_status ON submissions(status);
            CREATE INDEX IF NOT EXISTS idx_submissions_internal_status ON submissions(internal_status);
            CREATE INDEX IF NOT EXISTS idx_parse_results_manual_review ON parse_results(needs_manual_review, manual_review_reason_code);
            CREATE INDEX IF NOT EXISTS idx_jobs_retryable_status ON jobs(retryable, status);
            CREATE INDEX IF NOT EXISTS idx_corrections_reason_outcome ON corrections(reason_code, outcome_code);
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


def _submission_columns(payload: dict) -> dict:
    review_profile = dict(payload.get("review_profile", {}) or {})
    meta = dict(review_profile.get("rulebook_meta", {}) or {})
    return {
        "status": str(payload.get("status", "") or ""),
        "review_stage": str(payload.get("review_stage", "") or ""),
        "review_strategy": str(payload.get("review_strategy", "") or ""),
        "internal_status": str(payload.get("internal_status", "") or ""),
        "created_at": str(payload.get("created_at", "") or ""),
        "review_profile_revision": int(meta.get("revision", 1) or 1),
        "review_profile_preset": str(review_profile.get("preset_key", "") or ""),
    }


def _parse_result_columns(payload: dict) -> dict:
    metadata = dict(payload.get("metadata_json", {}) or {})
    triage = dict(metadata.get("triage", {}) or {})
    parse_quality = dict(metadata.get("parse_quality", {}) or {})
    return {
        "needs_manual_review": 1 if triage.get("needs_manual_review") else 0,
        "manual_review_reason_code": str(
            triage.get("manual_review_reason_code")
            or triage.get("unknown_reason")
            or triage.get("quality_review_reason_code")
            or parse_quality.get("review_reason_code")
            or ""
        ),
        "unknown_reason": str(triage.get("unknown_reason", "") or ""),
        "quality_level": str(parse_quality.get("quality_level", "") or ""),
        "review_reason_code": str(triage.get("quality_review_reason_code") or parse_quality.get("review_reason_code") or ""),
        "legacy_doc_bucket": str(triage.get("legacy_doc_bucket") or parse_quality.get("legacy_doc_bucket") or ""),
    }


def _job_columns(payload: dict) -> dict:
    metadata = dict(payload.get("metadata", {}) or {})
    review_profile = dict(metadata.get("review_profile", {}) or {})
    return {
        "job_type": str(payload.get("job_type", "") or ""),
        "status": str(payload.get("status", "") or ""),
        "error_code": str(payload.get("error_code", "") or ""),
        "retryable": 1 if payload.get("retryable") else 0,
        "updated_at": str(payload.get("updated_at", "") or payload.get("started_at", "") or ""),
        "retry_count": int(metadata.get("retry_count", 0) or 0),
        "provider": str(review_profile.get("provider", "") or metadata.get("provider", "") or ""),
    }


def _correction_columns(payload: dict) -> dict:
    analysis = dict(payload.get("analysis", {}) or {})
    delta = dict(analysis.get("delta", {}) or {})
    corrected_profile = dict((payload.get("corrected_value") or {}).get("review_profile", {}) or {})
    corrected_meta = dict(corrected_profile.get("rulebook_meta", {}) or {})
    return {
        "correction_type": str(payload.get("correction_type", "") or ""),
        "corrected_at": str(payload.get("corrected_at", "") or ""),
        "corrected_by": str(payload.get("corrected_by", "") or ""),
        "reason_code": str(payload.get("reason_code", "") or ""),
        "outcome_code": str(payload.get("outcome_code", "") or analysis.get("outcome_code", "") or ""),
        "unknown_delta": int(delta.get("unknown_materials", 0) or 0),
        "manual_review_delta": int(delta.get("manual_review_materials", 0) or 0),
        "review_profile_revision": int(corrected_meta.get("revision", 0) or 0),
    }


def _upsert_structured(connection: sqlite3.Connection, table: str, row_id: str, submission_id: str, payload: dict, columns: dict) -> None:
    column_names = ["id", "submission_id", "payload_json", *columns.keys()]
    placeholders = ", ".join("?" for _ in column_names)
    updates = ", ".join(f"{column} = excluded.{column}" for column in ["submission_id", "payload_json", *columns.keys()])
    values = [row_id, submission_id, json.dumps(payload, ensure_ascii=False), *columns.values()]
    connection.execute(
        f"""
        INSERT INTO {table} ({", ".join(column_names)})
        VALUES ({placeholders})
        ON CONFLICT(id) DO UPDATE SET
            {updates}
        """,
        values,
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
        submission_payload = submission.to_dict()
        _upsert_structured(connection, "submissions", submission.id, submission_id, submission_payload, _submission_columns(submission_payload))

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
                    parse_payload = parse_result.to_dict()
                    _upsert_structured(connection, "parse_results", parse_result.material_id, submission_id, parse_payload, _parse_result_columns(parse_payload))
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
                correction_payload = correction.to_dict()
                _upsert_structured(connection, "corrections", correction.id, submission_id, correction_payload, _correction_columns(correction_payload))

        for job in store.jobs.values():
            if getattr(job, "scope_id", "") == submission_id:
                job_payload = job.to_dict()
                _upsert_structured(connection, "jobs", job.id, submission_id, job_payload, _job_columns(job_payload))

        connection.commit()


def load_all_into_store() -> None:
    init_db()
    store.reset()
    with _connect() as connection:
        for row in connection.execute("SELECT payload_json FROM submissions ORDER BY rowid"):
            payload = json.loads(row["payload_json"])
            payload.setdefault("internal_owner", "")
            payload.setdefault("internal_status", "unassigned")
            payload.setdefault("internal_next_step", "")
            payload.setdefault("internal_note", "")
            payload.setdefault("internal_updated_by", "")
            payload.setdefault("internal_updated_at", "")
            store.add_submission(Submission(**payload))
        for row in connection.execute("SELECT payload_json FROM cases ORDER BY rowid"):
            store.add_case(Case(**json.loads(row["payload_json"])))
        for row in connection.execute("SELECT payload_json FROM materials ORDER BY rowid"):
            store.add_material(Material(**json.loads(row["payload_json"])))
        for row in connection.execute("SELECT payload_json FROM parse_results ORDER BY rowid"):
            payload = json.loads(row["payload_json"])
            metadata = dict(payload.get("metadata_json", {}) or {})
            triage = dict(metadata.get("triage", {}) or {})
            parse_quality = dict(metadata.get("parse_quality", {}) or {})
            triage.setdefault(
                "manual_review_reason_code",
                str(triage.get("unknown_reason") or triage.get("quality_review_reason_code") or parse_quality.get("review_reason_code") or ""),
            )
            metadata["triage"] = triage
            payload["metadata_json"] = metadata
            store.add_parse_result(ParseResult(**payload))
        for row in connection.execute("SELECT payload_json FROM review_results ORDER BY rowid"):
            store.add_review_result(ReviewResult(**json.loads(row["payload_json"])))
        for row in connection.execute("SELECT payload_json FROM report_artifacts ORDER BY rowid"):
            store.add_report_artifact(ReportArtifact(**json.loads(row["payload_json"])))
        for row in connection.execute("SELECT payload_json FROM jobs ORDER BY rowid"):
            payload = json.loads(row["payload_json"])
            payload.setdefault("updated_at", str(payload.get("started_at", "") or ""))
            payload.setdefault("error_code", "")
            payload.setdefault("retryable", False)
            payload.setdefault("metadata", {})
            store.add_job(Job(**payload))
        for row in connection.execute("SELECT payload_json FROM corrections ORDER BY rowid"):
            payload = json.loads(row["payload_json"])
            payload.setdefault("reason_code", "")
            payload.setdefault("reason_label", "")
            payload.setdefault("outcome_code", "")
            payload.setdefault("outcome_label", "")
            payload.setdefault("analysis", {})
            store.add_correction(Correction(**payload))


def list_retryable_jobs(limit: int = 8, *, status_filter: str = "", error_filter: str = "") -> list[dict]:
    init_db()
    clauses = ["retryable = 1", "job_type = 'ingest_submission'", "status IN ('failed', 'interrupted')"]
    params: list[object] = []
    if status_filter:
        clauses.append("status = ?")
        params.append(status_filter)
    if error_filter:
        clauses.append("LOWER(error_code) LIKE ?")
        params.append(f"%{error_filter.lower()}%")
    params.append(max(int(limit or 0), 0))
    query = (
        "SELECT payload_json FROM jobs "
        f"WHERE {' AND '.join(clauses)} "
        "ORDER BY updated_at DESC, id DESC LIMIT ?"
    )
    with _connect() as connection:
        rows = connection.execute(query, params).fetchall()
    payloads = [json.loads(row["payload_json"]) for row in rows]
    if payloads:
        return payloads

    fallback: list[dict] = []
    for job in store.jobs.values():
        payload = job.to_dict()
        if not payload.get("retryable"):
            continue
        if str(payload.get("job_type", "") or "") != "ingest_submission":
            continue
        if str(payload.get("status", "") or "").strip().lower() not in {"failed", "interrupted"}:
            continue
        if status_filter and str(payload.get("status", "") or "").strip().lower() != status_filter:
            continue
        if error_filter and error_filter.lower() not in str(payload.get("error_code", "") or "").lower():
            continue
        fallback.append(payload)
    return sorted(fallback, key=lambda item: (item.get("updated_at", "") or "", item.get("id", "") or ""), reverse=True)[: max(int(limit or 0), 0)]


def list_manual_review_queue(limit: int = 8) -> list[dict]:
    init_db()
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT payload_json
            FROM parse_results
            WHERE needs_manual_review = 1
            ORDER BY submission_id DESC, id DESC
            LIMIT ?
            """,
            (max(int(limit or 0), 0),),
        ).fetchall()
    payloads = [json.loads(row["payload_json"]) for row in rows]
    if payloads:
        return payloads

    fallback: list[dict] = []
    for parse_result in store.parse_results.values():
        payload = parse_result.to_dict()
        triage = dict((payload.get("metadata_json") or {}).get("triage") or {})
        if triage.get("needs_manual_review"):
            fallback.append(payload)
    return fallback[: max(int(limit or 0), 0)]


def list_correction_feedback(limit: int = 10) -> list[dict]:
    init_db()
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT payload_json
            FROM corrections
            ORDER BY corrected_at DESC, id DESC
            LIMIT ?
            """,
            (max(int(limit or 0), 0),),
        ).fetchall()
    payloads = [json.loads(row["payload_json"]) for row in rows]
    if payloads:
        return payloads
    fallback = [item.to_dict() for item in store.corrections.values()]
    return sorted(fallback, key=lambda item: (item.get("corrected_at", "") or "", item.get("id", "") or ""), reverse=True)[: max(int(limit or 0), 0)]


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
