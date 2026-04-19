# Privacy And Input Round Plan

## Date

- 2026-04-19

## Goal

- Add a manual desensitization pipeline that is explicit, isolated, and traceable.
- Ensure future AI-facing payloads can use desensitized material instead of raw extracted text.
- Support the two real-world intake shapes used by this project:
  - Mode A: one software copyright package per zip
  - Mode B: same material type across multiple software copyrights in one zip or one directory
- Validate the implementation with the real samples already placed under `input/`.

## Scope

### Functional scope

- Introduce a dedicated privacy/desensitization module.
- Save desensitized outputs and privacy manifests alongside parse outputs.
- Add directory-based intake for Mode B.
- Filter archive noise such as `__MACOSX`, `.DS_Store`, and AppleDouble `._*` files.
- Make the UI clearly show that desensitization has been applied.

### Validation scope

- Re-run automated tests.
- Add regression tests for:
  - desensitization behavior
  - directory intake for Mode B
  - noisy archive member filtering
- Run real-sample validation against:
  - `input/软著材料`
  - `input/合作协议`

## Delivery Order

1. Freeze the design and behavior of the privacy boundary.
2. Implement isolated desensitization logic and manifest generation.
3. Integrate privacy outputs into parsing and submission ingestion.
4. Add directory intake support for Mode B and clean noisy archive members.
5. Expose privacy status in the web UI.
6. Validate with tests and real local samples.
7. Record build notes, issues, fixes, and reuse guidance under `docs/dev/`.

## Expected Outputs

- Code:
  - privacy module
  - updated parsing and ingestion pipeline
  - updated web UI
  - regression tests
- Data artifacts:
  - desensitized text files
  - privacy manifest files
- Docs:
  - round todo
  - build log
  - issues and fixes
  - validation record
  - reusable privacy guidance

## Acceptance Criteria

- Raw text and desensitized text are stored separately.
- Desensitization is performed by local deterministic rules, not by an external model.
- The user can see from the UI that desensitization happened.
- Mode A works with the real zip packages in `input/软著材料`.
- Mode B works from a directory input such as `input/合作协议`.
- Automated tests remain green after the change.
