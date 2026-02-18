from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from time import time
from typing import Optional

from fastapi import HTTPException, Request


@dataclass
class IdempotencyRecord:
    fingerprint: str
    response_payload: dict
    created_at: float


class InMemoryIdempotencyStore:
    def __init__(self) -> None:
        self._records: dict[tuple[str, str], IdempotencyRecord] = {}
        self._lock = threading.Lock()

    def get(self, scope: str, key: str, ttl_seconds: int, now: float) -> Optional[IdempotencyRecord]:
        with self._lock:
            self._prune_expired(ttl_seconds, now)
            return self._records.get((scope, key))

    def put(self, scope: str, key: str, fingerprint: str, response_payload: dict, now: float) -> None:
        with self._lock:
            self._records[(scope, key)] = IdempotencyRecord(
                fingerprint=fingerprint,
                response_payload=response_payload,
                created_at=now,
            )

    def _prune_expired(self, ttl_seconds: int, now: float) -> None:
        expired = [
            cache_key
            for cache_key, record in self._records.items()
            if (now - record.created_at) >= ttl_seconds
        ]
        for cache_key in expired:
            self._records.pop(cache_key, None)


def parse_positive_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default)).strip()
    try:
        parsed = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer.") from exc
    if parsed <= 0:
        raise RuntimeError(f"{name} must be a positive integer.")
    return parsed


def idempotency_ttl_seconds() -> int:
    return parse_positive_int_env("PLC_IDEMPOTENCY_TTL_SEC", 3600)


def idempotency_key_from_request(request: Request) -> Optional[str]:
    raw = request.headers.get("idempotency-key", "").strip()
    return raw or None


def maybe_replay_response(
    request: Request,
    store: InMemoryIdempotencyStore,
    *,
    scope: str,
    fingerprint: str,
    now: Optional[float] = None,
) -> Optional[dict]:
    idempotency_key = idempotency_key_from_request(request)
    if not idempotency_key:
        return None

    timestamp = now if now is not None else time()
    cached = store.get(scope, idempotency_key, idempotency_ttl_seconds(), timestamp)
    if not cached:
        return None

    if cached.fingerprint != fingerprint:
        raise HTTPException(
            status_code=409,
            detail="Idempotency-Key reuse with different request payload.",
        )
    return cached.response_payload


def store_idempotent_response(
    request: Request,
    store: InMemoryIdempotencyStore,
    *,
    scope: str,
    fingerprint: str,
    response_payload: dict,
    now: Optional[float] = None,
) -> None:
    idempotency_key = idempotency_key_from_request(request)
    if not idempotency_key:
        return

    timestamp = now if now is not None else time()
    store.put(scope, idempotency_key, fingerprint, response_payload, timestamp)
