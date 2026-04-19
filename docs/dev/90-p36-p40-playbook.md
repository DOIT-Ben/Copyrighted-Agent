# P36-P40 Playbook

## Reusable Lessons

- Use page boundaries as the first modularization layer for admin tools; it keeps extraction understandable and testable.
- Preserve a stable import barrel when the API layer already depends on a well-known renderer module path.
- Shared helper extraction should include both HTML primitives and the page shell, otherwise every page keeps drifting structurally.
- Run browser E2E after renderer extraction even if unit and integration contracts already pass; admin UI wiring regressions often live at the route/render boundary.
- A good recovery sequence is:
  1. restore behavior
  2. freeze with regression
  3. modularize
  4. re-run regression

## Suggested Next Reuse

- If more UI work is planned, continue iterating inside page-scoped modules first.
- Only split into smaller component-level helpers once one page module becomes hard to scan again.
