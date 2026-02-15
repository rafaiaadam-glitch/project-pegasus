from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from time import perf_counter
from pathlib import Path
from typing import Any, Dict, Optional

from redis import Redis
from rq import Queue, Retry

from backend.db import get_database
from backend.observability import METRICS
from backend.storage import save_artifact_file, save_export, save_export_file, save_transcript
from pipeline.export_artifacts import export_artifacts
from pipeline.run_pipeline import PipelineContext, run_pipeline
from pipeline.transcribe_audio import _convert_to_wav, _load_whisper


LOGGER = logging.getLogger("pegasus.jobs")

_JOB_STARTED_AT: dict[str, float] = {}


def _log_job_event(event: str, **fields: Any) -> None:
    LOGGER.info(event, extra={k: v for k, v in fields.items() if v is not None})


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _storage_dir() -> Path:
    return Path(os.getenv("PLC_STORAGE_DIR", "storage")).resolve()


def _ensure_dirs() -> None:
    storage_dir = _storage_dir()
    (storage_dir / "audio").mkdir(parents=True, exist_ok=True)
    (storage_dir / "documents").mkdir(parents=True, exist_ok=True)
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
    source_path: Path,
    transcript_path: str,
    existing_lecture: Optional[Dict[str, Any]],
    source_type: str = "audio",
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
        or str(source_path),
        "transcript_path": transcript_path,
        "created_at": current.get("created_at") or metadata.get("createdAt") or _iso_now(),
        "updated_at": _iso_now(),
        "lecture_mode": current.get("lecture_mode") or metadata.get("lectureMode"),
        "source_type": current.get("source_type")
        or metadata.get("audioSource", {}).get("fileType")
        or source_type,
    }


def _resolve_thread_refs(db, course_id: str) -> list[str]:
    """Load known thread IDs for a course to seed cross-lecture continuity."""
    fetch_threads_for_course = getattr(db, "fetch_threads_for_course", None)
    if not callable(fetch_threads_for_course):
        return []

    try:
        threads = fetch_threads_for_course(course_id)
    except Exception:
        return []

    if not isinstance(threads, list):
        return []

    refs: list[str] = []
    seen: set[str] = set()
    for thread in threads:
        if not isinstance(thread, dict):
            continue
        thread_id = thread.get("id")
        if not isinstance(thread_id, str):
            continue
        normalized = thread_id.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        refs.append(normalized)
    return refs



def _parse_quality_threshold(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer.") from exc
    if value < 0:
        raise RuntimeError(f"{name} must be zero or greater.")
    return value


def _assert_minimum_artifact_quality(db, lecture_id: str) -> None:
    fetch_artifacts = getattr(db, "fetch_artifacts", None)
    if not callable(fetch_artifacts):
        raise RuntimeError("Database does not support artifact quality checks.")

    artifacts = fetch_artifacts(lecture_id)
    by_type = {row.get("artifact_type"): row for row in artifacts if isinstance(row, dict)}

    required_types = {"summary", "outline", "key-terms", "flashcards", "exam-questions"}
    missing_types = sorted(required_types - set(by_type))
    if missing_types:
        raise ValueError(
            "Cannot export lecture before all required artifacts are generated: "
            + ", ".join(missing_types)
        )

    min_summary_sections = _parse_quality_threshold("PLC_EXPORT_MIN_SUMMARY_SECTIONS", 1)
    summary = by_type.get("summary") or {}
    section_count = summary.get("summary_section_count")
    if section_count is None:
        section_count = 0
    if int(section_count) < min_summary_sections:
        raise ValueError(
            f"Summary quality threshold not met: requires >= {min_summary_sections} sections."
        )

    overview = str(summary.get("summary_overview") or "").strip()
    if not overview:
        raise ValueError("Summary quality threshold not met: overview is empty.")

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
        _update_job(job_id, "failed", error=str(exc), job_type="transcription")

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
    _log_job_event("job.created", job_id=job_id, lecture_id=lecture_id, job_type=job_type, status="queued")
    METRICS.increment_job_status(job_type, "queued")


def _update_job(
    job_id: str,
    status: str,
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    job_type: Optional[str] = None,
) -> None:
    db = get_database()
    db.update_job(
        job_id=job_id,
        status=status,
        result=result,
        error=error,
        updated_at=_iso_now(),
    )
    _log_job_event("job.updated", job_id=job_id, status=status, error=error)

    resolved_job_type = job_type
    if not resolved_job_type:
        fetch_job = getattr(db, "fetch_job", None)
        if callable(fetch_job):
            job = fetch_job(job_id)
            if isinstance(job, dict):
                resolved_job_type = str(job.get("job_type") or "unknown")

    if resolved_job_type:
        METRICS.increment_job_status(resolved_job_type, status)

        if status == "running":
            _JOB_STARTED_AT[job_id] = perf_counter()
        elif status in {"completed", "failed"}:
            started_at = _JOB_STARTED_AT.pop(job_id, None)
            if started_at is not None:
                METRICS.observe_job_latency(
                    resolved_job_type,
                    (perf_counter() - started_at) * 1000,
                )
        if status == "failed":
            METRICS.increment_job_failure(resolved_job_type)


def enqueue_job(job_type: str, lecture_id: Optional[str], task, *args, **kwargs) -> str:
    job_id = str(uuid.uuid4())
    _create_job_record(job_id, job_type, lecture_id)

    if _should_run_jobs_inline():
        _log_job_event("job.dispatch", job_id=job_id, lecture_id=lecture_id, job_type=job_type, mode="inline")
        _run_job_inline(job_id, task, *args, **kwargs)
        return job_id

    try:
        queue = _get_queue()
        _log_job_event("job.dispatch", job_id=job_id, lecture_id=lecture_id, job_type=job_type, mode="queue")
        queue.enqueue(
            task,
            job_id,
            *args,
            retry=Retry(max=3, interval=[10, 60, 300]),
            on_failure=_handle_job_failure,
            **kwargs,
        )
    except Exception as exc:
        _log_job_event("job.dispatch_failed", job_id=job_id, lecture_id=lecture_id, job_type=job_type, error=str(exc))
        _update_job(job_id, "running", result={"queueFallback": "inline", "reason": str(exc)})
        _run_job_inline(job_id, task, *args, **kwargs)

    return job_id


def _transcribe_with_whisper(audio_path: Path, model: str) -> Dict[str, Any]:
    whisper = _load_whisper()
    model_instance = whisper.load_model(model)
    result = model_instance.transcribe(str(audio_path))

    return {
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


def _transcribe_with_google_speech(audio_path: Path, language_code: str | None) -> Dict[str, Any]:
    try:
        from google.cloud import speech_v1 as speech
    except Exception as exc:
        raise RuntimeError(
            "google-cloud-speech is required for provider=google. "
            "Install with `pip install google-cloud-speech`."
        ) from exc

    # Convert audio to LINEAR16 WAV for best compatibility with Google STT
    # This handles M4A from mobile recordings and other formats
    stt_input_path = _convert_to_wav(audio_path)

    client = speech.SpeechClient()
    audio = speech.RecognitionAudio(content=stt_input_path.read_bytes())
    config = speech.RecognitionConfig(
        language_code=language_code or os.getenv("PLC_STT_LANGUAGE", "en-US"),
        enable_automatic_punctuation=True,
        model=os.getenv("PLC_GCP_STT_MODEL", "latest_long"),
    )
    response = client.recognize(config=config, audio=audio)

    lines: list[str] = []
    segments: list[dict[str, Any]] = []
    cursor = 0.0
    for result in response.results:
        if not result.alternatives:
            continue
        transcript = result.alternatives[0].transcript.strip()
        if not transcript:
            continue
        lines.append(transcript)
        start_sec = cursor
        cursor += max(2.0, len(transcript.split()) * 0.45)
        segments.append({"startSec": start_sec, "endSec": cursor, "text": transcript})

    return {
        "language": language_code or os.getenv("PLC_STT_LANGUAGE", "en-US"),
        "text": " ".join(lines).strip(),
        "segments": segments,
        "engine": {"provider": "google_speech", "model": os.getenv("PLC_GCP_STT_MODEL", "latest_long")},
    }


def _extract_pdf_text(pdf_path: Path) -> Dict[str, Any]:
    """
    Extract text from a PDF file and return in transcript-compatible format.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Dictionary containing language, text, segments, and engine metadata
    """
    from backend.pdf_extractor import extract_text_from_pdf

    extracted = extract_text_from_pdf(pdf_path)
    return {
        "language": "en",
        "text": extracted["text"],
        "segments": extracted["segments"],
        "engine": extracted["engine"],
        "metadata": extracted.get("metadata", {}),
    }


def run_transcription_job(
    job_id: str,
    lecture_id: str,
    model: str,
    provider: str = "google",  # Default to Google Speech-to-Text
    language_code: str | None = None,
) -> Dict[str, Any]:
    _log_job_event("job.run.start", job_id=job_id, lecture_id=lecture_id, job_type="transcription")
    _update_job(job_id, "running", job_type="transcription")
    try:
        _ensure_dirs()
        storage_dir = _storage_dir()

        # Check for PDF files first
        pdf_files = list((storage_dir / "documents").glob(f"{lecture_id}.*"))
        if pdf_files:
            # PDF file found - extract text instead of transcribing audio
            pdf_path = pdf_files[0]
            transcription = _extract_pdf_text(pdf_path)
            source_path = pdf_path
            source_type = "pdf"
        else:
            # No PDF, fall back to audio transcription
            audio_files = list((storage_dir / "audio").glob(f"{lecture_id}.*"))
            if not audio_files:
                raise FileNotFoundError("Neither PDF nor audio file found for lecture.")
            source_path = audio_files[0]
            source_type = "audio"

            provider_key = (provider or "google").strip().lower()
            if provider_key == "google":
                transcription = _transcribe_with_google_speech(source_path, language_code)
            elif provider_key == "whisper":
                transcription = _transcribe_with_whisper(source_path, model)
            else:
                raise ValueError(f"Unsupported transcription provider: {provider}")

        transcript = {
            "lectureId": lecture_id,
            "createdAt": _iso_now(),
            "language": transcription.get("language"),
            "text": transcription.get("text", "").strip(),
            "segments": transcription.get("segments", []),
            "engine": transcription.get("engine", {"provider": provider or "google", "model": model}),
        }
        transcript_payload = json.dumps(transcript, indent=2)
        transcript_path = save_transcript(transcript_payload, f"{lecture_id}.json")
        db = get_database()
        existing_lecture = db.fetch_lecture(lecture_id)
        db.upsert_lecture(
            _resolve_lecture_upsert_payload(
                lecture_id=lecture_id,
                source_path=source_path,
                transcript_path=transcript_path,
                existing_lecture=existing_lecture,
                source_type=source_type,
            )
        )
        payload = {"lectureId": lecture_id, "transcriptPath": transcript_path}
        _update_job(job_id, "completed", result=payload, job_type="transcription")
        _log_job_event("job.run.completed", job_id=job_id, lecture_id=lecture_id, job_type="transcription")
        return payload
    except Exception as exc:
        _update_job(job_id, "failed", error=str(exc), job_type="transcription")
        _log_job_event("job.run.failed", job_id=job_id, lecture_id=lecture_id, job_type="transcription", error=str(exc))
        raise


def run_generation_job(
    job_id: str,
    lecture_id: str,
    course_id: str,
    preset_id: str,
    llm_provider: str,
    llm_model: str,
) -> Dict[str, Any]:
    _log_job_event("job.run.start", job_id=job_id, lecture_id=lecture_id, job_type="generation")
    _update_job(job_id, "running", job_type="generation")
    try:
        storage_dir = _storage_dir()
        transcript_path = storage_dir / "transcripts" / f"{lecture_id}.json"
        if not transcript_path.exists():
            raise FileNotFoundError("Transcript not found.")
        transcript_payload = json.loads(transcript_path.read_text(encoding="utf-8"))
        transcript_text = transcript_payload.get("text", "")
        if not transcript_text:
            raise ValueError("Transcript text is empty.")

        db = get_database()
        thread_refs = _resolve_thread_refs(db, course_id)

        context = PipelineContext(
            course_id=course_id,
            lecture_id=lecture_id,
            preset_id=preset_id,
            generated_at=_iso_now(),
            thread_refs=thread_refs,
        )
        output_dir = Path("pipeline/output")
        run_pipeline(
            transcript_text,
            context,
            output_dir,
            use_llm=True,
            openai_model=llm_model,
            llm_provider=llm_provider,
            llm_model=llm_model,
        )
        artifacts_dir = output_dir / lecture_id
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
        _update_job(job_id, "completed", result=payload, job_type="generation")
        _log_job_event("job.run.completed", job_id=job_id, lecture_id=lecture_id, job_type="generation")
        return payload
    except Exception as exc:
        _update_job(job_id, "failed", error=str(exc), job_type="generation")
        _log_job_event("job.run.failed", job_id=job_id, lecture_id=lecture_id, job_type="generation", error=str(exc))
        raise


def run_export_job(job_id: str, lecture_id: str) -> Dict[str, Any]:
    _log_job_event("job.run.start", job_id=job_id, lecture_id=lecture_id, job_type="export")
    _update_job(job_id, "running", job_type="export")
    try:
        _ensure_dirs()
        artifact_dir = Path("pipeline/output") / lecture_id
        if not artifact_dir.exists():
            raise FileNotFoundError("Artifacts not found.")
        storage_dir = _storage_dir()
        export_dir = storage_dir / "exports" / lecture_id
        db = get_database()
        _assert_minimum_artifact_quality(db, lecture_id)
        export_artifacts(
            lecture_id=lecture_id, artifact_dir=artifact_dir, export_dir=export_dir
        )
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
        _update_job(job_id, "completed", result=exports_manifest, job_type="export")
        _log_job_event("job.run.completed", job_id=job_id, lecture_id=lecture_id, job_type="export")
        return exports_manifest
    except Exception as exc:
        _update_job(job_id, "failed", error=str(exc), job_type="export")
        _log_job_event("job.run.failed", job_id=job_id, lecture_id=lecture_id, job_type="export", error=str(exc))
        raise
