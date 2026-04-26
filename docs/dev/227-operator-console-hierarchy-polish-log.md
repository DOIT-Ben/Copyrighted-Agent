# 227 Operator Console Hierarchy Polish Log

Date: 2026-04-26

## Goal

- Reduce the operator console from a dense form stack into a shorter action path.
- Make the page easier to scan before a user starts editing materials.

## Changes

- Updated `app/web/page_submission.py`.
  - Tightened the operator summary copy.
  - Merged `材料纠偏` and `项目编排` into one group: `材料与项目整理`.
  - Reduced the operator flow from 5 groups to 4 groups.
  - Kept all existing actions and form endpoints unchanged.
- Updated `tests/integration/test_operator_console_and_exports.py` to assert the new grouped title.

## New Structure

1. `脱敏回传与继续审查`
2. `材料与项目整理`
3. `在线填报信息`
4. `审查配置与重跑`

## Regression

- `tests/integration/test_operator_console_and_exports.py`
- `tests/integration/test_web_mvp_contracts.py`

## Result

- Operator page is shorter and more sequential.
- Common manual tasks now read like one path instead of several disconnected blocks.
