"""Credential resolution.

Precedence, per key:
  1. process environment
  2. ~/.config/imagine/env                       (KEY=VALUE lines)
  3. provider-specific stores:
     - Cloudflare: ~/.cloudflare/<account>/workers-ai.env
       (the ~/.cloudflare convention: one subdirectory per account, one
       scoped-token env file per purpose; the file must set
       CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID)

The Cloudflare account name comes from --cf-account or IMAGINE_CF_ACCOUNT.
"""

from __future__ import annotations

import os
from pathlib import Path

CONFIG_ENV = Path.home() / ".config" / "imagine" / "env"
CLOUDFLARE_STORE = Path.home() / ".cloudflare"


def parse_env_file(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    try:
        text = path.read_text()
    except OSError:
        return data
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        key, _, value = line.partition("=")
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def _lookup(name: str, extra_files: tuple[Path, ...] = ()) -> str | None:
    if os.environ.get(name):
        return os.environ[name]
    for path in (CONFIG_ENV, *extra_files):
        value = parse_env_file(path).get(name)
        if value:
            return value
    return None


def gemini_key() -> str | None:
    return _lookup("GEMINI_API_KEY")


def cloudflare_credentials(account: str | None = None) -> tuple[str | None, str | None]:
    """Return (api_token, account_id) for Workers AI."""
    account = account or os.environ.get("IMAGINE_CF_ACCOUNT")
    extra: tuple[Path, ...] = ()
    if account:
        extra = (CLOUDFLARE_STORE / account / "workers-ai.env",)
    return (
        _lookup("CLOUDFLARE_API_TOKEN", extra),
        _lookup("CLOUDFLARE_ACCOUNT_ID", extra),
    )


def cloudflare_accounts() -> list[str]:
    """Account directories in ~/.cloudflare that carry a workers-ai.env."""
    if not CLOUDFLARE_STORE.is_dir():
        return []
    return sorted(
        entry.name
        for entry in CLOUDFLARE_STORE.iterdir()
        if entry.is_dir() and (entry / "workers-ai.env").is_file()
    )
