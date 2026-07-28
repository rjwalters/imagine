from imagine import config


def test_parse_env_file(tmp_path):
    env = tmp_path / "test.env"
    env.write_text(
        "# scoped token, created 2026-07-28\n"
        "export CLOUDFLARE_API_TOKEN=\"abc123\"\n"
        "CLOUDFLARE_ACCOUNT_ID='deadbeef'\n"
        "\n"
        "MALFORMED LINE\n"
    )
    data = config.parse_env_file(env)
    assert data == {
        "CLOUDFLARE_API_TOKEN": "abc123",
        "CLOUDFLARE_ACCOUNT_ID": "deadbeef",
    }


def test_parse_env_file_missing(tmp_path):
    assert config.parse_env_file(tmp_path / "nope.env") == {}


def test_env_var_wins_over_files(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "from-env")
    assert config.gemini_key() == "from-env"


def test_cloudflare_account_file(monkeypatch, tmp_path):
    store = tmp_path / ".cloudflare"
    account = store / "2amlogic"
    account.mkdir(parents=True)
    (account / "workers-ai.env").write_text(
        "CLOUDFLARE_API_TOKEN=tok\nCLOUDFLARE_ACCOUNT_ID=acct\n"
    )
    monkeypatch.setattr(config, "CLOUDFLARE_STORE", store)
    monkeypatch.setattr(config, "CONFIG_ENV", tmp_path / "no-config-env")
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
    monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID", raising=False)

    token, account_id = config.cloudflare_credentials("2amlogic")
    assert (token, account_id) == ("tok", "acct")
    assert config.cloudflare_accounts() == ["2amlogic"]
