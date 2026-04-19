# P30-P35 Issues

## Issue 1

- Symptom: the targeted ops regression failed even though the backend feature work was correct.
- Root cause: the integration test relied on `monkeypatch`, which the local lightweight pytest runner does not provide.
- Fix: replaced the fixture usage with explicit `os.environ` save / restore logic.

## Issue 2

- Symptom: adding a safe default `config/local.json` caused startup-self-check contract failures.
- Root cause: tests still encoded the old assumption that no local config file should exist by default.
- Fix: updated the tests to assert local-config presence and normalized Windows path separators.

## Issue 3

- Symptom: `app/web/pages.py` became syntactically invalid after a small text-only polish attempt.
- Root cause: a full-file PowerShell rewrite corrupted UTF-8 source encoding and damaged many Chinese literals.
- Fix: backed up the corrupted file, stopped patching the damaged source, and rebuilt the page module from route and test contracts.

## Issue 4

- Symptom: a compiled-module fallback looked attractive as an emergency recovery path.
- Root cause: `.pyc` artifacts are fragile here because compiling a wrapper overwrites the same cache slot.
- Fix: did not keep the `.pyc` workaround; restored a clean source-based implementation instead.
