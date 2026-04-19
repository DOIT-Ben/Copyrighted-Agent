# Real Provider Validation

## Summary

- generated_at: `2026-04-20T04:05:48`
- status: `blocked`
- summary: Real-provider validation is blocked.

## Config

- provider: `external_http`
- ai_enabled: `True`
- endpoint: `http://127.0.0.1:18011/review`
- model: `MiniMax-M2.7-highspeed`
- api_key_env: `MINIMAX_API_KEY`

## Provider Probe

- status: `pass`
- probe_status: `ok`
- summary: Latest safe provider probe completed successfully.

## Release Gate

- status: `pass`
- summary: Release gate is satisfied for the current environment.

## Mode A Smoke

- status: `blocked`
- path: `input\杞憲鏉愭枡\2501_杞憲鏉愭枡.zip`
- provider: ``
- resolution: ``
- summary: Mode A smoke sample path does not exist.

## Mode B Smoke

- status: `blocked`
- path: `input\鍚堜綔鍗忚`
- summary: Mode B smoke sample path does not exist.

## Recommended Action

- Provide a valid Mode A ZIP path before rerunning release validation.
