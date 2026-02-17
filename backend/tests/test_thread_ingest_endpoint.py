from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

pytest.importorskip("fastapi")
try:
    from fastapi.testclient import TestClient
except RuntimeError as exc:  # pragma: no cover - dependency guard for CI/runtime
    if "httpx" in str(exc):
        TestClient = None
    else:
        raise

if TestClient is None:
    pytestmark = pytest.mark.skip(reason="fastapi.testclient requires httpx")

import backend.app as app_module


def test_root_and_healthz_status_endpoints():
    client = TestClient(app_module.app)

    root_response = client.get("/")
    assert root_response.status_code == 200
    assert root_response.json()["status"] == "ok"

    healthz_response = client.get("/healthz")
    assert healthz_response.status_code == 200
    assert healthz_response.json()["status"] == "ok"


def test_thread_ingest_returns_threads_change_log_and_summary():
    client = TestClient(app_module.app)

    response = client.post(
        "/thread/ingest",
        json={
            "preset": "exam-mode",
            "text": "Today we defined operant conditioning. We discussed how Skinner boxes work and why reinforcement schedules matter.",
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["preset"]["id"] == "exam-mode"
    assert isinstance(payload["threads"], list)
    assert payload["threads"]
    assert "changeLog" in payload
    assert "appliedWeights" in payload["changeLog"]
    assert payload["changeLog"]["splitMergeBehavior"] in {"split", "merge"}
    assert payload["summary"]["threadCount"] == len(payload["threads"])
    assert payload["summary"]["collapsePriority"] in {"what", "how", "when", "where", "who", "why"}


def test_thread_ingest_resolves_human_friendly_preset_name():
    client = TestClient(app_module.app)

    response = client.post(
        "/thread/ingest",
        json={"preset": "📝 Exam Mode", "text": "Definition and process."},
    )

    assert response.status_code == 200
    assert response.json()["preset"]["id"] == "exam-mode"


def test_thread_ingest_rejects_empty_text():
    client = TestClient(app_module.app)

    response = client.post("/thread/ingest", json={"preset": "exam-mode", "text": "   "})

    assert response.status_code == 400
    assert "must not be empty" in response.json()["detail"]
