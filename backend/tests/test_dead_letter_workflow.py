from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

import backend.app as app_module


class FakeDB:
    def __init__(self) -> None:
        self.jobs: list[dict] = []
        self.lectures: dict[str, dict] = {}

    def fetch_jobs(self, lecture_id=None, limit=None, offset=None):
        jobs = list(self.jobs)
        if lecture_id:
            jobs = [job for job in jobs if job.get("lecture_id") == lecture_id]
        return jobs

    def fetch_job(self, job_id: str):
        for job in self.jobs:
            if job.get("id") == job_id:
                return job
        return None

    def fetch_lecture(self, lecture_id: str):
        return self.lectures.get(lecture_id)


def test_is_failed_job_filters_by_status_lecture_and_type():
    job = {"id": "job-1", "status": "failed", "job_type": "generation", "lecture_id": "lec-1"}

    assert app_module._is_failed_job(job, lecture_id=None, job_type=None)
    assert app_module._is_failed_job(job, lecture_id="lec-1", job_type=None)
    assert app_module._is_failed_job(job, lecture_id="lec-1", job_type="generation")
    assert not app_module._is_failed_job(job, lecture_id="lec-2", job_type=None)
    assert not app_module._is_failed_job(job, lecture_id=None, job_type="export")


def test_batch_replay_uses_failed_jobs_and_limit(monkeypatch):
    fake_db = FakeDB()
    fake_db.jobs = [
        {"id": "job-1", "status": "failed", "job_type": "generation", "lecture_id": "lec-1"},
        {"id": "job-2", "status": "failed", "job_type": "export", "lecture_id": "lec-2"},
        {"id": "job-3", "status": "completed", "job_type": "generation", "lecture_id": "lec-3"},
    ]
    fake_db.lectures = {
        "lec-1": {"id": "lec-1", "course_id": "course-1", "preset_id": "exam-mode"},
        "lec-2": {"id": "lec-2", "course_id": "course-2", "preset_id": "exam-mode"},
    }

    replay_calls = []

    def _fake_replay(db, job):
        replay_calls.append(job["id"])
        return {"jobId": f"new-{job['id']}"}

    monkeypatch.setattr(app_module, "_enqueue_replay_job", _fake_replay)

    failed_jobs = [job for job in fake_db.fetch_jobs() if app_module._is_failed_job(job, None, None)]
    selected_jobs = failed_jobs[:1]
    replayed = [app_module._enqueue_replay_job(fake_db, job) for job in selected_jobs]

    assert replay_calls == ["job-1"]
    assert replayed == [{"jobId": "new-job-1"}]
