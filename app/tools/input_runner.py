from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from app.core.pipelines.submission_pipeline import ingest_submission


def _metrics_from_result(result: dict) -> dict:
    materials = result.get("materials", [])
    parse_results = result.get("parse_results", [])
    project_reports = [
        item
        for item in result.get("reports", [])
        if item.get("report_type") != "submission_global_review_markdown"
    ]
    type_counter = Counter(item.get("material_type", "unknown") for item in materials)
    review_reason_counter = Counter()
    legacy_bucket_counter = Counter()
    redaction_hits = sum(int(item.get("metadata_json", {}).get("privacy", {}).get("total_replacements", 0)) for item in parse_results)
    needs_review = sum(
        1
        for item in parse_results
        if item.get("metadata_json", {}).get("triage", {}).get("needs_manual_review")
    )
    low_quality = sum(
        1
        for item in parse_results
        if item.get("metadata_json", {}).get("parse_quality", {}).get("quality_level") == "low"
    )
    for item in parse_results:
        triage = item.get("metadata_json", {}).get("triage", {})
        parse_quality = item.get("metadata_json", {}).get("parse_quality", {})
        review_reason = str(triage.get("quality_review_reason_code") or parse_quality.get("review_reason_code") or "").strip()
        if review_reason:
            review_reason_counter[review_reason] += 1
        legacy_bucket = str(triage.get("legacy_doc_bucket") or parse_quality.get("legacy_doc_bucket") or "").strip()
        if legacy_bucket:
            legacy_bucket_counter[legacy_bucket] += 1
    return {
        "materials": len(materials),
        "cases": len(result.get("cases", [])),
        "reports": len(project_reports),
        "types": dict(type_counter),
        "needs_review": needs_review,
        "low_quality": low_quality,
        "redactions": redaction_hits,
        "unknown": type_counter.get("unknown", 0),
        "review_reasons": dict(review_reason_counter),
        "legacy_doc_buckets": dict(legacy_bucket_counter),
    }


def _summarize(result: dict) -> str:
    metrics = _metrics_from_result(result)
    return (
        f"materials={metrics['materials']} "
        f"cases={metrics['cases']} "
        f"reports={metrics['reports']} "
        f"types={metrics['types']} "
        f"needs_review={metrics['needs_review']} "
        f"low_quality={metrics['low_quality']} "
        f"redactions={metrics['redactions']} "
        f"review_reasons={metrics['review_reasons']} "
        f"legacy_doc_buckets={metrics['legacy_doc_buckets']}"
    )


def _merge_metrics(aggregate: dict | None, metrics: dict) -> dict:
    if not aggregate:
        return {
            "packages": 1,
            "materials": metrics["materials"],
            "cases": metrics["cases"],
            "reports": metrics["reports"],
            "needs_review": metrics["needs_review"],
            "low_quality": metrics["low_quality"],
            "redactions": metrics["redactions"],
            "unknown": metrics["unknown"],
            "review_reasons": Counter(metrics["review_reasons"]),
            "legacy_doc_buckets": Counter(metrics["legacy_doc_buckets"]),
        }
    return {
        "packages": aggregate["packages"] + 1,
        "materials": aggregate["materials"] + metrics["materials"],
        "cases": aggregate["cases"] + metrics["cases"],
        "reports": aggregate["reports"] + metrics["reports"],
        "needs_review": aggregate["needs_review"] + metrics["needs_review"],
        "low_quality": aggregate["low_quality"] + metrics["low_quality"],
        "redactions": aggregate["redactions"] + metrics["redactions"],
        "unknown": aggregate["unknown"] + metrics["unknown"],
        "review_reasons": aggregate["review_reasons"] + Counter(metrics["review_reasons"]),
        "legacy_doc_buckets": aggregate["legacy_doc_buckets"] + Counter(metrics["legacy_doc_buckets"]),
    }


def _serialize_aggregate(aggregate: dict) -> dict:
    return {
        "packages": int(aggregate["packages"]),
        "materials": int(aggregate["materials"]),
        "cases": int(aggregate["cases"]),
        "reports": int(aggregate["reports"]),
        "needs_review": int(aggregate["needs_review"]),
        "low_quality": int(aggregate["low_quality"]),
        "redactions": int(aggregate["redactions"]),
        "unknown": int(aggregate["unknown"]),
        "review_reasons": dict(aggregate["review_reasons"]),
        "legacy_doc_buckets": dict(aggregate["legacy_doc_buckets"]),
    }


def collect_metrics_bundle(source_path: Path, mode: str) -> dict:
    if source_path.is_dir() and mode == "single_case_package":
        zip_files = sorted(source_path.glob("*.zip"))
        if zip_files:
            aggregate: dict | None = None
            entries = []
            for zip_path in zip_files:
                result = ingest_submission(zip_path=zip_path, mode=mode, created_by="input_runner")
                metrics = _metrics_from_result(result)
                entries.append({"name": zip_path.name, "metrics": metrics})
                aggregate = _merge_metrics(aggregate, metrics)
            return {
                "source_path": str(source_path),
                "mode": mode,
                "entries": entries,
                "aggregate": _serialize_aggregate(aggregate or _merge_metrics(None, _metrics_from_result({"materials": [], "cases": [], "reports": [], "parse_results": []}))),
            }

    result = ingest_submission(zip_path=source_path, mode=mode, created_by="input_runner")
    metrics = _metrics_from_result(result)
    aggregate = _serialize_aggregate(_merge_metrics(None, metrics))
    return {
        "source_path": str(source_path),
        "mode": mode,
        "entries": [{"name": source_path.name, "metrics": metrics}],
        "aggregate": aggregate,
    }


def _run_single(source_path: Path, mode: str) -> None:
    result = ingest_submission(zip_path=source_path, mode=mode, created_by="input_runner")
    print(f"{source_path.name}: {_summarize(result)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local input validation for software copyright materials.")
    parser.add_argument("--path", required=True, help="Zip file, directory of files, or directory of zip packages.")
    parser.add_argument(
        "--mode",
        required=True,
        choices=("single_case_package", "batch_same_material"),
        help="Submission mode to execute.",
    )
    args = parser.parse_args()

    source_path = Path(args.path)
    if not source_path.exists():
        raise SystemExit(f"Input path does not exist: {source_path}")

    bundle = collect_metrics_bundle(source_path, args.mode)
    for entry in bundle["entries"]:
        metrics = entry["metrics"]
        print(
            f"{entry['name']}: "
            f"materials={metrics['materials']} "
            f"cases={metrics['cases']} "
            f"reports={metrics['reports']} "
            f"types={metrics['types']} "
            f"needs_review={metrics['needs_review']} "
            f"low_quality={metrics['low_quality']} "
            f"redactions={metrics['redactions']} "
            f"review_reasons={metrics['review_reasons']} "
            f"legacy_doc_buckets={metrics['legacy_doc_buckets']}"
        )
    if bundle["aggregate"]["packages"] > 1:
        aggregate = bundle["aggregate"]
        print(
            "AGGREGATE: "
            f"packages={aggregate['packages']} "
            f"materials={aggregate['materials']} "
            f"cases={aggregate['cases']} "
            f"reports={aggregate['reports']} "
            f"unknown={aggregate['unknown']} "
            f"needs_review={aggregate['needs_review']} "
            f"low_quality={aggregate['low_quality']} "
            f"redactions={aggregate['redactions']} "
            f"review_reasons={aggregate['review_reasons']} "
            f"legacy_doc_buckets={aggregate['legacy_doc_buckets']}"
        )


if __name__ == "__main__":
    main()
