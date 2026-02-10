from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from redis import Redis
from rq import Queue, Retry

from backend.db import get_database
from backend.storage import save_artifact_file, save_export, save_export_file, save_transcript
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


def _load_lecture_metadata(lecture_id: str) -> Dict[str, Any]:
    metadata_path = _storage_dir() / "metadata" / f"{lecture_id}.json"
    if not metadata_path.exists():
        return {}
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def _resolve_lecture_upsert_payload(
    lecture_id: str,
    audio_path: Path,
    transcript_path: str,
    existing_lecture: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    metadata = _load_lecture_metadata(lecture_id)
    current = existing_lecture or {}
    return {
        "id": lecture_id,
        "course_id": current.get("course_id") or metadata.get("courseId") or "unknown",
        "preset_id": current.get("preset_id") or metadata.get("presetId") or "unknown",
        "title": current.get("title") or metadata.get("title") or lecture_id,
        "status": "transcribed",
        "audio_path": current.get("audio_path")
        or metadata.get("audioSource", {}).get("storagePath")
        or str(audio_path),
        "transcript_path": transcript_path,
        "created_at": current.get("created_at") or metadata.get("createdAt") or _iso_now(),
        "updated_at": _iso_now(),
    }

def _get_queue() -> Queue:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    connection = Redis.from_url(redis_url)
    return Queue("pegasus", connection=connection)




def _should_run_jobs_inline() -> bool:
    return os.getenv("PLC_INLINE_JOBS", "").strip().lower() in {"1", "true", "yes", "on"}


def _run_job_inline(job_id: str, task, *args, **kwargs) -> None:
    try:
        task(job_id, *args, **kwargs)
    except Exception as exc:  # pragma: no cover - task updates job status before raising
        _update_job(job_id, "failed", error=str(exc))

def _handle_job_failure(job, exc_type, exc_value, traceback) -> None:
    _update_job(job.id, "failed", error=str(exc_value))


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


def _update_job(
    job_id: str,
    status: str,
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
) -> None:
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

    if _should_run_jobs_inline():
        _run_job_inline(job_id, task, *args, **kwargs)
        return job_id

    try:
        queue = _get_queue()
        queue.enqueue(
            task,
            job_id,
            *args,
            retry=Retry(max=3, interval=[10, 60, 300]),
            on_failure=_handle_job_failure,
            **kwargs,
        )
    except Exception as exc:
        _update_job(job_id, "running", result={"queueFallback": "inline", "reason": str(exc)})
        _run_job_inline(job_id, task, *args, **kwargs)

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
        existing_lecture = db.fetch_lecture(lecture_id)
        db.upsert_lecture(
            _resolve_lecture_upsert_payload(
                lecture_id=lecture_id,
                audio_path=audio_path,
                transcript_path=transcript_path,
                existing_lecture=existing_lecture,
            )
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
        artifacts_dir = output_dir / lecture_id
        db = get_database()
        now = _iso_now()
        db.upsert_course(
            {
                "id": course_id,
                "title": course_id,
                "created_at": now,
                "updated_at": now,
            }
        )

        artifact_files = [
            "summary.json",
            "outline.json",
            "key-terms.json",
            "flashcards.json",
            "exam-questions.json",
        ]
        artifact_paths: dict[str, str] = {}
        for filename in artifact_files:
            path = artifacts_dir / filename
            if not path.exists():
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            artifact_type = payload.get("artifactType", filename.replace(".json", ""))
            stored_path = save_artifact_file(path, f"{lecture_id}/{filename}")
            overview = payload.get("overview") if artifact_type == "summary" else None
            section_count = (
                len(payload.get("sections", [])) if artifact_type == "summary" else None
            )
            db.upsert_artifact(
                {
                    "id": payload.get("id", f"{lecture_id}-{artifact_type}"),
                    "lecture_id": lecture_id,
                    "course_id": course_id,
                    "preset_id": preset_id,
                    "artifact_type": artifact_type,
                    "storage_path": stored_path,
                    "summary_overview": overview,
                    "summary_section_count": section_count,
                    "created_at": now,
                }
            )
            artifact_paths[artifact_type] = stored_path

        threads_path = artifacts_dir / "threads.json"
        if threads_path.exists():
            threads_payload = json.loads(threads_path.read_text(encoding="utf-8"))
            for thread in threads_payload.get("threads", []):
                db.upsert_thread(
                    {
                        "id": thread["id"],
                        "course_id": thread["courseId"],
                        "title": thread["title"],
                        "summary": thread["summary"],
                        "status": thread["status"],
                        "complexity_level": thread["complexityLevel"],
                        "lecture_refs": thread.get("lectureRefs", []),
                        "created_at": now,
                    }
                )

        payload = {
            "lectureId": lecture_id,
            "outputDir": str(artifacts_dir),
            "artifactPaths": artifact_paths,
        }
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
        db = get_database()
        now = _iso_now()
        export_files = {
            "markdown": export_dir / f"{lecture_id}.md",
            "anki": export_dir / f"{lecture_id}.csv",
            "pdf": export_dir / f"{lecture_id}.pdf",
        }
        export_paths = {}
        for export_type, path in export_files.items():
            stored_path = save_export_file(path, f"{lecture_id}/{path.name}")
            export_paths[export_type] = stored_path
            db.upsert_export(
                {
                    "id": f"{lecture_id}-{export_type}",
                    "lecture_id": lecture_id,
                    "export_type": export_type,
                    "storage_path": stored_path,
                    "created_at": now,
                }
            )
        exports_manifest = {
            "lectureId": lecture_id,
            "exportDir": str(export_dir),
            "exportPaths": export_paths,
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
