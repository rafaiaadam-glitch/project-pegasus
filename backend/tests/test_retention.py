from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

import backend.retention as retention_module


class FakeDB:
    def __init__(self) -> None:
        self.lectures = []
        self.jobs_by_lecture = {}
        self.updated = []

    def fetch_lectures(self):
        return list(self.lectures)

    def fetch_jobs(self, lecture_id=None, limit=None, offset=None):
        return list(self.jobs_by_lecture.get(lecture_id, []))

    def update_lecture_storage_paths(self, lecture_id, *, audio_path, transcript_path, updated_at):
        self.updated.append(
            {
                "lecture_id": lecture_id,
                "audio_path": audio_path,
                "transcript_path": transcript_path,
                "updated_at": updated_at,
            }
        )


def test_retention_cleanup_deletes_old_audio_and_transcript(monkeypatch):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    old = (now - timedelta(days=40)).isoformat()

    db = FakeDB()
    db.lectures = [
        {
            "id": "lec-old",
            "created_at": old,
            "audio_path": "/tmp/audio-old.wav",
            "transcript_path": "/tmp/transcript-old.json",
        }
    ]
    db.jobs_by_lecture["lec-old"] = [{"status": "completed"}]

    deleted_paths = []

    def _fake_delete(path):
        deleted_paths.append(path)
        return True

    monkeypatch.setattr(retention_module, "delete_storage_path", _fake_delete)

    summary = retention_module.run_retention_cleanup(
        db,
        retention_module.RetentionConfig(raw_audio_days=30, transcript_days=14, dry_run=False),
        now=now,
    )

    assert summary["audioDeleted"] == 1
    assert summary["transcriptsDeleted"] == 1
    assert summary["lecturesUpdated"] == 1
    assert summary["lecturesWouldUpdate"] == 0
    assert deleted_paths == ["/tmp/audio-old.wav", "/tmp/transcript-old.json"]
    assert db.updated[0]["audio_path"] is None
    assert db.updated[0]["transcript_path"] is None


def test_retention_cleanup_skips_lectures_with_active_jobs(monkeypatch):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    old = (now - timedelta(days=60)).isoformat()

    db = FakeDB()
    db.lectures = [
        {
            "id": "lec-active",
            "created_at": old,
            "audio_path": "/tmp/audio-active.wav",
            "transcript_path": "/tmp/transcript-active.json",
        }
    ]
    db.jobs_by_lecture["lec-active"] = [{"status": "running"}]

    monkeypatch.setattr(retention_module, "delete_storage_path", lambda path: True)

    summary = retention_module.run_retention_cleanup(
        db,
        retention_module.RetentionConfig(raw_audio_days=30, transcript_days=14, dry_run=False),
        now=now,
    )

    assert summary["audioDeleted"] == 0
    assert summary["transcriptsDeleted"] == 0
    assert summary["lecturesUpdated"] == 0
    assert summary["lecturesWouldUpdate"] == 0
    assert not db.updated


def test_retention_cleanup_tracks_delete_failures_without_clearing_paths(monkeypatch):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    old = (now - timedelta(days=40)).isoformat()

    db = FakeDB()
    db.lectures = [
        {
            "id": "lec-fail",
            "created_at": old,
            "audio_path": "/tmp/audio-fail.wav",
            "transcript_path": "/tmp/transcript-fail.json",
        }
    ]
    db.jobs_by_lecture["lec-fail"] = [{"status": "completed"}]

    monkeypatch.setattr(retention_module, "delete_storage_path", lambda path: False)

    summary = retention_module.run_retention_cleanup(
        db,
        retention_module.RetentionConfig(raw_audio_days=30, transcript_days=14, dry_run=False),
        now=now,
    )

    assert summary["audioDeleted"] == 0
    assert summary["transcriptsDeleted"] == 0
    assert summary["audioDeleteFailures"] == 1
    assert summary["transcriptDeleteFailures"] == 1
    assert summary["lecturesUpdated"] == 0
    assert summary["lecturesWouldUpdate"] == 0
    assert not db.updated


def test_retention_cleanup_dry_run_reports_candidates_without_db_writes(monkeypatch):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    old = (now - timedelta(days=40)).isoformat()

    db = FakeDB()
    db.lectures = [
        {
            "id": "lec-dry-run",
            "created_at": old,
            "audio_path": "/tmp/audio-dry-run.wav",
            "transcript_path": "/tmp/transcript-dry-run.json",
        }
    ]
    db.jobs_by_lecture["lec-dry-run"] = [{"status": "completed"}]

    delete_calls = []

    def _fake_delete(path):
        delete_calls.append(path)
        return True

    monkeypatch.setattr(retention_module, "delete_storage_path", _fake_delete)

    summary = retention_module.run_retention_cleanup(
        db,
        retention_module.RetentionConfig(raw_audio_days=30, transcript_days=14, dry_run=True),
        now=now,
    )

    assert summary["audioDeleted"] == 1
    assert summary["transcriptsDeleted"] == 1
    assert summary["lecturesUpdated"] == 0
    assert summary["lecturesWouldUpdate"] == 1
    assert not delete_calls
    assert not db.updated
