# Changelog

## Unreleased

- `gen` / `edit` retry transient provider errors (HTTP 429/500/502/503/504,
  connection errors) up to 3 attempts with 1s/2s backoff, honouring
  `Retry-After` up to 30s. Each retry logs one stderr line. `--no-retry` or
  `IMAGINE_NO_RETRY=1` restores single-attempt behaviour.

## 0.1.0 — 2026-07-28

Initial release.

- `imagine gen` / `edit` — Gemini (Nano Banana 2 / Pro / Lite) and Cloudflare
  Workers AI (FLUX.2 dev/klein, FLUX.1 schnell, Leonardo, SDXL) backends,
  reference images, aspect-ratio / size control, raw `--param` passthrough,
  JSON provenance sidecars.
- `imagine fit` — resize/compress to platform specs (contain or cover) via
  ImageMagick.
- `imagine models` / `imagine doctor` — routing table and credential /
  dependency diagnosis.
- Credential resolution: env → `~/.config/imagine/env` → `~/.cloudflare/
  <account>/workers-ai.env` (one-scoped-token-per-purpose convention).
- Claude Code skill pack: `/imagine:gen`, `/imagine:help`, `imagine` skill;
  marker-bounded installer/uninstaller in the Anvil/Repo style.
