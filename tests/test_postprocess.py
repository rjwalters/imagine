"""Postprocess (`fit`) tests. `magick` is faked everywhere; no ImageMagick needed."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from imagine import postprocess


def _patch_which(monkeypatch, value):
    monkeypatch.setattr(postprocess.shutil, "which", lambda name: value)


def _fake_magick(monkeypatch, dest: Path, initial_size: int, colors_size: int):
    """Fake `subprocess.run`: the resize pass writes `dest` at `initial_size`;
    every `-colors` pass shrinks it to `colors_size`. Returns commands seen."""
    calls: list[list[str]] = []

    def fake_run(cmd, capture_output=True, text=True):
        calls.append(cmd)
        if str(cmd[-1]).startswith("png8:"):
            Path(str(cmd[-1])[len("png8:"):]).write_bytes(b"x" * colors_size)
        else:
            dest.write_bytes(b"x" * initial_size)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(postprocess.subprocess, "run", fake_run)
    return calls


def _color_steps(calls):
    return [c[c.index("-colors") + 1] for c in calls if "-colors" in c]


def test_contain_png_args(tmp_path, monkeypatch):
    src = tmp_path / "src.png"
    dest = tmp_path / "out.png"
    _patch_which(monkeypatch, "/usr/bin/magick")
    calls = _fake_magick(monkeypatch, dest, 100, 100)
    postprocess.fit(src, dest, size="320x132")
    assert calls == [[
        "magick", str(src), "-background", "none", "-resize", "320x132",
        "-gravity", "center", "-extent", "320x132", str(dest),
    ]]


def test_cover_args_have_no_background(tmp_path, monkeypatch):
    src = tmp_path / "src.png"
    dest = tmp_path / "out.png"
    _patch_which(monkeypatch, "/usr/bin/magick")
    calls = _fake_magick(monkeypatch, dest, 100, 100)
    postprocess.fit(src, dest, size="320x132", mode="cover")
    assert calls == [[
        "magick", str(src), "-resize", "320x132^",
        "-gravity", "center", "-extent", "320x132", str(dest),
    ]]


def test_contain_background_by_dest_suffix(tmp_path, monkeypatch):
    src = tmp_path / "src.png"
    _patch_which(monkeypatch, "/usr/bin/magick")
    for suffix, expected in ((".jpg", "white"), (".png", "none"), (".webp", "none")):
        dest = tmp_path / f"out{suffix}"
        calls = _fake_magick(monkeypatch, dest, 100, 100)
        postprocess.fit(src, dest, size="320x132")
        bg = calls[0][calls[0].index("-background") + 1]
        assert bg == expected, f"{suffix}: got {bg!r}, want {expected!r}"


def test_plain_passthrough_without_size_or_budget(tmp_path, monkeypatch):
    src = tmp_path / "src.png"
    dest = tmp_path / "out.jpg"
    _patch_which(monkeypatch, "/usr/bin/magick")
    calls = _fake_magick(monkeypatch, dest, 100, 100)
    postprocess.fit(src, dest)
    assert calls == [["magick", str(src), str(dest)]]


def test_under_budget_needs_no_extra_magick(tmp_path, monkeypatch):
    src = tmp_path / "src.png"
    dest = tmp_path / "out.png"
    _patch_which(monkeypatch, "/usr/bin/magick")
    calls = _fake_magick(monkeypatch, dest, 100, 100)
    postprocess.fit(src, dest, size="320x132", max_kb=1)
    assert len(calls) == 1
    assert _color_steps(calls) == []


def test_budget_walk_stops_at_first_success(tmp_path, monkeypatch):
    src = tmp_path / "src.png"
    dest = tmp_path / "out.png"
    _patch_which(monkeypatch, "/usr/bin/magick")
    calls = _fake_magick(monkeypatch, dest, initial_size=10_000, colors_size=100)
    postprocess.fit(src, dest, size="320x132", max_kb=2)
    assert _color_steps(calls) == ["255"]


def test_unmeetable_budget_tries_all_steps_and_reports(tmp_path, monkeypatch):
    src = tmp_path / "src.png"
    dest = tmp_path / "out.png"
    _patch_which(monkeypatch, "/usr/bin/magick")
    calls = _fake_magick(monkeypatch, dest, initial_size=10_000, colors_size=9_000)
    with pytest.raises(SystemExit) as exc:
        postprocess.fit(src, dest, size="320x132", max_kb=2)
    assert _color_steps(calls) == ["255", "128", "64", "32"]
    msg = str(exc.value)
    assert "could not get" in msg
    assert f"currently {9_000 // 1024} KB" in msg
    assert "--size" in msg


def test_missing_magick_message(tmp_path, monkeypatch):
    _patch_which(monkeypatch, None)
    with pytest.raises(SystemExit) as exc:
        postprocess.fit(tmp_path / "src.png", tmp_path / "out.png")
    assert "brew install imagemagick" in str(exc.value)


def test_non_png_dest_with_budget_refused_before_any_magick(tmp_path, monkeypatch):
    src = tmp_path / "src.png"
    dest = tmp_path / "out.jpg"
    _patch_which(monkeypatch, "/usr/bin/magick")
    calls = _fake_magick(monkeypatch, dest, 100, 100)
    with pytest.raises(SystemExit) as exc:
        postprocess.fit(src, dest, max_kb=30)
    assert ".jpg" in str(exc.value)
    assert calls == []
    assert not dest.exists()


def test_non_png_dest_without_extension_names_it(tmp_path, monkeypatch):
    _patch_which(monkeypatch, "/usr/bin/magick")
    dest = tmp_path / "out"
    with pytest.raises(SystemExit) as exc:
        postprocess.fit(tmp_path / "src.png", dest, max_kb=30)
    assert "no extension" in str(exc.value)
