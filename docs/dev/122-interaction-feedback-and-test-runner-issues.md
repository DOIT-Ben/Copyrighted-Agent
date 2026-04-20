# 122 Interaction Feedback And Test Runner Issues

## Issue 1

- Symptom:
  - browser E2E appeared to hang during upload or review rerun
- Root cause:
  - `py -m pytest` executed the repository-local `pytest` package, not the external pytest library
  - that runner did not support `autouse`, `request`, `monkeypatch`, or `yield` fixture behavior
  - the intended mock-AI isolation therefore never applied
- Fix:
  - harden the local runner and make the mock runtime fixture autouse

## Issue 2

- Symptom:
  - success-banner redirects were correct in app logic but could be inconsistent in the live WSGI path
- Root cause:
  - the local `fastapi` shim needed better query-string handling
- Fix:
  - preserve `QUERY_STRING` and parse order correctly so `?notice=...#anchor` works in browser workflows

## Issue 3

- Symptom:
  - operator actions felt abrupt and the interface gave too little guidance after submit
- Root cause:
  - action completion state was implicit instead of visible
  - forms assumed operator context instead of explaining intent
- Fix:
  - add explicit feedback banners, target-panel return paths, field hints, and clearer action labels

## Guardrails

- Treat the local test runner as part of the product delivery surface, not just tooling.
- When browser E2E fails only under `py -m pytest`, inspect the runner semantics before blaming business logic.
- For admin workflows, every mutating action should answer two questions immediately:
  - did it succeed
  - where should the operator look next
- Keep deterministic regression on mock AI by default.
- Reserve live-provider verification for explicit sandbox and acceptance flows.

## Reuse Notes

- If a future change adds new operator actions, wire a success code, banner copy, and target anchor in the same round.
- If a future test truly needs live local AI config, mark it with `@pytest.mark.live_ai_config`.
- Prefer targeted reruns first:
  - `py -m pytest tests\e2e\test_browser_workflows.py`
  - `py -m pytest tests\integration\test_operator_console_and_exports.py`
