from __future__ import annotations

import os

import pytest

from tests.helpers.contracts import require_symbol


def _make_submission(submission_id: str = "sub_test_1", **overrides):
    Submission = require_symbol("app.core.domain.models", "Submission")
    defaults = {
        "id": submission_id,
        "mode": "single_case_package",
        "filename": "test.zip",
        "storage_path": "/tmp/test.zip",
        "status": "completed",
        "created_at": "2026-01-01T00:00:00",
        "material_ids": [],
        "case_ids": [],
        "report_ids": [],
    }
    defaults.update(overrides)
    return Submission(**defaults)


def _make_material(material_id: str = "mat_test_1", submission_id: str = "sub_test_1", **overrides):
    Material = require_symbol("app.core.domain.models", "Material")
    defaults = {
        "id": material_id,
        "case_id": "",
        "submission_id": submission_id,
        "material_type": "source_code",
        "original_filename": "main.py",
        "storage_path": "/tmp/main.py",
        "file_ext": ".py",
        "parse_status": "completed",
        "review_status": "completed",
    }
    defaults.update(overrides)
    return Material(**defaults)


@pytest.fixture()
def isolated_store(tmp_path):
    runtime_store = require_symbol("app.core.services.runtime_store", "store")
    original_submissions = dict(runtime_store.submissions)
    original_materials = dict(runtime_store.materials)
    original_cases = dict(runtime_store.cases)
    original_corrections = dict(runtime_store.corrections)
    original_sqlite = os.environ.get("SOFT_REVIEW_SQLITE_PATH")
    os.environ["SOFT_REVIEW_SQLITE_PATH"] = str(tmp_path / "test.db")

    init_db = require_symbol("app.core.services.sqlite_repository", "init_db")
    init_db()

    yield runtime_store

    runtime_store.submissions.clear()
    runtime_store.submissions.update(original_submissions)
    runtime_store.materials.clear()
    runtime_store.materials.update(original_materials)
    runtime_store.cases.clear()
    runtime_store.cases.update(original_cases)
    runtime_store.corrections.clear()
    runtime_store.corrections.update(original_corrections)
    if original_sqlite is None:
        os.environ.pop("SOFT_REVIEW_SQLITE_PATH", None)
    else:
        os.environ["SOFT_REVIEW_SQLITE_PATH"] = original_sqlite


@pytest.mark.unit
@pytest.mark.contract
def test_update_internal_state_sets_fields(isolated_store):
    update_fn = require_symbol("app.core.services.corrections", "update_submission_internal_state")
    sub = _make_submission()
    isolated_store.add_submission(sub)

    result = update_fn(
        sub.id,
        owner="alice",
        internal_status="in_review",
        next_step="等待客户补材料",
        note="已电话沟通",
        updated_by="test_user",
    )

    updated = result["submission"]
    assert updated["internal_owner"] == "alice"
    assert updated["internal_status"] == "in_review"
    assert updated["internal_next_step"] == "等待客户补材料"
    assert updated["internal_note"] == "已电话沟通"
    assert updated["internal_updated_by"] == "test_user"
    assert updated["internal_updated_at"] != ""

    correction = result["correction"]
    assert correction["correction_type"] == "update_internal_state"
    assert correction["submission_id"] == sub.id


@pytest.mark.unit
@pytest.mark.contract
def test_update_internal_state_normalizes_invalid_status(isolated_store):
    update_fn = require_symbol("app.core.services.corrections", "update_submission_internal_state")
    sub = _make_submission()
    isolated_store.add_submission(sub)

    result = update_fn(sub.id, internal_status="nonexistent_status")
    assert result["submission"]["internal_status"] == "unassigned"


@pytest.mark.unit
@pytest.mark.contract
def test_update_internal_state_raises_on_missing_submission(isolated_store):
    update_fn = require_symbol("app.core.services.corrections", "update_submission_internal_state")
    with pytest.raises(ValueError):
        update_fn("nonexistent_id", owner="bob")


@pytest.mark.unit
@pytest.mark.contract
def test_update_internal_state_truncates_long_fields(isolated_store):
    update_fn = require_symbol("app.core.services.corrections", "update_submission_internal_state")
    sub = _make_submission()
    isolated_store.add_submission(sub)

    result = update_fn(
        sub.id,
        owner="x" * 200,
        next_step="y" * 500,
        note="z" * 1000,
    )

    updated = result["submission"]
    assert len(updated["internal_owner"]) == 80
    assert len(updated["internal_next_step"]) == 240
    assert len(updated["internal_note"]) == 500


@pytest.mark.unit
@pytest.mark.contract
def test_change_material_type_updates_and_records_correction(isolated_store):
    change_fn = require_symbol("app.core.services.corrections", "change_material_type")
    sub = _make_submission(material_ids=["mat_test_1"])
    mat = _make_material(material_type="unknown")
    isolated_store.add_submission(sub)
    isolated_store.add_material(mat)

    result = change_fn("mat_test_1", "source_code", corrected_by="test_user", note="修正材料类型")

    assert result["material"]["material_type"] == "source_code"
    assert result["correction"]["correction_type"] == "change_material_type"
    assert result["correction"]["submission_id"] == sub.id


@pytest.mark.unit
@pytest.mark.contract
def test_change_material_type_rejects_invalid_type(isolated_store):
    change_fn = require_symbol("app.core.services.corrections", "change_material_type")
    sub = _make_submission(material_ids=["mat_test_1"])
    mat = _make_material()
    isolated_store.add_submission(sub)
    isolated_store.add_material(mat)

    with pytest.raises(ValueError):
        change_fn("mat_test_1", "totally_invalid_type")
