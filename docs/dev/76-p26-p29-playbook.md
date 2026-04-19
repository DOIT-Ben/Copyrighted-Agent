# P26-P29 Playbook

## Reusable Lessons

- Treat provider onboarding as a staged workflow: readiness audit, synthetic safe probe, operator observability, then real smoke.
- Persist the latest probe result even if the probe is launched from CLI; operational truth should not depend on terminal scrollback.
- In PowerShell background jobs, always pass the current repo path into the job and `Set-Location` there before running local `py -m ...` modules.
- Keep readiness language explicit and actionable: missing config should surface as blocking items, not vague warnings.
- Synthetic probe payloads are enough to validate gateway wiring; do not require real user material for connectivity checks.
- When a real gateway is blocked by local secrets, use the blocked time to harden observability and documentation rather than pausing delivery.

## Suggested Repeatable Flow

1. Audit config and readiness requirements for the target provider.
2. Add or update a phase-based readiness contract.
3. Persist the latest probe artifact.
4. Expose readiness and latest probe state in `/ops`.
5. Run focused regression.
6. Validate a live sandbox-first probe with synthetic safe payload.
7. Refresh rolling baseline artifacts.
8. Run final full regression.
9. Record exact blockers, commands, and artifacts in `docs/dev`.
