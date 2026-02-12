from __future__ import annotations

from pathlib import Path
import sys

import pytest
from fastapi import HTTPException
from starlette.requests import Request

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from backend.idempotency import (
    InMemoryIdempotencyStore,
    idempotency_ttl_seconds,
    maybe_replay_response,
    parse_positive_int_env,
    store_idempotent_response,
)


def _request_with_idempotency_key(key: str) -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/lectures/lecture-001/generate",
        "headers": [(b"idempotency-key", key.encode("latin-1"))],
        "client": ("127.0.0.1", 1234),
        "scheme": "http",
        "query_string": b"",
        "server": ("testserver", 80),
    }
    return Request(scope)


def test_parse_positive_int_env_rejects_bad_values(monkeypatch):
    monkeypatch.setenv("PLC_IDEMPOTENCY_TTL_SEC", "abc")
    with pytest.raises(RuntimeError, match="PLC_IDEMPOTENCY_TTL_SEC must be an integer"):
        idempotency_ttl_seconds()

    monkeypatch.setenv("PLC_IDEMPOTENCY_TTL_SEC", "0")
    with pytest.raises(RuntimeError, match="PLC_IDEMPOTENCY_TTL_SEC must be a positive integer"):
        idempotency_ttl_seconds()


def test_replay_returns_cached_response_for_matching_fingerprint():
    request = _request_with_idempotency_key("idem-1")
    store = InMemoryIdempotencyStore()

    store_idempotent_response(
        request,
        store,
        scope="lectures.generate",
        fingerprint="a",
        response_payload={"jobId": "job-1"},
        now=10.0,
    )

    replay = maybe_replay_response(
        request,
        store,
        scope="lectures.generate",
        fingerprint="a",
        now=11.0,
    )

    assert replay == {"jobId": "job-1"}


def test_replay_rejects_key_reuse_with_different_fingerprint():
    request = _request_with_idempotency_key("idem-1")
    store = InMemoryIdempotencyStore()

    store_idempotent_response(
        request,
        store,
        scope="lectures.generate",
        fingerprint="a",
        response_payload={"jobId": "job-1"},
        now=10.0,
    )

    with pytest.raises(HTTPException) as exc_info:
        maybe_replay_response(
            request,
            store,
            scope="lectures.generate",
            fingerprint="b",
            now=11.0,
        )

    assert exc_info.value.status_code == 409


def test_expired_idempotency_record_is_pruned(monkeypatch):
    request = _request_with_idempotency_key("idem-1")
    store = InMemoryIdempotencyStore()

    store_idempotent_response(
        request,
        store,
        scope="lectures.generate",
        fingerprint="a",
        response_payload={"jobId": "job-1"},
        now=1.0,
    )

    monkeypatch.setenv("PLC_IDEMPOTENCY_TTL_SEC", "1")
    replay = maybe_replay_response(
        request,
        store,
        scope="lectures.generate",
        fingerprint="a",
        now=2.5,
    )

    assert replay is None


def test_parse_positive_int_env_uses_default(monkeypatch):
    monkeypatch.delenv("ANY_VALUE", raising=False)
    assert parse_positive_int_env("ANY_VALUE", 7) == 7
