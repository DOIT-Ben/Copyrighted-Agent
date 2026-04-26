# 221 Encoding Governance Audit Log

Date: 2026-04-26

## Goal

- Verify whether the observed Chinese mojibake is a source-file encoding problem or a PowerShell display problem.
- Avoid destructive bulk re-encoding unless actual UTF-8 corruption is confirmed.

## Audit Notes

- PowerShell output shows mojibake for several Chinese strings in logs and inline command output.
- Targeted checks using Python `unicode_escape` inspection showed that multiple suspected files still contain valid source text and not replacement corruption.
- Checked areas included:
  - `app/tools/metrics_baseline.py`
  - `app/core/services/release_validation.py`
  - `app/web/page_submission.py`
  - `app/web/page_ops.py`
  - `app/core/utils/text.py`

## Findings

- The displayed mojibake is mostly terminal rendering noise.
- No broad UTF-8 rewrite is justified from the current evidence.
- `app/core/utils/text.py` intentionally references `\ufffd` for garbled-text detection logic; this is expected and not a corruption symptom.
- Runtime JSON logs can still look garbled when the shell code page does not match UTF-8. That does not imply the persisted JSON bytes are invalid.

## Governance Decision

- Do not perform mass file re-encoding.
- Keep future encoding checks targeted and evidence-based.
- When Chinese content correctness matters, inspect raw bytes or escaped text instead of trusting PowerShell glyph rendering.

## Follow-up

- If a specific page or API payload shows user-visible garbling in the browser, audit that exact persistence and render path separately.
