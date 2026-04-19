# P23-P25 Playbook

## Reusable Lessons

- If a follow-up slice is blocked only by missing environment configuration, keep shipping non-blocked observability and workflow improvements.
- A baseline tool becomes operationally useful only after three things are present together: latest snapshot, comparison delta, and timestamped history.
- For admin tools, operators need “what is the status”, “what changed”, and “how do I reproduce it” in the same page.
- Whenever status semantics change from passive existence to active health, update both service contracts and UI language in the same slice.
- Keep historical artifacts under a dedicated folder such as `docs/dev/history`; otherwise the latest file and the archive file patterns become difficult to reason about.

## Suggested Repeatable Flow

1. Run or generate the new baseline snapshot.
2. Auto-compare it with the latest previous baseline.
3. Archive both JSON and Markdown outputs.
4. Surface the newest summary plus recent history in `/ops`.
5. Run focused regression, then full regression.
6. Record exact metrics and archive paths in `docs/dev`.
