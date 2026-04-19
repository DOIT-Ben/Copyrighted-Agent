# Privacy Reuse Playbook

## Purpose

- Reuse this approach whenever a document-analysis workflow must keep sensitive material local while still preparing AI-compatible outputs.

## Recommended Sequence

1. Parse the original file locally.
2. Clean the extracted text.
3. Extract structured fields needed for deterministic business logic.
4. Run local manual desensitization rules.
5. Persist both clean and desensitized artifacts separately.
6. Keep external-model boundaries pointed only at desensitized text or masked structured payloads.
7. Surface privacy status in the user-facing UI.

## Implementation Pattern

- Raw artifact: `raw.txt`
- Clean artifact: `clean.txt`
- Desensitized artifact: `desensitized.txt`
- Privacy manifest: `privacy.json`

## UI Pattern

- Show privacy status at upload time.
- Show privacy summary at submission detail level.
- Show privacy badge wherever report reading or AI-adjacent output appears.

## Intake Pattern

- For zip inputs:
  - validate path safety
  - reject executables
  - ignore archive noise
- For directory inputs:
  - stage files into a managed runtime area
  - sanitize relative paths
  - apply the same ignore and block rules as zip ingestion

## Guardrails

- Do not let a future external AI provider read `raw.txt` or `clean.txt`.
- Keep privacy rules deterministic and local-first.
- Treat `Material.content` as a privacy-safe default field.
- Always add regression tests when new sensitive-field patterns are introduced.

## Residual Risk Handling

- If binary text extraction quality is poor, accept `unknown` rather than fabricating confidence.
- Document these cases explicitly and collect them into a parser-regression corpus for later improvement.
