---
name: imagine
description: Generate and edit AI images from the terminal via the imagine CLI — Gemini (Nano Banana) and Cloudflare Workers AI backends. Use for logos, brand assets, figures, deck art, concept renders, and fitting images to platform specs.
---

# imagine — AI image generation

`imagine` is a renderer-tier CLI, invoked like `marp` or `mmdc`: prompt in,
image file + JSON metadata sidecar out. Source: https://github.com/rjwalters/imagine

## Model routing

| Alias | When to use |
|---|---|
| `nano-banana` (default) | General work; strong in-image text; accepts reference images |
| `nano-banana-pro` | Final brand assets, layout precision, exact typography |
| `nano-banana-lite` | High-volume drafts |
| `flux-2-dev` | Photorealism, multi-reference composition |
| `flux-2-klein` / `-4b` | Fast unified generation + editing on Cloudflare |
| `flux-schnell` | Cheapest drafts |
| `lucid-origin` / `phoenix` | Leonardo styles, good text adherence |
| `sdxl` | Open-weights baseline |

Run `imagine models` for the live table. Raw ids (`@cf/...`, `gemini-*`) also work.

## Commands

```bash
imagine gen "PROMPT" [-m MODEL] [--ar 16:9] [--size 2K|WxH] [--ref img.png] [-o out.png] [--n 3]
imagine edit input.png "INSTRUCTION" [-m MODEL] [-o out.png]   # ref-capable models only
imagine fit img.png --size 320x132 --max-kb 30 [--mode contain|cover]
imagine doctor        # credential + dependency check; run this first on any failure
```

Every output `foo.png` gets a `foo.png.json` sidecar (prompt, model, sha256,
timestamp) — treat the pair as one artifact and keep them together.

## Workflow guidance for agents

- **Look at what you generated.** Read the output image and judge it against
  the request before declaring success; iterate with `imagine edit` or a
  revised prompt.
- **Style matching:** pass existing brand art via `--ref` and describe the
  delta, rather than describing the style from scratch.
- **Exact text in images:** put the literal words in quotes in the prompt and
  say "spelled exactly"; prefer `nano-banana-pro` when typography must be right.
- **Platform specs** (favicon, Google Workspace logo 320x132 <30KB, OG image
  1200x630, ...): generate large, then `imagine fit` — never ask the model for
  tiny pixel dimensions directly.
- **Anvil integration:** figurer/critic roles shell out to `imagine` exactly
  like other renderers; write outputs into the version directory under the
  thread's assets, sidecars included.

## Credentials

- Gemini: `GEMINI_API_KEY` in the environment or `~/.config/imagine/env`.
- Cloudflare: `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID`, or
  `--cf-account <name>` reading `~/.cloudflare/<name>/workers-ai.env`
  (a Workers AI-scoped token file, per the one-token-per-purpose convention).

`imagine doctor` reports exactly what is missing and where to get it.
