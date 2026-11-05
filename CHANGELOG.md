# Changelog

## Unreleased

- `install.sh` now writes `.claude/skills/imagine/install-metadata.json`
  (version, commit, layout_version, commands) and a gitignored
  `.install-local.json` sidecar (source path, installed_at), adding the sidecar
  to the target's `.gitignore`; `uninstall.sh` removes that line. Lets
  `/repo:update-tools` discover `imagine` (installer contract C5/C6).

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
