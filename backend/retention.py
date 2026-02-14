from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from backend.db import get_database
from backend.storage import delete_storage_path


TERMINAL_JOB_STATUSES = {"completed", "failed"}
ACTIVE_JOB_STATUSES = {"queued", "running"}


@dataclass
class RetentionConfig:
    raw_audio_days: int
    transcript_days: int
    dry_run: bool = False


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_days(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        days = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer.") from exc
    if days < 0:
        raise RuntimeError(f"{name} must be zero or greater.")
    return days


def _parse_datetime(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _is_terminal_without_active_jobs(db, lecture_id: str) -> bool:
    fetch_jobs = getattr(db, "fetch_jobs", None)
    if not callable(fetch_jobs):
        return True
    try:
        jobs = fetch_jobs(lecture_id=lecture_id)
    except Exception:
        return False
    if not isinstance(jobs, list):
        return False
    statuses = {str(job.get("status")) for job in jobs if isinstance(job, dict)}
    if statuses & ACTIVE_JOB_STATUSES:
        return False
    if not statuses:
        return True
    return statuses <= TERMINAL_JOB_STATUSES


def run_retention_cleanup(db, config: RetentionConfig, now: Optional[datetime] = None) -> dict[str, int]:
    current = now or _utc_now()
    lectures = db.fetch_lectures()

    summary = {
        "lecturesScanned": 0,
        "audioDeleted": 0,
        "transcriptsDeleted": 0,
        "lecturesUpdated": 0,
    }

    for lecture in lectures:
        if not isinstance(lecture, dict):
            continue
        summary["lecturesScanned"] += 1
        lecture_id = lecture.get("id")
        if not lecture_id:
            continue

        created_at = _parse_datetime(lecture.get("created_at"))
        if not created_at:
            continue

        age_days = (current - created_at).days
        if age_days < min(config.raw_audio_days, config.transcript_days):
            continue

        if not _is_terminal_without_active_jobs(db, lecture_id):
            continue

        audio_path = lecture.get("audio_path")
        transcript_path = lecture.get("transcript_path")
        next_audio_path = audio_path
        next_transcript_path = transcript_path
        updated = False

        if audio_path and age_days >= config.raw_audio_days:
            if not config.dry_run:
                deleted = delete_storage_path(audio_path)
                if deleted:
                    next_audio_path = None
            summary["audioDeleted"] += 1
            updated = True

        if transcript_path and age_days >= config.transcript_days:
            if not config.dry_run:
                deleted = delete_storage_path(transcript_path)
                if deleted:
                    next_transcript_path = None
            summary["transcriptsDeleted"] += 1
            updated = True

        if updated:
            summary["lecturesUpdated"] += 1
            update_paths = getattr(db, "update_lecture_storage_paths", None)
            if callable(update_paths):
                update_paths(
                    lecture_id,
                    audio_path=next_audio_path,
                    transcript_path=next_transcript_path,
                    updated_at=current.isoformat(),
                )

    return summary


def _cli() -> int:
    parser = argparse.ArgumentParser(description="Run retention cleanup for raw audio/transcripts.")
    parser.add_argument("--dry-run", action="store_true", help="Only report candidate deletions.")
    args = parser.parse_args()

    config = RetentionConfig(
        raw_audio_days=_parse_days("PLC_RETENTION_RAW_AUDIO_DAYS", 30),
        transcript_days=_parse_days("PLC_RETENTION_TRANSCRIPT_DAYS", 14),
        dry_run=args.dry_run,
    )

    db = get_database()
    summary = run_retention_cleanup(db, config)
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
