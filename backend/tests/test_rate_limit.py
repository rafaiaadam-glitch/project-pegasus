from __future__ import annotations

from pathlib import Path
import sys

import pytest
from starlette.requests import Request

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

import backend.app as app_module


def _request_with_headers(headers: dict[str, str]) -> Request:
    raw_headers = [(k.lower().encode("latin-1"), v.encode("latin-1")) for k, v in headers.items()]
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/lectures/lecture-001/transcribe",
        "headers": raw_headers,
        "client": ("127.0.0.1", 1234),
        "scheme": "http",
        "query_string": b"",
        "server": ("testserver", 80),
    }
    return Request(scope)


def test_parse_positive_int_env_rejects_invalid(monkeypatch):
    monkeypatch.setenv("PLC_WRITE_RATE_LIMIT_MAX_REQUESTS", "abc")

    with pytest.raises(RuntimeError, match="PLC_WRITE_RATE_LIMIT_MAX_REQUESTS must be an integer"):
        app_module._write_rate_limit_config()


def test_parse_positive_int_env_rejects_non_positive(monkeypatch):
    monkeypatch.setenv("PLC_WRITE_RATE_LIMIT_WINDOW_SEC", "0")

    with pytest.raises(RuntimeError, match="PLC_WRITE_RATE_LIMIT_WINDOW_SEC must be a positive integer"):
        app_module._write_rate_limit_config()


def test_client_identifier_prefers_x_forwarded_for():
    request = _request_with_headers({"x-forwarded-for": "10.0.0.8, 10.0.0.1"})

    assert app_module._client_identifier(request) == "10.0.0.8"


def test_in_memory_rate_limiter_enforces_limit_window():
    limiter = app_module._InMemoryRateLimiter()

    assert limiter.allow("client-a", limit=2, window_seconds=10, now=1.0)
    assert limiter.allow("client-a", limit=2, window_seconds=10, now=2.0)
    assert not limiter.allow("client-a", limit=2, window_seconds=10, now=3.0)
    assert limiter.allow("client-a", limit=2, window_seconds=10, now=12.1)
