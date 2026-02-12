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


class FakeDB:
    def __init__(self) -> None:
        self.lectures = {
            "lecture-1": {
                "id": "lecture-1",
                "audio_path": "/tmp/audio.mp3",
                "transcript_path": "/tmp/transcript.json",
            }
        }
        self.artifacts = [
            {
                "lecture_id": "lecture-1",
                "artifact_type": "summary",
                "storage_path": "/tmp/summary.json",
            }
        ]
        self.exports = [
            {
                "lecture_id": "lecture-1",
                "export_type": "markdown",
                "storage_path": "s3://bucket/exports/lecture-1.md",
            }
        ]

    def fetch_lecture(self, lecture_id: str):
        return self.lectures.get(lecture_id)

    def fetch_artifacts(self, lecture_id: str, **_kwargs):
        return [row for row in self.artifacts if row["lecture_id"] == lecture_id]

    def fetch_exports(self, lecture_id: str):
        return [row for row in self.exports if row["lecture_id"] == lecture_id]


def test_integrity_reports_missing_and_present_paths(monkeypatch):
    fake_db = FakeDB()

    monkeypatch.setattr(app_module, "get_database", lambda: fake_db)
    monkeypatch.setattr(
        app_module,
        "storage_path_exists",
        lambda path: path in {"/tmp/audio.mp3", "s3://bucket/exports/lecture-1.md"},
    )

    client = TestClient(app_module.app)
    response = client.get("/lectures/lecture-1/integrity")

    assert response.status_code == 200
    payload = response.json()
    assert payload["lectureId"] == "lecture-1"
    assert payload["checkCount"] == 4
    assert payload["missingCount"] == 2
    assert payload["status"] == "degraded"

    by_kind = {row["kind"]: row for row in payload["checks"]}
    assert by_kind["audio"]["exists"] is True
    assert by_kind["transcript"]["exists"] is False
    assert by_kind["artifact:summary"]["exists"] is False
    assert by_kind["export:markdown"]["exists"] is True


def test_integrity_returns_404_for_unknown_lecture(monkeypatch):
    fake_db = FakeDB()
    monkeypatch.setattr(app_module, "get_database", lambda: fake_db)

    client = TestClient(app_module.app)
    response = client.get("/lectures/unknown/integrity")

    assert response.status_code == 404
