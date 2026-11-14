"""Post-processing: fit an image to a platform spec (exact size, byte budget).

Shells out to ImageMagick (`magick`). Kept out of the providers on purpose —
generation and packaging are separate concerns, and specs like "Google
Workspace logo: 320x132, under 30 KB" are pure packaging.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

_ALPHA_OK = {".png", ".webp"}


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"imagine: {' '.join(cmd[:2])} failed: {proc.stderr.strip()[:500]}")


def fit(
    src: Path,
    dest: Path,
    size: str | None = None,
    max_kb: int | None = None,
    mode: str = "contain",
) -> Path:
    """Resize `src` to `size` (WxH) and/or compress under `max_kb`, into `dest`.

    mode "contain" letterboxes (onto transparency for .png/.webp, white for
    alpha-less formats); "cover" center-crops.
    """
    if not shutil.which("magick"):
        raise SystemExit("imagine: `magick` (ImageMagick) is required for fit — brew install imagemagick")

    if max_kb and dest.suffix.lower() != ".png":
        raise SystemExit(
            f"imagine: --max-kb needs a PNG destination (got "
            f"{dest.suffix or 'no extension'}) — the byte-budget pass re-encodes "
            f"as PNG8; drop --max-kb or pass a .png --out"
        )

    cmd = ["magick", str(src)]
    if size:
        if mode == "cover":
            cmd += ["-resize", f"{size}^", "-gravity", "center", "-extent", size]
        else:
            bg = "none" if dest.suffix.lower() in _ALPHA_OK else "white"
            cmd += ["-background", bg, "-resize", size,
                    "-gravity", "center", "-extent", size]
    cmd.append(str(dest))
    _run(cmd)

    if max_kb:
        # Walk color depth down until the byte budget is met.
        for colors in (0, 255, 128, 64, 32):
            if dest.stat().st_size <= max_kb * 1024:
                return dest
            if colors:
                _run(["magick", str(dest), "-dither", "FloydSteinberg",
                      "-colors", str(colors), f"png8:{dest}"])
        if dest.stat().st_size > max_kb * 1024:
            raise SystemExit(
                f"imagine: could not get {dest.name} under {max_kb} KB "
                f"(currently {dest.stat().st_size // 1024} KB) — try a smaller --size"
            )
    return dest
