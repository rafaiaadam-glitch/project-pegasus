from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from typing import Callable, Optional

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from redis import Redis

from backend.db import get_database
from backend.jobs import (
    enqueue_job,
    run_export_job,
    run_generation_job,
    run_transcription_job,
)
from backend.presets import PRESETS, PRESETS_BY_ID
from backend.storage import download_url, load_json_payload, save_audio

app = FastAPI(title="Pegasus Lecture Copilot API")
STORAGE_DIR = Path(os.getenv("PLC_STORAGE_DIR", "storage")).resolve()


class GenerateRequest(BaseModel):
    course_id: Optional[str] = None
    preset_id: Optional[str] = None
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


def _ensure_valid_preset_id(preset_id: str) -> None:
    if preset_id not in PRESETS_BY_ID:
        raise HTTPException(status_code=400, detail="Invalid preset_id.")


def _ensure_course_exists(db, course_id: str) -> None:
    fetch_course = getattr(db, "fetch_course", None)
    if callable(fetch_course) and not fetch_course(course_id):
        raise HTTPException(status_code=404, detail="Course not found.")


def _validate_generation_context(db, lecture_id: str, course_id: str, preset_id: str) -> None:
    lecture = db.fetch_lecture(lecture_id)
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found.")
    lecture_course_id = lecture.get("course_id")
    if lecture_course_id and lecture_course_id != course_id:
        raise HTTPException(status_code=400, detail="course_id does not match lecture.")
    lecture_preset_id = lecture.get("preset_id")
    if lecture_preset_id and lecture_preset_id != preset_id:
        raise HTTPException(status_code=400, detail="preset_id does not match lecture.")


def _resolve_generation_identifiers(db, lecture_id: str, payload: GenerateRequest) -> tuple[str, str]:
    lecture = db.fetch_lecture(lecture_id)
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found.")

    course_id = payload.course_id or lecture.get("course_id")
    if not course_id:
        raise HTTPException(status_code=400, detail="course_id is required.")

    preset_id = payload.preset_id or lecture.get("preset_id")
    if not preset_id:
        raise HTTPException(status_code=400, detail="preset_id is required.")

    _ensure_valid_preset_id(preset_id)
    _validate_generation_context(db, lecture_id, course_id, preset_id)
    _ensure_course_exists(db, course_id)
    return course_id, preset_id


def _latest_jobs_by_type(jobs: list[dict]) -> dict[str, dict]:
    latest_by_type: dict[str, dict] = {}
    for job in jobs:
        job_type = job.get("job_type")
        if not job_type or job_type in latest_by_type:
            continue
        latest_by_type[job_type] = job
    return latest_by_type


def _fetch_course_or_404(db, course_id: str) -> dict:
    course = db.fetch_course(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")
    return course


def _compute_stage_progress(latest_by_type: dict[str, dict], stage_order: list[str]) -> dict:
    stages: dict[str, dict] = {}
    for stage in stage_order:
        latest = latest_by_type.get(stage)
        stages[stage] = {
            "status": latest.get("status") if latest else "not_started",
            "jobId": latest.get("id") if latest else None,
            "createdAt": latest.get("created_at") if latest else None,
            "updatedAt": latest.get("updated_at") if latest else None,
            "error": latest.get("error") if latest else None,
        }

    completed_count = sum(1 for stage in stage_order if stages[stage]["status"] == "completed")
    progress_percent = int((completed_count / len(stage_order)) * 100)
    current_stage = next(
        (stage for stage in stage_order if stages[stage]["status"] != "completed"),
        "completed",
    )
    has_failed_stage = any(stages[stage]["status"] == "failed" for stage in stage_order)

    return {
        "stageCount": len(stage_order),
        "completedStageCount": completed_count,
        "progressPercent": progress_percent,
        "currentStage": current_stage,
        "hasFailedStage": has_failed_stage,
        "stages": stages,
    }


def _derive_overall_status(stage_progress: dict) -> str:
    if stage_progress["hasFailedStage"]:
        return "failed"
    if stage_progress["completedStageCount"] == stage_progress["stageCount"]:
        return "completed"

    # A lecture is considered in progress as soon as any stage has started,
    # including queued/running work before the first completion.
    any_started = any(
        stage.get("status") not in {None, "not_started"}
        for stage in stage_progress.get("stages", {}).values()
    )
    if any_started:
        return "in_progress"

    return "not_started"


def _build_lecture_progress_payload(db, lecture_id: str, lecture_status: Optional[str]) -> dict:
    stage_order = ["transcription", "generation", "export"]
    progress = _compute_stage_progress(
        _latest_jobs_by_type(db.fetch_jobs(lecture_id=lecture_id)),
        stage_order,
    )
    return {
        "lectureId": lecture_id,
        "lectureStatus": lecture_status,
        "overallStatus": _derive_overall_status(progress),
        "stageCount": progress["stageCount"],
        "completedStageCount": progress["completedStageCount"],
        "progressPercent": progress["progressPercent"],
        "currentStage": progress["currentStage"],
        "hasFailedStage": progress["hasFailedStage"],
        "stages": progress["stages"],
    }


def _lecture_links(lecture_id: str) -> dict[str, str]:
    return {
        "summary": f"/lectures/{lecture_id}/summary",
        "progress": f"/lectures/{lecture_id}/progress",
        "artifacts": f"/lectures/{lecture_id}/artifacts",
        "jobs": f"/lectures/{lecture_id}/jobs",
    }


def _pagination_payload(
    *,
    limit: Optional[int],
    offset: Optional[int],
    count: int,
    total: int,
) -> dict:
    normalized_offset = offset or 0
    normalized_limit = limit if limit is not None else count
    page_size_for_prev = normalized_limit if normalized_limit > 0 else 1
    has_more = normalized_offset + count < total
    next_offset = normalized_offset + count if has_more else None
    prev_offset = max(0, normalized_offset - page_size_for_prev) if normalized_offset > 0 else None
    return {
        "limit": limit,
        "offset": normalized_offset,
        "count": count,
        "total": total,
        "hasMore": has_more,
        "nextOffset": next_offset,
        "prevOffset": prev_offset,
    }


def _count_with_fallback(
    db,
    count_method: str,
    fallback_rows: list[dict],
    *args,
    fallback_counter: Optional[Callable[[], int]] = None,
    **kwargs,
) -> int:
    counter = getattr(db, count_method, None)
    if callable(counter):
        return int(counter(*args, **kwargs))
    if callable(fallback_counter):
        return int(fallback_counter())
    return len(fallback_rows)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "time": _iso_now()}


@app.get("/health/ready")
def readiness() -> JSONResponse:
    checks: dict[str, dict[str, str]] = {}
    overall_status = "ok"

    db = get_database()
    try:
        db.healthcheck()
        checks["database"] = {"status": "ok"}
    except Exception as exc:
        overall_status = "degraded"
        checks["database"] = {"status": "error", "reason": str(exc)}

    inline_jobs = os.getenv("PLC_INLINE_JOBS", "").strip().lower() in {"1", "true", "yes", "on"}
    if inline_jobs:
        checks["queue"] = {"status": "skipped", "reason": "PLC_INLINE_JOBS is enabled."}
    else:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            redis_client = Redis.from_url(redis_url)
            redis_client.ping()
            checks["queue"] = {"status": "ok"}
        except Exception as exc:
            overall_status = "degraded"
            checks["queue"] = {"status": "error", "reason": str(exc)}

    try:
        _ensure_dirs()
        probe = STORAGE_DIR / ".ready"
        probe.write_text(_iso_now(), encoding="utf-8")
        probe.unlink(missing_ok=True)
        checks["storage"] = {"status": "ok"}
    except Exception as exc:
        overall_status = "degraded"
        checks["storage"] = {"status": "error", "reason": str(exc)}

    status_code = 200 if overall_status == "ok" else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": overall_status,
            "time": _iso_now(),
            "checks": checks,
        },
    )


@app.get("/presets")
def list_presets() -> dict:
    return {"presets": PRESETS}


@app.get("/presets/{preset_id}")
def get_preset(preset_id: str) -> dict:
    preset = PRESETS_BY_ID.get(preset_id)
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found.")
    return preset


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
    _ensure_valid_preset_id(preset_id)
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
def list_courses(
    limit: Optional[int] = Query(default=None, ge=0),
    offset: Optional[int] = Query(default=None, ge=0),
) -> dict:
    db = get_database()
    courses = db.fetch_courses(limit=limit, offset=offset)
    total = _count_with_fallback(
        db,
        "count_courses",
        courses,
        fallback_counter=lambda: len(db.fetch_courses()),
    )
    return {
        "courses": courses,
        "pagination": _pagination_payload(
            limit=limit,
            offset=offset,
            count=len(courses),
            total=total,
        ),
    }


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
    status: Optional[str] = None,
    preset_id: Optional[str] = None,
    limit: Optional[int] = Query(default=None, ge=0),
    offset: Optional[int] = Query(default=None, ge=0),
) -> dict:
    if preset_id:
        _ensure_valid_preset_id(preset_id)

    db = get_database()
    _fetch_course_or_404(db, course_id)
    lectures = db.fetch_lectures(
        course_id=course_id,
        status=status,
        preset_id=preset_id,
        limit=limit,
        offset=offset,
    )
    total = _count_with_fallback(
        db,
        "count_lectures",
        lectures,
        course_id=course_id,
        status=status,
        preset_id=preset_id,
        fallback_counter=lambda: len(
            db.fetch_lectures(course_id=course_id, status=status, preset_id=preset_id)
        ),
    )
    return {
        "courseId": course_id,
        "lectures": lectures,
        "pagination": _pagination_payload(
            limit=limit,
            offset=offset,
            count=len(lectures),
            total=total,
        ),
    }


@app.get("/courses/{course_id}/threads")
def list_course_threads(
    course_id: str,
    limit: Optional[int] = Query(default=None, ge=0),
    offset: Optional[int] = Query(default=None, ge=0),
) -> dict:
    db = get_database()
    _fetch_course_or_404(db, course_id)
    threads = db.fetch_threads_for_course(course_id, limit=limit, offset=offset)
    total = _count_with_fallback(
        db,
        "count_threads_for_course",
        threads,
        course_id,
        fallback_counter=lambda: len(db.fetch_threads_for_course(course_id)),
    )
    return {
        "courseId": course_id,
        "threads": threads,
        "pagination": _pagination_payload(
            limit=limit,
            offset=offset,
            count=len(threads),
            total=total,
        ),
    }


@app.get("/courses/{course_id}/progress")
def course_progress(course_id: str, include_lectures: bool = True) -> dict:
    db = get_database()
    _fetch_course_or_404(db, course_id)

    lectures = db.fetch_lectures(course_id=course_id)
    stage_order = ["transcription", "generation", "export"]

    lecture_progress = []
    status_counts = {
        "not_started": 0,
        "in_progress": 0,
        "completed": 0,
        "failed": 0,
    }
    latest_activity_at: Optional[str] = None

    for lecture in lectures:
        lecture_id = lecture["id"]
        progress_payload = _build_lecture_progress_payload(db, lecture_id, lecture.get("status"))

        overall_status = progress_payload["overallStatus"]
        if overall_status in status_counts:
            status_counts[overall_status] += 1

        lecture_timestamps = []
        for stage in stage_order:
            stage_payload = progress_payload["stages"][stage]
            stage_activity = stage_payload.get("updatedAt") or stage_payload.get("createdAt")
            if stage_activity:
                lecture_timestamps.append(stage_activity)
        lecture_timestamps.extend(
            [
                lecture.get("updated_at"),
                lecture.get("created_at"),
            ]
        )
        lecture_timestamps = [value for value in lecture_timestamps if value]
        lecture_latest = max(lecture_timestamps) if lecture_timestamps else None
        if lecture_latest and (latest_activity_at is None or lecture_latest > latest_activity_at):
            latest_activity_at = lecture_latest

        lecture_progress.append(
            {
                **progress_payload,
                "stageStatuses": {
                    stage: progress_payload["stages"][stage]["status"] for stage in stage_order
                },
                "links": _lecture_links(lecture_id),
            }
        )

    total_lectures = len(lectures)
    course_progress_percent = round(
        (sum(row["progressPercent"] for row in lecture_progress) / total_lectures)
    ) if total_lectures else 0

    if status_counts["failed"] > 0:
        overall_status = "failed"
    elif total_lectures > 0 and status_counts["completed"] == total_lectures:
        overall_status = "completed"
    elif course_progress_percent > 0:
        overall_status = "in_progress"
    else:
        overall_status = "not_started"

    payload = {
        "courseId": course_id,
        "overallStatus": overall_status,
        "lectureCount": total_lectures,
        "completedLectureCount": status_counts["completed"],
        "failedLectureCount": status_counts["failed"],
        "inProgressLectureCount": status_counts["in_progress"],
        "notStartedLectureCount": status_counts["not_started"],
        "progressPercent": course_progress_percent,
        "latestActivityAt": latest_activity_at,
    }
    if include_lectures:
        payload["lectures"] = lecture_progress
    return payload



@app.get("/lectures/{lecture_id}")
def get_lecture(lecture_id: str) -> dict:
    db = get_database()
    lecture = db.fetch_lecture(lecture_id)
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found.")
    return lecture

@app.get("/lectures/{lecture_id}/transcript")
def get_lecture_transcript(
    lecture_id: str,
    include_text: bool = Query(default=True),
    segment_limit: Optional[int] = Query(default=None, ge=0),
) -> dict:
    db = get_database()
    lecture = db.fetch_lecture(lecture_id)
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found.")

    transcript_path = lecture.get("transcript_path")
    if not transcript_path:
        raise HTTPException(status_code=404, detail="Transcript not found for lecture.")

    try:
        transcript = load_json_payload(transcript_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Transcript file missing.")

    segments = transcript.get("segments", [])
    if segment_limit is not None:
        segments = segments[:segment_limit]

    return {
        "lectureId": lecture_id,
        "transcriptPath": transcript_path,
        "language": transcript.get("language"),
        "text": transcript.get("text", "") if include_text else "",
        "segments": segments,
        "segmentCount": len(segments),
    }

@app.get("/lectures")
def list_lectures(
    course_id: Optional[str] = None,
    status: Optional[str] = None,
    preset_id: Optional[str] = None,
    limit: Optional[int] = Query(default=None, ge=0),
    offset: Optional[int] = Query(default=None, ge=0),
) -> dict:
    if preset_id:
        _ensure_valid_preset_id(preset_id)

    db = get_database()
    lectures = db.fetch_lectures(
        course_id=course_id,
        status=status,
        preset_id=preset_id,
        limit=limit,
        offset=offset,
    )
    total = _count_with_fallback(
        db,
        "count_lectures",
        lectures,
        course_id=course_id,
        status=status,
        preset_id=preset_id,
        fallback_counter=lambda: len(
            db.fetch_lectures(course_id=course_id, status=status, preset_id=preset_id)
        ),
    )
    return {
        "lectures": lectures,
        "pagination": _pagination_payload(
            limit=limit,
            offset=offset,
            count=len(lectures),
            total=total,
        ),
    }


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
    if payload.preset_id:
        _ensure_valid_preset_id(payload.preset_id)

    db = get_database()
    course_id, preset_id = _resolve_generation_identifiers(db, lecture_id, payload)
    job_id = enqueue_job(
        "generation",
        lecture_id,
        run_generation_job,
        lecture_id,
        course_id,
        preset_id,
        payload.openai_model or os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    )
    job = db.fetch_job(job_id)
    return {
        "jobId": job_id,
        "status": job["status"] if job else "queued",
        "jobType": job.get("job_type") if job else "generation",
        "courseId": course_id,
        "presetId": preset_id,
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


@app.get("/lectures/{lecture_id}/jobs")
def list_lecture_jobs(
    lecture_id: str,
    limit: Optional[int] = Query(default=None, ge=0),
    offset: Optional[int] = Query(default=None, ge=0),
) -> dict:
    db = get_database()
    lecture = db.fetch_lecture(lecture_id)
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found.")
    jobs = db.fetch_jobs(lecture_id=lecture_id, limit=limit, offset=offset)
    total = _count_with_fallback(
        db,
        "count_jobs",
        jobs,
        lecture_id=lecture_id,
        fallback_counter=lambda: len(db.fetch_jobs(lecture_id=lecture_id)),
    )
    return {
        "lectureId": lecture_id,
        "jobs": [
            {
                "id": job["id"],
                "status": job["status"],
                "jobType": job.get("job_type"),
                "result": job.get("result"),
                "error": job.get("error"),
                "createdAt": job.get("created_at"),
                "updatedAt": job.get("updated_at"),
            }
            for job in jobs
        ],
        "pagination": _pagination_payload(
            limit=limit,
            offset=offset,
            count=len(jobs),
            total=total,
        ),
    }


@app.get("/lectures/{lecture_id}/progress")
def lecture_progress(lecture_id: str) -> dict:
    db = get_database()
    lecture = db.fetch_lecture(lecture_id)
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found.")

    payload = _build_lecture_progress_payload(db, lecture_id, lecture.get("status"))
    payload["links"] = _lecture_links(lecture_id)
    return payload


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
    limit: Optional[int] = Query(default=None, ge=0),
    offset: Optional[int] = Query(default=None, ge=0),
) -> dict:
    if preset_id:
        _ensure_valid_preset_id(preset_id)

    db = get_database()
    artifact_records = db.fetch_artifacts(
        lecture_id,
        artifact_type=artifact_type,
        preset_id=preset_id,
        limit=limit,
        offset=offset,
    )
    total = _count_with_fallback(
        db,
        "count_artifacts",
        artifact_records,
        lecture_id,
        artifact_type=artifact_type,
        preset_id=preset_id,
        fallback_counter=lambda: len(
            db.fetch_artifacts(
                lecture_id,
                artifact_type=artifact_type,
                preset_id=preset_id,
            )
        ),
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
        "pagination": _pagination_payload(
            limit=limit,
            offset=offset,
            count=len(artifact_records),
            total=total,
        ),
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
    progress = _build_lecture_progress_payload(db, lecture_id, lecture.get("status"))
    return {
        "lecture": lecture,
        "artifactCount": len(artifacts),
        "exportCount": len(exports),
        "artifactTypes": [row["artifact_type"] for row in artifacts],
        "exportTypes": [row["export_type"] for row in exports],
        "overallStatus": progress["overallStatus"],
        "progressPercent": progress["progressPercent"],
        "currentStage": progress["currentStage"],
        "hasFailedStage": progress["hasFailedStage"],
        "stages": progress["stages"],
        "links": {
            **_lecture_links(lecture_id),
            "exports": f"/exports/{lecture_id}/{{export_type}}",
        },
    }
