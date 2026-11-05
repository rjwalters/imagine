"""Model registry and routing.

Aliases are the stable interface; provider model IDs churn (Gemini preview
IDs get shut down, Cloudflare adds models). `resolve` accepts an alias, an
exact provider model ID, or infers the provider from the ID shape
(@cf/... → cloudflare, gemini-* → gemini).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Model:
    alias: str
    provider: str  # "gemini" | "cloudflare"
    model_id: str
    note: str
    supports_ref: bool = False  # accepts reference/input images
    body_format: str = "json"  # Cloudflare request body: "json" | "multipart"


MODELS: tuple[Model, ...] = (
    Model(
        "nano-banana", "gemini", "gemini-3.1-flash-image",
        "Nano Banana 2 — default; up to 4K, strong text rendering, reference images",
        supports_ref=True,
    ),
    Model(
        "nano-banana-pro", "gemini", "gemini-3-pro-image",
        "Nano Banana Pro — premium; best layout control and brand consistency",
        supports_ref=True,
    ),
    Model(
        "nano-banana-lite", "gemini", "gemini-3.1-flash-lite-image",
        "fastest / cheapest Gemini image model; drafts at volume",
        supports_ref=True,
    ),
    Model(
        "flux-2-dev", "cloudflare", "@cf/black-forest-labs/flux-2-dev",
        "FLUX.2 [dev] — photorealism, multi-reference, JSON prompting",
        supports_ref=True,
        body_format="multipart",
    ),
    Model(
        "flux-2-klein", "cloudflare", "@cf/black-forest-labs/flux-2-klein-9b",
        "FLUX.2 [klein] 9B — fast unified generation + editing",
        supports_ref=True,
        body_format="multipart",
    ),
    Model(
        "flux-2-klein-4b", "cloudflare", "@cf/black-forest-labs/flux-2-klein-4b",
        "FLUX.2 [klein] 4B — fastest FLUX.2 distill, 4-step inference",
        supports_ref=True,
        body_format="multipart",
    ),
    Model(
        "flux-schnell", "cloudflare", "@cf/black-forest-labs/flux-1-schnell",
        "FLUX.1 [schnell] — cheap fast drafts",
    ),
    Model(
        "lucid-origin", "cloudflare", "@cf/leonardo/lucid-origin",
        "Leonardo Lucid Origin — prompt adherence, text rendering, style range",
    ),
    Model(
        "phoenix", "cloudflare", "@cf/leonardo/phoenix-1.0",
        "Leonardo Phoenix — coherent text, strong prompt adherence",
    ),
    Model(
        "sdxl", "cloudflare", "@cf/stabilityai/stable-diffusion-xl-base-1.0",
        "Stable Diffusion XL base — open-weights workhorse",
    ),
)

DEFAULT_ALIAS = "nano-banana"


def resolve(name: str | None) -> Model:
    name = name or DEFAULT_ALIAS
    for model in MODELS:
        if name in (model.alias, model.model_id):
            return model
    # Raw IDs not in the registry still route by shape.
    if name.startswith("@cf/"):
        return Model(name, "cloudflare", name, "unregistered Cloudflare model", supports_ref=True)
    if name.startswith("gemini-"):
        return Model(name, "gemini", name, "unregistered Gemini model", supports_ref=True)
    known = ", ".join(m.alias for m in MODELS)
    raise SystemExit(f"imagine: unknown model '{name}' (known: {known}, or a raw @cf/... / gemini-* id)")
