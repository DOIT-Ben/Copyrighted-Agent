# Real Provider Validation

## Summary

- generated_at: `2026-04-20T04:03:35`
- status: `blocked`
- summary: Real-provider validation is blocked.

## Config

- provider: `mock`
- ai_enabled: `False`
- endpoint: ``
- model: ``
- api_key_env: ``

## Provider Probe

- status: `blocked`
- probe_status: `skipped`
- summary: Live external_http probe skipped because provider=mock.

## Release Gate

- status: `warning`
- summary: Release gate is not fully satisfied yet; warnings remain.

## Mode A Smoke

- status: `blocked`
- path: `input\杞憲鏉愭枡\2501_杞憲鏉愭枡.zip`
- provider: ``
- resolution: ``
- summary: Real-provider probe did not pass, so sample smokes were not executed.

## Mode B Smoke

- status: `blocked`
- path: `input\鍚堜綔鍗忚`
- summary: Real-provider probe did not pass, so sample smokes were not executed.

## Recommended Action

- Keep mock mode for normal local work, or create config\local.json / env overrides and switch ai_provider to external_http when you are ready for a live probe.
