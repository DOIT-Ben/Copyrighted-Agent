from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from app.core.services.runtime_store import store


ARTIFACT_MAP = {
    "raw": ("raw_text_path", "txt", "text/plain; charset=utf-8"),
    "clean": ("clean_text_path", "txt", "text/plain; charset=utf-8"),
    "desensitized": ("desensitized_text_path", "txt", "text/plain; charset=utf-8"),
    "privacy": ("privacy_manifest_path", "json", "application/json; charset=utf-8"),
}


def get_material_artifact(material_id: str, artifact_kind: str) -> dict:
    parse_result = store.parse_results.get(material_id)
    material = store.materials.get(material_id)
    if not parse_result or not material:
        raise ValueError(f"Material artifact not found: {material_id}")
    if artifact_kind not in ARTIFACT_MAP:
        raise ValueError(f"Unsupported artifact kind: {artifact_kind}")

    attr_name, suffix, media_type = ARTIFACT_MAP[artifact_kind]
    storage_path = getattr(parse_result, attr_name, "")
    if not storage_path:
        raise ValueError(f"Artifact path missing: {material_id} {artifact_kind}")
    path = Path(storage_path)
    if not path.exists():
        raise ValueError(f"Artifact file missing: {path}")

    return {
        "path": path,
        "filename": f"{material.original_filename}.{artifact_kind}.{suffix}",
        "media_type": media_type,
    }


def get_report_download(report_id: str) -> dict:
    report = store.report_artifacts.get(report_id)
    if not report:
        raise ValueError(f"Report not found: {report_id}")
    path = Path(report.storage_path)
    if path.exists():
        payload = path.read_bytes()
    else:
        payload = report.content.encode("utf-8")
    filename = f"{report.scope_type}_{report.scope_id}_{report.report_type}.{report.file_format}"
    media_type = "text/markdown; charset=utf-8" if report.file_format == "md" else "application/octet-stream"
    return {"payload": payload, "filename": filename, "media_type": media_type}


def get_report_json_download(report_id: str) -> dict:
    report = store.report_artifacts.get(report_id)
    if not report:
        raise ValueError(f"Report not found: {report_id}")

    payload: dict = {
        "report": report.to_dict(),
    }
    if report.scope_type == "case":
        case = store.cases.get(report.scope_id)
        if case:
            payload["case"] = case.to_dict()
            materials = [store.materials[item_id].to_dict() for item_id in case.material_ids if item_id in store.materials]
            payload["materials"] = materials
            if case.review_result_id and case.review_result_id in store.review_results:
                payload["review_result"] = store.review_results[case.review_result_id].to_dict()
    elif report.scope_type == "material":
        material = store.materials.get(report.scope_id)
        if material:
            payload["material"] = material.to_dict()
            if material.id in store.parse_results:
                payload["parse_result"] = store.parse_results[material.id].to_dict()
    elif report.scope_type == "submission":
        submission = store.submissions.get(report.scope_id)
        if submission:
            payload["submission"] = submission.to_dict()

    json_bytes = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    return {
        "payload": json_bytes,
        "filename": f"{report.scope_type}_{report.scope_id}_{report.report_type}.json",
        "media_type": "application/json; charset=utf-8",
    }


def build_submission_export_bundle(submission_id: str) -> dict:
    submission = store.submissions.get(submission_id)
    if not submission:
        raise ValueError(f"Submission not found: {submission_id}")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("submission/submission.json", json.dumps(submission.to_dict(), ensure_ascii=False, indent=2))

        for case_id in submission.case_ids:
            case = store.cases.get(case_id)
            if case:
                archive.writestr(f"cases/{case.id}.json", json.dumps(case.to_dict(), ensure_ascii=False, indent=2))
                if case.report_id and case.report_id in store.report_artifacts:
                    report = store.report_artifacts[case.report_id]
                    report_path = Path(report.storage_path)
                    if report_path.exists():
                        archive.writestr(f"reports/{report_path.name}", report_path.read_bytes())

        for material_id in submission.material_ids:
            material = store.materials.get(material_id)
            if not material:
                continue
            archive.writestr(f"materials/{material.id}.json", json.dumps(material.to_dict(), ensure_ascii=False, indent=2))
            parse_result = store.parse_results.get(material_id)
            if parse_result:
                archive.writestr(
                    f"parse_results/{material.id}.json",
                    json.dumps(parse_result.to_dict(), ensure_ascii=False, indent=2),
                )
                for artifact_kind, (attr_name, suffix, _) in ARTIFACT_MAP.items():
                    storage_path = getattr(parse_result, attr_name, "")
                    if not storage_path:
                        continue
                    artifact_path = Path(storage_path)
                    if artifact_path.exists():
                        archive.writestr(f"artifacts/{material.id}/{artifact_kind}.{suffix}", artifact_path.read_bytes())

            if material.report_id and material.report_id in store.report_artifacts:
                report = store.report_artifacts[material.report_id]
                report_path = Path(report.storage_path)
                if report_path.exists():
                    archive.writestr(f"reports/material_{report_path.name}", report_path.read_bytes())

        for correction_id in submission.correction_ids:
            correction = store.corrections.get(correction_id)
            if correction:
                archive.writestr(
                    f"corrections/{correction.id}.json",
                    json.dumps(correction.to_dict(), ensure_ascii=False, indent=2),
                )

        for job in store.jobs.values():
            if getattr(job, "scope_id", "") == submission_id:
                archive.writestr(f"jobs/{job.id}.json", json.dumps(job.to_dict(), ensure_ascii=False, indent=2))

    return {
        "payload": buffer.getvalue(),
        "filename": f"{submission.filename}_bundle.zip",
        "media_type": "application/zip",
    }
