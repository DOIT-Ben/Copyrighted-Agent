# P41-P44 Issues

## Issue 36

- Symptom: valid UTF-8 Chinese strings can still look broken in PowerShell previews.
- Root cause: terminal display encoding can distort preview output even when the source file is healthy.
- Fix: documented a Python `unicode_escape` verification workflow and added tests that look for known mojibake markers in active web source.

## Issue 37

- Symptom: the "continue" path could waste a round attempting real-provider work that is still not locally actionable.
- Root cause: `config/local.json` remains mock-first and no provider env variables are present.
- Fix: front-loaded a readiness audit, recorded the blocked state, and spent the round on the highest-value non-blocked guardrail work instead.

## Issue 38

- Symptom: a Windows-safety test can itself become fragile if suspicious mojibake markers are hardcoded directly.
- Root cause: the guardrail source then depends on the same kind of literal stability it is meant to protect.
- Fix: generated the suspicious marker set from canonical localized terms at runtime and revalidated the test plus full suite.
