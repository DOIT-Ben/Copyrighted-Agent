# 194 Backend Resilience Test Log

Time: 2026-04-25 14:01 +08:00

## Goal

Validate the backend stability categories requested in this round: database, cache, idempotency, dependency fallback, distributed deployment, backup/disaster recovery, and interface tolerance.

## Implemented Change

- Added SQLite `submission_id` indexes for the child graph tables:
  - `cases`
  - `materials`
  - `parse_results`
  - `review_results`
  - `report_artifacts`
  - `jobs`
  - `corrections`
- Added a unit contract test to assert required SQLite tables and indexes are created by `init_db()`.

## Verification

- Database / backup / cleanup focused set:
  - `py -m pytest tests.unit.test_sqlite_repository_contracts tests.integration.test_sqlite_persistence tests.unit.test_runtime_backup_contracts tests.unit.test_runtime_cleanup_contracts -q`
  - Result: 7 passed.
- Interface / security / dependency fallback focused set:
  - `py -m pytest tests.integration.test_api_contracts tests.non_functional.test_security_contracts tests.unit.test_external_http_adapter_contracts tests.unit.test_ai_provider_boundary_contracts -q`
  - Result: 17 passed.
- Manual correction / provider fallback focused set:
  - `py -m pytest tests.integration.test_manual_correction_api tests.integration.test_provider_sandbox_flow tests.integration.test_provider_probe_flow -q`
  - Result: 7 passed.
- Full unit suite:
  - `py -m pytest tests.unit -q`
  - Result: 101 passed.
- Full integration suite:
  - `py -m pytest tests.integration -q`
  - Result: 40 passed.
- Security and browser E2E:
  - `py -m pytest tests.non_functional.test_security_contracts tests.e2e.test_browser_workflows -q`
  - Result: 6 passed.

## Coverage Notes

- Database: covered for table creation, indexes, SQLite persistence restore, graph consistency after correction, runtime cleanup, backup and restore.
- SQL performance: covered at baseline index-contract level. No query benchmark or slow-query budget exists yet.
- Dirty data: covered mainly through ZIP input safety, filename sanitization, parser quality buckets, and invalid provider responses. No broad database corruption fuzz suite exists yet.
- Cache: not applicable in the current architecture; there is no Redis or app cache layer.
- Idempotency: partially covered through persistence upsert/delete-save behavior and repeated manual workflow actions. Uploading the same ZIP is intentionally treated as a new batch, not an idempotent request.
- Rate limiting / circuit breaking / degradation: dependency fallback and timeout/error classification are covered for AI provider calls. There is no global HTTP rate limiter or circuit breaker middleware yet.
- Distributed / cluster: not applicable in the current single-process, SQLite + runtime-directory deployment.
- Disaster recovery: runtime backup archive and restore plan are covered.
- Interface tolerance: non-ZIP rejection, ZIP-slip protection, executable rejection, unsafe Windows filename sanitization, invalid external JSON, provider timeout/error mapping, and safe AI payload contracts are covered.
