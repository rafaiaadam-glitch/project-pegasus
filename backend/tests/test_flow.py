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
except RuntimeError as exc:  # pragma: no cover - dependency guard for CI/runtime
    if "httpx" in str(exc):
        TestClient = None
    else:
        raise

if TestClient is None:
    pytestmark = pytest.mark.skip(reason="fastapi.testclient requires httpx")

import backend.app as app_module
import backend.jobs as jobs_module


class FakeDB:
    def __init__(self) -> None:
        self.jobs: dict[str, dict] = {}
        self.lectures: dict[str, dict] = {}
        self.courses: dict[str, dict] = {}
        self.artifacts: dict[str, dict] = {}
        self.threads: dict[str, dict] = {}
        self.exports: dict[str, dict] = {}
        self.job_history: dict[str, list[str]] = {}

    def migrate(self) -> None:
        return None

    def upsert_lecture(self, payload: dict) -> None:
        self.lectures[payload["id"]] = payload

    def fetch_lecture(self, lecture_id: str):
        return self.lectures.get(lecture_id)

    def upsert_course(self, payload: dict) -> None:
        self.courses[payload["id"]] = payload

    def create_job(self, payload: dict) -> None:
        self.jobs[payload["id"]] = payload
        self.job_history[payload["id"]] = [payload["status"]]

    def update_job(self, job_id: str, status=None, result=None, error=None, updated_at=None) -> None:
        job = self.jobs[job_id]
        if status is not None:
            job["status"] = status
            self.job_history[job_id].append(status)
        if result is not None:
            job["result"] = result
        if error is not None:
            job["error"] = error
        if updated_at is not None:
            job["updated_at"] = updated_at

    def fetch_job(self, job_id: str):
        return self.jobs.get(job_id)

    def upsert_artifact(self, payload: dict) -> None:
        self.artifacts[payload["id"]] = payload

    def fetch_artifacts(
        self,
        lecture_id: str,
        artifact_type: Optional[str] = None,
        preset_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ):
        rows = [row for row in self.artifacts.values() if row["lecture_id"] == lecture_id]
        if artifact_type:
            rows = [row for row in rows if row["artifact_type"] == artifact_type]
        if preset_id:
            rows = [row for row in rows if row["preset_id"] == preset_id]
        if offset:
            rows = rows[offset:]
        if limit is not None:
            rows = rows[:limit]
        return rows

    def upsert_thread(self, payload: dict) -> None:
        self.threads[payload["id"]] = payload

    def fetch_threads(self, lecture_id: str):
        return [
            row
            for row in self.threads.values()
            if lecture_id in (row.get("lecture_refs") or [])
        ]

    def upsert_export(self, payload: dict) -> None:
        self.exports[payload["id"]] = payload

    def fetch_exports(self, lecture_id: str):
        return [row for row in self.exports.values() if row["lecture_id"] == lecture_id]

    def count_artifacts(
        self,
        lecture_id: str,
        artifact_type: Optional[str] = None,
        preset_id: Optional[str] = None,
    ) -> int:
        rows = [row for row in self.artifacts.values() if row["lecture_id"] == lecture_id]
        if artifact_type:
            rows = [row for row in rows if row["artifact_type"] == artifact_type]
        if preset_id:
            rows = [row for row in rows if row["preset_id"] == preset_id]
        return len(rows)


def _write_artifact(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_full_pipeline_flow(monkeypatch, tmp_path):
    storage_dir = tmp_path / "storage"
    monkeypatch.setenv("PLC_STORAGE_DIR", str(storage_dir))
    monkeypatch.setattr(app_module, "STORAGE_DIR", storage_dir)

    fake_db = FakeDB()
    monkeypatch.setattr(app_module, "get_database", lambda: fake_db)
    monkeypatch.setattr(jobs_module, "get_database", lambda: fake_db)

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

    monkeypatch.setattr(jobs_module, "_load_whisper", lambda: StubWhisper())

    def fake_run_pipeline(transcript, context, output_dir, use_llm=False, openai_model="gpt-4o-mini"):
        base = output_dir / context.lecture_id
        now = context.generated_at
        summary = {
            "id": "summary-1",
            "courseId": context.course_id,
            "lectureId": context.lecture_id,
            "presetId": context.preset_id,
            "artifactType": "summary",
            "generatedAt": now,
            "version": "0.1",
            "overview": "Overview text.",
            "sections": [{"title": "Section", "bullets": ["Point"]}],
        }
        outline = {
            "id": "outline-1",
            "courseId": context.course_id,
            "lectureId": context.lecture_id,
            "presetId": context.preset_id,
            "artifactType": "outline",
            "generatedAt": now,
            "version": "0.1",
            "structure": [{"title": "Root", "children": []}],
        }
        key_terms = {
            "id": "key-terms-1",
            "courseId": context.course_id,
            "lectureId": context.lecture_id,
            "presetId": context.preset_id,
            "artifactType": "key-terms",
            "generatedAt": now,
            "version": "0.1",
            "terms": [{"term": "Term", "definition": "Definition"}],
        }
        flashcards = {
            "id": "flashcards-1",
            "courseId": context.course_id,
            "lectureId": context.lecture_id,
            "presetId": context.preset_id,
            "artifactType": "flashcards",
            "generatedAt": now,
            "version": "0.1",
            "cards": [{"front": "Q", "back": "A"}],
        }
        exam_questions = {
            "id": "exam-questions-1",
            "courseId": context.course_id,
            "lectureId": context.lecture_id,
            "presetId": context.preset_id,
            "artifactType": "exam-questions",
            "generatedAt": now,
            "version": "0.1",
            "questions": [
                {
                    "question": "Why?",
                    "answer": "Because.",
                    "difficulty": "medium",
                }
            ],
        }
        _write_artifact(base / "summary.json", summary)
        _write_artifact(base / "outline.json", outline)
        _write_artifact(base / "key-terms.json", key_terms)
        _write_artifact(base / "flashcards.json", flashcards)
        _write_artifact(base / "exam-questions.json", exam_questions)
        _write_artifact(
            base / "threads.json",
            {
                "threads": [
                    {
                        "id": "thread-1",
                        "courseId": context.course_id,
                        "title": "Thread",
                        "summary": "Summary",
                        "status": "foundational",
                        "complexityLevel": 1,
                        "lectureRefs": [context.lecture_id],
                    }
                ]
            },
        )

    monkeypatch.setattr(jobs_module, "run_pipeline", fake_run_pipeline)

    def immediate_enqueue(job_type, lecture_id, task, *args, **kwargs):
        job_id = f"{job_type}-1"
        fake_db.create_job(
            {
                "id": job_id,
                "lecture_id": lecture_id,
                "job_type": job_type,
                "status": "queued",
                "result": None,
                "error": None,
                "created_at": "now",
                "updated_at": "now",
            }
        )
        task(job_id, *args, **kwargs)
        return job_id

    monkeypatch.setattr(app_module, "enqueue_job", immediate_enqueue)

    client = TestClient(app_module.app)

    audio_path = tmp_path / "audio.mp3"
    audio_path.write_bytes(b"audio-bytes")
    with audio_path.open("rb") as handle:
        response = client.post(
            "/lectures/ingest",
            files={"audio": ("audio.mp3", handle, "audio/mpeg")},
            data={
                "course_id": "course-001",
                "lecture_id": "lecture-001",
                "preset_id": "exam-mode",
                "title": "Lecture 1",
                "duration_sec": "120",
                "source_type": "upload",
                "lecture_mode": "MATHEMATICS",
            },
        )
    assert response.status_code == 200
    assert response.json()["lectureMode"] == "MATHEMATICS"

    metadata_path = Path(response.json()["metadataPath"])
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["lectureMode"] == "MATHEMATICS"

    assert fake_db.fetch_lecture("lecture-001") is not None

    response = client.post("/lectures/lecture-001/transcribe")
    assert response.status_code == 200
    job = fake_db.fetch_job("transcription-1")
    assert job["status"] == "completed"

    response = client.post(
        "/lectures/lecture-001/generate",
        json={"course_id": "course-001", "preset_id": "exam-mode"},
    )
    assert response.status_code == 200
    job = fake_db.fetch_job("generation-1")
    assert job["status"] == "completed"
    assert fake_db.fetch_artifacts("lecture-001")

    response = client.post("/lectures/lecture-001/export")
    assert response.status_code == 200
    job = fake_db.fetch_job("export-1")
    assert job["status"] == "completed"
    assert fake_db.fetch_exports("lecture-001")

    response = client.get("/lectures/lecture-001/artifacts")
    assert response.status_code == 200
    payload = response.json()
    assert payload["artifactRecords"]
    assert payload["exportRecords"]
    assert payload["lecture"]["id"] == "lecture-001"

    assert fake_db.job_history["transcription-1"] == ["queued", "running", "completed"]
    assert fake_db.job_history["generation-1"] == ["queued", "running", "completed"]
    assert fake_db.job_history["export-1"] == ["queued", "running", "completed"]


def test_transcription_preserves_existing_lecture_metadata(monkeypatch, tmp_path):
    storage_dir = tmp_path / "storage"
    (storage_dir / "audio").mkdir(parents=True, exist_ok=True)
    audio_path = storage_dir / "audio" / "lecture-xyz.mp3"
    audio_path.write_bytes(b"audio")

    fake_db = FakeDB()
    fake_db.upsert_lecture(
        {
            "id": "lecture-xyz",
            "course_id": "course-123",
            "preset_id": "exam-mode",
            "title": "Original Lecture Title",
            "status": "uploaded",
            "audio_path": "stored/audio/path.mp3",
            "transcript_path": None,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
    )
    fake_db.create_job(
        {
            "id": "job-1",
            "lecture_id": "lecture-xyz",
            "job_type": "transcription",
            "status": "queued",
            "result": None,
            "error": None,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
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

    monkeypatch.setenv("PLC_STORAGE_DIR", str(storage_dir))
    monkeypatch.setattr(jobs_module, "get_database", lambda: fake_db)
    monkeypatch.setattr(jobs_module, "_load_whisper", lambda: StubWhisper())

    def fake_save_transcript(payload: str, name: str) -> str:
        out = storage_dir / "transcripts"
        out.mkdir(parents=True, exist_ok=True)
        target = out / name
        target.write_text(payload, encoding="utf-8")
        return str(target)

    monkeypatch.setattr(jobs_module, "save_transcript", fake_save_transcript)

    jobs_module.run_transcription_job("job-1", "lecture-xyz", "base")

    lecture = fake_db.fetch_lecture("lecture-xyz")
    assert lecture is not None
    assert lecture["course_id"] == "course-123"
    assert lecture["preset_id"] == "exam-mode"
    assert lecture["title"] == "Original Lecture Title"
    assert lecture["audio_path"] == "stored/audio/path.mp3"
    assert lecture["status"] == "transcribed"



@pytest.mark.parametrize(
    "export_type,expected_file",
    [
        ("markdown", "lecture-001.md"),
        ("anki", "lecture-001.csv"),
        ("pdf", "lecture-001.pdf"),
    ],
)
def test_export_download(monkeypatch, tmp_path, export_type, expected_file):
    fake_db = FakeDB()
    export_dir = tmp_path / "exports"
    export_dir.mkdir()
    export_path = export_dir / expected_file
    export_path.write_text("export", encoding="utf-8")
    fake_db.upsert_export(
        {
            "id": f"lecture-001-{export_type}",
            "lecture_id": "lecture-001",
            "export_type": export_type,
            "storage_path": str(export_path),
            "created_at": "now",
        }
    )
    monkeypatch.setattr(app_module, "get_database", lambda: fake_db)
    client = TestClient(app_module.app)
    response = client.get(f"/exports/lecture-001/{export_type}")
    assert response.status_code == 200
