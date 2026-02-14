from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

pytest.importorskip("fastapi")
try:
    from fastapi.testclient import TestClient
except RuntimeError as exc:  # pragma: no cover
    if "httpx" in str(exc):
        TestClient = None
    else:
        raise

if TestClient is None:
    pytestmark = pytest.mark.skip(reason="fastapi.testclient requires httpx")

import backend.app as app_module


def test_response_includes_generated_request_id():
    client = TestClient(app_module.app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers.get("x-request-id")


def test_response_preserves_incoming_request_id():
    client = TestClient(app_module.app)

    response = client.get("/health", headers={"x-request-id": "req-123"})

    assert response.status_code == 200
    assert response.headers.get("x-request-id") == "req-123"
