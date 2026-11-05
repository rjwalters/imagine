import email.message
import io
import json
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from imagine import cli
from imagine.providers import _retry, gemini

FIXTURE = (Path(__file__).parent / "fixtures" / "gemini_503_unavailable.json").read_bytes()
OK = json.dumps({"candidates": [{"content": {"parts": [
    {"inlineData": {"mimeType": "image/png", "data": "aGk="}}]}}]}).encode()


class FakeResp(io.BytesIO):
    headers = {"Content-Type": "application/json"}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def http_error(code, body=FIXTURE, retry_after=None):
    hdrs = email.message.Message()
    if retry_after is not None:
        hdrs["Retry-After"] = str(retry_after)
    return urllib.error.HTTPError("http://x", code, "err", hdrs, io.BytesIO(body))


@pytest.fixture
def script(monkeypatch):
    """Install a scripted urlopen; returns (calls, sleeps)."""
    calls, sleeps = [], []

    def install(*outcomes):
        seq = list(outcomes)

        def fake(req, timeout=None):
            calls.append(req)
            out = seq.pop(0)
            if isinstance(out, BaseException):
                raise out
            return FakeResp(out)

        monkeypatch.setattr(urllib.request, "urlopen", fake)
        return calls, sleeps

    monkeypatch.setattr(_retry, "_sleep", sleeps.append)
    monkeypatch.setattr(_retry, "_jitter", lambda: 0)
    monkeypatch.delenv("IMAGINE_NO_RETRY", raising=False)
    return install


def run(retry=True):
    return gemini._request("m", "k", {}, retry)


def test_503_then_success(script, capsys):
    calls, sleeps = script(http_error(503), OK)
    assert run()["candidates"]
    assert len(calls) == 2 and sleeps == [1.0]
    out = capsys.readouterr()
    assert out.out == ""
    assert "gemini 503, retrying in 1s (attempt 2/3)" in out.err


def test_503_exhausted_raises_original_message(script):
    calls, sleeps = script(http_error(503), http_error(503), http_error(503))
    with pytest.raises(SystemExit) as exc:
        run()
    assert str(exc.value).startswith("imagine: gemini 503 for m: ")
    assert "UNAVAILABLE" in str(exc.value)
    assert len(calls) == 3 and sleeps == [1.0, 2.0]


def test_429_honours_retry_after(script):
    calls, sleeps = script(http_error(429, retry_after=2), OK)
    run()
    assert sleeps == [2.0]


def test_retry_after_over_cap_fails_without_sleep(script):
    calls, sleeps = script(http_error(429, retry_after=120))
    with pytest.raises(SystemExit, match="gemini 429 for m"):
        run()
    assert len(calls) == 1 and sleeps == []


@pytest.mark.parametrize("code", [400, 401, 403, 404])
def test_non_transient_fails_fast(script, code):
    calls, sleeps = script(http_error(code))
    with pytest.raises(SystemExit, match=f"gemini {code} for m"):
        run()
    assert len(calls) == 1 and sleeps == []


def test_urlerror_then_success(script):
    calls, sleeps = script(urllib.error.URLError("reset"), OK)
    run()
    assert len(calls) == 2


def test_connection_error_exhausted_is_clean_exit(script):
    script(ConnectionResetError("x"), TimeoutError("y"), urllib.error.URLError("z"))
    with pytest.raises(SystemExit, match="connection error"):
        run()


def test_retry_false_single_attempt(script):
    calls, sleeps = script(http_error(503))
    with pytest.raises(SystemExit, match="gemini 503"):
        run(retry=False)
    assert len(calls) == 1 and sleeps == []


def test_env_disables_retry(script, monkeypatch):
    monkeypatch.setenv("IMAGINE_NO_RETRY", "1")
    calls, _ = script(http_error(503))
    with pytest.raises(SystemExit):
        run()
    assert len(calls) == 1


def test_cli_no_retry_flag_parsed():
    import argparse
    p = argparse.ArgumentParser()
    cli._add_generation_options(p)
    assert p.parse_args(["--no-retry"]).no_retry is True
    assert p.parse_args([]).no_retry is False
