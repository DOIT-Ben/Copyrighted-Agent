# P45-P49 Issues

## Issue 39

- Symptom: the final real-provider validation path still required manually stitching together several commands.
- Root cause: probe, release gate, and sample smoke validation were separate tools with no single orchestrator.
- Fix: added a dedicated release-validation service and CLI.

## Issue 40

- Symptom: the first integration test for the new validation workflow reported `warning` instead of `pass`.
- Root cause: the test disabled mock fallback, which currently affects readiness / release-gate semantics.
- Fix: aligned the test with the current gate contract and kept the real assertion on actual provider usage in mode A smoke.

## Issue 41

- Symptom: the new release-validation command still reports `blocked` in the live workspace.
- Root cause: the workspace remains in mock mode and has no real endpoint, model, or key mapping.
- Fix: recorded the blocked status as an artifact and reduced the remaining work to explicit config and env inputs.

## Issue 42

- Symptom: the first generated latest JSON artifact had an empty `artifacts` field.
- Root cause: artifact metadata was attached to the result after the file payload had already been serialized.
- Fix: inject artifact metadata into the payload before writing latest/history files, then rerun the validation command to refresh the latest evidence.
