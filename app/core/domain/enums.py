from __future__ import annotations

from enum import Enum


class SubmissionMode(str, Enum):
    SINGLE_CASE_PACKAGE = "single_case_package"
    BATCH_SAME_MATERIAL = "batch_same_material"


class MaterialType(str, Enum):
    INFO_FORM = "info_form"
    SOURCE_CODE = "source_code"
    SOFTWARE_DOC = "software_doc"
    AGREEMENT = "agreement"
    UNKNOWN = "unknown"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

