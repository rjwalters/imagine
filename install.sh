#!/usr/bin/env bash
# Install imagine skills into a target repository's .claude/ directory.
#
#   ./install.sh /path/to/consumer-repo     # or `.`
#   ./install.sh --dry-run /path/to/repo
#
# Write footprint (nothing else is touched):
#   .claude/skills/imagine/       skill file
#   .claude/commands/imagine/     one file per /imagine:* command
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
