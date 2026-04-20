# 117 Release Polish Issues

## Issue

- Browser E2E requests timed out when the local runtime inherited the live `external_http` provider configuration from `config/local.json`.

## Why It Happened

- The browser workflow tests start a real in-process web server with `create_app(testing=True)`.
- That app still reads the active local configuration and can therefore hit the live provider bridge during upload and case rerun flows.
- For UX-only changes, this introduces unnecessary timing variance into what should be a deterministic regression gate.

## Resolution For This Round

- Keep the live-provider configuration for real integration and acceptance work.
- Use mock-mode environment overrides for browser-facing regression validation in UX rounds.

## Reusable Rule

- Separate verification into two lanes:
  - deterministic UI and workflow regression in mock mode
  - explicit real-provider validation in the provider acceptance flow

## Follow-up Recommendation

- Add a dedicated test helper or fixture for browser E2E that forces mock mode by default unless a test explicitly opts into live-provider behavior.
