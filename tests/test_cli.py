import argparse

import pytest

from imagine import cli, config


def _isolate(monkeypatch, tmp_path):
    store = tmp_path / ".cloudflare"
    monkeypatch.setattr(config, "CLOUDFLARE_STORE", store)
    monkeypatch.setattr(config, "CONFIG_ENV", tmp_path / "no-config-env")
    for name in ("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID",
                 "IMAGINE_CF_ACCOUNT", "GEMINI_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(cli.gemini, "check", lambda *a, **k: None)
    monkeypatch.setattr(cli.cf, "check", lambda *a, **k: None)
    return store


def _add_account(store, name):
    d = store / name
    d.mkdir(parents=True)
    (d / "workers-ai.env").write_text("CLOUDFLARE_API_TOKEN=tok\nCLOUDFLARE_ACCOUNT_ID=acct\n")


def _cf_line(out):
    return next(line for line in out.splitlines() if line.startswith("cloudflare"))


def test_doctor_needs_account(monkeypatch, tmp_path, capsys):
    store = _isolate(monkeypatch, tmp_path)
    _add_account(store, "2amlogic")
    _add_account(store, "other")
    (store / "empty").mkdir()  # no workers-ai.env: not counted
    rc = cli.cmd_doctor(argparse.Namespace(cf_account=None))
    line = _cf_line(capsys.readouterr().out)
    assert rc == 1
    assert "NEEDS ACCOUNT" in line and "MISSING" not in line
    assert "2amlogic, other" in line and "empty" not in line
    assert "--cf-account" in line and "IMAGINE_CF_ACCOUNT" in line
    assert "even with a single account" in line


def test_doctor_missing_when_no_credentials(monkeypatch, tmp_path, capsys):
    _isolate(monkeypatch, tmp_path)
    rc = cli.cmd_doctor(argparse.Namespace(cf_account=None))
    line = _cf_line(capsys.readouterr().out)
    assert rc == 1
    assert "MISSING" in line and "NEEDS ACCOUNT" not in line


def test_doctor_account_selected_ok(monkeypatch, tmp_path, capsys):
    store = _isolate(monkeypatch, tmp_path)
    _add_account(store, "2amlogic")
    cli.cmd_doctor(argparse.Namespace(cf_account="2amlogic"))
    assert _cf_line(capsys.readouterr().out).split() == ["cloudflare", "OK"]


def _gen_args(**overrides):
    """Namespace for cli._generate on a Cloudflare model."""
    args = dict(
        model="flux-schnell", ref=None, size=None, param=None, n=1, ar=None,
        out=None, json=False, cf_account=None, no_retry=False,
    )
    args.update(overrides)
    return argparse.Namespace(**args)


def test_gen_needs_account_names_selection_guidance(monkeypatch, tmp_path):
    """gen must emit the post-#4 selection guidance, not the superseded wording."""
    store = _isolate(monkeypatch, tmp_path)
    _add_account(store, "2amlogic")
    with pytest.raises(SystemExit) as excinfo:
        cli._generate(_gen_args(), "tiny red dot", [])
    message = str(excinfo.value)
    assert "Cloudflare credentials not found" in message
    assert "2amlogic" in message
    assert "--cf-account" in message and "IMAGINE_CF_ACCOUNT" in message
    assert "even with a single account" in message
    assert "accounts with workers-ai.env" not in message  # the pre-#4 wording


def test_gen_missing_points_at_the_token_file(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    with pytest.raises(SystemExit) as excinfo:
        cli._generate(_gen_args(), "tiny red dot", [])
    message = str(excinfo.value)
    assert "~/.cloudflare/<account>/workers-ai.env" in message
    assert "CLOUDFLARE_API_TOKEN" in message and "CLOUDFLARE_ACCOUNT_ID" in message
    assert "IMAGINE_CF_ACCOUNT" not in message  # nothing to select


def test_doctor_and_gen_share_one_hint(monkeypatch, tmp_path, capsys):
    """The two surfaces format one helper result; they cannot drift apart."""
    store = _isolate(monkeypatch, tmp_path)
    _add_account(store, "2amlogic")
    status, hint = cli._cloudflare_missing(config.cloudflare_accounts())
    cli.cmd_doctor(argparse.Namespace(cf_account=None))
    assert _cf_line(capsys.readouterr().out) == f"cloudflare  {status}  {hint}"
    with pytest.raises(SystemExit) as excinfo:
        cli._generate(_gen_args(), "tiny red dot", [])
    assert str(excinfo.value) == f"imagine: Cloudflare credentials not found; {hint}"
