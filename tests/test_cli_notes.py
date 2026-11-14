"""Applicability notes: options the selected provider will ignore.

Every case below is decided from `args` and `model.provider` before the
provider call, so both providers are fully mocked — no credential, no network.
"""

from types import SimpleNamespace

import pytest

from imagine import cli

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8

# The two pre-existing notes, byte-identical to pre-hoist output (AC5).
AR_IS_GEMINI = "imagine: note: --ar is a Gemini option; use --size WxH for Cloudflare models"
UNDOCUMENTED_AR = "imagine: note: '7:3' is not a documented aspect ratio; passing through"


def _args(out, *, model="nano-banana", size=None, param=None, ar=None, n=1):
    return SimpleNamespace(
        model=model, ref=None, size=size, param=param, n=n, ar=ar,
        out=out, json=False, cf_account=None, no_retry=False,
    )


@pytest.fixture
def run(monkeypatch):
    """Run `_generate` with both providers mocked; returns the exit code."""
    def _run(out, **kwargs):
        monkeypatch.setattr(cli.config, "gemini_key", lambda: "fake")
        monkeypatch.setattr(cli.gemini, "generate", lambda *a, **k: [PNG])
        monkeypatch.setattr(
            cli.config, "cloudflare_credentials", lambda acct: ("tok", "acct")
        )
        monkeypatch.setattr(cli.cf, "generate", lambda *a, **k: [PNG])
        return cli._generate(_args(str(out), **kwargs), "tiny red dot", [])
    return _run


def _notes(err: str) -> list[str]:
    return [line for line in err.splitlines() if line.startswith("imagine: note: ")]


# --- the three newly-signalled cases -------------------------------------


def test_param_on_gemini_notes_once(run, tmp_path, capsys):
    assert run(tmp_path / "out.png", model="nano-banana", param=["steps=4"]) == 0
    notes = _notes(capsys.readouterr().err)
    assert notes == ["imagine: note: --param is a Cloudflare option; Gemini models ignore it"]
    # generation still proceeded: image and sidecar written
    assert (tmp_path / "out.png").read_bytes() == PNG
    assert (tmp_path / "out.png.json").exists()


def test_pixel_size_on_gemini_notes_once(run, tmp_path, capsys):
    assert run(tmp_path / "out.png", model="nano-banana", size="1920x1080") == 0
    notes = _notes(capsys.readouterr().err)
    assert notes == [
        "imagine: note: --size WxH is a Cloudflare option; "
        "use --size 1K/2K/4K for Gemini models"
    ]
    assert (tmp_path / "out.png").exists()


def test_image_size_on_cloudflare_notes_once(run, tmp_path, capsys):
    assert run(tmp_path / "out.png", model="flux-schnell", size="2K") == 0
    notes = _notes(capsys.readouterr().err)
    assert notes == [
        "imagine: note: --size 1K/2K/4K is a Gemini option; "
        "use --size WxH for Cloudflare models"
    ]
    assert (tmp_path / "out.png").exists()


# --- the two pre-existing notes, wording pinned (AC5) --------------------


def test_ar_on_cloudflare_wording_unchanged(run, tmp_path, capsys):
    assert run(tmp_path / "out.png", model="flux-schnell", ar="16:9") == 0
    assert _notes(capsys.readouterr().err) == [AR_IS_GEMINI]


def test_undocumented_ar_on_gemini_wording_unchanged(run, tmp_path, capsys):
    assert run(tmp_path / "out.png", model="nano-banana", ar="7:3") == 0
    assert _notes(capsys.readouterr().err) == [UNDOCUMENTED_AR]


# --- negative cases: the option applies, so stay silent ------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"model": "nano-banana", "ar": "16:9", "size": "2K"},
        {"model": "flux-schnell", "size": "800x600", "param": ["steps=4"]},
        # a documented ratio at the far end of KNOWN_ASPECT_RATIOS
        {"model": "nano-banana", "ar": "21:9"},
        # no options at all
        {"model": "nano-banana"},
        {"model": "flux-schnell"},
    ],
)
def test_no_note_when_option_applies(run, tmp_path, capsys, kwargs):
    assert run(tmp_path / "out.png", **kwargs) == 0
    assert _notes(capsys.readouterr().err) == []


# --- once per invocation, not once per image ----------------------------


def test_ar_on_cloudflare_noted_once_for_n3(run, tmp_path, capsys):
    assert run(tmp_path / "out.png", model="flux-schnell", ar="16:9", n=3) == 0
    cap = capsys.readouterr()
    assert cap.err.count("imagine: note:") == 1
    # all three images were still produced
    assert len(cap.out.split()) == 3


def test_undocumented_ar_noted_once_for_n2(run, tmp_path, capsys):
    assert run(tmp_path / "out.png", model="nano-banana", ar="7:3", n=2) == 0
    cap = capsys.readouterr()
    assert cap.err.count("imagine: note:") == 1
    assert len(cap.out.split()) == 2


# --- several inapplicable options at once -------------------------------


def test_two_inapplicable_options_give_two_notes(run, tmp_path, capsys):
    assert run(
        tmp_path / "out.png", model="nano-banana", param=["steps=4"], size="1920x1080"
    ) == 0
    assert _notes(capsys.readouterr().err) == [
        "imagine: note: --param is a Cloudflare option; Gemini models ignore it",
        "imagine: note: --size WxH is a Cloudflare option; "
        "use --size 1K/2K/4K for Gemini models",
    ]


def test_three_inapplicable_options_on_gemini(run, tmp_path, capsys):
    assert run(
        tmp_path / "out.png",
        model="nano-banana", param=["steps=4"], size="1920x1080", ar="7:3",
    ) == 0
    assert _notes(capsys.readouterr().err) == [
        "imagine: note: --param is a Cloudflare option; Gemini models ignore it",
        "imagine: note: --size WxH is a Cloudflare option; "
        "use --size 1K/2K/4K for Gemini models",
        UNDOCUMENTED_AR,
    ]


def test_both_inapplicable_options_on_cloudflare(run, tmp_path, capsys):
    assert run(tmp_path / "out.png", model="flux-schnell", ar="7:3", size="4K") == 0
    assert _notes(capsys.readouterr().err) == [
        AR_IS_GEMINI,
        "imagine: note: --size 1K/2K/4K is a Gemini option; "
        "use --size WxH for Cloudflare models",
    ]


# --- raw provider ids route like aliases --------------------------------


@pytest.mark.parametrize(
    "model,kwargs,expected",
    [
        # registry model_ids
        ("@cf/leonardo/phoenix-1.0", {"size": "2K"},
         "imagine: note: --size 1K/2K/4K is a Gemini option; "
         "use --size WxH for Cloudflare models"),
        ("gemini-3-pro-image", {"param": ["steps=4"]},
         "imagine: note: --param is a Cloudflare option; Gemini models ignore it"),
        # ids absent from the registry, routed purely by shape
        ("@cf/some/unregistered-model", {"size": "2K"},
         "imagine: note: --size 1K/2K/4K is a Gemini option; "
         "use --size WxH for Cloudflare models"),
        ("gemini-99-future-image", {"param": ["steps=4"]},
         "imagine: note: --param is a Cloudflare option; Gemini models ignore it"),
    ],
)
def test_raw_ids_get_the_right_note(run, tmp_path, capsys, model, kwargs, expected):
    assert run(tmp_path / "out.png", model=model, **kwargs) == 0
    assert _notes(capsys.readouterr().err) == [expected]


# --- interaction with existing failure paths ----------------------------


def test_missing_gemini_credential_still_exits(monkeypatch, tmp_path, capsys):
    """The note now precedes the credential error; the error still fires."""
    monkeypatch.setattr(cli.config, "gemini_key", lambda: "")
    monkeypatch.setattr(cli.gemini, "generate", lambda *a, **k: [PNG])
    with pytest.raises(SystemExit) as excinfo:
        cli._generate(
            _args(str(tmp_path / "out.png"), model="nano-banana", param=["steps=4"]),
            "tiny red dot", [],
        )
    assert "GEMINI_API_KEY not found" in str(excinfo.value)
    err = capsys.readouterr().err
    assert _notes(err) == [
        "imagine: note: --param is a Cloudflare option; Gemini models ignore it"
    ]
    assert not (tmp_path / "out.png").exists()


def test_missing_cloudflare_credential_still_exits(monkeypatch, tmp_path):
    monkeypatch.setattr(cli.config, "cloudflare_credentials", lambda acct: (None, None))
    monkeypatch.setattr(cli.config, "cloudflare_accounts", lambda: [])
    monkeypatch.setattr(cli.cf, "generate", lambda *a, **k: [PNG])
    with pytest.raises(SystemExit) as excinfo:
        cli._generate(
            _args(str(tmp_path / "out.png"), model="flux-schnell", ar="16:9"),
            "tiny red dot", [],
        )
    assert "Cloudflare credentials not found" in str(excinfo.value)


def test_bad_param_raises_before_any_note(monkeypatch, tmp_path, capsys):
    """`--param` with no `=` keeps raising before note logic runs."""
    monkeypatch.setattr(cli.config, "gemini_key", lambda: "fake")
    monkeypatch.setattr(cli.gemini, "generate", lambda *a, **k: [PNG])
    with pytest.raises(SystemExit) as excinfo:
        cli._generate(
            _args(str(tmp_path / "out.png"), model="nano-banana",
                  param=["steps"], size="1920x1080"),
            "tiny red dot", [],
        )
    assert "--param expects key=value" in str(excinfo.value)
    assert _notes(capsys.readouterr().err) == []


# --- edit goes through the same path ------------------------------------


def test_edit_gets_the_same_notes(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli.config, "gemini_key", lambda: "fake")
    monkeypatch.setattr(cli.gemini, "generate", lambda *a, **k: [PNG])
    source = tmp_path / "in.png"
    source.write_bytes(PNG)
    args = SimpleNamespace(
        model="nano-banana", image=str(source), instruction="make it blue", ref=None,
        size="1920x1080", param=None, n=1, ar=None, out=str(tmp_path / "out.png"),
        json=False, cf_account=None, no_retry=False,
    )
    assert cli.cmd_edit(args) == 0
    assert _notes(capsys.readouterr().err) == [
        "imagine: note: --size WxH is a Cloudflare option; "
        "use --size 1K/2K/4K for Gemini models"
    ]
