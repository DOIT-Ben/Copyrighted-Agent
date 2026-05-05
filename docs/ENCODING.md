# Encoding And Copywriting Guardrails

This project contains Chinese product copy and Windows-first scripts, so encoding discipline matters.

## Rules

- Treat all source, Markdown, JSON, TOML, CSS, and JavaScript files as UTF-8.
- Do not rewrite large files with PowerShell `Get-Content | Set-Content` unless encoding is explicitly controlled.
- Prefer `apply_patch` for edits to source files.
- Before fixing text that appears garbled in PowerShell, verify the real file content with Python.
- Keep new user-facing Chinese copy short, direct, and task-oriented.
- Put large UX copy changes behind tests that assert the expected page text still renders.

## Verification

Use Python to inspect suspicious text:

```powershell
@'
from pathlib import Path

path = Path(r"app\web\page_submission.py")
for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
    if any(ord(ch) > 127 for ch in line):
        print(f"{idx}: {line.encode('unicode_escape').decode('ascii')}")
'@ | .venv\Scripts\python.exe -
```

If the output shows normal `\uXXXX` escapes, the file is valid UTF-8 and the terminal preview is the problem.

## CI Guardrails

- `.gitattributes` keeps text files normalized by type.
- `tests/non_functional/test_encoding_contracts.py` checks key docs and config files are UTF-8 readable.
- `tests/unit/test_web_source_contracts.py` checks active web source files avoid known mojibake markers.

## Preferred Workflow

1. Edit with `apply_patch`.
2. Run targeted page or source tests.
3. Run `.venv\Scripts\pytest.exe -q`.
4. Commit only source, docs, tests, and project metadata.
