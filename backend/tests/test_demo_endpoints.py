from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

pytest.importorskip("fastapi")

try:
    from fastapi.testclient import TestClient
except RuntimeError:
    TestClient = None

if TestClient is None:
    pytestmark = pytest.mark.skip(reason="fastapi.testclient requires httpx")

import backend.app as app_module


@pytest.fixture(autouse=True)
def storage_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_MODE", "local")
    monkeypatch.setenv("PLC_STORAGE_DIR", str(tmp_path))


def test_demo_root_health_and_presets():
    client = TestClient(app_module.app)

    root_response = client.get("/")
    assert root_response.status_code == 200
    assert "Pegasus Ingest Demo" in root_response.text

    health_response = client.get("/healthz")
    assert health_response.status_code == 200
    assert health_response.json()["status"] == "ok"

    presets_response = client.get("/presets")
    assert presets_response.status_code == 200
    assert "presets" in presets_response.json()


def test_thread_ingest_and_session_lookup():
    client = TestClient(app_module.app)

    ingest_response = client.post(
        "/thread/ingest",
        json={
            "preset": "Exam Mode",
            "text": "Today we covered reinforcement schedules, extinction, and operant conditioning.",
        },
    )
    assert ingest_response.status_code == 200
    payload = ingest_response.json()
    assert payload["summary"]
    assert payload["threads"]
    assert payload["changeLog"]

    session_response = client.get(f"/sessions/{payload['session_id']}")
    assert session_response.status_code == 200
    session_payload = session_response.json()
    assert session_payload["response"]["session_id"] == payload["session_id"]
    assert session_payload["request"]["preset"] == "Exam Mode"


def test_thread_ingest_rejects_unknown_preset():
    client = TestClient(app_module.app)
    response = client.post(
        "/thread/ingest",
        json={"preset": "Not Real", "text": "content"},
    )
    assert response.status_code == 400
