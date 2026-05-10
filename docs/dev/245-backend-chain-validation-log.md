# 245 Backend Chain Validation Log

Date: 2026-05-09

## Goal

Validate whether the backend chain is complete enough for the current soft-copyright review agent workflow.

## Scope

- Upload API and async job creation.
- Job polling and completion state.
- Submission graph persistence.
- Material parsing and case grouping.
- Report generation and report download endpoints.
- Submission bundle export.
- Manual correction and retry/ops APIs.
- Provider bridge, provider probe, release validation, release gate, runtime backup/cleanup contracts.

## Commands

```powershell
py -m pytest -q tests\integration\test_api_contracts.py tests\integration\test_manual_correction_api.py tests\integration\test_job_recovery_flow.py tests\integration\test_sqlite_persistence.py tests\integration\test_mode_a_pipeline_contracts.py tests\integration\test_mode_b_pipeline_contracts.py tests\integration\test_minimax_bridge_flow.py tests\integration\test_provider_probe_flow.py tests\integration\test_release_validation_flow.py tests\integration\test_delivery_closeout_flow.py tests\unit\test_ops_status_contracts.py tests\unit\test_provider_probe_contracts.py tests\unit\test_release_validation_contracts.py tests\unit\test_release_gate_contracts.py
```

Result: 42 passed, 0 failed.

```powershell
py -m pytest -q
```

Result: 227 passed, 0 failed.

## Live Stack Smoke

Running services:

- Web/API: `http://127.0.0.1:18080`
- MiniMax bridge: `http://127.0.0.1:18011/review`

Sample:

- `input/<soft-copyright-materials>/2505_*.zip`

Live smoke result:

```json
{
  "submit_status": 202,
  "job_id": "job_b2b719c16f",
  "job_status": "completed",
  "job_progress": 100,
  "job_stage": "result_generated",
  "submission_id": "sub_fb46a29428",
  "submission_status": "completed",
  "review_stage": "review_completed",
  "material_count": 4,
  "file_api_count": 4,
  "case_count": 1,
  "report_count": 2,
  "first_report_id": "rep_92bb7eb94b",
  "report_page_status": "200",
  "report_json_status": "200",
  "bundle_status": "200",
  "ops_retry_api_status": "200"
}
```

## Observations

- The main backend chain is closed: upload -> async job -> parsing -> grouping -> review -> report -> downloads.
- The real stack accepts the sample package and returns completed job state with generated reports.
- Diagnostics, corrections, retry queue, JSON report download, and bundle export endpoints are reachable.
- Full automated regression includes E2E browser workflows, integration flows, security contracts, parser contracts, provider contracts, and report contracts.

## Known Follow-Ups

- Continue periodic real-provider validation with `scripts\run_real_validation.ps1` before release.
- Keep monitoring provider fallback behavior because one full-suite sandbox request intentionally observed a `503` fallback path during provider error coverage.
- Add multi-sample live smoke if release confidence needs to cover all packages under `input/<soft-copyright-materials>`.
