# Privacy And Input Round Validation

## Automated Regression

- Command: `py -m pytest`
- Result: `52 passed, 0 failed`

## Added Test Coverage

- `tests/unit/test_privacy_desensitization_contracts.py`
  - local redaction of labeled fields and contacts
  - AI-safe case payload masking
- `tests/integration/test_privacy_and_directory_intake.py`
  - Mode B directory intake
  - privacy manifest persistence
  - macOS archive noise filtering

## Real Sample Validation

### Mode A

- Command:
  - `D:\Soft\python310\python.exe -m app.tools.input_runner --path input\软著材料 --mode single_case_package`
- Result summary:
  - 6 zip packages processed successfully
  - 6/6 submissions completed
  - 4/6 packages achieved full four-type recognition
  - 2/6 packages still contain `unknown` materials due real binary `.doc` extraction quality and damaged filenames
  - all 6 packages produced redaction hits and privacy artifacts

### Mode B

- Command:
  - `D:\Soft\python310\python.exe -m app.tools.input_runner --path input\合作协议 --mode batch_same_material`
- Result summary:
  - 11 materials processed successfully
  - all 11 materials classified as `agreement`
  - 2 grouped cases produced
  - redaction hits recorded across the batch

## Privacy Artifact Validation

- Each parsed material now persists:
  - `raw.txt`
  - `clean.txt`
  - `desensitized.txt`
  - `privacy.json`

## Residual Risks

- Some real `.doc` binary files still extract low-quality text, which limits downstream classification accuracy.
- The current web upload flow is still zip-first; directory intake is available through the ingestion pipeline and local runner, not yet through a browser-side folder UI.
- The current AI provider remains mock-only; the privacy boundary is prepared for future real-provider integration.
