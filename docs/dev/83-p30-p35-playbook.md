# P30-P35 Playbook

## Reusable Lessons

- Use `config/local.json` to make local startup and ops status reproducible even before real provider credentials exist.
- When a local pytest runner is intentionally lightweight, prefer minimal fixture dependencies in new tests.
- If a page module is badly corrupted, use route contracts and page tests as the reconstruction boundary; they are faster and safer than line-by-line string salvage.
- Back up broken source into `docs/dev/history` before recovery work so the failure remains traceable.
- Treat “mock mode warning” as a healthy intermediate operational state when real credentials are intentionally absent.

## Guardrails To Reuse

- Prefer `apply_patch` over full-file shell rewrites for Python source.
- Run targeted regression after each recovery step before spending time on a full suite.
- Update tests immediately when product defaults change intentionally.
- Keep `/ops` command guidance aligned with real executable commands in the workspace.
