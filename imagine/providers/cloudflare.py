"""Cloudflare Workers AI image generation via /ai/run."""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from ._retry import fetch

API = "https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{model}"


def _decode_b64_maybe_data_uri(value: str) -> bytes:
    if value.startswith("data:"):
        value = value.split(",", 1)[1]
    return base64.b64decode(value)


def build_json_body(
    prompt: str,
    refs: list[Path],
    width: int | None,
    height: int | None,
    params: dict | None,
) -> tuple[bytes, str]:
    """Return (body, content_type) for models that take a JSON request."""
    payload: dict = {"prompt": prompt}
    if width:
        payload["width"] = width
    if height:
        payload["height"] = height
    if refs:
        # Schema naming for reference images has churned, so send the common
        # field and let --param override for exotic models.
        payload["input_image"] = base64.b64encode(refs[0].read_bytes()).decode("ascii")
        if len(refs) > 1:
            payload["input_images"] = [
                base64.b64encode(p.read_bytes()).decode("ascii") for p in refs
            ]
    if params:
        payload.update(params)
    return json.dumps(payload).encode("utf-8"), "application/json"


def build_multipart_body(
    prompt: str,
    refs: list[Path],
    width: int | None,
    height: int | None,
    params: dict | None,
    boundary: str | None = None,
) -> tuple[bytes, str]:
    """Return (body, content_type) for models that require multipart/form-data.

    Pure (no network). Reference images go in numbered ``input_image_<n>``
    parts; the field name is unverified against the live schema — override
    with --param if Cloudflare renames it. ``--param`` values replace
    same-named fields; non-string values are JSON-encoded.
    """
    boundary = boundary or uuid.uuid4().hex
    fields: dict[str, str] = {"prompt": prompt}
    if width:
        fields["width"] = str(width)
    if height:
        fields["height"] = str(height)
    for key, value in (params or {}).items():
        fields[key] = value if isinstance(value, str) else json.dumps(value)

    out = bytearray()
    for name, value in fields.items():
        out += f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'.encode()
        out += value.encode("utf-8") + b"\r\n"
    for i, path in enumerate(refs):
        out += (
            f'--{boundary}\r\nContent-Disposition: form-data; name="input_image_{i}"; '
            f'filename="{path.name.replace(chr(34), "")}"\r\n'
            "Content-Type: application/octet-stream\r\n\r\n"
        ).encode()
        out += path.read_bytes() + b"\r\n"
    out += f"--{boundary}--\r\n".encode()
    return bytes(out), f"multipart/form-data; boundary={boundary}"


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
    body_format: str = "json",
) -> list[bytes]:
    builder = build_multipart_body if body_format == "multipart" else build_json_body
    data, content_type_header = builder(prompt, refs, width, height, params)

    req = urllib.request.Request(
        API.format(account=account_id, model=model_id),
        data=data,
        headers={"Content-Type": content_type_header, "Authorization": f"Bearer {token}"},
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
