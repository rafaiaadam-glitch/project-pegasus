from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from redis import Redis
from rq import Queue

from backend.db import get_database
from backend.storage import save_export, save_transcript
from pipeline.export_artifacts import export_artifacts
from pipeline.run_pipeline import PipelineContext, run_pipeline
from pipeline.transcribe_audio import _load_whisper


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _storage_dir() -> Path:
    return Path(os.getenv("PLC_STORAGE_DIR", "storage")).resolve()


def _ensure_dirs() -> None:
    storage_dir = _storage_dir()
    (storage_dir / "audio").mkdir(parents=True, exist_ok=True)
    (storage_dir / "metadata").mkdir(parents=True, exist_ok=True)
    (storage_dir / "transcripts").mkdir(parents=True, exist_ok=True)
    (storage_dir / "exports").mkdir(parents=True, exist_ok=True)


def _get_queue() -> Queue:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    connection = Redis.from_url(redis_url)
    return Queue("pegasus", connection=connection)


def _create_job_record(job_id: str, job_type: str, lecture_id: Optional[str]) -> None:
    db = get_database()
    now = _iso_now()
    db.create_job(
        {
            "id": job_id,
            "lecture_id": lecture_id,
            "job_type": job_type,
            "status": "queued",
            "result": None,
            "error": None,
            "created_at": now,
            "updated_at": now,
        }
    )


def _update_job(job_id: str, status: str, result: Dict[str, Any] | None = None, error: str | None = None) -> None:
    db = get_database()
    db.update_job(
        job_id=job_id,
        status=status,
        result=result,
        error=error,
        updated_at=_iso_now(),
    )


def enqueue_job(job_type: str, lecture_id: Optional[str], task, *args, **kwargs) -> str:
    job_id = str(uuid.uuid4())
    _create_job_record(job_id, job_type, lecture_id)
    queue = _get_queue()
    queue.enqueue(task, job_id, *args, **kwargs)
    return job_id


def run_transcription_job(job_id: str, lecture_id: str, model: str) -> Dict[str, Any]:
    _update_job(job_id, "running")
    try:
        _ensure_dirs()
        storage_dir = _storage_dir()
        audio_files = list((storage_dir / "audio").glob(f"{lecture_id}.*"))
        if not audio_files:
            raise FileNotFoundError("Audio not found for lecture.")
        audio_path = audio_files[0]
        whisper = _load_whisper()
        model_instance = whisper.load_model(model)
        result = model_instance.transcribe(str(audio_path))

        transcript = {
            "lectureId": lecture_id,
            "createdAt": _iso_now(),
            "language": result.get("language"),
            "text": result.get("text", "").strip(),
            "segments": [
                {
                    "startSec": float(segment["start"]),
                    "endSec": float(segment["end"]),
                    "text": segment["text"].strip(),
                }
                for segment in result.get("segments", [])
            ],
            "engine": {"provider": "whisper", "model": model},
        }
        transcript_payload = json.dumps(transcript, indent=2)
        transcript_path = save_transcript(transcript_payload, f"{lecture_id}.json")
        db = get_database()
        db.upsert_lecture(
            {
                "id": lecture_id,
                "course_id": "unknown",
                "preset_id": "unknown",
                "title": lecture_id,
                "status": "transcribed",
                "audio_path": str(audio_path),
                "transcript_path": transcript_path,
                "created_at": _iso_now(),
                "updated_at": _iso_now(),
            }
        )
        payload = {"lectureId": lecture_id, "transcriptPath": transcript_path}
        _update_job(job_id, "completed", result=payload)
        return payload
    except Exception as exc:
        _update_job(job_id, "failed", error=str(exc))
        raise


def run_generation_job(
    job_id: str,
    lecture_id: str,
    course_id: str,
    preset_id: str,
    openai_model: str,
) -> Dict[str, Any]:
    _update_job(job_id, "running")
    try:
        storage_dir = _storage_dir()
        transcript_path = storage_dir / "transcripts" / f"{lecture_id}.json"
        if not transcript_path.exists():
            raise FileNotFoundError("Transcript not found.")
        transcript_payload = json.loads(transcript_path.read_text(encoding="utf-8"))
        transcript_text = transcript_payload.get("text", "")
        if not transcript_text:
            raise ValueError("Transcript text is empty.")

        context = PipelineContext(
            course_id=course_id,
            lecture_id=lecture_id,
            preset_id=preset_id,
            generated_at=_iso_now(),
            thread_refs=["thread-placeholder"],
        )
        output_dir = Path("pipeline/output")
        run_pipeline(
            transcript_text,
            context,
            output_dir,
            use_llm=True,
            openai_model=openai_model,
        )
        payload = {"lectureId": lecture_id, "outputDir": str(output_dir / lecture_id)}
        _update_job(job_id, "completed", result=payload)
        return payload
    except Exception as exc:
        _update_job(job_id, "failed", error=str(exc))
        raise


def run_export_job(job_id: str, lecture_id: str) -> Dict[str, Any]:
    _update_job(job_id, "running")
    try:
        _ensure_dirs()
        artifact_dir = Path("pipeline/output") / lecture_id
        if not artifact_dir.exists():
            raise FileNotFoundError("Artifacts not found.")
        storage_dir = _storage_dir()
        export_dir = storage_dir / "exports" / lecture_id
        export_artifacts(
            lecture_id=lecture_id, artifact_dir=artifact_dir, export_dir=export_dir
        )
        exports_manifest = {
            "lectureId": lecture_id,
            "exportDir": str(export_dir),
        }
        save_export(
            json.dumps(exports_manifest, indent=2).encode("utf-8"),
            f"{lecture_id}.json",
        )
        _update_job(job_id, "completed", result=exports_manifest)
        return exports_manifest
    except Exception as exc:
        _update_job(job_id, "failed", error=str(exc))
        raise
import queue
import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict


@dataclass
class Job:
    id: str
    status: str = "queued"
    result: Dict[str, Any] | None = None
    error: str | None = None


class JobQueue:
    def __init__(self) -> None:
        self._queue: queue.Queue[tuple[Job, Callable[[], Dict[str, Any]]]] = queue.Queue()
        self._jobs: Dict[str, Job] = {}
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()

    def submit(self, func: Callable[[], Dict[str, Any]]) -> Job:
        job_id = str(uuid.uuid4())
        job = Job(id=job_id)
        self._jobs[job_id] = job
        self._queue.put((job, func))
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def _run(self) -> None:
        while True:
            job, func = self._queue.get()
            job.status = "running"
            try:
                job.result = func()
                job.status = "completed"
            except Exception as exc:  # pragma: no cover - runtime job errors
                job.error = str(exc)
                job.status = "failed"
            finally:
                self._queue.task_done()


JOB_QUEUE = JobQueue()
