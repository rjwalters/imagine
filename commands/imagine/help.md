---
name: help
description: Explain the installed /imagine commands, model routing, and credential setup
domain: imagine
type: command
user-invocable: true
---

# /imagine:help

Orient the user:

1. Run `imagine models` and `imagine doctor`; show both outputs.
2. Summarize the commands: `/imagine:gen` (describe → image), plus the raw
   CLI surface (`gen`, `edit`, `fit`, `models`, `doctor`).
3. If doctor reports missing credentials, walk through fixing exactly the
   missing ones (Gemini key → https://aistudio.google.com/apikey into
   `~/.config/imagine/env`; Cloudflare → Workers AI-scoped token in
   `~/.cloudflare/<account>/workers-ai.env`).
4. Point to the `imagine` skill and https://github.com/rjwalters/imagine for
   details.
