from __future__ import annotations

import copy
import json
import logging
import os
import secrets
from collections import defaultdict, deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from typing import Callable, Optional
import threading

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel
from redis import Redis

from backend.db import get_database
from backend.idempotency import (
    InMemoryIdempotencyStore,
    maybe_replay_response,
    store_idempotent_response,
)
from backend.observability import METRICS, render_prometheus_metrics
from backend.jobs import (
    enqueue_job,
    run_export_job,
    run_generation_job,
    run_transcription_job,
)
from backend.presets import PRESETS, PRESETS_BY_ID
from backend.runtime_config import validate_runtime_environment
from backend.storage import (
    delete_storage_path,
    download_url,
    load_json_payload,
    save_audio,
    save_document,
    storage_path_exists,
)



@asynccontextmanager
async def app_lifespan(_: FastAPI) -> AsyncIterator[None]:
    validate_runtime_environment("api")
    yield


app = FastAPI(title="Pegasus Lecture Copilot API", lifespan=app_lifespan)

# Configure CORS for mobile app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

LOGGER = logging.getLogger("pegasus.api")
STORAGE_DIR = Path(os.getenv("PLC_STORAGE_DIR", "storage")).resolve()

@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid4())
    request.state.request_id = request_id

    started_at = perf_counter()
    response = await call_next(request)
    duration_ms = (perf_counter() - started_at) * 1000

    response.headers["x-request-id"] = request_id
    LOGGER.info(
        "request.complete",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
        },
    )
    return response




class _InMemoryRateLimiter:
    def __init__(self) -> None:
        self._events_by_key: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, *, limit: int, window_seconds: int, now: float) -> bool:
        cutoff = now - window_seconds
        with self._lock:
            events = self._events_by_key[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit:
                return False
            events.append(now)
            return True


_WRITE_RATE_LIMITER = _InMemoryRateLimiter()
_IDEMPOTENCY_STORE = InMemoryIdempotencyStore()

class GenerateRequest(BaseModel):
    course_id: Optional[str] = None
    preset_id: Optional[str] = None
    openai_model: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _enforce_write_auth(request: Request) -> None:
    expected_token = os.getenv("PLC_WRITE_API_TOKEN", "").strip()
    if not expected_token:
        return

    authorization = request.headers.get("authorization", "")
    scheme, _, provided_token = authorization.partition(" ")

    if scheme.lower() != "bearer" or not provided_token.strip():
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header.")

    if not secrets.compare_digest(provided_token.strip(), expected_token):
        raise HTTPException(status_code=403, detail="Invalid API token.")




def _parse_positive_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default)).strip()
    try:
        parsed = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer.") from exc
    if parsed <= 0:
        raise RuntimeError(f"{name} must be a positive integer.")
    return parsed


def _write_rate_limit_config() -> tuple[int, int]:
    max_requests = _parse_positive_int_env("PLC_WRITE_RATE_LIMIT_MAX_REQUESTS", 60)
    window_seconds = _parse_positive_int_env("PLC_WRITE_RATE_LIMIT_WINDOW_SEC", 60)
    return max_requests, window_seconds


def _client_identifier(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for.strip():
        return forwarded_for.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _enforce_write_rate_limit(request: Request, *, now: Optional[float] = None) -> None:
    max_requests, window_seconds = _write_rate_limit_config()
    timestamp = now if now is not None else perf_counter()
    if not _WRITE_RATE_LIMITER.allow(
        _client_identifier(request),
        limit=max_requests,
        window_seconds=window_seconds,
        now=timestamp,
    ):
        raise HTTPException(
            status_code=429,
            detail="Too many write requests. Please retry shortly.",
        )



def _idempotency_fingerprint(operation: str, payload: dict) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return operation + ":" + serialized


def _replay_or_none(request: Request, operation: str, payload: dict) -> Optional[dict]:
    return maybe_replay_response(
        request,
        _IDEMPOTENCY_STORE,
        scope=operation,
        fingerprint=_idempotency_fingerprint(operation, payload),
    )


def _remember_response(request: Request, operation: str, payload: dict, response_payload: dict) -> None:
    store_idempotent_response(
        request,
        _IDEMPOTENCY_STORE,
        scope=operation,
        fingerprint=_idempotency_fingerprint(operation, payload),
        response_payload=response_payload,
    )

def _ensure_dirs() -> None:
    (STORAGE_DIR / "audio").mkdir(parents=True, exist_ok=True)
    (STORAGE_DIR / "documents").mkdir(parents=True, exist_ok=True)
    (STORAGE_DIR / "metadata").mkdir(parents=True, exist_ok=True)
    (STORAGE_DIR / "transcripts").mkdir(parents=True, exist_ok=True)
    (STORAGE_DIR / "exports").mkdir(parents=True, exist_ok=True)




def _max_audio_upload_bytes() -> int:
    raw_value = os.getenv("PLC_MAX_AUDIO_UPLOAD_MB", "200").strip()
    try:
        limit_mb = int(raw_value)
    except ValueError as exc:
        raise RuntimeError("PLC_MAX_AUDIO_UPLOAD_MB must be an integer.") from exc
    if limit_mb <= 0:
        raise RuntimeError("PLC_MAX_AUDIO_UPLOAD_MB must be a positive integer.")
    return limit_mb * 1024 * 1024


def _max_pdf_upload_bytes() -> int:
    raw_value = os.getenv("PLC_MAX_PDF_UPLOAD_MB", "50").strip()
    try:
        limit_mb = int(raw_value)
    except ValueError as exc:
        raise RuntimeError("PLC_MAX_PDF_UPLOAD_MB must be an integer.") from exc
    if limit_mb <= 0:
        raise RuntimeError("PLC_MAX_PDF_UPLOAD_MB must be a positive integer.")
    return limit_mb * 1024 * 1024


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


def _validate_generation_context(lecture: dict, course_id: str, preset_id: str) -> None:
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
    _validate_generation_context(lecture, course_id, preset_id)
    _ensure_course_exists(db, course_id)
    return course_id, preset_id




def _find_active_job_for_lecture(db, lecture_id: str, job_type: str) -> Optional[dict]:
    fetch_jobs = getattr(db, "fetch_jobs", None)
    if not callable(fetch_jobs):
        return None

    try:
        jobs = fetch_jobs(lecture_id=lecture_id)
    except Exception:
        return None

    if not isinstance(jobs, list):
        return None

    for job in jobs:
        if not isinstance(job, dict):
            continue
        if job.get("job_type") != job_type:
            continue
        if job.get("status") in {"queued", "running"}:
            return job
    return None

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


def _request_actor(request: Request) -> str:
    actor = request.headers.get("x-actor-id", "").strip()
    if actor:
        return actor

    authorization = request.headers.get("authorization", "").strip()
    if authorization.lower().startswith("bearer "):
        return "bearer-token"

    return "anonymous"


def _deletion_audit_result_summary(entity_type: str, result: dict) -> dict:
    if entity_type == "lecture":
        deleted = result.get("deleted") if isinstance(result.get("deleted"), dict) else {}
        return {
            "lectureId": result.get("lectureId"),
            "deleted": {
                "artifacts": int(deleted.get("artifacts") or 0),
                "exports": int(deleted.get("exports") or 0),
                "jobs": int(deleted.get("jobs") or 0),
                "lectures": int(deleted.get("lectures") or 0),
                "threadsUpdated": int(deleted.get("threadsUpdated") or 0),
                "storagePaths": int(deleted.get("storagePaths") or 0),
                "metadataRemoved": bool(deleted.get("metadataRemoved")),
            },
        }

    lecture_deletions = []
    for lecture in result.get("lectureDeletions") or []:
        if not isinstance(lecture, dict):
            continue
        lecture_deleted = lecture.get("deleted") if isinstance(lecture.get("deleted"), dict) else {}
        lecture_deletions.append(
            {
                "lectureId": lecture.get("lectureId"),
                "deleted": {
                    "lectures": int(lecture_deleted.get("lectures") or 0),
                    "artifacts": int(lecture_deleted.get("artifacts") or 0),
                    "exports": int(lecture_deleted.get("exports") or 0),
                    "jobs": int(lecture_deleted.get("jobs") or 0),
                },
            }
        )

    return {
        "courseId": result.get("courseId"),
        "courseDeleted": bool(result.get("courseDeleted")),
        "lecturesDeleted": int(result.get("lecturesDeleted") or 0),
        "lectureDeletions": lecture_deletions,
    }


def _record_deletion_audit_event(
    db,
    *,
    request: Request,
    entity_type: str,
    entity_id: str,
    purge_storage: bool,
    result: dict,
) -> Optional[str]:
    create_event = getattr(db, "create_deletion_audit_event", None)
    if not callable(create_event):
        return None

    event_id = str(uuid4())
    create_event(
        {
            "id": event_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "actor": _request_actor(request),
            "request_id": getattr(request.state, "request_id", None),
            "purge_storage": purge_storage,
            "result": copy.deepcopy(_deletion_audit_result_summary(entity_type, result)),
            "created_at": _iso_now(),
        }
    )
    return event_id


def _validate_deletion_entity_type(entity_type: Optional[str]) -> Optional[str]:
    if entity_type is None:
        return None
    normalized = entity_type.strip().lower()
    if normalized not in {"lecture", "course"}:
        raise HTTPException(status_code=400, detail="entity_type must be one of: lecture, course.")
    return normalized


def _delete_lecture_data(db, lecture_id: str, *, purge_storage: bool) -> dict:
    lecture = db.fetch_lecture(lecture_id)
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found.")

    artifacts = db.fetch_artifacts(lecture_id)
    exports = db.fetch_exports(lecture_id)
    threads = db.fetch_threads(lecture_id)

    storage_paths: list[str] = []
    for path in (
        lecture.get("audio_path"),
        lecture.get("transcript_path"),
        *[row.get("storage_path") for row in artifacts],
        *[row.get("storage_path") for row in exports],
    ):
        if path:
            storage_paths.append(path)

    for thread in threads:
        thread_id = thread.get("id")
        if not thread_id:
            continue
        refs = [ref for ref in (thread.get("lecture_refs") or []) if ref != lecture_id]
        if refs:
            update_refs = getattr(db, "update_thread_lecture_refs", None)
            if callable(update_refs):
                update_refs(thread_id, refs)
        else:
            delete_thread = getattr(db, "delete_thread", None)
            if callable(delete_thread):
                delete_thread(thread_id)

    delete_records = getattr(db, "delete_lecture_records", None)
    if not callable(delete_records):
        raise HTTPException(status_code=500, detail="Database does not support lecture deletion.")
    deleted_counts = delete_records(lecture_id)

    metadata_path = STORAGE_DIR / "metadata" / f"{lecture_id}.json"
    storage_deleted = 0
    if purge_storage:
        for storage_path in storage_paths:
            if delete_storage_path(storage_path):
                storage_deleted += 1
        if metadata_path.exists():
            metadata_path.unlink()
            storage_deleted += 1

    return {
        "lectureId": lecture_id,
        "deleted": {
            **deleted_counts,
            "threadsUpdated": len(threads),
            "storagePaths": storage_deleted,
            "metadataRemoved": purge_storage and not metadata_path.exists(),
        },
    }



def _build_lecture_integrity_payload(lecture_id: str) -> dict:
    db = get_database()
    lecture = db.fetch_lecture(lecture_id)
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found.")

    checks: list[dict[str, object]] = []

    def add_check(label: str, path: Optional[str]) -> None:
        if not path:
            checks.append({"kind": label, "path": None, "exists": False, "state": "missing_reference"})
            return
        exists = storage_path_exists(path)
        checks.append(
            {
                "kind": label,
                "path": path,
                "exists": exists,
                "state": "ok" if exists else "missing_file",
            }
        )

    add_check("audio", lecture.get("audio_path"))
    add_check("transcript", lecture.get("transcript_path"))

    artifacts = db.fetch_artifacts(lecture_id)
    for artifact in artifacts:
        add_check(f"artifact:{artifact.get('artifact_type')}", artifact.get("storage_path"))

    exports = db.fetch_exports(lecture_id)
    for export in exports:
        add_check(f"export:{export.get('export_type')}", export.get("storage_path"))

    missing_count = sum(1 for check in checks if not check["exists"])
    return {
        "lectureId": lecture_id,
        "status": "ok" if missing_count == 0 else "degraded",
        "missingCount": missing_count,
        "checkCount": len(checks),
        "checks": checks,
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


def _queue_depth_snapshot(db) -> dict[str, int]:
    jobs = db.fetch_jobs() if hasattr(db, "fetch_jobs") else []
    depth = {"queued": 0, "running": 0, "failed": 0}
    for job in jobs:
        status = str(job.get("status") or "").strip().lower()
        if status in depth:
            depth[status] += 1
    return depth


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


@app.get("/ops/metrics")
def ops_metrics() -> dict:
    db = get_database()
    queue_depth = _queue_depth_snapshot(db)
    return {
        "status": "ok",
        "time": _iso_now(),
        "metrics": METRICS.snapshot(queue_depth=queue_depth),
    }


@app.get("/ops/metrics/prometheus")
def ops_metrics_prometheus() -> PlainTextResponse:
    db = get_database()
    queue_depth = _queue_depth_snapshot(db)
    snapshot = METRICS.snapshot(queue_depth=queue_depth)
    return PlainTextResponse(
        content=render_prometheus_metrics(snapshot),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


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
    request: Request,
    course_id: str = Form(...),
    lecture_id: str = Form(...),
    preset_id: str = Form(...),
    title: str = Form(...),
    course_title: Optional[str] = Form(None),
    duration_sec: int = Form(0),
    source_type: str = Form("upload"),
    lecture_mode: Optional[str] = Form(None),
    audio: Optional[UploadFile] = File(None),
    file: Optional[UploadFile] = File(None),
    auto_transcribe: bool = Form(True),
    transcribe_provider: Optional[str] = Form(None),
    transcribe_model: Optional[str] = Form(None),
    transcribe_language_code: Optional[str] = Form(None),
) -> dict:
    _enforce_write_auth(request)
    _enforce_write_rate_limit(request)

    # Accept either 'audio' or 'file' parameter for backward compatibility
    uploaded_file = audio or file
    if not uploaded_file:
        raise HTTPException(status_code=400, detail="Either 'audio' or 'file' parameter is required")

    # Detect file type from content-type or extension
    content_type = uploaded_file.content_type or ""
    ext = Path(uploaded_file.filename or "").suffix.lower() or ".bin"
    is_pdf = content_type == "application/pdf" or ext == ".pdf"
    file_type = "pdf" if is_pdf else "audio"

    idempotency_payload = {
        "course_id": course_id,
        "lecture_id": lecture_id,
        "preset_id": preset_id,
        "title": title,
        "duration_sec": duration_sec,
        "source_type": source_type,
        "lecture_mode": lecture_mode or "",
        "audio_filename": uploaded_file.filename or "",
        "file_type": file_type,
    }
    replay = _replay_or_none(request, "lectures.ingest", idempotency_payload)
    if replay is not None:
        return replay
    _ensure_valid_preset_id(preset_id)
    _ensure_dirs()

    # Route to appropriate storage function based on file type
    try:
        if is_pdf:
            stored_path = save_document(
                uploaded_file.file,
                f"{lecture_id}.pdf",
                max_bytes=_max_pdf_upload_bytes(),
            )
        else:
            stored_path = save_audio(
                uploaded_file.file,
                f"{lecture_id}{ext}",
                max_bytes=_max_audio_upload_bytes(),
            )
    except ValueError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc

    metadata = {
        "id": lecture_id,
        "courseId": course_id,
        "presetId": preset_id,
        "title": title,
        "lectureMode": lecture_mode,
        "recordedAt": _iso_now(),
        "durationSec": duration_sec,
        "audioSource": {
            "sourceType": source_type,
            "originalFilename": uploaded_file.filename,
            "storagePath": stored_path,
            "sizeBytes": Path(stored_path).stat().st_size if not stored_path.startswith(("s3://", "gs://")) else 0,
            "checksumSha256": _sha256(Path(stored_path)) if not stored_path.startswith(("s3://", "gs://")) else "",
            "fileType": file_type,
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
            "audio_path": stored_path,
            "transcript_path": None,
            "source_type": file_type,
            "created_at": _iso_now(),
            "updated_at": _iso_now(),
        }
    )

    transcription_job: Optional[dict] = None
    if auto_transcribe:
        provider = transcribe_provider or os.getenv("PLC_INGEST_TRANSCRIBE_PROVIDER", "google")
        model = transcribe_model or os.getenv("PLC_INGEST_TRANSCRIBE_MODEL", "base")
        language_code = transcribe_language_code or os.getenv("PLC_STT_LANGUAGE")

        job_id = enqueue_job(
            "transcription",
            lecture_id,
            run_transcription_job,
            lecture_id,
            model,
            provider,
            language_code,
        )
        job = db.fetch_job(job_id)
        transcription_job = {
            "jobId": job_id,
            "status": job["status"] if job else "queued",
            "jobType": job.get("job_type") if job else "transcription",
            "provider": provider,
            "model": model,
        }

    response_payload = {
        "lectureId": lecture_id,
        "metadataPath": str(metadata_path),
        "audioPath": stored_path,
        "lectureMode": lecture_mode,
        "fileType": file_type,
    }
    _remember_response(request, "lectures.ingest", idempotency_payload, response_payload)
    return response_payload


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
def transcribe_lecture(
    request: Request,
    lecture_id: str,
    model: str = "latest_long",  # Google STT model
    provider: str = "google",  # Default to Google Speech-to-Text
    language_code: Optional[str] = None,
) -> dict:
    _enforce_write_auth(request)
    _enforce_write_rate_limit(request)
    idempotency_payload = {
        "lecture_id": lecture_id,
        "model": model,
        "provider": provider,
        "language_code": language_code,
    }
    replay = _replay_or_none(request, "lectures.transcribe", idempotency_payload)
    if replay is not None:
        return replay
    _ensure_dirs()
    audio_files = list((STORAGE_DIR / "audio").glob(f"{lecture_id}.*"))
    if not audio_files:
        raise HTTPException(status_code=404, detail="Audio not found for lecture.")
    db = get_database()
    active_job = _find_active_job_for_lecture(db, lecture_id, "transcription")
    if active_job:
        response_payload = {
            "jobId": active_job.get("id"),
            "status": active_job.get("status", "queued"),
            "jobType": "transcription",
            "deduplicated": True,
        }
        _remember_response(request, "lectures.transcribe", idempotency_payload, response_payload)
        return response_payload

    job_id = enqueue_job(
        "transcription",
        lecture_id,
        run_transcription_job,
        lecture_id,
        model,
        provider,
        language_code,
    )
    job = db.fetch_job(job_id)
    response_payload = {
        "jobId": job_id,
        "status": job["status"] if job else "queued",
        "jobType": job.get("job_type") if job else "transcription",
    }
    _remember_response(request, "lectures.transcribe", idempotency_payload, response_payload)
    return response_payload


@app.post("/lectures/{lecture_id}/generate")
def generate_artifacts(request: Request, lecture_id: str, payload: GenerateRequest) -> dict:
    _enforce_write_auth(request)
    _enforce_write_rate_limit(request)
    idempotency_payload = {
        "lecture_id": lecture_id,
        "course_id": payload.course_id,
        "preset_id": payload.preset_id,
        "openai_model": payload.openai_model,
        "llm_provider": payload.llm_provider,
        "llm_model": payload.llm_model,
    }
    replay = _replay_or_none(request, "lectures.generate", idempotency_payload)
    if replay is not None:
        return replay
    if payload.preset_id:
        _ensure_valid_preset_id(payload.preset_id)

    db = get_database()
    course_id, preset_id = _resolve_generation_identifiers(db, lecture_id, payload)
    active_job = _find_active_job_for_lecture(db, lecture_id, "generation")
    if active_job:
        response_payload = {
            "jobId": active_job.get("id"),
            "status": active_job.get("status", "queued"),
            "jobType": "generation",
            "courseId": course_id,
            "presetId": preset_id,
            "deduplicated": True,
        }
        _remember_response(request, "lectures.generate", idempotency_payload, response_payload)
        return response_payload

    job_id = enqueue_job(
        "generation",
        lecture_id,
        run_generation_job,
        lecture_id,
        course_id,
        preset_id,
        payload.llm_provider or os.getenv("PLC_LLM_PROVIDER", "gemini"),
        payload.llm_model or payload.openai_model or os.getenv("PLC_LLM_MODEL") or os.getenv("OPENAI_MODEL", "gemini-1.5-flash"),
    )
    job = db.fetch_job(job_id)
    response_payload = {
        "jobId": job_id,
        "status": job["status"] if job else "queued",
        "jobType": job.get("job_type") if job else "generation",
        "courseId": course_id,
        "presetId": preset_id,
    }
    _remember_response(request, "lectures.generate", idempotency_payload, response_payload)
    return response_payload


@app.post("/lectures/{lecture_id}/export")
def export_lecture(request: Request, lecture_id: str) -> dict:
    _enforce_write_auth(request)
    _enforce_write_rate_limit(request)
    idempotency_payload = {"lecture_id": lecture_id}
    replay = _replay_or_none(request, "lectures.export", idempotency_payload)
    if replay is not None:
        return replay
    db = get_database()
    active_job = _find_active_job_for_lecture(db, lecture_id, "export")
    if active_job:
        response_payload = {
            "jobId": active_job.get("id"),
            "status": active_job.get("status", "queued"),
            "jobType": "export",
            "deduplicated": True,
        }
        _remember_response(request, "lectures.export", idempotency_payload, response_payload)
        return response_payload

    job_id = enqueue_job("export", lecture_id, run_export_job, lecture_id)
    job = db.fetch_job(job_id)
    response_payload = {
        "jobId": job_id,
        "status": job["status"] if job else "queued",
        "jobType": job.get("job_type") if job else "export",
    }
    _remember_response(request, "lectures.export", idempotency_payload, response_payload)
    return response_payload


def _enqueue_replay_job(db, job: dict) -> dict:
    if job.get("status") != "failed":
        raise HTTPException(status_code=409, detail="Only failed jobs can be replayed.")

    job_type = job.get("job_type")
    lecture_id = job.get("lecture_id")
    if not lecture_id:
        raise HTTPException(status_code=400, detail="Job is missing lecture context.")

    if job_type == "transcription":
        new_job_id = enqueue_job(
            "transcription",
            lecture_id,
            run_transcription_job,
            lecture_id,
            "base",
        )
    elif job_type == "generation":
        lecture = db.fetch_lecture(lecture_id)
        if not lecture:
            raise HTTPException(status_code=404, detail="Lecture not found.")
        course_id = lecture.get("course_id")
        preset_id = lecture.get("preset_id")
        if not course_id or not preset_id:
            raise HTTPException(
                status_code=400,
                detail="Lecture is missing course_id or preset_id for generation replay.",
            )
        new_job_id = enqueue_job(
            "generation",
            lecture_id,
            run_generation_job,
            lecture_id,
            course_id,
            preset_id,
            os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        )
    elif job_type == "export":
        new_job_id = enqueue_job("export", lecture_id, run_export_job, lecture_id)
    else:
        raise HTTPException(status_code=400, detail="Replay is unsupported for this job type.")

    replayed_job = db.fetch_job(new_job_id)
    METRICS.increment_retry(job_type)
    return {
        "jobId": new_job_id,
        "status": replayed_job["status"] if replayed_job else "queued",
        "jobType": replayed_job.get("job_type") if replayed_job else job_type,
        "lectureId": lecture_id,
        "replayedFromJobId": job.get("id"),
    }


def _is_failed_job(job: dict, lecture_id: Optional[str], job_type: Optional[str]) -> bool:
    if job.get("status") != "failed":
        return False
    if lecture_id and job.get("lecture_id") != lecture_id:
        return False
    if job_type and job.get("job_type") != job_type:
        return False
    return True


def _job_api_payload(job: dict) -> dict:
    return {
        "id": job["id"],
        "status": job["status"],
        "jobType": job.get("job_type"),
        "lectureId": job.get("lecture_id"),
        "result": job.get("result"),
        "error": job.get("error"),
        "createdAt": job.get("created_at"),
        "updatedAt": job.get("updated_at"),
    }




@app.delete("/lectures/{lecture_id}")
def delete_lecture(lecture_id: str, request: Request, purge_storage: bool = Query(default=True)) -> dict:
    _enforce_write_auth(request)
    _enforce_write_rate_limit(request)
    db = get_database()
    result = _delete_lecture_data(db, lecture_id, purge_storage=purge_storage)
    audit_event_id = _record_deletion_audit_event(
        db,
        request=request,
        entity_type="lecture",
        entity_id=lecture_id,
        purge_storage=purge_storage,
        result=result,
    )
    if audit_event_id:
        result["auditEventId"] = audit_event_id
    return result


@app.delete("/courses/{course_id}")
def delete_course(course_id: str, request: Request, purge_storage: bool = Query(default=True)) -> dict:
    _enforce_write_auth(request)
    _enforce_write_rate_limit(request)

    db = get_database()
    course = db.fetch_course(course_id) if hasattr(db, "fetch_course") else None
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")

    lectures = db.fetch_lectures(course_id=course_id) if hasattr(db, "fetch_lectures") else []
    deleted_lectures: list[dict] = []
    for lecture in lectures:
        lecture_result = _delete_lecture_data(db, lecture["id"], purge_storage=purge_storage)
        lecture_audit_event_id = _record_deletion_audit_event(
            db,
            request=request,
            entity_type="lecture",
            entity_id=lecture["id"],
            purge_storage=purge_storage,
            result=lecture_result,
        )
        if lecture_audit_event_id:
            lecture_result["auditEventId"] = lecture_audit_event_id
        deleted_lectures.append(lecture_result)

    delete_course_method = getattr(db, "delete_course", None)
    if not callable(delete_course_method):
        raise HTTPException(status_code=500, detail="Database does not support course deletion.")
    removed = delete_course_method(course_id)

    result = {
        "courseId": course_id,
        "courseDeleted": removed > 0,
        "lecturesDeleted": len(deleted_lectures),
        "lectureDeletions": deleted_lectures,
    }
    audit_event_id = _record_deletion_audit_event(
        db,
        request=request,
        entity_type="course",
        entity_id=course_id,
        purge_storage=purge_storage,
        result=result,
    )
    if audit_event_id:
        result["auditEventId"] = audit_event_id
    return result


@app.get("/ops/deletion-audit")
def list_deletion_audit_events(
    request: Request,
    entity_type: Optional[str] = Query(default=None),
    entity_id: Optional[str] = Query(default=None),
    limit: Optional[int] = Query(default=100, ge=1, le=500),
    offset: Optional[int] = Query(default=0, ge=0),
) -> dict:
    _enforce_write_auth(request)

    normalized_entity_type = _validate_deletion_entity_type(entity_type)

    db = get_database()
    fetch_events = getattr(db, "fetch_deletion_audit_events", None)
    count_events = getattr(db, "count_deletion_audit_events", None)

    if not callable(fetch_events) or not callable(count_events):
        raise HTTPException(status_code=501, detail="Deletion audit storage is not configured.")

    rows = fetch_events(
        entity_type=normalized_entity_type,
        entity_id=entity_id,
        limit=limit,
        offset=offset,
    )
    total = count_events(entity_type=normalized_entity_type, entity_id=entity_id)
    return {
        "events": rows,
        "filters": {
            "entityType": normalized_entity_type,
            "entityId": entity_id,
        },
        "pagination": _pagination_payload(
            limit=limit,
            offset=offset,
            count=len(rows),
            total=total,
        ),
    }

@app.post("/jobs/{job_id}/replay")
def replay_job(request: Request, job_id: str) -> dict:
    _enforce_write_auth(request)
    _enforce_write_rate_limit(request)
    db = get_database()
    job = db.fetch_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return _enqueue_replay_job(db, job)


@app.get("/jobs/dead-letter")
def list_dead_letter_jobs(
    lecture_id: Optional[str] = Query(default=None),
    job_type: Optional[str] = Query(default=None),
    limit: Optional[int] = Query(default=None, ge=0),
    offset: Optional[int] = Query(default=None, ge=0),
) -> dict:
    db = get_database()
    all_jobs = db.fetch_jobs()
    failed_jobs = [job for job in all_jobs if _is_failed_job(job, lecture_id, job_type)]

    start = offset or 0
    end = start + limit if limit is not None else None
    page = failed_jobs[start:end]

    return {
        "jobs": [_job_api_payload(job) for job in page],
        "filters": {
            "status": "failed",
            "lectureId": lecture_id,
            "jobType": job_type,
        },
        "pagination": _pagination_payload(
            limit=limit,
            offset=offset,
            count=len(page),
            total=len(failed_jobs),
        ),
    }


@app.post("/jobs/dead-letter/replay")
def replay_dead_letter_jobs(
    request: Request,
    lecture_id: Optional[str] = Query(default=None),
    job_type: Optional[str] = Query(default=None),
    limit: Optional[int] = Query(default=None, ge=1),
) -> dict:
    _enforce_write_auth(request)
    _enforce_write_rate_limit(request)

    db = get_database()
    failed_jobs = [job for job in db.fetch_jobs() if _is_failed_job(job, lecture_id, job_type)]
    selected_jobs = failed_jobs[:limit] if limit is not None else failed_jobs

    replayed: list[dict] = []
    skipped: list[dict] = []
    for job in selected_jobs:
        try:
            replayed.append(_enqueue_replay_job(db, job))
        except HTTPException as exc:
            skipped.append(
                {
                    "jobId": job.get("id"),
                    "jobType": job.get("job_type"),
                    "lectureId": job.get("lecture_id"),
                    "reason": exc.detail,
                }
            )

    return {
        "status": "accepted",
        "requested": len(selected_jobs),
        "replayedCount": len(replayed),
        "skippedCount": len(skipped),
        "replayedJobs": replayed,
        "skippedJobs": skipped,
        "filters": {
            "status": "failed",
            "lectureId": lecture_id,
            "jobType": job_type,
            "limit": limit,
        },
    }


@app.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    db = get_database()
    job = db.fetch_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    payload = _job_api_payload(job)
    del payload["lectureId"]
    del payload["createdAt"]
    del payload["updatedAt"]
    return payload


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
        "jobs": [_job_api_payload(job) for job in jobs],
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




@app.get("/lectures/{lecture_id}/integrity")
def lecture_integrity(lecture_id: str) -> dict:
    return _build_lecture_integrity_payload(lecture_id)

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


# Thread Metrics Endpoints
@app.get("/lectures/{lecture_id}/thread-metrics")
def get_lecture_thread_metrics(request: Request, lecture_id: str):
    """Get thread detection metrics for a specific lecture."""
    db = get_database()
    metrics = db_module.fetch_thread_metrics_by_lecture(db.conn, lecture_id)
    return {"metrics": metrics}


@app.get("/courses/{course_id}/thread-metrics")
def get_course_thread_metrics(request: Request, course_id: str, limit: int = 50):
    """Get thread detection metrics for all lectures in a course."""
    db = get_database()
    metrics = db_module.fetch_thread_metrics_by_course(db.conn, course_id, limit)
    return {"metrics": metrics}


@app.get("/courses/{course_id}/thread-metrics/summary")
def get_course_thread_metrics_summary(request: Request, course_id: str):
    """Get aggregated thread metrics summary for a course."""
    db = get_database()
    summary = db_module.fetch_thread_metrics_summary(db.conn, course_id)
    return summary if summary else {"error": "No metrics found"}


@app.get("/thread-metrics/summary")
def get_global_thread_metrics_summary(request: Request):
    """Get aggregated thread metrics summary across all courses."""
    db = get_database()
    summary = db_module.fetch_thread_metrics_summary(db.conn, None)
    return summary if summary else {"error": "No metrics found"}
