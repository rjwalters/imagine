import json
from types import SimpleNamespace

import pytest

from imagine import cli

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 8
WEBP = b"RIFF\x04\x00\x00\x00WEBPVP8 "
JUNK = b"not an image"


def _args(out, n=1, param=None, json_out=False, model="nano-banana"):
    return SimpleNamespace(
        model=model, ref=None, size=None, param=param, n=n, ar=None,
        out=out, json=json_out, cf_account=None, no_retry=False,
    )


@pytest.fixture
def run(monkeypatch):
    def _run(out, batches, n=1, param=None, json_out=False):
        monkeypatch.setattr(cli.config, "gemini_key", lambda: "fake")
        monkeypatch.setattr(cli.gemini, "generate", lambda *a, **k: list(batches))
        return cli._generate(
            _args(str(out) if out else None, n, param, json_out), "tiny red dot", []
        )
    return _run


@pytest.mark.parametrize(
    "data,fmt", [(PNG, "png"), (JPEG, "jpeg"), (WEBP, "webp"), (JUNK, "unknown"), (b"", "unknown")]
)
def test_sniff(data, fmt):
    assert cli._sniff_format(data) == fmt


def test_jpeg_renamed_with_sidecar(run, tmp_path, capsys):
    run(tmp_path / "out.png", [JPEG])
    cap = capsys.readouterr()
    real = tmp_path / "out.jpg"
    assert cap.out.strip() == str(real)
    assert "provider returned JPEG" in cap.err
    assert real.read_bytes() == JPEG
    assert not (tmp_path / "out.png").exists()
    meta = json.loads((tmp_path / "out.jpg.json").read_text())
    assert meta["format"] == "jpeg" and meta["mime"] == "image/jpeg"
    import hashlib
    assert meta["sha256"] == hashlib.sha256(JPEG).hexdigest()


def test_matching_extension_untouched_but_format_recorded(run, tmp_path, capsys):
    run(tmp_path / "out.png", [PNG])
    cap = capsys.readouterr()
    assert cap.out.strip() == str(tmp_path / "out.png")
    assert cap.err == ""
    meta = json.loads((tmp_path / "out.png.json").read_text())
    assert meta["format"] == "png" and meta["mime"] == "image/png"


def test_uppercase_and_jpeg_aliases(run, tmp_path):
    run(tmp_path / "a.PNG", [PNG])
    assert (tmp_path / "a.PNG").exists()
    run(tmp_path / "b.jpeg", [JPEG])
    assert (tmp_path / "b.jpeg").exists()
    run(tmp_path / "c.PNG", [JPEG])
    assert (tmp_path / "c.jpg").exists()


def test_no_extension_gets_real_one(run, tmp_path):
    run(tmp_path / "out", [WEBP])
    assert (tmp_path / "out.webp").read_bytes() == WEBP


def test_unknown_bytes_keep_requested_extension(run, tmp_path):
    run(tmp_path / "out.png", [JUNK])
    meta = json.loads((tmp_path / "out.png.json").read_text())
    assert meta["format"] == "unknown" and meta["mime"] is None


def test_directory_component_created(run, tmp_path):
    run(tmp_path / "sub" / "dir" / "x.png", [JPEG])
    assert (tmp_path / "sub" / "dir" / "x.jpg.json").exists()


def test_n_naming_uses_per_image_extension(run, tmp_path, capsys):
    run(tmp_path / "out.png", [JPEG, PNG])
    assert (tmp_path / "out-1.jpg").exists()
    assert (tmp_path / "out-2.png").exists()
    assert capsys.readouterr().out.split() == [
        str(tmp_path / "out-1.jpg"), str(tmp_path / "out-2.png")
    ]


# --- params provenance (issue #19) ---

# The sidecar key set before `params` was added; `params` must be additive.
BASE_RECORD_KEYS = {
    "tool", "provider", "model", "alias", "prompt", "refs", "aspect_ratio",
    "size", "format", "mime", "sha256", "created",
}


def _sidecar(tmp_path, name="out.png"):
    return json.loads((tmp_path / f"{name}.json").read_text())


def test_params_recorded_with_json_types(run, tmp_path):
    run(tmp_path / "out.png", [PNG], param=["steps=4", "sampler=euler"])
    meta = _sidecar(tmp_path)
    assert meta["params"] == {"steps": 4, "sampler": "euler"}
    assert isinstance(meta["params"]["steps"], int)
    assert isinstance(meta["params"]["sampler"], str)


def test_params_empty_dict_when_no_flags(run, tmp_path):
    run(tmp_path / "out.png", [PNG])
    meta = _sidecar(tmp_path)
    assert "params" in meta
    assert meta["params"] == {}


def test_params_in_json_record(run, tmp_path, capsys):
    run(tmp_path / "out.png", [PNG], param=["steps=4", "sampler=euler"], json_out=True)
    records = json.loads(capsys.readouterr().err)
    assert len(records) == 1
    assert records[0]["params"] == {"steps": 4, "sampler": "euler"}
    assert isinstance(records[0]["params"]["steps"], int)


def test_params_empty_in_json_record(run, tmp_path, capsys):
    run(tmp_path / "out.png", [PNG], json_out=True)
    records = json.loads(capsys.readouterr().err)
    assert records[0]["params"] == {}


def test_existing_sidecar_fields_unchanged(run, tmp_path):
    run(tmp_path / "out.png", [PNG])
    assert set(_sidecar(tmp_path)) == BASE_RECORD_KEYS | {"params"}


def test_params_nested_json_values_round_trip(run, tmp_path):
    run(tmp_path / "out.png", [PNG], param=['opts={"a":1}', "sizes=[1,2]"])
    meta = _sidecar(tmp_path)
    assert meta["params"] == {"opts": {"a": 1}, "sizes": [1, 2]}


def test_params_recorded_even_when_provider_never_receives_them(run, tmp_path, monkeypatch):
    """Gemini ignores --param; the sidecar records the request, not the wire payload."""
    seen = {}

    def _capture(*a, **k):
        seen.update(k)
        return [PNG]

    monkeypatch.setattr(cli.config, "gemini_key", lambda: "fake")
    monkeypatch.setattr(cli.gemini, "generate", _capture)
    cli._generate(
        _args(str(tmp_path / "out.png"), param=["steps=4"]), "tiny red dot", []
    )
    assert "params" not in seen
    assert _sidecar(tmp_path)["params"] == {"steps": 4}


def test_params_identical_across_n(run, tmp_path):
    run(tmp_path / "out.png", [PNG], n=2, param=["steps=4"])
    first = _sidecar(tmp_path, "out-1.png")
    second = _sidecar(tmp_path, "out-2.png")
    assert first["params"] == second["params"] == {"steps": 4}
