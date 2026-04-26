# Real Provider Validation

## Summary

- generated_at: `2026-04-26T11:09:20`
- status: `blocked`
- summary: Real-provider validation is blocked.

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

- status: `pass`
- summary: Release gate is satisfied for the current environment.

## Mode A Smoke

- status: `blocked`
- path: `input\软著材料\2501_软著材料.zip`
- provider: `mock`
- resolution: `provider_exception_fallback`
- summary: Mode A smoke used provider=mock instead of external_http.

## Mode B Smoke

- status: `pass`
- path: `input\合作协议`
- summary: Mode B smoke passed.

## Recommended Action

- Check AI config, provider reachability, and fallback behavior before rerunning.
