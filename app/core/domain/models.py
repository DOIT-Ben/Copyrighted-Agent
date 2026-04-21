from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class Submission:
    id: str
    mode: str
    filename: str
    storage_path: str
    status: str
    created_at: str
    review_strategy: str = "auto_review"
    created_by: str = "local"
    material_ids: list[str] = field(default_factory=list)
    case_ids: list[str] = field(default_factory=list)
    report_ids: list[str] = field(default_factory=list)
    correction_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Case:
    id: str
    case_name: str
    software_name: str
    version: str
    company_name: str
    status: str
    source_submission_id: str
    created_at: str
    material_ids: list[str] = field(default_factory=list)
    review_result_id: str = ""
    report_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Material:
    id: str
    case_id: str | None
    submission_id: str
    material_type: str
    original_filename: str
    storage_path: str
    file_ext: str
    parse_status: str
    review_status: str
    detected_software_name: str = ""
    detected_version: str = ""
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    issues: list[dict[str, Any]] = field(default_factory=list)
    report_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ParseResult:
    material_id: str
    raw_text_path: str
    clean_text_path: str
    desensitized_text_path: str
    metadata_json: dict[str, Any]
    privacy_manifest_path: str = ""
    parser_name: str = ""
    parser_version: str = "mvp"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReviewResult:
    id: str
    scope_type: str
    scope_id: str
    reviewer_type: str
    severity_summary_json: dict[str, Any]
    issues_json: list[dict[str, Any]]
    score: float
    conclusion: str
    created_at: str
    rule_conclusion: str = ""
    ai_summary: str = ""
    ai_provider: str = "mock"
    ai_resolution: str = "explicit_mock"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReportArtifact:
    id: str
    scope_type: str
    scope_id: str
    report_type: str
    file_format: str
    storage_path: str
    created_at: str
    content: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Job:
    id: str
    job_type: str
    scope_type: str
    scope_id: str
    status: str
    progress: int
    error_message: str = ""
    started_at: str = ""
    finished_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Correction:
    id: str
    submission_id: str
    correction_type: str
    material_id: str = ""
    case_id: str = ""
    original_value: dict[str, Any] = field(default_factory=dict)
    corrected_value: dict[str, Any] = field(default_factory=dict)
    note: str = ""
    corrected_by: str = "local"
    corrected_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
