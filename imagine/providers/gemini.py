"""Gemini image generation (Nano Banana family) via generateContent."""

from __future__ import annotations

import base64
import json
import mimetypes
import urllib.error
import urllib.request
from pathlib import Path

API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

# Aspect ratios the imageConfig accepts; anything else is passed through
# with a warning from the CLI layer.
KNOWN_ASPECT_RATIOS = {
    "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9",
}
KNOWN_IMAGE_SIZES = {"1K", "2K", "4K"}


def _inline_part(path: Path) -> dict:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return {"inlineData": {"mimeType": mime, "data": data}}


def _request(model_id: str, api_key: str, body: dict) -> dict:
    req = urllib.request.Request(
        API.format(model=model_id),
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as err:
        detail = err.read().decode("utf-8", "replace")
        raise SystemExit(f"imagine: gemini {err.code} for {model_id}: {detail[:2000]}") from err


def _extract_images(response: dict) -> list[bytes]:
    images: list[bytes] = []
    for candidate in response.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                images.append(base64.b64decode(inline["data"]))
    return images


def generate(
    model_id: str,
    prompt: str,
    api_key: str,
    refs: list[Path] = [],
    aspect_ratio: str | None = None,
    image_size: str | None = None,
) -> list[bytes]:
    parts: list[dict] = [_inline_part(p) for p in refs]
    parts.append({"text": prompt})

    generation_config: dict = {"responseModalities": ["IMAGE"]}
    image_config: dict = {}
    if aspect_ratio:
        image_config["aspectRatio"] = aspect_ratio
    if image_size:
        image_config["imageSize"] = image_size
    if image_config:
        generation_config["imageConfig"] = image_config

    body = {
        "contents": [{"parts": parts}],
        "generationConfig": generation_config,
    }
    response = _request(model_id, api_key, body)
    images = _extract_images(response)
    if not images:
        # Some model versions want TEXT alongside IMAGE; retry once.
        body["generationConfig"]["responseModalities"] = ["TEXT", "IMAGE"]
        response = _request(model_id, api_key, body)
        images = _extract_images(response)
    if not images:
        feedback = response.get("promptFeedback") or response.get("candidates")
        raise SystemExit(
            f"imagine: gemini returned no image for {model_id}: {json.dumps(feedback)[:2000]}"
        )
    return images


def check(api_key: str, model_id: str) -> str | None:
    """Cheap connectivity/entitlement check. Returns an error string or None."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}"
    req = urllib.request.Request(url, headers={"x-goog-api-key": api_key})
    try:
        with urllib.request.urlopen(req, timeout=30):
            return None
    except urllib.error.HTTPError as err:
        return f"HTTP {err.code}: {err.read().decode('utf-8', 'replace')[:300]}"
    except OSError as err:
        return str(err)
