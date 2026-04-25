# 200 MiniMax Provider Stability Log

Date: 2026-04-25

## Scope

- Investigated the latest `provider_exception_fallback` seen during live review.
- Verified the failure was not an upstream MiniMax outage.
- Root cause: the local MiniMax bridge process was still running the old `is_ai_safe_case_payload` validation logic and rejected the newly added safe material inventory with `case_payload_not_ai_safe`.

## Fix

- Restarted the local MiniMax bridge after the safe material inventory change.
- Restarted the web service so both processes read the same configuration and code version.
- Standardized the configured model name to `minimax-m2.7-highspeed`, matching the requested MiniMax model name.
- Updated the MiniMax bridge default model to `minimax-m2.7-highspeed`.

## Evidence

- Before restart:
  - `data/runtime/logs/minimax_bridge.jsonl`
  - `2026-04-25T18:00:23`: `validation_errors=["case_payload_not_ai_safe"]`
  - `2026-04-25T18:04:42`: `validation_errors=["case_payload_not_ai_safe"]`
- After restart:
  - Provider probe: `status=ok`, `phase=probe_passed`, HTTP `200`
  - Bridge log: `validation_errors=[]`, `resolution=minimax_bridge_success`
  - Live submission: `sub_ab939ec38e`
  - AI provider: `external_http`
  - AI resolution: `minimax_bridge_success`
  - No fallback wording in generated report.

## Validation

- `py -m app.tools.provider_probe --config config\local.json --probe`
  - Result: `provider_probe status=ok`
- `py -m pytest tests.unit.test_minimax_bridge_contracts tests.unit.test_provider_probe_contracts tests.integration.test_provider_probe_flow tests.integration.test_minimax_bridge_flow tests.unit.test_privacy_desensitization_contracts tests.integration.test_mode_a_pipeline_contracts -q`
  - Result: `18 passed`

