# Legacy CLI Area

The active product is the Web MVP under `app/`.

The root `cli.py` and the `src/` package are retained as legacy CLI-era code for migration history and comparison. They are not the preferred place for new product work.

## Current Policy

- New review logic should be implemented in `app/core/reviewers/`, `app/core/services/`, or `app/core/pipelines/`.
- New UI work should be implemented in `app/web/`.
- New operational commands should be implemented in `app/tools/` or `scripts/`.
- Do not extend `cli.py` or `src/` unless the task is explicitly about legacy compatibility.

## Future Cleanup Path

1. Identify any still-useful functions in `cli.py` or `src/`.
2. Move reusable behavior into `app/core/`.
3. Add tests around the migrated behavior.
4. Move remaining legacy files into `legacy/` or remove them when no longer needed.

## Preferred Entrypoints

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_uv_web.ps1 -Mock
powershell -ExecutionPolicy Bypass -File scripts\start_uv_web.ps1 -Port 18080
.venv\Scripts\pytest.exe -q
```
