from __future__ import annotations

import threading

from tests.helpers.contracts import require_symbol


def test_runtime_store_exposes_reentrant_lock_for_compound_operations():
    RuntimeStore = require_symbol("app.core.services.runtime_store", "RuntimeStore")
    store = RuntimeStore()

    with store.locked() as locked_store:
        locked_store.reset()
        assert locked_store is store


def test_runtime_store_add_operations_are_safe_under_parallel_writes():
    RuntimeStore = require_symbol("app.core.services.runtime_store", "RuntimeStore")
    Job = require_symbol("app.core.domain.models", "Job")
    store = RuntimeStore()

    def worker(index: int) -> None:
        store.add_job(
            Job(
                id=f"job_parallel_{index}",
                job_type="ingest_submission",
                scope_type="submission",
                scope_id=f"sub_parallel_{index}",
                status="queued",
                progress=0,
                updated_at="2026-05-10T00:00:00",
            )
        )

    threads = [threading.Thread(target=worker, args=(index,)) for index in range(50)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(store.jobs) == 50
