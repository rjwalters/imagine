import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SIDECAR = ".claude/skills/imagine/.install-local.json"
META = ".claude/skills/imagine/install-metadata.json"


def sh(script, *args):
    return subprocess.run(["bash", str(script), *map(str, args)],
                          capture_output=True, text=True, check=True)


def fingerprint(root):
    return {str(p.relative_to(root)): (p.read_bytes() if p.is_file() else None)
            for p in sorted(root.rglob("*"))}


def make_target(tmp_path):
    t = tmp_path / "consumer"
    t.mkdir()
    subprocess.run(["git", "init", "-q", str(t)], check=True)
    return t


def test_metadata_and_sidecar(tmp_path):
    t = make_target(tmp_path)
    sh(ROOT / "install.sh", t)
    meta = json.loads((t / META).read_text())
    assert set(meta) == {"version", "commit", "layout_version", "commands"}
    assert meta["version"] == (ROOT / "VERSION").read_text().strip()
    assert meta["layout_version"] == 1
    assert meta["commands"] == sorted(meta["commands"]) and "gen" in meta["commands"]
    raw = (t / META).read_text()
    assert str(ROOT) not in raw and str(tmp_path) not in raw
    side = json.loads((t / SIDECAR).read_text())
    assert side["source"] == str(ROOT)
    assert side["installed_at"].endswith("Z")
    assert subprocess.run(["git", "-C", str(t), "check-ignore", SIDECAR]).returncode == 0


def test_reinstall_idempotent(tmp_path):
    t = make_target(tmp_path)
    sh(ROOT / "install.sh", t)
    first = (t / META).read_bytes()
    sh(ROOT / "install.sh", t)
    assert (t / META).read_bytes() == first
    assert (t / ".gitignore").read_text().splitlines().count(SIDECAR) == 1


def test_gitignore_without_trailing_newline(tmp_path):
    t = make_target(tmp_path)
    (t / ".gitignore").write_text("node_modules")
    sh(ROOT / "install.sh", t)
    assert (t / ".gitignore").read_text() == f"node_modules\n{SIDECAR}\n"


def test_dry_run_changes_nothing(tmp_path):
    t = make_target(tmp_path)
    (t / ".gitignore").write_text("x\n")
    before = fingerprint(t)
    out = sh(ROOT / "install.sh", "--dry-run", t).stdout
    assert fingerprint(t) == before
    assert "install-metadata.json" in out and ".install-local.json" in out and ".gitignore" in out


def test_uninstall_restores_gitignore(tmp_path):
    t = make_target(tmp_path)
    (t / ".gitignore").write_text("keep\n")
    sh(ROOT / "install.sh", t)
    sh(ROOT / "uninstall.sh", t)
    assert (t / ".gitignore").read_text() == "keep\n"
    assert not (t / ".claude").exists()


def test_uninstall_removes_gitignore_it_created(tmp_path):
    t = make_target(tmp_path)
    sh(ROOT / "install.sh", t)
    sh(ROOT / "uninstall.sh", t)
    assert not (t / ".gitignore").exists()


def test_source_not_git_checkout(tmp_path):
    src = tmp_path / "src"
    shutil.copytree(ROOT, src, ignore=shutil.ignore_patterns(".git", ".loom", ".venv", "node_modules"))
    t = make_target(tmp_path)
    sh(src / "install.sh", t)
    assert json.loads((t / META).read_text())["commit"] == "unknown"
