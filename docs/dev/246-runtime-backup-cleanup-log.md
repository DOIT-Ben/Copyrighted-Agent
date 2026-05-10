# 246 Runtime Backup And Cleanup Log

Date: 2026-05-09

## Goal

Create a current runtime database backup, then clean expired runtime cache artifacts safely.

## Backup

Command:

```powershell
py -m app.tools.runtime_backup create --json
```

Result:

- Archive: `data/backups/runtime_backup_20260509_232030.zip`
- Size: `772351313` bytes
- File count: `143668`
- SQLite path: `data/runtime/soft_review.db`
- SQLite snapshot included: `true`
- SQLite snapshot mode: `sqlite_backup_api`

## Cleanup Plan

Command:

```powershell
py -m app.tools.runtime_cleanup
```

Dry-run summary:

- Retention: `14` days
- Cutoff before: `2026-04-25T23:25:52`
- Candidate count: `4293`
- Candidate size: `975509021` bytes, about `930.32 MiB`
- Scope `submissions`: `2866`
- Scope `uploads`: `1401`
- Scope `logs`: `26`
- SQLite action: `skip_manual_backup`

The cleanup candidates were limited to:

- `data/runtime/submissions`
- `data/runtime/uploads`
- `data/runtime/logs`

## Cleanup Execution

Command:

```powershell
py -m app.tools.runtime_cleanup --apply
```

Execution summary:

- Deleted count: `4293`
- Failed count: `0`
- Missing count: `0`
- SQLite database was not deleted by cleanup.

Supplemental top-level runtime debug cache cleanup:

- Deleted count: `16`
- Deleted size: `7659820` bytes, about `7.3 MiB`
- Scope: explicit whitelist under `data/runtime`
- Patterns: `diagnostic_*`, `release_validation_debug*`, `legacy_doc_content_recovery_debug*.zip`, `tmp_quality_gate.zip`

## Verification

Backup manifest inspection:

- Format version: `soft_review.runtime_backup.v1`
- SQLite snapshot mode: `sqlite_backup_api`

SQLite integrity check:

```text
PRAGMA integrity_check = ok
```

Post-cleanup dry-run:

- Candidate count: `0`
- Candidate bytes: `0`

Post supplemental cleanup whitelist scan:

- Candidate count: `0`

Current SQLite table counts:

- `submissions`: `8`
- `materials`: `33`
- `parse_results`: `33`
- `cases`: `6`
- `report_artifacts`: `50`
- `review_results`: `16`
- `jobs`: `7`
- `corrections`: `4`

## Notes

- The previous archive `data/backups/runtime_backup_20260419_2219.zip` was preserved.
- The new archive `data/backups/runtime_backup_20260509_232030.zip` is the latest rollback point.
- No source code changes were made for this operation.
