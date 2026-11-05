# Changelog

## Unreleased

- **Behaviour change:** `gen` / `edit` now sniff the returned image bytes
  (PNG / JPEG / WebP) and write the file under the real extension, so
  `-o out.png` becomes `out.jpg` when the provider returns JPEG. The actual
  path is printed on stdout and in `--json`, the sidecar is `<actual path>.json`,
  and a one-line stderr note is emitted. Sidecars gain `format` and `mime`.
  Unknown bytes keep the requested extension with `format: "unknown"`.
- Documented that `-o` is a stem hint and that step counts use `--param steps=N`
  (there is no `--steps` flag).

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
