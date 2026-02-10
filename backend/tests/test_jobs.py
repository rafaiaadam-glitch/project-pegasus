from __future__ import annotations

import json
import sys

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

import backend.jobs as jobs_module


class FakeDB:
    def __init__(self) -> None:
        self.jobs: dict[str, dict] = {}
        self.lectures: dict[str, dict] = {}

    def create_job(self, payload: dict) -> None:
        self.jobs[payload["id"]] = payload

    def update_job(self, job_id: str, status=None, result=None, error=None, updated_at=None) -> None:
        job = self.jobs[job_id]
        if status is not None:
            job["status"] = status
        if result is not None:
            job["result"] = result
        if error is not None:
            job["error"] = error
        if updated_at is not None:
            job["updated_at"] = updated_at

    def fetch_lecture(self, lecture_id: str):
        return self.lectures.get(lecture_id)

    def upsert_lecture(self, payload: dict) -> None:
        self.lectures[payload["id"]] = payload


def test_transcription_uses_metadata_when_lecture_missing(monkeypatch, tmp_path):
    storage_dir = tmp_path / "storage"
    (storage_dir / "audio").mkdir(parents=True, exist_ok=True)
    (storage_dir / "metadata").mkdir(parents=True, exist_ok=True)
    audio_path = storage_dir / "audio" / "lecture-abc.mp3"
    audio_path.write_bytes(b"audio")

    metadata = {
        "id": "lecture-abc",
        "courseId": "course-from-metadata",
        "presetId": "exam-mode",
        "title": "Metadata Lecture",
        "audioSource": {"storagePath": "storage/audio/lecture-abc.mp3"},
        "createdAt": "2024-03-10T00:00:00Z",
    }
    (storage_dir / "metadata" / "lecture-abc.json").write_text(
        json.dumps(metadata), encoding="utf-8"
    )

    fake_db = FakeDB()
    fake_db.create_job(
        {
            "id": "job-1",
            "lecture_id": "lecture-abc",
            "job_type": "transcription",
            "status": "queued",
            "result": None,
            "error": None,
            "created_at": "2024-03-10T00:00:00Z",
            "updated_at": "2024-03-10T00:00:00Z",
        }
    )

    class StubWhisperModel:
        def transcribe(self, _path: str):
            return {
                "language": "en",
                "text": "Sample transcript.",
                "segments": [{"start": 0.0, "end": 1.0, "text": "Sample transcript."}],
            }

    class StubWhisper:
        def load_model(self, _model: str):
            return StubWhisperModel()

    def fake_save_transcript(payload: str, name: str) -> str:
        out = storage_dir / "transcripts"
        out.mkdir(parents=True, exist_ok=True)
        target = out / name
        target.write_text(payload, encoding="utf-8")
        return str(target)

    monkeypatch.setenv("PLC_STORAGE_DIR", str(storage_dir))
    monkeypatch.setattr(jobs_module, "get_database", lambda: fake_db)
    monkeypatch.setattr(jobs_module, "_load_whisper", lambda: StubWhisper())
    monkeypatch.setattr(jobs_module, "save_transcript", fake_save_transcript)

    jobs_module.run_transcription_job("job-1", "lecture-abc", "base")

    lecture = fake_db.fetch_lecture("lecture-abc")
    assert lecture is not None
    assert lecture["course_id"] == "course-from-metadata"
    assert lecture["preset_id"] == "exam-mode"
    assert lecture["title"] == "Metadata Lecture"
    assert lecture["audio_path"] == "storage/audio/lecture-abc.mp3"
    assert lecture["status"] == "transcribed"


def test_enqueue_job_runs_inline_when_configured(monkeypatch):
    fake_db = FakeDB()
    monkeypatch.setattr(jobs_module, "get_database", lambda: fake_db)
    monkeypatch.setenv("PLC_INLINE_JOBS", "true")

    def stub_task(job_id: str, value: str):
        jobs_module._update_job(job_id, "running")
        jobs_module._update_job(job_id, "completed", result={"value": value})

    job_id = jobs_module.enqueue_job("stub", "lecture-1", stub_task, "ok")

    job = fake_db.jobs[job_id]
    assert job["status"] == "completed"
    assert job["result"] == {"value": "ok"}


def test_enqueue_job_falls_back_to_inline_when_queue_unavailable(monkeypatch):
    fake_db = FakeDB()
    monkeypatch.setattr(jobs_module, "get_database", lambda: fake_db)
    monkeypatch.delenv("PLC_INLINE_JOBS", raising=False)

    def broken_queue():
        raise RuntimeError("redis unavailable")

    monkeypatch.setattr(jobs_module, "_get_queue", broken_queue)

    def stub_task(job_id: str, value: str):
        jobs_module._update_job(job_id, "running")
        jobs_module._update_job(job_id, "completed", result={"value": value})

    job_id = jobs_module.enqueue_job("stub", "lecture-2", stub_task, "fallback")

    job = fake_db.jobs[job_id]
    assert job["status"] == "completed"
    assert job["result"] == {"value": "fallback"}


def test_enqueue_job_marks_failed_if_inline_task_raises(monkeypatch):
    fake_db = FakeDB()
    monkeypatch.setattr(jobs_module, "get_database", lambda: fake_db)
    monkeypatch.setenv("PLC_INLINE_JOBS", "1")

    def bad_task(job_id: str):
        jobs_module._update_job(job_id, "running")
        raise ValueError("boom")

    jobs_module.enqueue_job("stub", "lecture-3", bad_task)

    job = next(iter(fake_db.jobs.values()))
    assert job["status"] == "failed"
    assert "boom" in (job.get("error") or "")
