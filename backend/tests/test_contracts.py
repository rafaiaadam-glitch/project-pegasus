from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest
from typing import Optional

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


class FakeDB:
    def __init__(self) -> None:
        self.lectures: dict[str, dict] = {}
        self.courses: dict[str, dict] = {}
        self.artifacts: list[dict] = []
        self.exports: list[dict] = []
        self.threads: list[dict] = []
        self.jobs: list[dict] = []

    def migrate(self) -> None:
        return None

    def fetch_lecture(self, lecture_id: str):
        return self.lectures.get(lecture_id)

    def fetch_lectures(
        self,
        course_id: Optional[str] = None,
        status: Optional[str] = None,
        preset_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ):
        rows = list(self.lectures.values())
        if course_id:
            rows = [row for row in rows if row.get("course_id") == course_id]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        if preset_id:
            rows = [row for row in rows if row.get("preset_id") == preset_id]
        rows.sort(key=lambda row: row.get("created_at", ""), reverse=True)
        if offset is not None:
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

    def fetch_threads_for_course(
        self,
        course_id: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ):
        rows = [row for row in self.threads if row.get("course_id") == course_id]
        rows.sort(key=lambda row: row.get("created_at", ""), reverse=True)
        if offset:
            rows = rows[offset:]
        if limit is not None:
            rows = rows[:limit]
        return rows

    def fetch_jobs(
        self,
        lecture_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ):
        rows = list(self.jobs)
        if lecture_id:
            rows = [row for row in rows if row.get("lecture_id") == lecture_id]
        rows.sort(key=lambda row: row.get("created_at", ""), reverse=True)
        if offset:
            rows = rows[offset:]
        if limit is not None:
            rows = rows[:limit]
        return rows

    def count_courses(self) -> int:
        return len(self.courses)

    def count_lectures(
        self,
        course_id: Optional[str] = None,
        status: Optional[str] = None,
        preset_id: Optional[str] = None,
    ) -> int:
        rows = list(self.lectures.values())
        if course_id:
            rows = [row for row in rows if row.get("course_id") == course_id]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        if preset_id:
            rows = [row for row in rows if row.get("preset_id") == preset_id]
        return len(rows)

    def count_jobs(self, lecture_id: Optional[str] = None) -> int:
        if lecture_id:
            return sum(1 for row in self.jobs if row.get("lecture_id") == lecture_id)
        return len(self.jobs)

    def count_artifacts(
        self,
        lecture_id: str,
        artifact_type: Optional[str] = None,
        preset_id: Optional[str] = None,
    ) -> int:
        rows = [row for row in self.artifacts if row["lecture_id"] == lecture_id]
        if artifact_type:
            rows = [row for row in rows if row["artifact_type"] == artifact_type]
        if preset_id:
            rows = [row for row in rows if row["preset_id"] == preset_id]
        return len(rows)

    def count_threads_for_course(self, course_id: str) -> int:
        return sum(1 for row in self.threads if row.get("course_id") == course_id)



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
    assert "pagination" in payload
    assert "artifactPaths" in payload
    assert "exportRecords" in payload
    assert "lecture" in payload
    assert payload["artifacts"]["summary"]["overview"] == "Overview"
    assert payload["artifactPaths"]["summary"] == str(summary_path)
    assert payload["artifacts"]["threads"][0]["id"] == "thread-1"
    assert payload["pagination"] == {
        "limit": None,
        "offset": 0,
        "count": 1,
        "total": 1,
        "hasMore": False,
        "nextOffset": None,
        "prevOffset": None,
    }


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
    fake_db.jobs.append(
        {
            "id": "job-export-1",
            "lecture_id": lecture_id,
            "job_type": "export",
            "status": "queued",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
    )
    fake_db.jobs.append(
        {
            "id": "job-generation-1",
            "lecture_id": lecture_id,
            "job_type": "generation",
            "status": "completed",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
    )
    fake_db.jobs.append(
        {
            "id": "job-transcription-1",
            "lecture_id": lecture_id,
            "job_type": "transcription",
            "status": "completed",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
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
    assert payload["overallStatus"] == "in_progress"
    assert payload["progressPercent"] == 66
    assert payload["currentStage"] == "export"
    assert payload["hasFailedStage"] is False
    assert payload["stages"]["transcription"]["status"] == "completed"
    assert payload["stages"]["generation"]["status"] == "completed"
    assert payload["stages"]["export"]["status"] == "queued"
    assert payload["links"]["summary"] == f"/lectures/{lecture_id}/summary"
    assert payload["links"]["progress"] == f"/lectures/{lecture_id}/progress"
    assert payload["links"]["artifacts"] == f"/lectures/{lecture_id}/artifacts"
    assert payload["links"]["jobs"] == f"/lectures/{lecture_id}/jobs"
    assert payload["links"]["exports"] == f"/exports/{lecture_id}/{{export_type}}"


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
        "status": "uploaded",
        "preset_id": "exam-mode",
        "created_at": "2024-01-01T00:00:00Z",
    }
    fake_db.lectures["lecture-2"] = {
        "id": "lecture-2",
        "course_id": "course-2",
        "title": "Lecture Two",
        "status": "generated",
        "preset_id": "research-mode",
        "created_at": "2024-01-03T00:00:00Z",
    }

    monkeypatch.setattr(app_module, "get_database", lambda: fake_db)
    client = TestClient(app_module.app)

    response = client.get("/courses")
    assert response.status_code == 200
    courses_payload = response.json()
    courses = courses_payload["courses"]
    assert [course["id"] for course in courses] == ["course-2", "course-1"]
    assert courses_payload["pagination"] == {
        "limit": None,
        "offset": 0,
        "count": 2,
        "total": 2,
        "hasMore": False,
        "nextOffset": None,
        "prevOffset": None,
    }

    response = client.get("/courses/course-1")
    assert response.status_code == 200
    assert response.json()["title"] == "Course One"

    response = client.get("/courses/course-1/lectures")
    assert response.status_code == 200
    lecture_payload = response.json()
    assert [lecture["id"] for lecture in lecture_payload["lectures"]] == ["lecture-1"]
    assert lecture_payload["pagination"] == {
        "limit": None,
        "offset": 0,
        "count": 1,
        "total": 1,
        "hasMore": False,
        "nextOffset": None,
        "prevOffset": None,
    }

    response = client.get("/courses/course-2/lectures", params={"status": "generated"})
    assert response.status_code == 200
    filtered_course_lectures = response.json()
    assert [lecture["id"] for lecture in filtered_course_lectures["lectures"]] == ["lecture-2"]
    assert filtered_course_lectures["pagination"] == {
        "limit": None,
        "offset": 0,
        "count": 1,
        "total": 1,
        "hasMore": False,
        "nextOffset": None,
        "prevOffset": None,
    }

    response = client.get("/courses/course-2/lectures", params={"preset_id": "research-mode"})
    assert response.status_code == 200
    filtered_by_preset = response.json()
    assert [lecture["id"] for lecture in filtered_by_preset["lectures"]] == ["lecture-2"]
    assert filtered_by_preset["pagination"]["total"] == 1

    response = client.get("/courses/course-2/lectures", params={"preset_id": "exam-mode"})
    assert response.status_code == 200
    filtered_by_preset_empty = response.json()
    assert filtered_by_preset_empty["lectures"] == []
    assert filtered_by_preset_empty["pagination"]["total"] == 0

    response = client.get("/courses/course-2/lectures", params={"status": "uploaded"})
    assert response.status_code == 200
    filtered_empty = response.json()
    assert filtered_empty["lectures"] == []
    assert filtered_empty["pagination"] == {
        "limit": None,
        "offset": 0,
        "count": 0,
        "total": 0,
        "hasMore": False,
        "nextOffset": None,
        "prevOffset": None,
    }

    missing_course_lectures = client.get("/courses/missing/lectures")
    assert missing_course_lectures.status_code == 404

    response = client.get("/lectures", params={"course_id": "course-2"})
    assert response.status_code == 200
    lecture_listing = response.json()
    assert [lecture["id"] for lecture in lecture_listing["lectures"]] == ["lecture-2"]
    assert lecture_listing["pagination"] == {
        "limit": None,
        "offset": 0,
        "count": 1,
        "total": 1,
        "hasMore": False,
        "nextOffset": None,
        "prevOffset": None,
    }


    response = client.get("/lectures", params={"status": "generated"})
    assert response.status_code == 200
    status_filtered = response.json()
    assert [lecture["id"] for lecture in status_filtered["lectures"]] == ["lecture-2"]
    assert status_filtered["pagination"] == {
        "limit": None,
        "offset": 0,
        "count": 1,
        "total": 1,
        "hasMore": False,
        "nextOffset": None,
        "prevOffset": None,
    }

    response = client.get("/lectures", params={"preset_id": "research-mode"})
    assert response.status_code == 200
    preset_filtered = response.json()
    assert [lecture["id"] for lecture in preset_filtered["lectures"]] == ["lecture-2"]
    assert preset_filtered["pagination"]["total"] == 1

    response = client.get("/lectures", params={"status": "generated", "preset_id": "exam-mode"})
    assert response.status_code == 200
    preset_status_filtered_empty = response.json()
    assert preset_status_filtered_empty["lectures"] == []
    assert preset_status_filtered_empty["pagination"]["total"] == 0

    response = client.get("/lectures", params={"limit": 1})
    assert response.status_code == 200
    limited_listing = response.json()
    assert len(limited_listing["lectures"]) == 1
    assert limited_listing["pagination"] == {
        "limit": 1,
        "offset": 0,
        "count": 1,
        "total": 2,
        "hasMore": True,
        "nextOffset": 1,
        "prevOffset": None,
    }


@pytest.mark.parametrize(
    "path,params",
    [
        ("/courses", {"limit": -1}),
        ("/lectures", {"offset": -1}),
    ],
)
def test_listing_endpoints_reject_negative_pagination(monkeypatch, path, params):
    fake_db = FakeDB()
    monkeypatch.setattr(app_module, "get_database", lambda: fake_db)
    client = TestClient(app_module.app)

    response = client.get(path, params=params)
    assert response.status_code == 422


def test_presets_catalog():
    client = TestClient(app_module.app)

    response = client.get("/presets")
    assert response.status_code == 200
    presets = response.json()["presets"]
    assert len(presets) >= 5
    assert {preset["id"] for preset in presets} >= {
        "exam-mode",
        "concept-map-mode",
        "beginner-mode",
        "neurodivergent-friendly-mode",
        "research-mode",
    }

    response = client.get("/presets/exam-mode")
    assert response.status_code == 200
    payload = response.json()
    assert payload["kind"] == "exam"
    assert "outputProfile" in payload

    response = client.get("/presets/missing-preset")
    assert response.status_code == 404


def test_course_threads_listing(monkeypatch):
    fake_db = FakeDB()
    fake_db.courses["course-1"] = {
        "id": "course-1",
        "title": "Course One",
        "created_at": "2024-01-01T00:00:00Z",
    }
    fake_db.threads = [
        {
            "id": "thread-1",
            "course_id": "course-1",
            "title": "Foundations",
            "summary": "Base concept",
            "status": "foundational",
            "complexity_level": 1,
            "lecture_refs": ["lecture-1"],
            "created_at": "2024-01-02T00:00:00Z",
        },
        {
            "id": "thread-2",
            "course_id": "course-1",
            "title": "Advanced Topic",
            "summary": "Later concept",
            "status": "advanced",
            "complexity_level": 3,
            "lecture_refs": ["lecture-2"],
            "created_at": "2024-01-03T00:00:00Z",
        },
        {
            "id": "thread-3",
            "course_id": "course-2",
            "title": "Other course",
            "summary": "Different",
            "status": "foundational",
            "complexity_level": 2,
            "lecture_refs": ["lecture-9"],
            "created_at": "2024-01-01T00:00:00Z",
        },
    ]

    monkeypatch.setattr(app_module, "get_database", lambda: fake_db)
    client = TestClient(app_module.app)

    response = client.get("/courses/course-1/threads")
    assert response.status_code == 200
    payload = response.json()
    assert payload["courseId"] == "course-1"
    assert [thread["id"] for thread in payload["threads"]] == ["thread-2", "thread-1"]


def test_course_threads_listing_requires_existing_course(monkeypatch):
    fake_db = FakeDB()
    fake_db.threads = [
        {
            "id": "thread-1",
            "course_id": "course-1",
            "title": "Foundations",
            "summary": "Base concept",
            "status": "foundational",
            "complexity_level": 1,
            "lecture_refs": ["lecture-1"],
            "created_at": "2024-01-02T00:00:00Z",
        }
    ]

    monkeypatch.setattr(app_module, "get_database", lambda: fake_db)
    client = TestClient(app_module.app)

    response = client.get("/courses/missing-course/threads")
    assert response.status_code == 404
    assert response.json() == {"detail": "Course not found."}


def test_course_threads_listing_supports_pagination(monkeypatch):
    fake_db = FakeDB()
    fake_db.courses["course-1"] = {
        "id": "course-1",
        "title": "Course One",
        "created_at": "2024-01-01T00:00:00Z",
    }
    fake_db.threads = [
        {
            "id": "thread-1",
            "course_id": "course-1",
            "title": "Foundations",
            "summary": "Base concept",
            "status": "foundational",
            "complexity_level": 1,
            "lecture_refs": ["lecture-1"],
            "created_at": "2024-01-02T00:00:00Z",
        },
        {
            "id": "thread-2",
            "course_id": "course-1",
            "title": "Advanced Topic",
            "summary": "Later concept",
            "status": "advanced",
            "complexity_level": 3,
            "lecture_refs": ["lecture-2"],
            "created_at": "2024-01-03T00:00:00Z",
        },
        {
            "id": "thread-3",
            "course_id": "course-1",
            "title": "Applied Topic",
            "summary": "Even later concept",
            "status": "advanced",
            "complexity_level": 4,
            "lecture_refs": ["lecture-3"],
            "created_at": "2024-01-04T00:00:00Z",
        },
    ]

    monkeypatch.setattr(app_module, "get_database", lambda: fake_db)
    client = TestClient(app_module.app)

    response = client.get("/courses/course-1/threads", params={"limit": 1, "offset": 1})
    assert response.status_code == 200
    payload = response.json()
    assert payload["courseId"] == "course-1"
    assert [thread["id"] for thread in payload["threads"]] == ["thread-2"]
    assert payload["pagination"] == {
        "limit": 1,
        "offset": 1,
        "count": 1,
        "total": 3,
        "hasMore": True,
        "nextOffset": 2,
        "prevOffset": 0,
    }


def test_lecture_jobs_listing_includes_pagination(monkeypatch):
    fake_db = FakeDB()
    lecture_id = "lecture-1"
    fake_db.lectures[lecture_id] = {
        "id": lecture_id,
        "course_id": "course-1",
        "title": "Lecture One",
        "created_at": "2024-01-01T00:00:00Z",
    }
    fake_db.jobs.extend(
        [
            {
                "id": "job-1",
                "lecture_id": lecture_id,
                "job_type": "transcription",
                "status": "completed",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            },
            {
                "id": "job-2",
                "lecture_id": lecture_id,
                "job_type": "generation",
                "status": "queued",
                "created_at": "2024-01-02T00:00:00Z",
                "updated_at": "2024-01-02T00:00:00Z",
            },
        ]
    )

    monkeypatch.setattr(app_module, "get_database", lambda: fake_db)
    client = TestClient(app_module.app)

    response = client.get(f"/lectures/{lecture_id}/jobs", params={"limit": 1, "offset": 0})
    assert response.status_code == 200
    payload = response.json()
    assert [job["id"] for job in payload["jobs"]] == ["job-2"]
    assert payload["pagination"] == {
        "limit": 1,
        "offset": 0,
        "count": 1,
        "total": 2,
        "hasMore": True,
        "nextOffset": 1,
        "prevOffset": None,
    }


def test_course_threads_listing_rejects_negative_pagination(monkeypatch):
    fake_db = FakeDB()
    fake_db.courses["course-1"] = {
        "id": "course-1",
        "title": "Course One",
        "created_at": "2024-01-01T00:00:00Z",
    }

    monkeypatch.setattr(app_module, "get_database", lambda: fake_db)
    client = TestClient(app_module.app)

    response = client.get("/courses/course-1/threads", params={"offset": -1})
    assert response.status_code == 422


def test_course_progress_rollup(monkeypatch):
    fake_db = FakeDB()
    fake_db.courses["course-1"] = {
        "id": "course-1",
        "title": "Course One",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    fake_db.lectures["lecture-1"] = {
        "id": "lecture-1",
        "course_id": "course-1",
        "title": "Lecture One",
        "status": "processing",
        "created_at": "2024-01-01T00:00:00Z",
    }
    fake_db.lectures["lecture-2"] = {
        "id": "lecture-2",
        "course_id": "course-1",
        "title": "Lecture Two",
        "status": "failed",
        "created_at": "2024-01-02T00:00:00Z",
    }
    fake_db.jobs.extend(
        [
            {
                "id": "job-lecture-1-export",
                "lecture_id": "lecture-1",
                "job_type": "export",
                "status": "queued",
                "created_at": "2024-01-03T00:00:00Z",
            },
            {
                "id": "job-lecture-1-generation",
                "lecture_id": "lecture-1",
                "job_type": "generation",
                "status": "completed",
                "created_at": "2024-01-02T00:00:00Z",
            },
            {
                "id": "job-lecture-1-transcription",
                "lecture_id": "lecture-1",
                "job_type": "transcription",
                "status": "completed",
                "created_at": "2024-01-01T00:00:00Z",
            },
            {
                "id": "job-lecture-2-generation",
                "lecture_id": "lecture-2",
                "job_type": "generation",
                "status": "failed",
                "created_at": "2024-01-04T00:00:00Z",
            },
            {
                "id": "job-lecture-2-transcription",
                "lecture_id": "lecture-2",
                "job_type": "transcription",
                "status": "completed",
                "created_at": "2024-01-03T00:00:00Z",
            },
        ]
    )

    monkeypatch.setattr(app_module, "get_database", lambda: fake_db)
    client = TestClient(app_module.app)

    response = client.get("/courses/course-1/progress")
    assert response.status_code == 200
    payload = response.json()

    assert payload["courseId"] == "course-1"
    assert payload["lectureCount"] == 2
    assert payload["completedLectureCount"] == 0
    assert payload["failedLectureCount"] == 1
    assert payload["inProgressLectureCount"] == 1
    assert payload["notStartedLectureCount"] == 0
    assert payload["progressPercent"] == 50
    assert payload["latestActivityAt"] == "2024-01-04T00:00:00Z"
    assert [row["lectureId"] for row in payload["lectures"]] == ["lecture-2", "lecture-1"]
    assert payload["lectures"][0]["overallStatus"] == "failed"
    assert payload["lectures"][0]["stageCount"] == 3
    assert payload["lectures"][0]["completedStageCount"] == 1
    assert payload["lectures"][0]["currentStage"] == "generation"
    assert payload["lectures"][1]["completedStageCount"] == 2
    assert payload["lectures"][1]["currentStage"] == "export"
    assert payload["lectures"][0]["hasFailedStage"] is True
    assert payload["lectures"][0]["stageStatuses"]["generation"] == "failed"
    assert payload["lectures"][1]["stageStatuses"]["export"] == "queued"
    assert payload["lectures"][0]["links"]["summary"] == "/lectures/lecture-2/summary"
    assert payload["lectures"][0]["links"]["progress"] == "/lectures/lecture-2/progress"
    assert payload["lectures"][0]["links"]["artifacts"] == "/lectures/lecture-2/artifacts"
    assert payload["lectures"][0]["links"]["jobs"] == "/lectures/lecture-2/jobs"


def test_course_progress_summary_without_lectures(monkeypatch):
    fake_db = FakeDB()
    fake_db.courses["course-1"] = {
        "id": "course-1",
        "title": "Course One",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    fake_db.lectures["lecture-1"] = {
        "id": "lecture-1",
        "course_id": "course-1",
        "title": "Lecture One",
        "status": "uploaded",
        "preset_id": "exam-mode",
        "created_at": "2024-01-01T00:00:00Z",
    }

    monkeypatch.setattr(app_module, "get_database", lambda: fake_db)
    client = TestClient(app_module.app)

    response = client.get("/courses/course-1/progress", params={"include_lectures": "false"})
    assert response.status_code == 200
    payload = response.json()

    assert payload["overallStatus"] == "not_started"
    assert payload["lectureCount"] == 1
    assert payload["completedLectureCount"] == 0
    assert payload["failedLectureCount"] == 0
    assert payload["inProgressLectureCount"] == 0
    assert payload["notStartedLectureCount"] == 1
    assert payload["progressPercent"] == 0
    assert payload["latestActivityAt"] == "2024-01-01T00:00:00Z"
    assert "lectures" not in payload


def test_course_progress_missing_course(monkeypatch):
    fake_db = FakeDB()
    monkeypatch.setattr(app_module, "get_database", lambda: fake_db)
    client = TestClient(app_module.app)

    response = client.get("/courses/missing/progress")
    assert response.status_code == 404
    assert response.json()["detail"] == "Course not found."




def test_listing_endpoints_reject_invalid_preset_id(monkeypatch):
    fake_db = FakeDB()
    fake_db.courses["course-1"] = {
        "id": "course-1",
        "title": "Course One",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    fake_db.lectures["lecture-1"] = {
        "id": "lecture-1",
        "course_id": "course-1",
        "preset_id": "exam-mode",
        "status": "uploaded",
        "title": "Lecture One",
        "created_at": "2024-01-01T00:00:00Z",
    }

    monkeypatch.setattr(app_module, "get_database", lambda: fake_db)
    client = TestClient(app_module.app)

    global_listing = client.get("/lectures", params={"preset_id": "invalid-preset"})
    assert global_listing.status_code == 400
    assert global_listing.json()["detail"] == "Invalid preset_id."

    course_listing = client.get(
        "/courses/course-1/lectures",
        params={"preset_id": "invalid-preset"},
    )
    assert course_listing.status_code == 400
    assert course_listing.json()["detail"] == "Invalid preset_id."

    artifact_listing = client.get(
        "/lectures/lecture-1/artifacts",
        params={"preset_id": "invalid-preset"},
    )
    assert artifact_listing.status_code == 400
    assert artifact_listing.json()["detail"] == "Invalid preset_id."

def test_generate_rejects_invalid_preset_id():
    client = TestClient(app_module.app)

    response = client.post(
        "/lectures/lecture-001/generate",
        json={"course_id": "course-001", "preset_id": "invalid-preset"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid preset_id."


def test_generate_rejects_missing_lecture(monkeypatch):
    fake_db = FakeDB()
    monkeypatch.setattr(app_module, "get_database", lambda: fake_db)
    client = TestClient(app_module.app)

    response = client.post(
        "/lectures/lecture-missing/generate",
        json={"course_id": "course-001", "preset_id": "exam-mode"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Lecture not found."


def test_generate_rejects_missing_course(monkeypatch):
    fake_db = FakeDB()
    fake_db.lectures["lecture-001"] = {
        "id": "lecture-001",
        "course_id": "course-missing",
        "preset_id": "exam-mode",
        "title": "Lecture",
    }
    monkeypatch.setattr(app_module, "get_database", lambda: fake_db)
    client = TestClient(app_module.app)

    response = client.post(
        "/lectures/lecture-001/generate",
        json={"preset_id": "exam-mode"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Course not found."


def test_generate_rejects_course_mismatch(monkeypatch):
    fake_db = FakeDB()
    fake_db.lectures["lecture-001"] = {
        "id": "lecture-001",
        "course_id": "course-stored",
        "preset_id": "exam-mode",
        "title": "Lecture",
    }
    monkeypatch.setattr(app_module, "get_database", lambda: fake_db)
    client = TestClient(app_module.app)

    response = client.post(
        "/lectures/lecture-001/generate",
        json={"course_id": "course-request", "preset_id": "exam-mode"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "course_id does not match lecture."


def test_generate_rejects_preset_mismatch(monkeypatch):
    fake_db = FakeDB()
    fake_db.lectures["lecture-001"] = {
        "id": "lecture-001",
        "course_id": "course-001",
        "preset_id": "exam-mode",
        "title": "Lecture",
    }
    monkeypatch.setattr(app_module, "get_database", lambda: fake_db)
    client = TestClient(app_module.app)

    response = client.post(
        "/lectures/lecture-001/generate",
        json={"course_id": "course-001", "preset_id": "research-mode"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "preset_id does not match lecture."


def test_get_lecture_details(monkeypatch):
    fake_db = FakeDB()
    fake_db.lectures["lecture-42"] = {
        "id": "lecture-42",
        "course_id": "course-1",
        "title": "Lecture Forty Two",
        "status": "uploaded",
        "created_at": "2024-01-01T00:00:00Z",
    }

    monkeypatch.setattr(app_module, "get_database", lambda: fake_db)
    client = TestClient(app_module.app)

    response = client.get("/lectures/lecture-42")
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == "lecture-42"
    assert payload["title"] == "Lecture Forty Two"

    missing = client.get("/lectures/missing")
    assert missing.status_code == 404


def test_list_lecture_jobs_contract(monkeypatch):
    fake_db = FakeDB()
    lecture_id = "lecture-007"
    fake_db.lectures[lecture_id] = {
        "id": lecture_id,
        "title": "Lecture Seven",
        "status": "uploaded",
    }
    fake_db.jobs.append(
        {
            "id": "job-2",
            "lecture_id": lecture_id,
            "job_type": "generation",
            "status": "completed",
            "result": {"ok": True},
            "error": None,
            "created_at": "2024-01-02T00:00:00Z",
            "updated_at": "2024-01-02T00:01:00Z",
        }
    )
    fake_db.jobs.append(
        {
            "id": "job-1",
            "lecture_id": lecture_id,
            "job_type": "transcription",
            "status": "failed",
            "result": None,
            "error": "boom",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:01:00Z",
        }
    )

    monkeypatch.setattr(app_module, "get_database", lambda: fake_db)
    client = TestClient(app_module.app)

    response = client.get(f"/lectures/{lecture_id}/jobs")
    assert response.status_code == 200
    payload = response.json()
    assert payload["lectureId"] == lecture_id
    assert [job["id"] for job in payload["jobs"]] == ["job-2", "job-1"]
    assert payload["jobs"][0]["jobType"] == "generation"

    missing = client.get("/lectures/missing/jobs")
    assert missing.status_code == 404


def test_lecture_progress_contract(monkeypatch):
    fake_db = FakeDB()
    lecture_id = "lecture-011"
    fake_db.lectures[lecture_id] = {
        "id": lecture_id,
        "title": "Lecture Eleven",
        "status": "processing",
    }
    fake_db.jobs.append(
        {
            "id": "job-export-1",
            "lecture_id": lecture_id,
            "job_type": "export",
            "status": "queued",
            "result": None,
            "error": None,
            "created_at": "2024-01-04T00:00:00Z",
            "updated_at": "2024-01-04T00:00:00Z",
        }
    )
    fake_db.jobs.append(
        {
            "id": "job-generation-1",
            "lecture_id": lecture_id,
            "job_type": "generation",
            "status": "completed",
            "result": {"artifactCount": 5},
            "error": None,
            "created_at": "2024-01-03T00:00:00Z",
            "updated_at": "2024-01-03T00:01:00Z",
        }
    )
    fake_db.jobs.append(
        {
            "id": "job-transcription-1",
            "lecture_id": lecture_id,
            "job_type": "transcription",
            "status": "completed",
            "result": {"transcriptPath": "storage/transcripts/lecture-011.json"},
            "error": None,
            "created_at": "2024-01-02T00:00:00Z",
            "updated_at": "2024-01-02T00:01:00Z",
        }
    )

    monkeypatch.setattr(app_module, "get_database", lambda: fake_db)
    client = TestClient(app_module.app)

    response = client.get(f"/lectures/{lecture_id}/progress")
    assert response.status_code == 200
    payload = response.json()

    assert payload["lectureId"] == lecture_id
    assert payload["lectureStatus"] == "processing"
    assert payload["overallStatus"] == "in_progress"
    assert payload["stageCount"] == 3
    assert payload["completedStageCount"] == 2
    assert payload["progressPercent"] == 66
    assert payload["currentStage"] == "export"
    assert payload["hasFailedStage"] is False
    assert payload["stages"]["transcription"]["status"] == "completed"
    assert payload["stages"]["generation"]["status"] == "completed"
    assert payload["stages"]["export"]["status"] == "queued"
    assert payload["links"]["summary"] == f"/lectures/{lecture_id}/summary"
    assert payload["links"]["progress"] == f"/lectures/{lecture_id}/progress"
    assert payload["links"]["artifacts"] == f"/lectures/{lecture_id}/artifacts"
    assert payload["links"]["jobs"] == f"/lectures/{lecture_id}/jobs"

    missing = client.get("/lectures/missing/progress")
    assert missing.status_code == 404


def test_lecture_progress_contract_transcription_queued_is_in_progress(monkeypatch):
    fake_db = FakeDB()
    lecture_id = "lecture-011b"
    fake_db.lectures[lecture_id] = {
        "id": lecture_id,
        "title": "Lecture Eleven B",
        "status": "processing",
    }
    fake_db.jobs.append(
        {
            "id": "job-transcription-queued",
            "lecture_id": lecture_id,
            "job_type": "transcription",
            "status": "queued",
            "result": None,
            "error": None,
            "created_at": "2024-01-02T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z",
        }
    )

    monkeypatch.setattr(app_module, "get_database", lambda: fake_db)
    client = TestClient(app_module.app)

    response = client.get(f"/lectures/{lecture_id}/progress")
    assert response.status_code == 200
    payload = response.json()

    assert payload["overallStatus"] == "in_progress"
    assert payload["completedStageCount"] == 0
    assert payload["progressPercent"] == 0
    assert payload["currentStage"] == "transcription"
    assert payload["stages"]["transcription"]["status"] == "queued"


def test_lecture_progress_contract_failed_stage(monkeypatch):
    fake_db = FakeDB()
    lecture_id = "lecture-012"
    fake_db.lectures[lecture_id] = {
        "id": lecture_id,
        "title": "Lecture Twelve",
        "status": "failed",
    }
    fake_db.jobs.append(
        {
            "id": "job-generation-failed",
            "lecture_id": lecture_id,
            "job_type": "generation",
            "status": "failed",
            "result": None,
            "error": "schema validation failed",
            "created_at": "2024-01-03T00:00:00Z",
            "updated_at": "2024-01-03T00:01:00Z",
        }
    )
    fake_db.jobs.append(
        {
            "id": "job-transcription-complete",
            "lecture_id": lecture_id,
            "job_type": "transcription",
            "status": "completed",
            "result": {"transcriptPath": "storage/transcripts/lecture-012.json"},
            "error": None,
            "created_at": "2024-01-02T00:00:00Z",
            "updated_at": "2024-01-02T00:01:00Z",
        }
    )

    monkeypatch.setattr(app_module, "get_database", lambda: fake_db)
    client = TestClient(app_module.app)

    response = client.get(f"/lectures/{lecture_id}/progress")
    assert response.status_code == 200
    payload = response.json()

    assert payload["overallStatus"] == "failed"
    assert payload["progressPercent"] == 33
    assert payload["currentStage"] == "generation"
    assert payload["hasFailedStage"] is True
    assert payload["links"]["summary"] == f"/lectures/{lecture_id}/summary"
    assert payload["links"]["progress"] == f"/lectures/{lecture_id}/progress"
