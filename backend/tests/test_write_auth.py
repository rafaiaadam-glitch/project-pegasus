from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

pytest.importorskip("fastapi")

try:
    from fastapi.testclient import TestClient
except RuntimeError:  # pragma: no cover - environment-specific import guard
    TestClient = None

if TestClient is None:
    pytestmark = pytest.mark.skip(reason="fastapi.testclient requires httpx")

import backend.app as app_module


@pytest.mark.parametrize(
    "endpoint,request_kwargs",
    [
        ("/lectures/lecture-001/transcribe", {}),
        ("/lectures/lecture-001/generate", {"json": {}}),
        ("/lectures/lecture-001/export", {}),
    ],
)
def test_write_endpoints_require_bearer_token_when_enabled(monkeypatch, endpoint, request_kwargs):
    monkeypatch.setenv("PLC_WRITE_API_TOKEN", "secret-token")
    client = TestClient(app_module.app)

    response = client.post(endpoint, **request_kwargs)

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing or invalid Authorization header."


@pytest.mark.parametrize(
    "endpoint,request_kwargs",
    [
        ("/lectures/lecture-001/transcribe", {}),
        ("/lectures/lecture-001/generate", {"json": {}}),
        ("/lectures/lecture-001/export", {}),
    ],
)
def test_write_endpoints_reject_invalid_token_when_enabled(monkeypatch, endpoint, request_kwargs):
    monkeypatch.setenv("PLC_WRITE_API_TOKEN", "secret-token")
    client = TestClient(app_module.app)

    response = client.post(
        endpoint,
        headers={"Authorization": "Bearer wrong-token"},
        **request_kwargs,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid API token."


def test_write_auth_allows_request_when_token_matches(monkeypatch):
    monkeypatch.setenv("PLC_WRITE_API_TOKEN", "secret-token")
    client = TestClient(app_module.app)

    response = client.post(
        "/lectures/lecture-001/transcribe",
        headers={"Authorization": "Bearer secret-token"},
    )

    # Authorization passes; downstream route logic now executes.
    assert response.status_code == 404
    assert response.json()["detail"] == "Audio not found for lecture."
