from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

import backend.app as app_module


class FakeDB:
    def __init__(self) -> None:
        self.lectures: dict[str, dict] = {}
        self.jobs: dict[str, dict] = {}

    def fetch_lecture(self, lecture_id: str):
        return self.lectures.get(lecture_id)

    def fetch_job(self, job_id: str):
        return self.jobs.get(job_id)


def test_replay_rejects_non_failed_job():
    fake_db = FakeDB()
    with pytest.raises(app_module.HTTPException, match="Only failed jobs can be replayed"):
        app_module._enqueue_replay_job(
            fake_db,
            {"id": "job-1", "status": "completed", "job_type": "export", "lecture_id": "lec-1"},
        )


def test_replay_rejects_unsupported_job_type():
    fake_db = FakeDB()
    with pytest.raises(app_module.HTTPException, match="unsupported"):
        app_module._enqueue_replay_job(
            fake_db,
            {"id": "job-1", "status": "failed", "job_type": "unknown", "lecture_id": "lec-1"},
        )


def test_replay_generation_requires_lecture_context():
    fake_db = FakeDB()
    with pytest.raises(app_module.HTTPException, match="Lecture not found"):
        app_module._enqueue_replay_job(
            fake_db,
            {"id": "job-1", "status": "failed", "job_type": "generation", "lecture_id": "lec-1"},
        )


def test_replay_generation_enqueues_job(monkeypatch):
    fake_db = FakeDB()
    fake_db.lectures["lec-1"] = {"id": "lec-1", "course_id": "course-1", "preset_id": "exam-mode"}
    fake_db.jobs["job-new"] = {"id": "job-new", "status": "queued", "job_type": "generation"}

    calls = {}

    def _fake_enqueue(job_type, lecture_id, task, *args, **kwargs):
        calls["job_type"] = job_type
        calls["lecture_id"] = lecture_id
        calls["args"] = args
        return "job-new"

    monkeypatch.setattr(app_module, "enqueue_job", _fake_enqueue)

    payload = app_module._enqueue_replay_job(
        fake_db,
        {"id": "job-old", "status": "failed", "job_type": "generation", "lecture_id": "lec-1"},
    )

    assert calls["job_type"] == "generation"
    assert calls["lecture_id"] == "lec-1"
    assert payload["jobId"] == "job-new"
    assert payload["replayedFromJobId"] == "job-old"
