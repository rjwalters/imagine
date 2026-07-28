---
name: gen
description: Generate an image from a description — pick the right model, run the imagine CLI, review the result visually, and iterate until it matches
domain: imagine
type: command
user-invocable: true
---

# /imagine:gen — generate an image

The user describes an image; you deliver a file that matches. Everything runs
through the `imagine` CLI (see the `imagine` skill for full routing and flags).

1. **Clarify only what blocks generation** (target use / dimensions if a
   platform spec is implied). Otherwise proceed.
2. **Route:** default `nano-banana`; `nano-banana-pro` for final brand assets
   or exact typography; `flux-schnell` for cheap exploration; `--ref` any
   existing art the user points at.
3. **Generate:** `imagine gen "..." [flags] -o <sensible-name>.png`. If the
   CLI fails, run `imagine doctor` and relay its guidance verbatim.
4. **Review the image yourself** (Read the file). Check: requested elements
   present, any text spelled exactly, style matches references. If not,
   iterate — revised prompt or `imagine edit` — up to ~3 rounds before
   showing intermediate results and asking for direction.
5. **Package if a platform spec applies:** `imagine fit out.png --size WxH
   --max-kb N`. Report the final path(s) and what you verified.
