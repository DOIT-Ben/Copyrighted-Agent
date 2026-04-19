# P45-P49 Validation

## Compile Validation

- Command:
  - `py -m py_compile app\core\services\release_validation.py app\tools\release_validation.py tests\unit\test_release_validation_contracts.py tests\integration\test_release_validation_flow.py`
- Result:
  - passed

## Targeted Regression

- Command:
  - `py -m pytest tests\unit\test_release_validation_contracts.py tests\integration\test_release_validation_flow.py tests\unit\test_release_gate_contracts.py tests\integration\test_provider_probe_flow.py`
- Result:
  - the local lightweight pytest runner executed the full suite
  - `127 passed, 0 failed`

## Current Workspace Validation

- Command:
  - `py -m app.tools.release_validation --config config\local.json --mode-a-path input\软著材料\2501_软著材料.zip --mode-b-path input\合作协议 --json`
- Result:
  - `status=blocked`
  - `provider_probe=skipped`
  - `release_gate=warning`
  - latest JSON now includes non-empty `artifacts` metadata pointing to `docs/dev/real-provider-validation-latest.*` and timestamped history artifacts under `docs/dev/history`
  - the current blocker is local mock config, not code readiness

## Final Regression

- Command:
  - `py -m pytest`
- Result:
  - `127 passed, 0 failed`
