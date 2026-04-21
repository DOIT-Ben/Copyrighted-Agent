# Real Stack Restart Build Log

Date: 2026-04-21

Scope:
- Remove the need for manual process cleanup when old frontend or bridge listeners keep stale ports alive.
- Provide a single operator-facing command to restart the real bridge and latest frontend instance cleanly.

Changes:
- Added `scripts/restart_real_stack.ps1`.
- The script:
  - stops listeners on `8000`, target bridge port, and target web port
  - optionally accepts an inline API key or reads the configured API key env
  - starts `start_real_bridge.ps1`
  - waits until the bridge port is listening
  - starts `start_real_web.ps1`
  - waits until the web port is listening
  - prints the final frontend, ops, and bridge URLs
  - prints stack status via `scripts/show_stack_status.ps1`
- Updated `docs/dev/09-runbook.md` to document the new restart path.

Reason:
- The workspace previously had stale listeners on `8000`, `18011`, and `18080`, which made it easy to open the wrong frontend instance.
- A clean restart entrypoint reduces operator error and makes local verification reproducible.
