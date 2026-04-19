# Privacy And Input Round Issues

## Issue 1

- Symptom: after introducing the generalized input-preparation helper, the old zip extraction call still remained in the submission pipeline.
- Impact: all submission modes failed because `archive_target` no longer existed in that path.
- Fix: removed the stale extraction branch and kept `_prepare_input_source()` as the single intake entry.

## Issue 2

- Symptom: front-end page patching around `app/web/pages.py` drifted because the file already had historical encoding noise.
- Impact: a few privacy UI edits landed in the wrong place during intermediate iterations.
- Fix: corrected the affected HTML structure, rechecked render paths, and kept subsequent edits smaller and more targeted.
- Reuse rule: when a legacy file already shows encoding noise, prefer bounded changes and verify rendered output immediately after edits.

## Issue 3

- Symptom: real zip packages from macOS contained `__MACOSX`, `.DS_Store`, and `._*` members.
- Impact: noisy files polluted parsing and inflated unknown-material counts.
- Fix: added explicit ignore rules in archive extraction and directory staging.

## Issue 4

- Symptom: Mode B originally worked for zip inputs but not for directory inputs.
- Impact: the real `input/合作协议` folder could not be processed through the same submission pipeline.
- Fix: added `stage_directory_input()` and routed directory inputs through the same ingestion path.

## Issue 5

- Symptom: the older classifier was fragile on real Chinese samples and on mojibake-heavy filenames.
- Impact: some real Mode A packages still produced `unknown` materials.
- Fix: rewrote the classifier with cleaner filename/content rules and added a second classification pass after parsing.
- Residual risk: some binary `.doc` samples still remain `unknown` when extraction quality is poor and filenames are damaged.

## Issue 6

- Symptom: ad-hoc validation scripts had path/encoding friction with Chinese directory names depending on the shell and interpreter boundary.
- Impact: local debugging output was noisy and sometimes misleading.
- Fix: used content-based path discovery and UTF-8 stdout reconfiguration in validation scripts.
- Reuse rule: when validating Chinese-path data locally, prefer enumerating directories from the filesystem instead of hardcoding literals into quick scripts.
