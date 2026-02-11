from __future__ import annotations

import json
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


class FakeDB:
    def __init__(self, lecture_payload: dict | None) -> None:
        self._lecture_payload = lecture_payload

    def fetch_lecture(self, lecture_id: str):
        if not self._lecture_payload:
            return None
        if self._lecture_payload.get("id") != lecture_id:
            return None
        return self._lecture_payload


def test_get_lecture_transcript_success(tmp_path, monkeypatch):
    transcript_path = tmp_path / "transcript.json"
    transcript_path.write_text(
        json.dumps(
            {
                "language": "en",
                "text": "Cell signaling overview.",
                "segments": [
                    {"start": 0.0, "end": 2.0, "text": "Cell signaling overview."}
                ],
            }
        ),
        encoding="utf-8",
    )

    fake_db = FakeDB(
        {
            "id": "lec-1",
            "transcript_path": str(transcript_path),
        }
    )
    monkeypatch.setattr(app_module, "get_database", lambda: fake_db)

    client = TestClient(app_module.app)
    response = client.get("/lectures/lec-1/transcript")

    assert response.status_code == 200
    payload = response.json()
    assert payload["lectureId"] == "lec-1"
    assert payload["language"] == "en"
    assert payload["text"] == "Cell signaling overview."
    assert len(payload["segments"]) == 1


def test_get_lecture_transcript_missing_record(monkeypatch):
    fake_db = FakeDB(None)
    monkeypatch.setattr(app_module, "get_database", lambda: fake_db)

    client = TestClient(app_module.app)
    response = client.get("/lectures/missing/transcript")

    assert response.status_code == 404
    assert response.json()["detail"] == "Lecture not found."


def test_get_lecture_transcript_respects_query_flags(tmp_path, monkeypatch):
    transcript_path = tmp_path / "transcript.json"
    transcript_path.write_text(
        json.dumps(
            {
                "language": "en",
                "text": "Long lecture transcript text",
                "segments": [
                    {"start": 0.0, "end": 1.0, "text": "A"},
                    {"start": 1.0, "end": 2.0, "text": "B"},
                ],
            }
        ),
        encoding="utf-8",
    )

    fake_db = FakeDB({"id": "lec-2", "transcript_path": str(transcript_path)})
    monkeypatch.setattr(app_module, "get_database", lambda: fake_db)

    client = TestClient(app_module.app)
    response = client.get("/lectures/lec-2/transcript?include_text=false&segment_limit=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["text"] == ""
    assert payload["segmentCount"] == 1
    assert len(payload["segments"]) == 1
