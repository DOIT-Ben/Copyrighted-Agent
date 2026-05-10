# 247 Single-User Hardening Log

Date: 2026-05-10

## Scope

- Hardened the single-user local backend without adding full multi-user auth/RBAC.
- Focused on upload safety, ZIP extraction quotas, external LLM privacy boundary, runtime-store concurrency, and bounded log downloads.

## Changes

- Added configurable runtime limits to `AppConfig`:
  - `max_upload_bytes`
  - `max_zip_members`
  - `max_zip_member_bytes`
  - `max_zip_total_uncompressed_bytes`
  - `max_log_download_bytes`
- Added WSGI multipart `Content-Length` early rejection for oversized uploads.
- Sanitized uploaded ZIP filenames before saving under `data_root/uploads`.
- Added ZIP extraction quotas for member count, per-member uncompressed size, and total uncompressed size.
- Added bounded app-log tail download so `/downloads/logs/app` no longer reads and returns unlimited log contents.
- Added AI-safe rule-result projection before non-mock provider calls:
  - removes raw evidence fields, original filenames, matched text, raw paths, and nested evidence anchors
  - redacts `当前识别到...` / `observed...` evidence summaries before prompt construction
  - keeps local full-fidelity review data for operator-facing reports
- Added `RuntimeStore.locked()` and write-side `RLock` protection for core store mutation helpers.

## Tests

- Added upload quota, ZIP quota, log-tail, AI rule-result redaction, external prompt boundary, and runtime-store concurrency tests.
- Targeted validation:
  - `py -m pytest -q tests\non_functional\test_security_contracts.py tests\unit\test_privacy_desensitization_contracts.py tests\unit\test_runtime_store_contracts.py`
  - Result: `18 passed`
- Related regression:
  - `py -m pytest -q tests\unit tests\integration\test_api_contracts.py tests\integration\test_mode_a_pipeline_contracts.py tests\integration\test_mode_b_pipeline_contracts.py tests\integration\test_minimax_bridge_flow.py tests\integration\test_provider_sandbox_flow.py tests\integration\test_job_recovery_flow.py tests\integration\test_sqlite_persistence.py tests\non_functional\test_security_contracts.py`
  - Result: `32 passed`
- Full regression:
  - `py -m pytest -q`
  - Result: `235 passed`

## Remaining Notes

- Full auth remains intentionally deferred because the current deployment assumption is single-user local use.
- If the app is later exposed to LAN/public networks, add an operator token or full auth before deployment.
