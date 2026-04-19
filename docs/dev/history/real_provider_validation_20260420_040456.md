# Real Provider Validation

## Summary

- generated_at: `2026-04-20T04:04:56`
- status: `blocked`
- summary: Real-provider validation is blocked.

## Config

- provider: `external_http`
- ai_enabled: `True`
- endpoint: `http://127.0.0.1:18011/review`
- model: `MiniMax-M2.7-highspeed`
- api_key_env: `MINIMAX_API_KEY`

## Provider Probe

- status: `blocked`
- probe_status: `skipped`
- summary: external_http is partially configured: API key env.

## Release Gate

- status: `blocked`
- summary: Release gate is blocked for the current environment.

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

- Complete the missing requirements: API key env.
