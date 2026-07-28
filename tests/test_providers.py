import pytest

from imagine.providers import DEFAULT_ALIAS, MODELS, resolve


def test_default_alias_resolves_to_gemini():
    model = resolve(None)
    assert model.alias == DEFAULT_ALIAS
    assert model.provider == "gemini"
    assert model.supports_ref


def test_every_alias_resolves_to_itself():
    for model in MODELS:
        assert resolve(model.alias) is model
        assert resolve(model.model_id) is model


def test_raw_cloudflare_id_routes_by_shape():
    model = resolve("@cf/some-vendor/new-model")
    assert model.provider == "cloudflare"


def test_raw_gemini_id_routes_by_shape():
    model = resolve("gemini-9-ultra-image")
    assert model.provider == "gemini"


def test_unknown_model_exits_with_help():
    with pytest.raises(SystemExit, match="unknown model"):
        resolve("dall-e-1")
