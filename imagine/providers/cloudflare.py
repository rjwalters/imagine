"""Cloudflare Workers AI image generation via /ai/run."""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from pathlib import Path

from ._retry import fetch

API = "https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{model}"


def _decode_b64_maybe_data_uri(value: str) -> bytes:
    if value.startswith("data:"):
        value = value.split(",", 1)[1]
    return base64.b64decode(value)


def generate(
    model_id: str,
    prompt: str,
    token: str,
    account_id: str,
    refs: list[Path] = [],
    width: int | None = None,
    height: int | None = None,
    params: dict | None = None,
    retry: bool = True,
) -> list[bytes]:
    payload: dict = {"prompt": prompt}
    if width:
        payload["width"] = width
    if height:
        payload["height"] = height
    if refs:
        # FLUX.2 models take reference images; schema naming has churned, so
        # send the common field and let --param override for exotic models.
        payload["input_image"] = base64.b64encode(refs[0].read_bytes()).decode("ascii")
        if len(refs) > 1:
            payload["input_images"] = [
                base64.b64encode(p.read_bytes()).decode("ascii") for p in refs
            ]
    if params:
        payload.update(params)

    req = urllib.request.Request(
        API.format(account=account_id, model=model_id),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST",
    )
    raw, content_type = fetch(req, 300, provider="cloudflare", model_id=model_id, retry=retry)

    if content_type.startswith("image/"):
        return [raw]

    body = json.loads(raw)
    result = body.get("result") or {}
    if isinstance(result, dict):
        if result.get("image"):
            return [_decode_b64_maybe_data_uri(result["image"])]
        if result.get("images"):
            return [_decode_b64_maybe_data_uri(img) for img in result["images"]]
    raise SystemExit(
        f"imagine: unrecognized cloudflare response shape for {model_id}: "
        f"{json.dumps(body)[:2000]}"
    )


def check(token: str, account_id: str) -> str | None:
    """Cheap token/entitlement check. Returns an error string or None."""
    url = (
        f"https://api.cloudflare.com/client/v4/accounts/{account_id}"
        f"/ai/models/search?per_page=1"
    )
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.load(resp)
        return None if body.get("success") else json.dumps(body.get("errors"))[:300]
    except urllib.error.HTTPError as err:
        return f"HTTP {err.code}: {err.read().decode('utf-8', 'replace')[:300]}"
    except OSError as err:
        return str(err)
