from __future__ import annotations

import pytest

from tests.helpers.contracts import require_symbol


@pytest.mark.integration
@pytest.mark.contract
def test_sqlite_persistence_can_restore_submission_graph(mode_a_zip_path):
    ingest_submission = require_symbol("app.core.pipelines.submission_pipeline", "ingest_submission")
    change_material_type = require_symbol("app.core.services.corrections", "change_material_type")
    clear_database = require_symbol("app.core.services.sqlite_repository", "clear_database")
    load_all_into_store = require_symbol("app.core.services.sqlite_repository", "load_all_into_store")
    runtime_store = require_symbol("app.core.services.runtime_store", "store")

    clear_database()
    result = ingest_submission(zip_path=mode_a_zip_path, mode="single_case_package")
    submission_id = result["submission"]["id"]
    material_id = result["materials"][0]["id"]

    change_material_type(material_id, "agreement", corrected_by="tester", note="persist me")
    runtime_store.reset()
    load_all_into_store()

    restored_submission = runtime_store.submissions[submission_id]
    restored_material = runtime_store.materials[material_id]

    assert restored_submission.id == submission_id
    assert restored_submission.material_ids
    assert restored_submission.correction_ids
    assert restored_material.material_type == "agreement"
    assert runtime_store.corrections[restored_submission.correction_ids[0]].note == "persist me"

    clear_database()
