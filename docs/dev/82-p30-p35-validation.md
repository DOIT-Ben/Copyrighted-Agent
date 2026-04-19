# P30-P35 Validation

## Compile Validation

- Command:
  - `py -m py_compile app\core\services\provider_probe.py app\core\services\release_gate.py app\tools\provider_probe.py app\tools\release_gate.py app\api\main.py app\web\pages.py`
- Result:
  - passed

## Targeted Regression

- Command:
  - `py -m pytest tests\integration\test_web_mvp_contracts.py tests\integration\test_operator_console_and_exports.py tests\integration\test_manual_correction_api.py tests\e2e\test_browser_workflows.py tests\unit\test_startup_self_check_contracts.py`
- Result:
  - final targeted run passed
  - browser E2E, submission HTML actions, `/ops`, and startup-self-check contracts all green

## Provider Probe

- Command:
  - `py -m app.tools.provider_probe --config config\local.json`
- Result:
  - `status=ok`
  - `phase=mock_mode`
  - latest artifact persisted to `data\runtime\ops\provider_probe_latest.json`

## Release Gate

- Command:
  - `py -m app.tools.release_gate --config config\local.json`
- Result:
  - `status=warning`
  - `mode=mock_local`
  - local config passed
  - remaining warnings are expected until real external-provider smoke is configured

## Final Regression

- Command:
  - `py -m pytest`
- Result:
  - `121 passed, 0 failed`
