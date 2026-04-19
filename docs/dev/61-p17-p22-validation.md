# P17-P22 Validation

## Automated Regression

- Command: `py -m pytest`
- Result: `110 passed, 0 failed`

## Provider Probe Validation

- Command:

```powershell
$job = Start-Job -ScriptBlock { py -m app.tools.provider_sandbox --port 18010 --request-log-path data/runtime/logs/provider_probe_sandbox.jsonl --once }
Start-Sleep -Seconds 1
py -m app.tools.provider_probe --enable-ai --provider external_http --endpoint http://127.0.0.1:18010/review --model sandbox-model --probe
```

- Result:
  - readiness status `ok`
  - probe status `ok`
  - HTTP `200`
  - returned `provider_request_id`

## Baseline Trend Validation

- Command:

```bash
py -m app.tools.metrics_baseline --compare docs\dev\55-real-sample-baseline.json --markdown-path docs\dev\56-real-sample-baseline-compare.md --json-path docs\dev\57-real-sample-baseline-compare.json
```

- Result:
  - Mode A `needs_review: -10`
  - Mode A `low_quality: -10`
  - Mode B `needs_review: -2`
  - Mode B `low_quality: -2`
  - Mode B `cases: +1`

## Real Sample Smoke

- Command: `py -m app.tools.input_runner --path input\软著材料 --mode single_case_package`
- Result: `packages=6 materials=24 cases=6 reports=6 unknown=0 needs_review=0 low_quality=0 redactions=252`

- Command: `py -m app.tools.input_runner --path input\合作协议 --mode batch_same_material`
- Result: `materials=11 cases=11 reports=1 needs_review=0 low_quality=0 redactions=152`

## Ops Validation

- `/ops` now exposes:
  - Provider Readiness
  - Latest Backup
  - Latest Baseline
  - provider probe and baseline compare commands

- Integration coverage:
  - `tests/integration/test_operator_console_and_exports.py`
  - `tests/unit/test_ops_status_contracts.py`
