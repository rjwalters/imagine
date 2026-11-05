#!/usr/bin/env bash
# Install imagine skills into a target repository's .claude/ directory.
#
#   ./install.sh /path/to/consumer-repo     # or `.`
#   ./install.sh --dry-run /path/to/repo
#
# Write footprint (nothing else is touched):
#   .claude/skills/imagine/       skill file
#   .claude/commands/imagine/     one file per /imagine:* command
#   .claude/skills/imagine/install-metadata.json   tracked: version, commit, layout_version, commands
#   .claude/skills/imagine/.install-local.json     gitignored sidecar: source clone path, installed_at
#   .gitignore                    one line ignoring the sidecar (idempotent)
#   CLAUDE.md                     one marker-bounded block, replaced in place
set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    -*) echo "install.sh: unknown option $1" >&2; exit 2 ;;
    *) TARGET="$1"; shift ;;
  esac
done

[[ -n "${TARGET:-}" ]] || { echo "usage: ./install.sh [--dry-run] /path/to/target-repo" >&2; exit 2; }
TARGET="$(cd "$TARGET" && pwd)"

BEGIN_MARK="<!-- BEGIN IMAGINE -->"
END_MARK="<!-- END IMAGINE -->"
BLOCK="$BEGIN_MARK
## imagine — AI image generation

This repo has the [imagine](https://github.com/rjwalters/imagine) skills
installed. Use \`/imagine:gen\` to create images, or the \`imagine\` CLI
directly. Start with \`/imagine:help\`; details in
\`.claude/skills/imagine/SKILL.md\`.
$END_MARK"

run() { if [[ $DRY_RUN -eq 1 ]]; then echo "would: $*"; else "$@"; fi; }

run mkdir -p "$TARGET/.claude/skills/imagine" "$TARGET/.claude/commands/imagine"
run cp "$SOURCE_DIR/skills/imagine/SKILL.md" "$TARGET/.claude/skills/imagine/SKILL.md"
for cmd in "$SOURCE_DIR"/commands/imagine/*.md; do
  run cp "$cmd" "$TARGET/.claude/commands/imagine/$(basename "$cmd")"
done

# Installer contract (rjwalters/repo INSTALLER-CONTRACT.md C5/C6): tracked
# metadata is byte-identical across machines (no path/host/user/timestamp);
# machine-local facts go in a gitignored sidecar.
META_REL=".claude/skills/imagine/install-metadata.json"
SIDECAR_REL=".claude/skills/imagine/.install-local.json"
if [[ $DRY_RUN -eq 1 ]]; then
  echo "would: write $TARGET/$META_REL"
  echo "would: write $TARGET/$SIDECAR_REL"
  echo "would: add $SIDECAR_REL to $TARGET/.gitignore"
else
  python3 - "$SOURCE_DIR" "$TARGET" "$META_REL" "$SIDECAR_REL" <<'PY'
import datetime, json, pathlib, subprocess, sys
source, target = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
meta_rel, sidecar_rel = sys.argv[3], sys.argv[4]
try:
    commit = subprocess.run(["git", "-C", str(source), "rev-parse", "HEAD"],
                            capture_output=True, text=True, check=True).stdout.strip() or "unknown"
except (subprocess.CalledProcessError, OSError):
    commit = "unknown"
meta = {
    "version": (source / "VERSION").read_text().strip(),
    "commit": commit,
    "layout_version": 1,
    "commands": sorted(p.stem for p in (source / "commands" / "imagine").glob("*.md")),
}
(target / meta_rel).write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n")
sidecar = {
    "source": str(source),
    "installed_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
}
(target / sidecar_rel).write_text(json.dumps(sidecar, indent=2, sort_keys=True) + "\n")
gi = target / ".gitignore"
text = gi.read_text() if gi.exists() else ""
if sidecar_rel not in text.splitlines():
    if text and not text.endswith("\n"):
        text += "\n"
    gi.write_text(text + sidecar_rel + "\n")
PY
fi

claude_md="$TARGET/CLAUDE.md"
if [[ $DRY_RUN -eq 1 ]]; then
  echo "would: update marker block in $claude_md"
else
  touch "$claude_md"
  python3 - "$claude_md" <<PY
import sys, pathlib
path = pathlib.Path(sys.argv[1])
begin, end = "$BEGIN_MARK", "$END_MARK"
block = """$BLOCK"""
text = path.read_text() if path.exists() else ""
if begin in text and end in text:
    head, _, rest = text.partition(begin)
    _, _, tail = rest.partition(end)
    text = head + block + tail
else:
    text = text.rstrip("\n") + ("\n\n" if text.strip() else "") + block + "\n"
path.write_text(text)
PY
fi

echo "imagine skills installed into $TARGET"
echo "next: \`imagine doctor\` (install CLI with: uv tool install git+https://github.com/rjwalters/imagine)"
