"""imagine CLI: gen, edit, models, doctor, fit."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

from . import __version__, config
from .providers import DEFAULT_ALIAS, MODELS, resolve
from .providers import cloudflare as cf
from .providers import gemini
from .postprocess import fit as fit_image


def _slug(text: str, limit: int = 40) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:limit].rstrip("-") or "image"


def _parse_params(pairs: list[str]) -> dict:
    params: dict = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep:
            raise SystemExit(f"imagine: --param expects key=value, got '{pair}'")
        try:
            params[key] = json.loads(value)
        except json.JSONDecodeError:
            params[key] = value
    return params


def _out_paths(out: str | None, prompt: str, count: int) -> list[Path]:
    if out:
        base = Path(out)
        if count == 1:
            return [base]
        return [base.with_name(f"{base.stem}-{i + 1}{base.suffix or '.png'}") for i in range(count)]
    stem = _slug(prompt)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    if count == 1:
        return [Path(f"{stem}-{stamp}.png")]
    return [Path(f"{stem}-{stamp}-{i + 1}.png") for i in range(count)]


# format -> (canonical extension, mime, extensions accepted as already correct)
_FORMATS = {
    "png": (".png", "image/png", {".png"}),
    "jpeg": (".jpg", "image/jpeg", {".jpg", ".jpeg"}),
    "webp": (".webp", "image/webp", {".webp"}),
}


def _sniff_format(data: bytes) -> str:
    """Identify image bytes by magic number: png | jpeg | webp | unknown."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return "unknown"


def _actual_path(path: Path, fmt: str) -> Path:
    """Return path with the extension the bytes really need (unknown: unchanged)."""
    if fmt == "unknown":
        return path
    ext, _mime, accepted = _FORMATS[fmt]
    if path.suffix.lower() in accepted:
        return path
    return path.with_suffix(ext) if path.suffix else path.with_name(path.name + ext)


def _size_args(size: str | None) -> tuple[str | None, int | None, int | None]:
    """Split --size into (gemini imageSize, cloudflare width, height)."""
    if not size:
        return None, None, None
    if size.upper() in gemini.KNOWN_IMAGE_SIZES:
        return size.upper(), None, None
    match = re.fullmatch(r"(\d+)x(\d+)", size.lower())
    if match:
        return None, int(match.group(1)), int(match.group(2))
    raise SystemExit(f"imagine: --size must be 1K/2K/4K or WxH, got '{size}'")


def _cloudflare_missing(accounts: list[str]) -> tuple[str, str]:
    """Status label + guidance when Cloudflare credentials do not resolve.

    One source of truth for both surfaces that report it (`doctor` and the
    `gen` / `edit` path), so the selection guidance added for issue #4 cannot
    drift between them again.
    """
    if accounts:
        return "NEEDS ACCOUNT", (
            f"found workers-ai.env for: {', '.join(accounts)}; select one with "
            "--cf-account <name> or IMAGINE_CF_ACCOUNT=<name> "
            "(selection is required even with a single account)"
        )
    return "MISSING", (
        "add a Workers AI-scoped token file: ~/.cloudflare/<account>/workers-ai.env "
        "(CLOUDFLARE_API_TOKEN + CLOUDFLARE_ACCOUNT_ID)"
    )


def _generate(args: argparse.Namespace, prompt: str, refs: list[Path]) -> int:
    model = resolve(args.model)
    for ref in refs:
        if not ref.is_file():
            raise SystemExit(f"imagine: reference image not found: {ref}")
    if refs and not model.supports_ref:
        raise SystemExit(
            f"imagine: {model.alias} does not take reference images — "
            f"use nano-banana / nano-banana-pro / flux-2-*"
        )

    image_size, width, height = _size_args(args.size)
    params = _parse_params(args.param or [])

    batches: list[bytes] = []
    for _ in range(args.n):
        if model.provider == "gemini":
            key = config.gemini_key()
            if not key:
                raise SystemExit(
                    "imagine: GEMINI_API_KEY not found (env or ~/.config/imagine/env) — "
                    "create one at https://aistudio.google.com/apikey"
                )
            if args.ar and args.ar not in gemini.KNOWN_ASPECT_RATIOS:
                print(f"imagine: note: '{args.ar}' is not a documented aspect ratio; "
                      f"passing through", file=sys.stderr)
            batches.extend(gemini.generate(
                model.model_id, prompt, key, refs=refs,
                aspect_ratio=args.ar, image_size=image_size, retry=not args.no_retry,
            ))
        else:
            token, account_id = config.cloudflare_credentials(args.cf_account)
            if not token or not account_id:
                _, hint = _cloudflare_missing(config.cloudflare_accounts())
                raise SystemExit(f"imagine: Cloudflare credentials not found; {hint}")
            if args.ar:
                print("imagine: note: --ar is a Gemini option; use --size WxH for "
                      "Cloudflare models", file=sys.stderr)
            batches.extend(cf.generate(
                model.model_id, prompt, token, account_id, refs=refs,
                width=width, height=height, params=params,
                body_format=model.body_format, retry=not args.no_retry,
            ))

    outputs = _out_paths(args.out, prompt, len(batches))
    records = []
    for requested, data in zip(outputs, batches):
        fmt = _sniff_format(data)
        path = _actual_path(requested, fmt)
        if path != requested:
            print(f"imagine: provider returned {fmt.upper()}; wrote {path}", file=sys.stderr)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        record = {
            "tool": f"imagine {__version__}",
            "provider": model.provider,
            "model": model.model_id,
            "alias": model.alias,
            "prompt": prompt,
            "refs": [str(r) for r in refs],
            "aspect_ratio": args.ar,
            "size": args.size,
            "format": fmt,
            "mime": _FORMATS[fmt][1] if fmt != "unknown" else None,
            "sha256": hashlib.sha256(data).hexdigest(),
            "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }
        path.with_suffix(path.suffix + ".json").write_text(json.dumps(record, indent=2) + "\n")
        records.append({"path": str(path), **record})
        print(path)
    if args.json:
        print(json.dumps(records, indent=2), file=sys.stderr)
    return 0


def cmd_gen(args: argparse.Namespace) -> int:
    return _generate(args, args.prompt, [Path(r) for r in (args.ref or [])])


def cmd_edit(args: argparse.Namespace) -> int:
    refs = [Path(args.image)] + [Path(r) for r in (args.ref or [])]
    if args.model is None:
        args.model = DEFAULT_ALIAS  # editing wants a ref-capable default
    return _generate(args, args.instruction, refs)


def cmd_models(args: argparse.Namespace) -> int:
    width = max(len(m.alias) for m in MODELS)
    for model in MODELS:
        default = " (default)" if model.alias == DEFAULT_ALIAS else ""
        refs = " [ref-images]" if model.supports_ref else ""
        print(f"{model.alias:<{width}}  {model.provider:<10}  {model.model_id}{default}")
        print(f"{'':<{width}}  {'':<10}  {model.note}{refs}")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    failures = 0

    key = config.gemini_key()
    if not key:
        print("gemini      MISSING  set GEMINI_API_KEY (env or ~/.config/imagine/env); "
              "create at https://aistudio.google.com/apikey")
        failures += 1
    else:
        error = gemini.check(key, resolve("nano-banana").model_id)
        print(f"gemini      {'OK' if error is None else 'FAIL     ' + error}")
        failures += error is not None

    token, account_id = config.cloudflare_credentials(args.cf_account)
    if not token or not account_id:
        status, hint = _cloudflare_missing(config.cloudflare_accounts())
        print(f"cloudflare  {status}  {hint}")
        failures += 1
    else:
        error = cf.check(token, account_id)
        print(f"cloudflare  {'OK' if error is None else 'FAIL     ' + error}")
        failures += error is not None

    import shutil as _shutil
    print(f"magick      {'OK' if _shutil.which('magick') else 'MISSING  brew install imagemagick (needed for `imagine fit`)'}")
    return 1 if failures else 0


def cmd_fit(args: argparse.Namespace) -> int:
    src = Path(args.image)
    if not src.is_file():
        raise SystemExit(f"imagine: no such file: {src}")
    dest = Path(args.out) if args.out else src.with_name(f"{src.stem}-fit{src.suffix}")
    fit_image(src, dest, size=args.size, max_kb=args.max_kb, mode=args.mode)
    print(dest)
    return 0


def _add_generation_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--model", "-m", help=f"model alias or raw id (default: {DEFAULT_ALIAS})")
    parser.add_argument("--ar", help="aspect ratio, e.g. 16:9, 21:9 (Gemini models)")
    parser.add_argument("--size", help="1K/2K/4K (Gemini) or WxH pixels (Cloudflare)")
    parser.add_argument("--ref", action="append", metavar="IMAGE",
                        help="reference image (repeatable)")
    parser.add_argument("--out", "-o", help="output path (default: <prompt-slug>-<stamp>.png)")
    parser.add_argument("--n", type=int, default=1, help="number of images (default 1)")
    parser.add_argument("--cf-account", help="account dir under ~/.cloudflare (or IMAGINE_CF_ACCOUNT)")
    parser.add_argument("--param", action="append", metavar="K=V",
                        help="raw provider parameter passthrough (repeatable)")
    parser.add_argument("--no-retry", action="store_true",
                        help="single attempt; don't retry transient provider errors "
                             "(or set IMAGINE_NO_RETRY=1)")
    parser.add_argument("--json", action="store_true", help="print metadata records to stderr")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="imagine",
        description="AI image generation CLI — Gemini (Nano Banana) and Cloudflare Workers AI.",
    )
    parser.add_argument("--version", action="version", version=f"imagine {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_gen = sub.add_parser("gen", help="generate image(s) from a prompt")
    p_gen.add_argument("prompt")
    _add_generation_options(p_gen)
    p_gen.set_defaults(func=cmd_gen)

    p_edit = sub.add_parser("edit", help="edit an image with a natural-language instruction")
    p_edit.add_argument("image")
    p_edit.add_argument("instruction")
    _add_generation_options(p_edit)
    p_edit.set_defaults(func=cmd_edit)

    p_models = sub.add_parser("models", help="list model aliases and routing")
    p_models.set_defaults(func=cmd_models)

    p_doctor = sub.add_parser("doctor", help="check credentials and dependencies")
    p_doctor.add_argument("--cf-account", help="account dir under ~/.cloudflare")
    p_doctor.set_defaults(func=cmd_doctor)

    p_fit = sub.add_parser("fit", help="resize/compress an image to a platform spec")
    p_fit.add_argument("image")
    p_fit.add_argument("--size", help="target WxH, e.g. 320x132")
    p_fit.add_argument("--max-kb", type=int, help="byte budget in KB")
    p_fit.add_argument("--mode", choices=("contain", "cover"), default="contain",
                       help="contain = letterbox on transparency, cover = center-crop")
    p_fit.add_argument("--out", "-o", help="output path (default: <name>-fit.png)")
    p_fit.set_defaults(func=cmd_fit)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
