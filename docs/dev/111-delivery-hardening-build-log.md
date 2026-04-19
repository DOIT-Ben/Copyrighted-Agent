# Delivery Hardening Build Log

## Date

- 2026-04-20

## Scope

- 收敛本地运行方式
- 收敛真实验证方式
- 收敛 README / runbook / `/ops` 命令入口
- 处理交付前的版本管理准备

## Changes Completed

### 1. Added Delivery Scripts

- Added `scripts/start_mock_web.ps1`
- Added `scripts/start_real_bridge.ps1`
- Added `scripts/start_real_web.ps1`
- Added `scripts/run_real_validation.ps1`
- Added `scripts/show_stack_status.ps1`

### 2. Hardened Script Behavior For Windows

- Fixed the PowerShell `param(...)` placement issue so the scripts execute correctly.
- Forced UTF-8 console / Python output in the scripts to reduce Windows Chinese-path encoding failures.
- Made `run_real_validation.ps1` auto-resolve the default sample inputs from `input/` instead of hardcoding fragile localized paths.

### 3. Aligned The Product Surface

- Updated `app/web/page_ops.py`
- Added script entrypoints to the operator command panel
- Added bridge / endpoint / model visibility to the ops surface
- Kept existing operator / provider / release-gate contract strings intact

### 4. Aligned Public Documentation

- Rewrote `README.md` to reflect the current product shape and startup flow
- Updated `docs/dev/09-runbook.md`
- Updated `docs/dev/106-real-provider-acceptance-checklist.md`
- Updated `config/local.example.json`

### 5. Normalized The Default Local Config

- Updated `config/local.json` to the validated local bridge-backed `external_http` path:
  - endpoint `http://127.0.0.1:18011/review`
  - model `MiniMax-M2.7-highspeed`
  - API key env `MINIMAX_API_KEY`
- Kept `ai_fallback_to_mock=true`
- Kept mock mode available through `scripts/start_mock_web.ps1`

## Files Changed

- `README.md`
- `config/local.json`
- `config/local.example.json`
- `app/web/page_ops.py`
- `tests/integration/test_operator_console_and_exports.py`
- `docs/dev/09-runbook.md`
- `docs/dev/106-real-provider-acceptance-checklist.md`
- `docs/dev/110-delivery-hardening-todo.md`
- `scripts/start_mock_web.ps1`
- `scripts/start_real_bridge.ps1`
- `scripts/start_real_web.ps1`
- `scripts/run_real_validation.ps1`
- `scripts/show_stack_status.ps1`
