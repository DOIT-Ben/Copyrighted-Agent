# Delivery Hardening Validation

## Date

- 2026-04-20

## Script Validation

- Validated `scripts/show_stack_status.ps1`
  - confirms config fields
  - confirms web / bridge / test-web port occupancy
  - confirms presence or absence of API key env
- Validated `scripts/run_real_validation.ps1`
  - first exposed missing API key env in the current shell
  - after env injection, passed end-to-end

## Live Runtime Validation

- Confirmed current local config resolves to:
  - `ai_provider=external_http`
  - `ai_endpoint=http://127.0.0.1:18011/review`
  - `ai_model=MiniMax-M2.7-highspeed`
  - `ai_api_key_env=MINIMAX_API_KEY`
- Confirmed live pages:
  - `http://127.0.0.1:8000/`
  - `http://127.0.0.1:18080/ops`

## Real Provider Validation

- Command used:

```powershell
$env:MINIMAX_API_KEY='<redacted>'
powershell -ExecutionPolicy Bypass -File scripts\run_real_validation.ps1
```

- Result:
  - `status=pass`
  - `provider_probe=ok`
  - `release_gate=pass`
  - `mode_a_smoke=pass`
  - `mode_b_smoke=pass`
- Latest artifact:
  - `docs/dev/real-provider-validation-latest.json`
  - `docs/dev/real-provider-validation-latest.md`

## Full Regression

- Ran full suite via background log capture:

```powershell
py -m pytest
```

- Final result:
  - `passed=131 failed=0 skipped=0 xfailed=0`
- Captured logs:
  - `data/runtime/logs/pytest-full.out.log`
  - `data/runtime/logs/pytest-full.err.log`

## Targeted Runtime Check

- `http://127.0.0.1:8000/` returned `200` and contained:
  - `Control Center`
  - `Import Console`
- `http://127.0.0.1:18080/ops` returned `200` and contained:
  - `Support / Ops`
  - `Provider Readiness`
