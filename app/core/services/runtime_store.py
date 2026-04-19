from __future__ import annotations

from dataclasses import asdict
from typing import Any


class RuntimeStore:
    def __init__(self) -> None:
        self.submissions: dict[str, Any] = {}
        self.cases: dict[str, Any] = {}
        self.materials: dict[str, Any] = {}
        self.parse_results: dict[str, Any] = {}
        self.review_results: dict[str, Any] = {}
        self.report_artifacts: dict[str, Any] = {}
        self.jobs: dict[str, Any] = {}
        self.corrections: dict[str, Any] = {}

    def reset(self) -> None:
        self.__init__()

    def _store(self, bucket: dict[str, Any], item: Any) -> Any:
        bucket[item.id] = item
        return item

    def add_submission(self, item):
        return self._store(self.submissions, item)

    def add_case(self, item):
        return self._store(self.cases, item)

    def add_material(self, item):
        return self._store(self.materials, item)

    def add_parse_result(self, item):
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
