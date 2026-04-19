# P26-P29 Validation

## Automated Regression

- Focused command:

```bash
py -m pytest tests\unit\test_provider_probe_contracts.py tests\unit\test_startup_self_check_contracts.py tests\integration\test_provider_probe_flow.py tests\integration\test_operator_console_and_exports.py
```

- Result: `115 passed, 0 failed`

- Final full regression:

```bash
py -m pytest
```

- Result: `115 passed, 0 failed`

## Live Sandbox-First Probe Validation

```powershell
$repo = (Get-Location).Path
$job = Start-Job -ArgumentList $repo -ScriptBlock { param($repoPath) Set-Location $repoPath; py -m app.tools.provider_sandbox --port 18010 --request-log-path data/runtime/logs/provider_probe_sandbox_round6.jsonl --once }
Start-Sleep -Seconds 1
py -m app.tools.provider_probe --enable-ai --provider external_http --endpoint http://127.0.0.1:18010/review --model sandbox-model --probe
Receive-Job $job -Wait -AutoRemoveJob
```

Result:

- `provider_probe status=ok`
- `phase=probe_passed`
- `http_status=200`
- `provider_request_id=sandbox-054a95a3`
- latest probe artifact written to `data/runtime/ops/provider_probe_latest.json`

## Persisted Artifact Verification

- Verified `data/runtime/ops/provider_probe_latest.json`
- `generated_at: 2026-04-20T00:16:54`
- `status: ok`
- `phase: probe_passed`
- `readiness_phase: ready_for_probe`
- endpoint recorded as `http://127.0.0.1:18010/review`

## Rolling Baseline Validation

```bash
py -m app.tools.metrics_baseline --compare-latest-in-dir docs\dev --archive-dir docs\dev\history --archive-stem real-sample-baseline
```

Result:

- generated_at `2026-04-20T00:16:31`
- mode A `materials=24 cases=6 reports=6 unknown=0 needs_review=0 low_quality=0 redactions=252`
- mode B `materials=11 cases=11 reports=1 unknown=0 needs_review=0 low_quality=0 redactions=152`
- archive files:
  - `docs/dev/history/real-sample-baseline_20260420_001631.json`
  - `docs/dev/history/real-sample-baseline_20260420_001631.md`

## Deferred Validation

- Real non-sandbox provider smoke remains blocked on 2026-04-20 because local `config/local.json` and real provider credentials are still absent.
- This is an environment blocker, not a code-path blocker.
