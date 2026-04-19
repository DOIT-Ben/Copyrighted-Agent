# P36-P40 Issues

## Issue 1

- Symptom: the page layer was stable but still concentrated too much responsibility in one file.
- Root cause: the previous round optimized for rapid recovery from source corruption.
- Fix: reorganized the page layer into shared helpers plus page-scoped renderer modules.

## Issue 2

- Symptom: some renderer class names did not naturally line up with the existing admin CSS structure.
- Root cause: the emergency rebuild had not yet normalized its layout vocabulary against the stylesheet.
- Fix: updated the modular renderers to use the established workspace / sidebar / panel structure so the CSS stays the source of truth.

## Issue 3

- Symptom: changing renderer structure could have forced route-level import churn.
- Root cause: `app.api.main` depended directly on symbols from `app.web.pages`.
- Fix: preserved `app.web.pages` as a stable export barrel and moved the real implementation behind it.
