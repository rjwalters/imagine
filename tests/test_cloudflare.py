"""Cloudflare provider tests. Mocked urlopen + fixtures only; never a live call."""

import io
import json
import urllib.error
from pathlib import Path

import pytest

from imagine.providers import cloudflare, resolve

FIXTURES = Path(__file__).parent / "fixtures"


class FakeResp(io.BytesIO):
    def __init__(self, data: bytes, content_type: str):
        super().__init__(data)
        self.headers = {"Content-Type": content_type}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _capture(monkeypatch, resp=None, error=None):
    seen = {}

    def fake_urlopen(req, timeout=None):
        seen["req"] = req
        if error:
            raise error
        return resp

    monkeypatch.setattr(cloudflare.urllib.request, "urlopen", fake_urlopen)
    return seen


def test_flux2_aliases_use_multipart_and_others_json():
    for alias in ("flux-2-dev", "flux-2-klein", "flux-2-klein-4b"):
        assert resolve(alias).body_format == "multipart"
    for alias in ("flux-schnell", "sdxl", "lucid-origin", "phoenix"):
        assert resolve(alias).body_format == "json"


def test_multipart_body_fields_and_boundary():
    body, ctype = cloudflare.build_multipart_body("a vase", [], 512, None, None, boundary="BB")
    assert ctype == "multipart/form-data; boundary=BB"
    text = body.decode()
    assert 'name="prompt"\r\n\r\na vase\r\n' in text
    assert 'name="width"\r\n\r\n512\r\n' in text
    assert 'name="height"' not in text
    assert text.endswith("--BB--\r\n")


def test_multipart_refs_and_param_overrides(tmp_path):
    a, b = tmp_path / "a.png", tmp_path / "b.png"
    a.write_bytes(b"AAA")
    b.write_bytes(b"BBB")
    body, _ = cloudflare.build_multipart_body(
        "p", [a, b], 64, 64, {"steps": 4, "width": "128"}, boundary="BB"
    )
    text = body.decode()
    assert 'name="input_image_0"; filename="a.png"' in text and "AAA" in text
    assert 'name="input_image_1"; filename="b.png"' in text and "BBB" in text
    assert 'name="steps"\r\n\r\n4\r\n' in text
    assert 'name="width"\r\n\r\n128\r\n' in text
    assert text.count('name="width"') == 1


def test_multipart_request_sent_for_flux2(monkeypatch):
    seen = _capture(monkeypatch, FakeResp(b"\x89PNG", "image/png"))
    out = cloudflare.generate("@cf/black-forest-labs/flux-2-dev", "x", "tok", "acct",
                              body_format="multipart")
    assert out == [b"\x89PNG"]
    req = seen["req"]
    assert req.get_header("Content-type").startswith("multipart/form-data; boundary=")
    assert b'name="prompt"' in req.data


def test_json_model_still_sends_json(monkeypatch):
    seen = _capture(monkeypatch, FakeResp(b"img", "image/png"))
    cloudflare.generate("@cf/black-forest-labs/flux-1-schnell", "x", "tok", "acct", width=8)
    req = seen["req"]
    assert req.get_header("Content-type") == "application/json"
    assert json.loads(req.data) == {"prompt": "x", "width": 8}


def test_json_result_image_shape_decodes(monkeypatch):
    raw = (FIXTURES / "cloudflare_result_image.json").read_bytes()
    _capture(monkeypatch, FakeResp(raw, "application/json"))
    assert cloudflare.generate("m", "x", "t", "a", body_format="multipart") == [b"image-bytes"]


def test_400_surfaces_model_id_and_provider_message(monkeypatch):
    raw = (FIXTURES / "cloudflare_flux2_400_multipart.json").read_bytes()
    err = urllib.error.HTTPError("u", 400, "Bad Request", {}, io.BytesIO(raw))
    _capture(monkeypatch, error=err)
    with pytest.raises(SystemExit) as exc:
        cloudflare.generate("@cf/black-forest-labs/flux-2-dev", "x", "t", "a")
    msg = str(exc.value)
    assert "cloudflare 400" in msg and "@cf/black-forest-labs/flux-2-dev" in msg
    assert "required properties at '/' are 'multipart'" in msg
