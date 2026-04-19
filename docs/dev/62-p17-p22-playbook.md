# P17-P22 Reuse Playbook

## Provider Onboarding Sequence

1. Keep production provider disabled in config.
2. Stand up `app.tools.provider_sandbox`.
3. Run `app.tools.provider_probe` with a safe synthetic payload.
4. Only after probe success, point the real gateway config at the actual endpoint.
5. Keep `ai_require_desensitized=true` and keep fallback behavior explicit.

## Ops Page Rule

- If an operator must open the terminal to discover whether backup, baseline, or provider state is healthy, the dashboard is still incomplete.
- `/ops` should always show the latest known backup, the latest known baseline, and current provider readiness summary.

## Parser Hardening Sequence

1. Run real samples and collect aggregate metrics.
2. Identify exact files and reason codes.
3. Fix normalization issues before loosening thresholds.
4. Add regression tests for every recovered file family.
5. Re-run the same real-sample baseline compare against a saved JSON snapshot.

## PDF Extraction Rule

- Before assuming a PDF is image-only or noisy, check whether the file contains compressed content streams and `ToUnicode` maps.
- A lightweight internal parser can often recover enough text for rule review without introducing new external dependencies.

## Release Rule

- Do not call a round complete until all four are true:
  - full automated regression passes
  - real-sample smoke is rerun
  - trend artifacts are regenerated
  - docs are updated for plan, build, issues, validation, and reuse guidance
