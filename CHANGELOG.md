# Changelog

## Unreleased

- `gen` / `edit` now print a one-line `imagine: note:` on stderr when an option
  does not apply to the selected provider: `--param` or `--size WxH` on a Gemini
  model, and `--size 1K/2K/4K` on a Cloudflare model. Generation still proceeds
  and exits 0. All applicability notes — including the pre-existing `--ar is a
  Gemini option` and undocumented-aspect-ratio notes, whose wording is unchanged
  — are now emitted once per invocation rather than once per image under `--n`.
- `gen` / `edit` sidecars and `--json` records gain a `params` object holding the
  parsed `--param` values (`{}` when none were given), so two runs differing only
  in `--param` no longer write identical provenance. Recorded as requested, even
  on a provider that ignores `--param`.
- `install.sh` now writes `.claude/skills/imagine/install-metadata.json`
  (version, commit, layout_version, commands) and a gitignored
  `.install-local.json` sidecar (source path, installed_at), adding the sidecar
  to the target's `.gitignore`; `uninstall.sh` removes that line. Lets
  `/repo:update-tools` discover `imagine` (installer contract C5/C6).
- **Behaviour change:** `gen` / `edit` now sniff the returned image bytes
  (PNG / JPEG / WebP) and write the file under the real extension, so
  `-o out.png` becomes `out.jpg` when the provider returns JPEG. The actual
  path is printed on stdout and in `--json`, the sidecar is `<actual path>.json`,
  and a one-line stderr note is emitted. Sidecars gain `format` and `mime`.
  Unknown bytes keep the requested extension with `format: "unknown"`.
- Documented that `-o` is a stem hint and that step counts use `--param steps=N`
  (there is no `--steps` flag).
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
