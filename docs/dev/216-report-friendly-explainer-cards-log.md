# 216 Report Friendly Explainer Cards Log

- Date: 2026-04-26
- Scope: make the review report easier to understand before users open the detailed trace tables

## Changes

- Added a new `重点问题说明` section to the case report page.
- Each card now explains one priority issue in plain language:
  - what is wrong
  - which rule/dimension triggered it
  - what evidence was observed
  - what the operator should do next
- Kept the existing detailed trace table and evidence board for deeper follow-up.

## Why

- The previous report page already had enough raw data, but users still had to scan tables first.
- The new explainer cards move the "哪里不对 / 为什么 / 先怎么改" answers above the dense detail layers.
- This is the final productization pass for friendlier report reading without weakening the structured export path.
