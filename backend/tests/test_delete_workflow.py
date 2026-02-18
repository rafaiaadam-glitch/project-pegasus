from __future__ import annotations

from pathlib import Path
import sys
from typing import Optional

from starlette.requests import Request

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

import backend.app as app_module


class FakeDB:
    def __init__(self) -> None:
        self.courses: dict[str, dict] = {}
        self.lectures: dict[str, dict] = {}
        self.artifacts: list[dict] = []
        self.exports: list[dict] = []
        self.threads: dict[str, dict] = {}
        self.deletion_audit_events: list[dict] = []

    def fetch_course(self, course_id: str):
        return self.courses.get(course_id)

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
        if offset:
            rows = rows[offset:]
        if limit is not None:
            rows = rows[:limit]
        return rows

    def fetch_lecture(self, lecture_id: str):
        return self.lectures.get(lecture_id)

    def fetch_artifacts(self, lecture_id: str, **_kwargs):
        return [row for row in self.artifacts if row.get("lecture_id") == lecture_id]

    def fetch_exports(self, lecture_id: str):
        return [row for row in self.exports if row.get("lecture_id") == lecture_id]

    def fetch_threads(self, lecture_id: str):
        return [
            row
            for row in self.threads.values()
            if lecture_id in (row.get("lecture_refs") or [])
        ]

    def update_thread_lecture_refs(self, thread_id: str, lecture_refs: list[str]) -> None:
        self.threads[thread_id]["lecture_refs"] = lecture_refs

    def delete_thread(self, thread_id: str) -> None:
        self.threads.pop(thread_id, None)

    def delete_lecture_records(self, lecture_id: str) -> dict[str, int]:
        artifacts_before = len(self.artifacts)
        exports_before = len(self.exports)
        self.artifacts = [row for row in self.artifacts if row.get("lecture_id") != lecture_id]
        self.exports = [row for row in self.exports if row.get("lecture_id") != lecture_id]
        artifacts_deleted = artifacts_before - len(self.artifacts)
        exports_deleted = exports_before - len(self.exports)
        lecture_deleted = 1 if self.lectures.pop(lecture_id, None) else 0
        return {
            "artifacts": artifacts_deleted,
            "exports": exports_deleted,
            "jobs": 0,
            "lectures": lecture_deleted,
        }

    def delete_course(self, course_id: str) -> int:
        return 1 if self.courses.pop(course_id, None) else 0

    def create_deletion_audit_event(self, payload: dict) -> None:
        self.deletion_audit_events.append(payload)

    def fetch_deletion_audit_events(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ):
        rows = list(self.deletion_audit_events)
        if entity_type:
            rows = [row for row in rows if row.get("entity_type") == entity_type]
        if entity_id:
            rows = [row for row in rows if row.get("entity_id") == entity_id]
        if offset:
            rows = rows[offset:]
        if limit is not None:
            rows = rows[:limit]
        return rows

    def count_deletion_audit_events(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
    ) -> int:
        return len(
            self.fetch_deletion_audit_events(
                entity_type=entity_type,
                entity_id=entity_id,
            )
        )


def _request(headers: Optional[dict[str, str]] = None) -> Request:
    header_items = []
    for key, value in (headers or {}).items():
        header_items.append((key.lower().encode("latin-1"), value.encode("latin-1")))

    request = Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/",
            "raw_path": b"/",
            "query_string": b"",
            "headers": header_items,
            "client": ("127.0.0.1", 9999),
            "server": ("test", 80),
        }
    )
    request.state.request_id = "req-123"
    return request


def test_delete_single_lecture_removes_records_and_updates_threads(monkeypatch, tmp_path):
    fake_db = FakeDB()
    fake_db.courses["course-1"] = {"id": "course-1", "title": "Course"}
    fake_db.lectures["lecture-1"] = {
        "id": "lecture-1",
        "course_id": "course-1",
        "audio_path": str(tmp_path / "audio-1.mp3"),
        "transcript_path": str(tmp_path / "transcript-1.json"),
    }
    fake_db.artifacts.append(
        {"id": "a1", "lecture_id": "lecture-1", "storage_path": str(tmp_path / "artifact-1.json")}
    )
    fake_db.exports.append(
        {"id": "e1", "lecture_id": "lecture-1", "storage_path": str(tmp_path / "export-1.pdf")}
    )
    fake_db.threads["thread-1"] = {
        "id": "thread-1",
        "lecture_refs": ["lecture-1", "lecture-2"],
    }

    metadata_dir = tmp_path / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    (metadata_dir / "lecture-1.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(app_module, "get_database", lambda: fake_db)
    monkeypatch.setattr(app_module, "STORAGE_DIR", tmp_path)
    monkeypatch.setattr(app_module, "delete_storage_path", lambda _path: True)

    payload = app_module.delete_lecture("lecture-1", _request(), purge_storage=True)

    assert payload["deleted"]["lectures"] == 1
    assert payload["deleted"]["artifacts"] == 1
    assert payload["deleted"]["exports"] == 1
    assert payload["deleted"]["metadataRemoved"] is True
    assert payload["auditEventId"]
    assert "lecture-1" not in fake_db.lectures
    assert fake_db.threads["thread-1"]["lecture_refs"] == ["lecture-2"]
    assert len(fake_db.deletion_audit_events) == 1
    assert fake_db.deletion_audit_events[0]["entity_type"] == "lecture"
    assert "auditEventId" not in fake_db.deletion_audit_events[0]["result"]


def test_delete_course_removes_course_and_all_lectures(monkeypatch, tmp_path):
    fake_db = FakeDB()
    fake_db.courses["course-1"] = {"id": "course-1", "title": "Course"}
    fake_db.lectures["lecture-1"] = {
        "id": "lecture-1",
        "course_id": "course-1",
        "audio_path": str(tmp_path / "audio-1.mp3"),
    }
    fake_db.lectures["lecture-2"] = {
        "id": "lecture-2",
        "course_id": "course-1",
        "audio_path": str(tmp_path / "audio-2.mp3"),
    }
    fake_db.threads["thread-1"] = {"id": "thread-1", "lecture_refs": ["lecture-1"]}

    metadata_dir = tmp_path / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    (metadata_dir / "lecture-1.json").write_text("{}", encoding="utf-8")
    (metadata_dir / "lecture-2.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(app_module, "get_database", lambda: fake_db)
    monkeypatch.setattr(app_module, "STORAGE_DIR", tmp_path)
    monkeypatch.setattr(app_module, "delete_storage_path", lambda _path: True)

    payload = app_module.delete_course("course-1", _request(), purge_storage=True)

    assert payload["courseDeleted"] is True
    assert payload["lecturesDeleted"] == 2
    assert payload["auditEventId"]
    assert fake_db.courses == {}
    assert fake_db.lectures == {}
    assert fake_db.threads == {}
    assert len(fake_db.deletion_audit_events) == 3
    assert fake_db.deletion_audit_events[-1]["entity_type"] == "course"


def test_list_deletion_audit_events_filters_by_entity(monkeypatch):
    fake_db = FakeDB()
    fake_db.deletion_audit_events = [
        {"id": "e1", "entity_type": "lecture", "entity_id": "l1", "created_at": "2026-01-01T00:00:00Z"},
        {"id": "e2", "entity_type": "course", "entity_id": "c1", "created_at": "2026-01-01T00:00:01Z"},
    ]

    monkeypatch.setattr(app_module, "get_database", lambda: fake_db)

    payload = app_module.list_deletion_audit_events(
        _request(),
        entity_type="lecture",
        entity_id=None,
        limit=100,
        offset=0,
    )

    assert payload["pagination"]["total"] == 1
    assert len(payload["events"]) == 1
    assert payload["events"][0]["id"] == "e1"


def test_list_deletion_audit_events_rejects_unknown_entity_type(monkeypatch):
    fake_db = FakeDB()
    monkeypatch.setattr(app_module, "get_database", lambda: fake_db)

    try:
        app_module.list_deletion_audit_events(
            _request(),
            entity_type="artifact",
            entity_id=None,
            limit=100,
            offset=0,
        )
    except app_module.HTTPException as exc:
        assert exc.status_code == 400
    else:  # pragma: no cover
        raise AssertionError("Expected HTTPException for invalid entity_type")


def test_deletion_audit_summary_strips_runtime_fields():
    lecture_result = {
        "lectureId": "l-1",
        "deleted": {
            "artifacts": 2,
            "exports": 1,
            "jobs": 3,
            "lectures": 1,
            "threadsUpdated": 0,
            "storagePaths": 4,
            "metadataRemoved": True,
        },
        "auditEventId": "runtime-only",
    }

    summary = app_module._deletion_audit_result_summary("lecture", lecture_result)

    assert summary["lectureId"] == "l-1"
    assert summary["deleted"]["artifacts"] == 2
    assert "auditEventId" not in summary
