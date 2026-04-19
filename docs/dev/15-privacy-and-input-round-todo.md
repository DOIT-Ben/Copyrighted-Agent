# Privacy And Input Round Todo

## In Progress

- [x] Add a standalone desensitization module with structured output
- [x] Persist desensitized text and privacy manifest files per material
- [x] Define an AI-safe material payload boundary
- [x] Add directory intake support for Mode B
- [x] Skip noisy archive members such as `__MACOSX`, `.DS_Store`, and `._*`
- [x] Expose desensitization status and summary in the web UI
- [x] Add tests for privacy behavior and directory intake
- [x] Run real samples from `input/软著材料`
- [x] Run real samples from `input/合作协议`
- [x] Record problems, fixes, and reuse guidance in `docs/dev/`

## Risks To Watch

- Binary `.doc` parsing quality on real samples
- Filename mojibake inside third-party zip packages
- Over-masking that removes too much structure for grouping and review
- Under-masking that leaves contact or identity information visible
- Directory intake semantics for Mode B when files cannot be confidently grouped

## Exit Condition

- The project can demonstrate privacy-first processing on both Mode A and Mode B inputs with traceable local artifacts and passing regression tests.
