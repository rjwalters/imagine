#!/usr/bin/env bash
# Remove imagine skills from a target repository. Removes only what
# install.sh wrote: the two .claude/ directories, the sidecar's .gitignore line and the
# CLAUDE.md block.
set -euo pipefail

TARGET="${1:?usage: ./uninstall.sh /path/to/target-repo}"
TARGET="$(cd "$TARGET" && pwd)"

# Drop the .gitignore line install.sh added (other lines untouched).
gitignore="$TARGET/.gitignore"
if [[ -f "$gitignore" ]]; then
  python3 - "$gitignore" <<'PY'
import sys, pathlib
path = pathlib.Path(sys.argv[1])
line = ".claude/skills/imagine/.install-local.json"
lines = path.read_text().splitlines(keepends=True)
kept = [l for l in lines if l.rstrip("\n") != line]
if kept != lines:
    if kept:
        path.write_text("".join(kept))
    else:
        path.unlink()
PY
fi

rm -rf "$TARGET/.claude/skills/imagine" "$TARGET/.claude/commands/imagine"
rmdir "$TARGET/.claude/skills" "$TARGET/.claude/commands" "$TARGET/.claude" 2>/dev/null || true

claude_md="$TARGET/CLAUDE.md"
if [[ -f "$claude_md" ]]; then
  python3 - "$claude_md" <<'PY'
import sys, pathlib, re
path = pathlib.Path(sys.argv[1])
text = path.read_text()
cleaned = re.sub(r"\n?\n?<!-- BEGIN IMAGINE -->.*?<!-- END IMAGINE -->\n?", "\n", text, flags=re.S)
if cleaned.strip():
    path.write_text(cleaned)
else:
    path.unlink()
PY
fi

echo "imagine skills removed from $TARGET"
