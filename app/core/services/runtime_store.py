from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict
from threading import RLock
from typing import Any


class RuntimeStore:
    def __init__(self) -> None:
        existing_lock = getattr(self, "_lock", None)
        self._lock = existing_lock or RLock()
        self.submissions: dict[str, Any] = {}
        self.cases: dict[str, Any] = {}
        self.materials: dict[str, Any] = {}
        self.parse_results: dict[str, Any] = {}
        self.review_results: dict[str, Any] = {}
        self.report_artifacts: dict[str, Any] = {}
        self.jobs: dict[str, Any] = {}
        self.corrections: dict[str, Any] = {}

    @contextmanager
    def locked(self):
        with self._lock:
            yield self

    def reset(self) -> None:
        with self._lock:
            self.submissions = {}
            self.cases = {}
            self.materials = {}
            self.parse_results = {}
            self.review_results = {}
            self.report_artifacts = {}
            self.jobs = {}
            self.corrections = {}

    def _store(self, bucket: dict[str, Any], item: Any) -> Any:
        with self._lock:
            bucket[item.id] = item
        return item

    def add_submission(self, item):
        return self._store(self.submissions, item)

    def add_case(self, item):
        return self._store(self.cases, item)

    def add_material(self, item):
        return self._store(self.materials, item)

    def add_parse_result(self, item):
        with self._lock:
            self.parse_results[item.material_id] = item
        return item

    def add_review_result(self, item):
        return self._store(self.review_results, item)

    def add_report_artifact(self, item):
        return self._store(self.report_artifacts, item)

    def add_job(self, item):
        return self._store(self.jobs, item)

    def add_correction(self, item):
        return self._store(self.corrections, item)

    def to_jsonable(self, item: Any) -> dict[str, Any]:
        if hasattr(item, "to_dict"):
            return item.to_dict()
        return asdict(item)


store = RuntimeStore()
