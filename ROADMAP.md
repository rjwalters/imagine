# Roadmap

Imagine is a renderer-tier CLI (`gen`, `edit`, `fit`, `models`, `doctor`) plus
Claude Code skills that turn image models into a dependable command an agent
workflow can shell out to.

Status as of 2026-11-13, `main` @ `b8f2deb`.

`WORK_PLAN.md` is a generated view of tracker label state and `WORK_LOG.md` a
generated log of merges; this file is the hand-maintained plan they do not
carry: what is evidenced, what comes next, and why.

## Where it stands

Released: **0.1.0** (2026-07-28, `CHANGELOG.md`). `VERSION`, `pyproject.toml`
and `imagine/__init__.py` all say `0.1.0`.

Merged since the release and still under `## Unreleased` in `CHANGELOG.md`:

| Area | Evidence |
|---|---|
| FLUX.2 Cloudflare models get a multipart body | PR #9, `tests/test_cloudflare.py`, fixture `cloudflare_flux2_400_multipart.json` |
| Output extension follows the returned bytes; sidecar gains `format` / `mime` | PR #10, `tests/test_cli_output.py` |
| `doctor` reports `NEEDS ACCOUNT` when a token file exists but no account is selected | PR #11, `tests/test_cli.py` |
| Install metadata and gitignored sidecar from `install.sh` | PR #12, `tests/test_install.py` |
| Bounded retry of transient provider errors, `--no-retry` | PR #13, `tests/test_retry.py` |
| Opaque-output warning and the full-bleed-then-mask recipe | PR #14, `skills/imagine/SKILL.md` |

Test state: `uv run pytest -q` gives 51 passed at this sha, all on recorded or
mocked provider responses (the rule in `CLAUDE.md`). The runtime has no
dependencies (`pyproject.toml`); `magick` is needed only by `fit`.

Not evidenced:

- `imagine/postprocess.py` (`fit`) has no test at all.
- There is no CI workflow in the repo; the suite runs only where someone
  invokes it (`package.json` `check:ci`).
- The multipart reference-image field name `input_image_<n>` is marked
  "unverified against the live schema" in `imagine/providers/cloudflare.py`.

Tracker: issues #1 to #6 are closed as completed. The only open issue, #16, is
an automated digest and not a work item. One open pull request, #7.

## Now

Each of these can start today and is one pull request. None has an issue yet.

1. **Options that do not apply to the selected provider are dropped silently.**
   `--param` is read but never passed to Gemini models; `--size WxH` is ignored
   by Gemini and `--size 1K/2K/4K` by Cloudflare (`imagine/cli.py`
   `_generate`). `--ar` on a Cloudflare model already prints a note.
   Done when each of those three cases prints one `imagine: note:` line on
   stderr naming the ignored option, with a test per case.
2. **The sidecar does not record `--param` values.** Two runs that differ only
   in `--param steps=N` or a seed write identical provenance.
   Done when the sidecar and the `--json` record carry a `params` object (empty
   when none were given) and a test asserts it.
3. **`fit` can write PNG bytes under a non-PNG name, and is untested.** The
   byte-budget pass writes `png8:<dest>` whatever the destination extension, and
   the default destination reuses the source suffix, so fitting a `.jpg` (which
   `gen` now produces) yields a mislabelled file; the `--out` help text says
   the default is `<name>-fit.png`, which the code does not do.
   Done when the default destination is `<stem>-fit.png`, a non-PNG `--out`
   with `--max-kb` is either honoured in that format or refused with a clear
   message, and `tests/test_postprocess.py` covers the command built for
   `contain`, `cover`, and the byte-budget walk without needing `magick`.
4. **`fit` output has no sidecar.** The README calls the image plus sidecar
   "the artifact", but a fitted file carries no provenance.
   Done when `fit` writes `<dest>.json` with tool version, operation
   parameters, source path, source sha256 and output sha256, links the source
   sidecar's prompt and model when one exists, and a test asserts the fields.

## Next

- **Cut 0.2.0.** The unreleased set includes a behaviour change (output
  extension follows bytes). Done when `CHANGELOG.md` has a `0.2.0` heading,
  the three version strings agree, and a tag exists. Follows Now 1 to 4 so the
  release carries a consistent sidecar and `fit` contract; cutting the tag is
  a maintainer step.
- **Version-consistency test.** Done when a test fails if `VERSION`,
  `pyproject.toml` and `imagine.__version__` differ. Small enough to ride with
  the release pull request.
- **Sidecar schema reference.** After Now 2 and 4 settle the fields: done when
  the README's "Output contract" section (or a linked doc) lists every sidecar
  field for `gen`, `edit` and `fit`, and a test checks the documented field
  list against a generated record.

## Later

- **Pass `--param` through to Gemini.** Question first: which level of the
  request a key maps to (`generationConfig`, `imageConfig`, or top level), and
  whether that can be stated without a live call.
- **A CI workflow running `uv run pytest -q`.** Question first: whether the
  maintainer wants a hosted workflow on this repo, since nothing here requires
  it today and the tests need no credential.
- **Real alpha output.** Issue #1 was closed by documenting the mask recipe.
  Question first: whether a `fit` or new subcommand should apply the documented
  ImageMagick mask, or whether the recipe in the skill is the intended end
  state.
- **Default backend after the Gemini exception.** `CLAUDE.md` describes Gemini
  here as a time-bounded exception. Question first: which alias becomes the
  default, and which Cloudflare model covers reference-image edits, when that
  ends.

## Blocked and waiting

- **Live check of FLUX.2 reference images.** The multipart `input_image_<n>`
  field name is unverified in code. Provider credentials stay attended
  (`CLAUDE.md`), so this waits for an attended run of
  `imagine edit <image> "<instruction>" -m flux-2-klein`; if the field name is
  wrong, the fix ships with a recorded fixture.
- **PR #7, Renovate configuration.** Open since 2026-09-21 with no review
  label; its own description says it is inert until the Renovate app is
  installed. Waits on a maintainer decision to adopt or close. The runtime has
  no dependencies and the only development dependency is `pytest`.

Nothing in the tracker is labelled ready for work today; the four Now items
become dispatchable once filed.

## Not planned

- Transcoding generated images. `-o` is a stem hint and the file keeps the
  provider's bytes (`skills/imagine/SKILL.md`).
- Runtime dependencies. The CLI stays stdlib-only; packaging work that needs
  more goes through `magick` in `fit`.
- Live provider calls in tests, or provider credentials on unattended workers
  (`CLAUDE.md`).
- Routing text or code generation through this tool (`CLAUDE.md`).
- Owning the generate, look, revise loop. The calling agent stays in charge of
  it; Imagine renders.
