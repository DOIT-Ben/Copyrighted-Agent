# Real Provider Validation

## Summary

- generated_at: `2026-04-26T11:04:01`
- status: `warning`
- summary: Real-provider validation completed, but warnings remain.

## Config

- provider: `external_http`
- ai_enabled: `True`
- endpoint: `http://127.0.0.1:18011/review`
- model: `minimax-m2.7-highspeed`
- api_key_env: `MINIMAX_API_KEY`

## Provider Probe

- status: `pass`
- probe_status: `ok`
- summary: Latest safe provider probe completed successfully.

## Release Gate

- status: `warning`
- summary: Release gate is not fully satisfied yet; warnings remain.

## Mode A Smoke

- status: `pass`
- path: `input\软著材料\2501_软著材料.zip`
- provider: `external_http`
- resolution: `minimax_bridge_success`
- summary: Mode A smoke passed.

## Mode B Smoke

- status: `pass`
- path: `input\合作协议`
- summary: Mode B smoke passed.

## Recommended Action

- The provider returned an HTTP error. Check upstream logs and response body handling before retrying.
