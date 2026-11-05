# Imagine

**AI image generation as a renderer-tier CLI, plus Claude Code skills.**

Imagine turns state-of-the-art image models into a boring, dependable command-line renderer — the `marp` of AI images. Agent workflows shell out to it, get a PNG plus a JSON provenance sidecar back, and stay in charge of the loop (prompt, look, revise). Backends: **Gemini (Nano Banana family)** and **Cloudflare Workers AI** (FLUX, Leonardo, SDXL).

**Sibling projects:** [Anvil](https://github.com/rjwalters/anvil) orchestrates long-form artifact creation — its figurer roles can shell out to Imagine the way they shell out to `marp` or `mmdc`. [Loom](https://github.com/rjwalters/loom) orchestrates AI development workers. [Repo](https://github.com/rjwalters/repo) keeps any repository healthy. All install side by side.

## Quickstart

```bash
uv tool install git+https://github.com/rjwalters/imagine   # installs `imagine`
imagine doctor                                              # tells you exactly what's missing
imagine gen "a neon owl badge, glowing orange tube letters" -o owl.png
imagine edit owl.png "recolor the lettering to electric blue"
imagine fit owl.png --size 320x132 --max-kb 30              # platform-spec packaging
```

Generated images are opaque RGB: asking for a "transparent background" yields a drawn checkerboard or white fill, not an alpha channel. For real transparency, generate full-bleed and mask locally (see `skills/imagine/SKILL.md`).

## Models

| Alias | Provider | Best for |
|---|---|---|
| `nano-banana` (default) | Gemini | General work, in-image text, reference-image edits |
| `nano-banana-pro` | Gemini | Final brand assets, exact typography, layout control |
| `nano-banana-lite` | Gemini | High-volume drafts |
| `flux-2-dev` | Cloudflare | Photorealism, multi-reference |
| `flux-2-klein` / `flux-2-klein-4b` | Cloudflare | Fast unified gen + edit |
| `flux-schnell` | Cloudflare | Cheapest drafts |
| `lucid-origin`, `phoenix` | Cloudflare | Leonardo styles, text adherence |
| `sdxl` | Cloudflare | Open-weights baseline |

`imagine models` prints the live table. Raw ids (`@cf/vendor/model`, `gemini-*`) route by shape, so new provider models work without a release.

## Credentials

One key per provider, resolved from (in order) the process environment, `~/.config/imagine/env`, then provider stores:

- **Gemini** — `GEMINI_API_KEY` ([create](https://aistudio.google.com/apikey)).
- **Cloudflare** — `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID`, or `--cf-account <name>` / `IMAGINE_CF_ACCOUNT=<name>` reading `~/.cloudflare/<name>/workers-ai.env`. That follows the one-scoped-token-per-purpose convention: create a token scoped to **Account → Workers AI → Read+Edit**, nothing else.

## Output contract

Every generated `foo.png` is written next to a `foo.png.json` sidecar recording tool version, provider, model, prompt, references, sha256, and timestamp. The pair is the artifact; downstream workflows (Anvil threads, brand repos) should move them together.

## Claude Code skills

```bash
./install.sh /path/to/consumer-repo    # or `.`
```

Installs `/imagine:gen` and `/imagine:help` commands plus the `imagine` skill into the target's `.claude/`, and appends one marker-bounded block to its `CLAUDE.md` (replaced in place on re-install; `./uninstall.sh` removes exactly what was written). The skill teaches the agent the loop that makes generation actually work: route to the right model, pass brand art as `--ref`, **look at the output**, iterate, then `fit` to the platform spec.

## Development

```bash
uv sync
uv run pytest
uv run imagine models
```

Stdlib-only runtime (no dependencies); `magick` (ImageMagick) is required only by `imagine fit`.

## License

MIT
