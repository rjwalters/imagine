"""Bounded retry for transient provider errors (503/429/5xx, connection errors)."""

from __future__ import annotations

import os
import random
import sys
import time
import urllib.error
import urllib.request

MAX_ATTEMPTS = 3
BACKOFF_BASE = 1.0  # seconds; 1s, 2s between the three attempts
RETRY_AFTER_CAP = 30.0
TRANSIENT_CODES = {429, 500, 502, 503, 504}

# Module-level so tests can replace them and not actually wait.
_sleep = time.sleep
_jitter = lambda: random.uniform(0, 0.25)  # noqa: E731


def retry_disabled() -> bool:
    return os.environ.get("IMAGINE_NO_RETRY", "").strip().lower() not in ("", "0", "false", "no")


def _retry_after(err: urllib.error.HTTPError) -> float | None:
    value = err.headers.get("Retry-After") if err.headers else None
    if value is None:
        return None
    try:
        seconds = float(value)
    except ValueError:
        return None  # HTTP-date form: fall back to normal backoff
    return seconds if seconds >= 0 else None


def fetch(
    req: urllib.request.Request,
    timeout: float,
    *,
    provider: str,
    model_id: str,
    retry: bool = True,
) -> tuple[bytes, str]:
    """POST/GET `req`, returning (body, content_type).

    Transient failures are retried up to MAX_ATTEMPTS total. Everything else, and
    the final failure, raises SystemExit with the `imagine: <provider> <code> for
    <model>: ...` message.
    """
    attempts = MAX_ATTEMPTS if retry and not retry_disabled() else 1
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read(), resp.headers.get("Content-Type", "")
        except urllib.error.HTTPError as err:
            detail = err.read().decode("utf-8", "replace")
            final = SystemExit(f"imagine: {provider} {err.code} for {model_id}: {detail[:2000]}")
            if err.code not in TRANSIENT_CODES or attempt == attempts:
                raise final from err
            delay = BACKOFF_BASE * 2 ** (attempt - 1) + _jitter()
            if err.code in (429, 503):
                advised = _retry_after(err)
                if advised is not None:
                    if advised > RETRY_AFTER_CAP:
                        raise final from err
                    delay = advised
            reason = str(err.code)
        except (urllib.error.URLError, ConnectionError, TimeoutError) as err:
            if attempt == attempts:
                raise SystemExit(
                    f"imagine: {provider} connection error for {model_id}: {err}"
                ) from err
            delay = BACKOFF_BASE * 2 ** (attempt - 1) + _jitter()
            reason = "connection error"
        print(
            f"imagine: {provider} {reason}, retrying in {delay:.0f}s "
            f"(attempt {attempt + 1}/{attempts})",
            file=sys.stderr,
        )
        _sleep(delay)
    raise AssertionError("unreachable")  # pragma: no cover
