# 118 Test Runtime Isolation Build Log

## Goal

- Remove the remaining regression instability caused by pytest inheriting the live `external_http` provider configuration from `config/local.json`.

## Changes

- Added a default pytest runtime override in [tests/conftest.py](D:/Code/软著智能体/tests/conftest.py):
  - `SOFT_REVIEW_AI_ENABLED=false`
  - `SOFT_REVIEW_AI_PROVIDER=mock`
  - clear endpoint, model, and API-key env bindings
- Added a new pytest marker in [pytest.ini](D:/Code/软著智能体/pytest.ini):
  - `live_ai_config`
- The default rule is now:
  - ordinary tests run against deterministic mock AI config
  - only explicitly marked tests may inherit local live AI config

## Why This Fix

- The previous failure was not a frontend bug.
- It was a test-environment leak where browser workflows could hit the real provider bridge during upload and rerun actions.
- Fixing the test harness gives us stable regression gates without changing the real runtime behavior.

## Scope Control

- No production application logic changed in this round.
- Real-provider validation still belongs to the dedicated acceptance and probe flows.
