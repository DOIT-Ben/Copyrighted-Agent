# Real Provider Acceptance Checklist

## Current Validated State On 2026-04-20

- first true non-mock validation has passed in this workspace
- validated upstream vendor path: MiniMax via local bridge
- validated model: `MiniMax-M2.7-highspeed`
- validated local endpoint: `http://127.0.0.1:18011/review`
- validated API key env name: `MINIMAX_API_KEY`
- latest pass artifact: `docs/dev/real-provider-validation-latest.json`

## Goal

Reach the first true non-mock validated state with one repeatable command and clear pass criteria.

## Inputs You Still Need To Provide

1. Export the actual API key into the configured environment variable.
2. Start the local bridge:
   - `py -m app.tools.minimax_bridge --port 18011 --upstream-base-url https://api.minimaxi.com/v1 --upstream-model MiniMax-M2.7-highspeed --upstream-api-key-env MINIMAX_API_KEY`
3. Optionally use the delivery wrappers:
   - `powershell -ExecutionPolicy Bypass -File scripts\start_real_bridge.ps1`
   - `powershell -ExecutionPolicy Bypass -File scripts\run_real_validation.ps1`

## Validation Command

Raw command:

```bash
py -m app.tools.release_validation --config config\local.json --mode-a-path input\软著材料\2501_软著材料.zip --mode-b-path input\合作协议
```

Preferred wrapper:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_real_validation.ps1
```

## Pass Criteria

- `release_validation status=pass`
- `provider_probe=ok`
- `release_gate=pass`
- `mode_a_smoke=pass`
- `mode_a_smoke.review_provider=external_http`
- `mode_a_smoke.review_resolution` is not any fallback mode
- `mode_b_smoke=pass`
- latest artifacts are written under `docs/dev`

## Active Config Path

- `config/local.json`
- `SOFT_REVIEW_*` env overrides
- do not edit legacy `config/settings.py` for this flow

## If It Fails

- `provider_probe=failed`
  Fix endpoint reachability, auth, timeout, or response JSON contract first.
- `release_gate=warning` or `blocked`
  Read the first recommended action in the artifact and clear the gate item.
- `mode_a_smoke=blocked`
  Inspect provider usage and fallback behavior in the generated artifact.
- `mode_b_smoke=warning`
  Inspect the sample corpus output for remaining `unknown / needs_review / low_quality`.

## Current State On 2026-04-20

- the command already exists
- the code path is tested
- the first live MiniMax bridge path has already passed
- `config/local.json` now points to the validated bridge-backed `external_http` path
