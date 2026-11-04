# imagine — repo rules

The image-generation CLI that `2AMLogic/2am` `docs/image-generation.md` points
every repo at. Gemini is permitted here for image generation only, a
time-bounded exception in `2AMLogic/2am` `docs/llm-policy.md`; nothing here
may route text or code work to Gemini.

## Provider credentials stay attended (operator, 2026-11-04)

- **No provider credential on a fleet worker.** Never create, request, copy
  or look for `GEMINI_API_KEY`, a Cloudflare Workers AI token or
  `~/.config/imagine/env` on a worker or in a fleet session. If a fix seems to
  need one, it doesn't. Use the path below.
- **Tests use recorded or mocked provider responses.** A provider change ships
  with a test built on a recorded response (fixtures under `tests/`), never a
  live call.
- **Live provider checks are an attended step.** A PR that changes provider
  behaviour says in its body what to run live (the exact `imagine gen …`
  command and what to look for). Leave it to an attended session; don't park
  the PR waiting for it.

<!-- BEGIN LOOM ORCHESTRATION -->
This repository uses [Loom](https://github.com/rjwalters/loom) for AI-powered development orchestration — see the Loom repository for the full guide (roles, labels, worktrees, configuration). When installed, Loom also writes a locally-substituted copy of that guide to `.loom/CLAUDE.md`.

Work is coordinated through `loom:` labels on issues and pull requests, and the same roles run either under `loom-daemon` or by hand in an attended session — daemon mode is optional. Create the labels once with `.loom/scripts/sync-labels.sh` (an install ships `.github/labels.yml` but does not create the labels on the forge). A pull request ready for review carries `loom:review-requested`; Judge reviews it and applies `loom:pr` (approved) or `loom:changes-requested`; Doctor fixes a `loom:changes-requested` pull request and returns it to `loom:review-requested`. Only a `loom:pr` pull request gets merged, and always via this repo's merge script (`.loom/scripts/merge-pr.sh`) — never a raw forge merge command such as `gh pr merge`. Full state machine: `.loom/docs/label-state-machine.md`.
<!-- END LOOM ORCHESTRATION -->
