# UI Regression Note

## Date

- 2026-04-19

## Symptom

- The frontend looked like raw text or a giant button instead of the intended admin dashboard.
- The latest dashboard HTML was already present, but the browser did not apply the stylesheet.

## Root Cause

- `/static/styles.css` was returned with `text/plain; charset=utf-8`.
- Browsers expect a stylesheet response to use `text/css`.
- When the stylesheet is rejected, the page falls back to unstyled HTML, which made the interface look broken.

## Fix

- Updated the stylesheet route in `app/api/main.py` to return `text/css; charset=utf-8`.
- Added `Cache-Control: no-store` to reduce stale local cache during MVP iteration.
- Added a regression test to verify stylesheet delivery and media type.

## Verification

- Local contract and integration suite passed after the fix.
- Current result: `47 passed, 0 failed`.

## Reuse Guidance

- If a frontend suddenly looks unstyled, inspect the stylesheet route before changing layout code.
- Verify both the HTML shell and the CSS response media type.
- During local iteration, prefer no-store or another cache-busting strategy for CSS.
