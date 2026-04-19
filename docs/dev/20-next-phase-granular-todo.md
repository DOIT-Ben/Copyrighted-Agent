# Next Phase Granular Todo

## Date

- 2026-04-19

## Goal

- Push the project from "privacy-safe MVP that can run" to "internal analysis system that can be used continuously".

## Priority Order

1. Improve real-sample parsing and classification quality
2. Build manual correction workflow
3. Add persistent storage
4. Complete browser-side intake and operator tooling
5. Prepare real AI provider integration
6. Add deployment and operations baseline

## P0 Parsing And Classification Quality

### P0.1 Build a real-sample parser regression corpus

- [ ] Create `data/regression_samples/` for parser-focused samples
- [ ] Copy or derive safe internal regression cases from the current real inputs
- [ ] Create one sample set for `.doc`
- [ ] Create one sample set for `.docx`
- [ ] Create one sample set for `.pdf`
- [ ] Create one sample set for mojibake filename cases
- [ ] Create one sample set for macOS archive noise cases
- [ ] Create metadata notes for each sample:
  - expected material type
  - expected parse quality
  - known failure mode

### P0.2 Improve binary `.doc` parsing

- [ ] Audit current `DocBinaryParser` output quality on `2502` and `2505`
- [ ] Add heuristics to distinguish garbage text from valid extracted text
- [ ] Evaluate whether `.doc` fallback extraction can be improved without external services
- [ ] Add parser quality score into parse metadata
- [ ] Mark low-quality parse results explicitly in the UI or report
- [ ] Add regression tests for low-quality `.doc` parsing behavior

### P0.3 Improve classifier resilience

- [ ] Add more filename keyword variants for info forms
- [ ] Add more filename keyword variants for software docs
- [ ] Add more filename keyword variants for agreements
- [ ] Add more code-language content heuristics
- [ ] Add content-based agreement heuristics for damaged filenames
- [ ] Add content-based software-doc heuristics for damaged filenames
- [ ] Add classification debug fields into metadata:
  - first pass result
  - second pass result
  - confidence
  - reason
- [ ] Add tests for damaged-filename classification

### P0.4 Add parse quality and unknown handling rules

- [ ] Define when a material should remain `unknown`
- [ ] Add a parse-quality threshold for "unsafe to auto-classify"
- [ ] Expose unknown-material count in submission detail
- [ ] Add operator note text for "why this material is unknown"
- [ ] Add regression tests for unknown fallback behavior

## P1 Manual Correction Workflow

### P1.1 Manual material correction data model

- [ ] Define correction record structure
- [ ] Decide whether correction is attached to `Material` or stored separately
- [ ] Add fields for:
  - original classification
  - corrected classification
  - corrected case target
  - corrected by
  - corrected at
  - correction note

### P1.2 Manual correction backend actions

- [ ] Add endpoint to change material type
- [ ] Add endpoint to assign a material to an existing case
- [ ] Add endpoint to remove a material from a case
- [ ] Add endpoint to create a new case from selected materials
- [ ] Add endpoint to merge cases
- [ ] Add endpoint to rerun case-level review after correction
- [ ] Add endpoint to regenerate report artifacts after correction

### P1.3 Manual correction UI

- [ ] Add a "needs review" queue panel for unknown materials
- [ ] Add classification edit control per material
- [ ] Add case assignment control per material
- [ ] Add case merge action in the submission detail view
- [ ] Add rerun review action
- [ ] Add regenerate report action
- [ ] Add operator confirmation UI for destructive regrouping actions

### P1.4 Manual correction audit trail

- [ ] Add correction history list in submission detail
- [ ] Add correction count KPI
- [ ] Add operator notes display
- [ ] Add tests for correction audit persistence

## P2 Persistent Storage

### P2.1 Storage design

- [ ] Choose first persistence target: `SQLite`
- [ ] Define schema for:
  - submissions
  - cases
  - materials
  - parse results
  - review results
  - report artifacts
  - jobs
  - corrections
- [ ] Decide what remains file-based and what moves into DB metadata

### P2.2 Repository layer

- [ ] Create a storage abstraction layer
- [ ] Add runtime-store adapter for current in-memory behavior
- [ ] Add SQLite repository implementation
- [ ] Add migration/bootstrap script for local DB initialization
- [ ] Add repository tests

### P2.3 Pipeline persistence integration

- [ ] Persist submissions to DB
- [ ] Persist materials to DB
- [ ] Persist parse results to DB
- [ ] Persist review results to DB
- [ ] Persist report metadata to DB
- [ ] Load submission detail from DB instead of only runtime memory
- [ ] Verify restart-safe behavior

## P3 Browser Intake And Operator Experience

### P3.1 Browser-side Mode B intake

- [ ] Decide UI pattern for Mode B:
  - upload zip
  - select folder
  - drag-drop many files
- [ ] Add a dedicated Mode B intake form
- [ ] Show accepted intake shapes in the UI
- [ ] Show file-count preview before submission
- [ ] Show operator warning when folder intake is not supported by browser

### P3.2 Upload and processing feedback

- [ ] Add live job status indicator
- [ ] Add material count progress
- [ ] Add parse count progress
- [ ] Add review count progress
- [ ] Add final summary card after ingestion

### P3.3 Privacy visibility improvements

- [ ] Add privacy manifest download link per material
- [ ] Add desensitized-text preview panel
- [ ] Add raw/clean/desensitized artifact availability status
- [ ] Add privacy hit categories filter in submission detail
- [ ] Add privacy summary to generated reports

## P4 Real AI Provider Preparation

### P4.1 Provider boundary design

- [ ] Define exact AI-safe payload contract
- [ ] Ensure no raw text path can enter provider calls
- [ ] Add provider adapter interface
- [ ] Add provider config loading
- [ ] Add provider enable/disable switch

### P4.2 Mock-to-real integration path

- [ ] Keep mock provider as fallback
- [ ] Add first real provider implementation
- [ ] Add redaction-safe prompt template
- [ ] Add provider error handling
- [ ] Add provider timeout and retry policy
- [ ] Add tests for provider fallback behavior

### P4.3 AI result governance

- [ ] Mark AI-generated conclusions clearly in UI
- [ ] Separate rule findings from AI explanations
- [ ] Add operator override for AI conclusion
- [ ] Add AI invocation audit record

## P5 Reports And Export

### P5.1 Report content quality

- [ ] Add privacy summary section into material report
- [ ] Add privacy summary section into case report
- [ ] Add privacy summary section into batch report
- [ ] Add parse-quality note for low-confidence materials
- [ ] Add unknown-material warning section where needed

### P5.2 Export capability

- [ ] Add report download endpoint
- [ ] Add privacy manifest download endpoint
- [ ] Add batch export for submission artifacts
- [ ] Add operator-friendly export naming rules

## P6 E2E And Validation

### P6.1 Browser-level E2E

- [ ] Add homepage upload E2E
- [ ] Add submission detail E2E
- [ ] Add report reader E2E
- [ ] Add privacy panel visibility E2E
- [ ] Add Mode B intake E2E

### P6.2 Real-sample validation workflow

- [ ] Add reusable validation command docs
- [ ] Add validation snapshot output format
- [ ] Record unknown-material rates across sample batches
- [ ] Record redaction-hit totals across sample batches
- [ ] Add a pass/fail threshold for sample validation

## P7 Deployment And Ops

### P7.1 Runtime packaging

- [ ] Replace current minimal run path with a clearer app startup strategy
- [ ] Add config file support
- [ ] Add runtime directories bootstrap
- [ ] Add environment variable documentation

### P7.2 Logging and supportability

- [ ] Add structured application logs
- [ ] Add ingestion error logs
- [ ] Add parser warning logs
- [ ] Add privacy-stage logs
- [ ] Add operator troubleshooting section in docs

## Recommended Immediate Sprint

- [ ] Finish parser-quality diagnosis for `2502` and `2505`
- [ ] Add parse-quality metadata and UI visibility
- [ ] Build the first manual correction endpoints
- [ ] Add manual correction queue to submission detail
- [ ] Start SQLite schema and repository layer

## Definition Of Done For The Next Stage

- [ ] Unknown materials from real samples are reduced or explicitly explained
- [ ] Operators can manually correct classification and regroup cases
- [ ] Data survives service restart
- [ ] Privacy boundary remains local-first and auditable
- [ ] Browser workflows cover both Mode A and Mode B intake paths
