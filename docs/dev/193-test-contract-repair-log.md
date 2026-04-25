# 193 Test Contract Repair Log

Time: 2026-04-25 13:45:53 +08:00

## Goal

Repair the failing automated checks after the frontend simplification and business-side closeout work, while keeping the UI concise.

## Changes

- Restored the home page contract text `浏览器端导入说明` inside the existing import copy block instead of adding another panel.
- Restored the ops page probe contract by showing `探针观测 / 探针历史` in the existing observatory details block.
- Restored batch detail navigation contract text with compact summary tiles for `下一步` and `更多信息`.
- Fixed runtime cleanup age calculation to use natural-day age instead of flooring exact seconds, so retention cleanup is stable around partial-day boundaries.

## Verification

- Unit: `py -m pytest tests.unit -q` -> 100 passed.
- Integration: `py -m pytest tests.integration -q` -> 40 passed.
- Security: `py -m pytest tests.non_functional.test_security_contracts -q` -> 3 passed.
- E2E: `py -m pytest tests.e2e -q` -> 3 passed.

## Notes

- The repository currently has unit, integration, E2E, and security suites. I did not find dedicated visual or performance test modules under `tests/`; those remain manual or future automation work.
- The local custom `pytest` package does not reliably support function-level selectors or Windows directory paths. Use module-style commands such as `py -m pytest tests.integration -q`.
