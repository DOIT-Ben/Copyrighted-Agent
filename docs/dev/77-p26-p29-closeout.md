# P26-P29 Closeout

## Status

- Complete for the current provider-readiness and probe-observability slice

## What Is Now Ready

- phase-based provider readiness with explicit operator remediation
- persisted latest probe artifact at `data/runtime/ops/provider_probe_latest.json`
- sandbox-first `external_http` smoke flow using synthetic `llm_safe` payload only
- `/ops` visibility for `Provider Readiness`, `Latest Probe`, and `Probe Observatory`
- startup self-check output that includes local-config and provider-probe status
- final full regression at `115 passed, 0 failed`

## Remaining Non-Blocking Follow-Ups

- create local `config/local.json`
- configure a real endpoint / model / API-key environment mapping
- run a real non-sandbox provider smoke
- decide whether to persist probe history in addition to the latest-result artifact
- safely remove the legacy ops renderer backup after a dedicated cleanup pass

## Recommended Next Slice

- real-provider smoke once local credentials exist
- probe-history retention and optional `/ops` downloads
- startup or release-gated probe policy definition
- cleanup / consolidation pass for the preserved legacy ops renderer
