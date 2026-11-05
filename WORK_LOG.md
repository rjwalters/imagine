# Work Log

Chronological record of merged PRs and closed issues, maintained by the Guide role.

### 2026-11-05

- **PR #14**: docs: document opaque output and add full-bleed-then-mask transparency recipe
- **PR #13**: feat: retry transient provider errors with bounded backoff
- **PR #12**: feat: write install metadata and gitignored sidecar from install.sh
- **PR #11**: fix: doctor reports NEEDS ACCOUNT when workers-ai.env exists but no account selected
- **PR #10**: fix: write generated images under the extension their bytes require
- **PR #9**: fix: send multipart/form-data for FLUX.2 Cloudflare models
- **Issue #6** (closed): install.sh: ship install-metadata.json + local-source sidecar so imagine participates in tool discovery/update
- **Issue #5** (closed): gen: -o out.png writes provider bytes verbatim, so a .png file can contain JPEG (and the sidecar does not record the real format)
- **Issue #4** (closed): doctor: reports cloudflare MISSING when a valid workers-ai.env exists but no account is selected
- **Issue #3** (closed): gen: flux-2-dev fails with Cloudflare 400 — model requires a multipart body the CLI never sends
- **Issue #2** (closed): gen: retry transient provider errors (Gemini 503 UNAVAILABLE) instead of failing with exit 1
- **Issue #1** (closed): gen: "transparent background" prompts return baked-in checkerboard, not real alpha

### 2026-11-04

- **PR #8**: Install Loom ahead of fleet admission, with a provider-credential rule
