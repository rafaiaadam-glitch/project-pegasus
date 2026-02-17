from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

pytest.importorskip("fastapi")
try:
    from fastapi.testclient import TestClient
except RuntimeError as exc:
    if "httpx" in str(exc):
        TestClient = None
    else:
        raise

if TestClient is None:
    pytestmark = pytest.mark.skip(reason="fastapi.testclient requires httpx")

import backend.app as app_module


def test_root_and_healthz_routes() -> None:
    client = TestClient(app_module.app)

    root_response = client.get("/")
    healthz_response = client.get("/healthz")

    assert root_response.status_code == 200
    assert root_response.json()["service"] == "pegasus-api"
    assert healthz_response.status_code == 200
    assert healthz_response.json()["status"] == "ok"


def test_presets_route_returns_dropdown_friendly_payload() -> None:
    client = TestClient(app_module.app)

    response = client.get("/presets")

    assert response.status_code == 200
    payload = response.json()
    assert payload["presets"]
    preset = payload["presets"][0]
    assert set(preset.keys()) == {"id", "name", "description"}


def test_thread_ingest_contract_with_name_resolution() -> None:
    client = TestClient(app_module.app)

    response = client.post(
        "/thread/ingest",
        json={
            "text": "Today we covered operant conditioning, reinforcement schedules, and extinction versus punishment.",
            "preset": "Exam Mode",
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["summary"]
    assert payload["threads"]
    assert payload["preset"]["id"] == "exam-mode"
    assert payload["preset"]["weights"]
    assert payload["changeLog"]
    assert any("Applied weights" in event["detail"] for event in payload["changeLog"])
