from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from typing import Optional

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
from backend.storage import download_url, save_audio

app = FastAPI(title="Pegasus Lecture Copilot API")
STORAGE_DIR = Path(os.getenv("PLC_STORAGE_DIR", "storage")).resolve()


class GenerateRequest(BaseModel):
    course_id: str
    preset_id: str
    openai_model: Optional[str] = None


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
    course_title: Optional[str] = Form(None),
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
    db.upsert_course(
        {
            "id": course_id,
            "title": course_title or course_id,
            "created_at": _iso_now(),
            "updated_at": _iso_now(),
        }
    )
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


@app.get("/courses")
def list_courses(limit: Optional[int] = None, offset: Optional[int] = None) -> dict:
    db = get_database()
    return {"courses": db.fetch_courses(limit=limit, offset=offset)}


@app.get("/courses/{course_id}")
def get_course(course_id: str) -> dict:
    db = get_database()
    course = db.fetch_course(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")
    return course


@app.get("/courses/{course_id}/lectures")
def list_course_lectures(
    course_id: str,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> dict:
    db = get_database()
    return {
        "courseId": course_id,
        "lectures": db.fetch_lectures(course_id=course_id, limit=limit, offset=offset),
    }


@app.get("/lectures")
def list_lectures(
    course_id: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> dict:
    db = get_database()
    return {"lectures": db.fetch_lectures(course_id=course_id, limit=limit, offset=offset)}


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
    job_id = enqueue_job(
        "generation",
        lecture_id,
        run_generation_job,
        lecture_id,
        payload.course_id,
        payload.preset_id,
        payload.openai_model or os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    )
    db = get_database()
    job = db.fetch_job(job_id)
    return {
        "jobId": job_id,
        "status": job["status"] if job else "queued",
        "jobType": job.get("job_type") if job else "generation",
    }


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
        url = download_url(storage_path)
        if not url:
            raise HTTPException(status_code=404, detail="Export URL unavailable.")
        return JSONResponse({"downloadUrl": url})
    path = Path(storage_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Export file missing.")
    return FileResponse(path, filename=path.name)


@app.get("/lectures/{lecture_id}/artifacts")
def review_artifacts(
    lecture_id: str,
    artifact_type: Optional[str] = None,
    preset_id: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> dict:
    db = get_database()
    artifact_records = db.fetch_artifacts(
        lecture_id,
        artifact_type=artifact_type,
        preset_id=preset_id,
        limit=limit,
        offset=offset,
    )
    payload: dict[str, object] = {}
    artifact_paths: dict[str, str] = {}
    artifact_downloads: dict[str, str] = {}
    for record in artifact_records:
        artifact_type_key = record["artifact_type"]
        storage_path = record["storage_path"]
        artifact_paths[artifact_type_key] = storage_path
        if storage_path.startswith("s3://"):
            url = download_url(storage_path)
            if url:
                artifact_downloads[artifact_type_key] = url
            payload[artifact_type_key] = None
            continue
        path = Path(storage_path)
        if path.exists():
            payload[artifact_type_key] = json.loads(path.read_text(encoding="utf-8"))
        else:
            payload[artifact_type_key] = None
    threads = db.fetch_threads(lecture_id)
    if threads:
        payload.setdefault("threads", threads)
    return {
        "lectureId": lecture_id,
        "artifacts": payload,
        "artifactRecords": artifact_records,
        "artifactPaths": artifact_paths,
        "artifactDownloadUrls": artifact_downloads,
        "exportRecords": db.fetch_exports(lecture_id),
        "lecture": db.fetch_lecture(lecture_id),
    }


@app.get("/lectures/{lecture_id}/summary")
def lecture_summary(lecture_id: str) -> dict:
    db = get_database()
    lecture = db.fetch_lecture(lecture_id)
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found.")
    artifacts = db.fetch_artifacts(lecture_id)
    exports = db.fetch_exports(lecture_id)
    return {
        "lecture": lecture,
        "artifactCount": len(artifacts),
        "exportCount": len(exports),
        "artifactTypes": [row["artifact_type"] for row in artifacts],
        "exportTypes": [row["export_type"] for row in exports],
        "links": {
            "artifacts": f"/lectures/{lecture_id}/artifacts",
            "exports": f"/exports/{lecture_id}/{{export_type}}",
            "jobs": "/jobs/{job_id}",

            @app.get("/courses/{course_id}/threads/{title}/history")
def get_thread_history(course_id: str, title: str):
    db = get_database()
    # 1. Find the core thread record
    thread = db.fetch_thread_by_title(course_id, title)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    # 2. Fetch all chronological updates and occurrences for this thread
    history = db.fetch_thread_evolution(thread["id"])
    
    return {
        "thread": thread,
        "timeline": history # Returns chronological list of refinements and complexity jumps
    }
        },
    }
