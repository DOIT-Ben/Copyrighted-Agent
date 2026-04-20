# 119 Test Runtime Isolation Validation

## Validation Plan

- Run the browser workflow tests directly to confirm the timeout issue disappears.
- Run the full pytest suite to ensure the new default test runtime does not break other coverage lanes.

## Commands

```powershell
py -m pytest tests\e2e\test_browser_workflows.py
py -m pytest
```

## Result

- Browser workflow regression: passed.
- Full regression: `passed=131 failed=0 skipped=0 xfailed=0`.
- The previous timeout symptom did not reappear after the default mock test-runtime override was added.

## Observations

- Browser E2E no longer depends on the local live provider being fast or available.
- Real-provider coverage remains intact because dedicated provider and release-validation tests still use explicit sandboxed `AppConfig` inputs.

## Notes

- If a future test genuinely needs to inherit the local live AI configuration, mark it with `@pytest.mark.live_ai_config`.
