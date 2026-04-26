# 220 Real Sample Acceptance Log

Date: 2026-04-26

## Scope

- Validate real sample acceptance against local MiniMax bridge and `external_http`.
- Record the release-gate false warning fix that affected acceptance status.

## Inputs

- Mode A sample: `input\软著材料\2501_软著材料.zip`
- Mode B sample: `input\合作协议`
- Config: `config\local.json`

## Timeline

### Run 1

- Command: `py -m app.tools.release_validation --config config\local.json --mode-a-path "input\软著材料\2501_软著材料.zip" --mode-b-path "input\合作协议" --json`
- Result time: `2026-04-26T11:04:01`
- Overall: `warning`
- Provider probe: `pass`
- Release gate: `warning`
- Mode A smoke: `pass`
- Mode B smoke: `pass`

### Baseline refresh

- Command: `py -m app.tools.metrics_baseline --compare-latest-in-dir docs\dev --archive-dir docs\dev\history --archive-stem real-sample-baseline --markdown-path docs\dev\220-real-sample-baseline-latest.md --json-path docs\dev\220-real-sample-baseline-latest.json`
- Result:
  - `mode_a_real`: `unknown=0`, `needs_review=0`, `low_quality=0`
  - `mode_b_real`: `unknown=0`, `needs_review=0`, `low_quality=0`
  - Delta: all `0`

### Release gate remediation

- Root cause: historical failed provider probe could keep the gate in warning even after a newer successful probe existed.
- Fix: `app/core/services/release_gate.py`
- Added regression: `tests/unit/test_release_gate_contracts.py`

### Run 2

- Result time: `2026-04-26T11:09:20`
- Overall: `blocked`
- Provider probe: `pass`
- Release gate: `pass`
- Mode B smoke: `pass`
- Mode A smoke: `blocked`
- Block reason: Mode A used `mock` with resolution `provider_exception_fallback`

## Interpretation

- Real sample material quality is healthy.
- Current blocker is provider bridge stability, not sample content quality.
- Acceptance must be re-run after bridge runtime cleanup and response-tolerance hardening.

## Final Acceptance Run

- Runtime cleanup:
  - Stopped duplicate `app.tools.minimax_bridge` processes.
  - Started one clean bridge instance on `http://127.0.0.1:18011/review`.
- Bridge hardening:
  - Added plain-text and conclusion-only response tolerance in `app/tools/minimax_bridge.py`.
- Final run time: `2026-04-26T11:14:23`
- Overall: `pass`
- Provider probe: `pass`
- Release gate: `pass`
- Mode A smoke: `pass`
  - `review_provider=external_http`
  - `review_resolution=minimax_bridge_success`
- Mode B smoke: `pass`

## Final Decision

- Real sample acceptance is now green in the current local environment.
- Remaining work on this topic is limited to ordinary regression coverage and commit hygiene, not business blocking fixes.

## Related Artifacts

- `docs/dev/real-provider-validation-latest.json`
- `docs/dev/real-provider-validation-latest.md`
- `docs/dev/220-real-sample-baseline-latest.json`
- `docs/dev/220-real-sample-baseline-latest.md`
