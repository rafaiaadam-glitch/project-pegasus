from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from backend.db import get_database
from backend.jobs import (
    enqueue_job,
    run_export_job,
    run_generation_job,
    run_transcription_job,
)
from backend.storage import save_audio
from backend.jobs import JOB_QUEUE
from backend.storage import save_audio, save_export, save_transcript
from pipeline.export_artifacts import export_artifacts
from pipeline.run_pipeline import PipelineContext, run_pipeline
from pipeline.transcribe_audio import _load_whisper

app = FastAPI(title="Pegasus Lecture Copilot API")
STORAGE_DIR = Path(os.getenv("PLC_STORAGE_DIR", "storage")).resolve()


class GenerateRequest(BaseModel):
    course_id: str
    preset_id: str
    openai_model: str | None = None


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_dirs() -> None:
    (STORAGE_DIR / "audio").mkdir(parents=True, exist_ok=True)
    (STORAGE_DIR / "metadata").mkdir(parents=True, exist_ok=True)
    (STORAGE_DIR / "transcripts").mkdir(parents=True, exist_ok=True)
    (STORAGE_DIR / "exports").mkdir(parents=True, exist_ok=True)


def _sha256(path: Path) -> str:
    import hashlib

    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "time": _iso_now()}


@app.post("/lectures/ingest")
def ingest_lecture(
    course_id: str = Form(...),
    lecture_id: str = Form(...),
    preset_id: str = Form(...),
    title: str = Form(...),
    duration_sec: int = Form(0),
    source_type: str = Form("upload"),
    audio: UploadFile = File(...),
) -> dict:
    _ensure_dirs()
    ext = Path(audio.filename or "").suffix or ".bin"
    stored_audio = save_audio(audio.file, f"{lecture_id}{ext}")

    metadata = {
        "id": lecture_id,
        "courseId": course_id,
        "presetId": preset_id,
        "title": title,
        "recordedAt": _iso_now(),
        "durationSec": duration_sec,
        "audioSource": {
            "sourceType": source_type,
            "originalFilename": audio.filename,
            "storagePath": stored_audio,
            "sizeBytes": Path(stored_audio).stat().st_size if "s3://" not in stored_audio else 0,
            "checksumSha256": _sha256(Path(stored_audio)) if "s3://" not in stored_audio else "",
        },
        "status": "uploaded",
        "artifacts": [],
        "createdAt": _iso_now(),
        "updatedAt": _iso_now(),
    }
    metadata_path = STORAGE_DIR / "metadata" / f"{lecture_id}.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    db = get_database()
    db.upsert_lecture(
        {
            "id": lecture_id,
            "course_id": course_id,
            "preset_id": preset_id,
            "title": title,
            "status": "uploaded",
            "audio_path": stored_audio,
            "transcript_path": None,
            "created_at": _iso_now(),
            "updated_at": _iso_now(),
        }
    )
    return {
        "lectureId": lecture_id,
        "metadataPath": str(metadata_path),
        "audioPath": stored_audio,
    }
    return {"lectureId": lecture_id, "metadataPath": str(metadata_path)}


@app.post("/lectures/{lecture_id}/transcribe")
def transcribe_lecture(lecture_id: str, model: str = "base") -> dict:
    _ensure_dirs()
    audio_files = list((STORAGE_DIR / "audio").glob(f"{lecture_id}.*"))
    if not audio_files:
        raise HTTPException(status_code=404, detail="Audio not found for lecture.")
    job_id = enqueue_job(
        "transcription",
        lecture_id,
        run_transcription_job,
        lecture_id,
        model,
    )
    db = get_database()
    job = db.fetch_job(job_id)
    return {
        "jobId": job_id,
        "status": job["status"] if job else "queued",
        "jobType": job.get("job_type") if job else "transcription",
    }


@app.post("/lectures/{lecture_id}/generate")
def generate_artifacts(lecture_id: str, payload: GenerateRequest) -> dict:
    audio_path = audio_files[0]

    def _job() -> dict:
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
        transcript_path = save_transcript(
            transcript_payload, f"{lecture_id}.json"
        )
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
        return {"lectureId": lecture_id, "transcriptPath": transcript_path}

    job = JOB_QUEUE.submit(_job)
    return {"jobId": job.id, "status": job.status}


@app.post("/lectures/{lecture_id}/generate")
def generate_artifacts(lecture_id: str, course_id: str, preset_id: str) -> dict:
    job_id = enqueue_job(
        "generation",
        lecture_id,
        run_generation_job,
        lecture_id,
        payload.course_id,
        payload.preset_id,
        payload.openai_model or os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        course_id,
        preset_id,
        os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    )
    db = get_database()
    job = db.fetch_job(job_id)
    return {
        "jobId": job_id,
        "status": job["status"] if job else "queued",
        "jobType": job.get("job_type") if job else "generation",
    }
    transcript_path = STORAGE_DIR / "transcripts" / f"{lecture_id}.json"
    if not transcript_path.exists():
        raise HTTPException(status_code=404, detail="Transcript not found.")
    transcript_payload = json.loads(transcript_path.read_text(encoding="utf-8"))
    transcript_text = transcript_payload.get("text", "")
    if not transcript_text:
        raise HTTPException(status_code=400, detail="Transcript text is empty.")

    def _job() -> dict:
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
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        )
        return {"lectureId": lecture_id, "outputDir": str(output_dir / lecture_id)}

    job = JOB_QUEUE.submit(_job)
    return {"jobId": job.id, "status": job.status}


@app.post("/lectures/{lecture_id}/export")
def export_lecture(lecture_id: str) -> dict:
    job_id = enqueue_job("export", lecture_id, run_export_job, lecture_id)
    db = get_database()
    job = db.fetch_job(job_id)
    return {
        "jobId": job_id,
        "status": job["status"] if job else "queued",
        "jobType": job.get("job_type") if job else "export",
    }
    artifact_dir = Path("pipeline/output") / lecture_id
    if not artifact_dir.exists():
        raise HTTPException(status_code=404, detail="Artifacts not found.")
    export_dir = STORAGE_DIR / "exports" / lecture_id

    def _job() -> dict:
        export_artifacts(
            lecture_id=lecture_id, artifact_dir=artifact_dir, export_dir=export_dir
        )
        return {"lectureId": lecture_id, "exportDir": str(export_dir)}

    job = JOB_QUEUE.submit(_job)
    return {"jobId": job.id, "status": job.status}


@app.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    db = get_database()
    job = db.fetch_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return {
        "id": job["id"],
        "status": job["status"],
        "jobType": job.get("job_type"),
        "result": job.get("result"),
        "error": job.get("error"),
    }


@app.get("/exports/{lecture_id}/{export_type}")
def download_export(lecture_id: str, export_type: str):
    db = get_database()
    exports = db.fetch_exports(lecture_id)
    record = next((item for item in exports if item["export_type"] == export_type), None)
    if not record:
        raise HTTPException(status_code=404, detail="Export not found.")
    storage_path = record["storage_path"]
    if storage_path.startswith("s3://"):
        return JSONResponse({"downloadUrl": storage_path})
    path = Path(storage_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Export file missing.")
    return FileResponse(path, filename=path.name)


@app.get("/lectures/{lecture_id}/artifacts")
def review_artifacts(lecture_id: str) -> dict:
    artifact_dir = Path("pipeline/output") / lecture_id
    if not artifact_dir.exists():
        raise HTTPException(status_code=404, detail="Artifacts not found.")
    db = get_database()
    artifact_map = {
        "summary": "summary.json",
        "outline": "outline.json",
        "keyTerms": "key-terms.json",
        "flashcards": "flashcards.json",
        "examQuestions": "exam-questions.json",
        "threads": "threads.json",
        "threadOccurrences": "thread-occurrences.json",
        "threadUpdates": "thread-updates.json",
    }
    payload: dict[str, object] = {}
    for key, filename in artifact_map.items():
        path = artifact_dir / filename
        if path.exists():
            payload[key] = json.loads(path.read_text(encoding="utf-8"))
        else:
            payload[key] = None
    return {
        "lectureId": lecture_id,
        "artifacts": payload,
        "artifactRecords": db.fetch_artifacts(lecture_id),
        "exportRecords": db.fetch_exports(lecture_id),
        "lecture": db.fetch_lecture(lecture_id),
    return {"lectureId": lecture_id, "artifacts": payload}
    job = JOB_QUEUE.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return {
        "id": job.id,
        "status": job.status,
        "result": job.result,
        "error": job.error,
    }
