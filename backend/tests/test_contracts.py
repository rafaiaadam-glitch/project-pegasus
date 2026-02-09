from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest
from typing import Optional

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

import backend.app as app_module


class FakeDB:
    def __init__(self) -> None:
        self.lectures: dict[str, dict] = {}
        self.courses: dict[str, dict] = {}
        self.artifacts: list[dict] = []
        self.exports: list[dict] = []
        self.threads: list[dict] = []

    def migrate(self) -> None:
        return None

    def fetch_lecture(self, lecture_id: str):
        return self.lectures.get(lecture_id)

    def fetch_lectures(
        self,
        course_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ):
        rows = list(self.lectures.values())
        if course_id:
            rows = [row for row in rows if row.get("course_id") == course_id]
        rows.sort(key=lambda row: row.get("created_at", ""), reverse=True)
        if offset:
            rows = rows[offset:]
        if limit is not None:
            rows = rows[:limit]
        return rows

    def fetch_course(self, course_id: str):
        return self.courses.get(course_id)

    def fetch_courses(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ):
        rows = list(self.courses.values())
        rows.sort(key=lambda row: row.get("created_at", ""), reverse=True)
        if offset:
            rows = rows[offset:]
        if limit is not None:
            rows = rows[:limit]
        return rows

    def fetch_artifacts(
        self,
        lecture_id: str,
        artifact_type: Optional[str] = None,
        preset_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ):
        rows = [row for row in self.artifacts if row["lecture_id"] == lecture_id]
        if artifact_type:
            rows = [row for row in rows if row["artifact_type"] == artifact_type]
        if preset_id:
            rows = [row for row in rows if row["preset_id"] == preset_id]
        if offset:
            rows = rows[offset:]
        if limit is not None:
            rows = rows[:limit]
        return rows

    def fetch_exports(self, lecture_id: str):
        return [row for row in self.exports if row["lecture_id"] == lecture_id]

    def fetch_threads(self, lecture_id: str):
        return [row for row in getattr(self, "threads", []) if lecture_id in row.get("lecture_refs", [])]


def test_artifacts_contract(monkeypatch, tmp_path):
    fake_db = FakeDB()
    lecture_id = "lecture-001"
    summary_path = tmp_path / "summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "id": "summary-1",
                "artifactType": "summary",
                "overview": "Overview",
                "sections": [{"title": "Intro", "bullets": ["Point"]}],
            }
        ),
        encoding="utf-8",
    )
    fake_db.lectures[lecture_id] = {
        "id": lecture_id,
        "title": "Lecture 1",
        "status": "generated",
    }
    fake_db.artifacts.append(
        {
            "id": "summary-1",
            "lecture_id": lecture_id,
            "course_id": "course-001",
            "preset_id": "exam-mode",
            "artifact_type": "summary",
            "storage_path": str(summary_path),
        }
    )
    fake_db.threads.append(
        {
            "id": "thread-1",
            "course_id": "course-001",
            "title": "Core Thread",
            "summary": "Summary",
            "status": "foundational",
            "complexity_level": 1,
            "lecture_refs": [lecture_id],
            "created_at": "now",
        }
    )
    fake_db.exports.append(
        {
            "id": "lecture-001-markdown",
            "lecture_id": lecture_id,
            "export_type": "markdown",
            "storage_path": str(tmp_path / "lecture-001.md"),
        }
    )

    monkeypatch.setattr(app_module, "get_database", lambda: fake_db)
    client = TestClient(app_module.app)

    response = client.get(f"/lectures/{lecture_id}/artifacts")
    assert response.status_code == 200
    payload = response.json()

    assert payload["lectureId"] == lecture_id
    assert "artifacts" in payload
    assert "artifactRecords" in payload
    assert "artifactPaths" in payload
    assert "exportRecords" in payload
    assert "lecture" in payload
    assert payload["artifacts"]["summary"]["overview"] == "Overview"
    assert payload["artifactPaths"]["summary"] == str(summary_path)
    assert payload["artifacts"]["threads"][0]["id"] == "thread-1"


def test_summary_contract(monkeypatch):
    fake_db = FakeDB()
    lecture_id = "lecture-002"
    fake_db.lectures[lecture_id] = {
        "id": lecture_id,
        "title": "Lecture 2",
        "status": "uploaded",
    }
    fake_db.artifacts.append(
        {
            "id": "summary-2",
            "lecture_id": lecture_id,
            "course_id": "course-001",
            "preset_id": "exam-mode",
            "artifact_type": "summary",
            "storage_path": "s3://bucket/summary.json",
        }
    )
    fake_db.exports.append(
        {
            "id": "lecture-002-pdf",
            "lecture_id": lecture_id,
            "export_type": "pdf",
            "storage_path": "s3://bucket/lecture-002.pdf",
        }
    )

    monkeypatch.setattr(app_module, "get_database", lambda: fake_db)
    client = TestClient(app_module.app)

    response = client.get(f"/lectures/{lecture_id}/summary")
    assert response.status_code == 200
    payload = response.json()

    assert payload["lecture"]["id"] == lecture_id
    assert payload["artifactCount"] == 1
    assert payload["exportCount"] == 1
    assert payload["artifactTypes"] == ["summary"]
    assert payload["exportTypes"] == ["pdf"]
    assert "links" in payload


def test_course_and_lecture_listings(monkeypatch):
    fake_db = FakeDB()
    fake_db.courses["course-1"] = {
        "id": "course-1",
        "title": "Course One",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    fake_db.courses["course-2"] = {
        "id": "course-2",
        "title": "Course Two",
        "created_at": "2024-01-02T00:00:00Z",
        "updated_at": "2024-01-02T00:00:00Z",
    }
    fake_db.lectures["lecture-1"] = {
        "id": "lecture-1",
        "course_id": "course-1",
        "title": "Lecture One",
        "created_at": "2024-01-01T00:00:00Z",
    }
    fake_db.lectures["lecture-2"] = {
        "id": "lecture-2",
        "course_id": "course-2",
        "title": "Lecture Two",
        "created_at": "2024-01-03T00:00:00Z",
    }

    monkeypatch.setattr(app_module, "get_database", lambda: fake_db)
    client = TestClient(app_module.app)

    response = client.get("/courses")
    assert response.status_code == 200
    courses = response.json()["courses"]
    assert [course["id"] for course in courses] == ["course-2", "course-1"]

    response = client.get("/courses/course-1")
    assert response.status_code == 200
    assert response.json()["title"] == "Course One"

    response = client.get("/courses/course-1/lectures")
    assert response.status_code == 200
    assert [lecture["id"] for lecture in response.json()["lectures"]] == ["lecture-1"]

    response = client.get("/lectures", params={"course_id": "course-2"})
    assert response.status_code == 200
    assert [lecture["id"] for lecture in response.json()["lectures"]] == ["lecture-2"]

    response = client.get("/lectures", params={"limit": 1})
    assert response.status_code == 200
    assert len(response.json()["lectures"]) == 1
