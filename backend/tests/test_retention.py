from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from backend.retention import RetentionPolicy, enforce_local_retention, load_retention_policy


def _touch_with_age(path: Path, now_ts: float, age_days: int, payload: bytes = b"x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    ts = now_ts - (age_days * 24 * 60 * 60)
    path.chmod(0o644)
    import os

    os.utime(path, (ts, ts))


def test_enforce_local_retention_deletes_only_expired_files(tmp_path: Path):
    now_ts = 2_000_000_000
    storage = tmp_path / "storage"

    old_audio = storage / "audio" / "old.mp3"
    fresh_audio = storage / "audio" / "new.mp3"
    old_transcript = storage / "transcripts" / "old.json"
    old_artifact = storage / "artifacts" / "old-summary.json"

    _touch_with_age(old_audio, now_ts, age_days=31, payload=b"old")
    _touch_with_age(fresh_audio, now_ts, age_days=1, payload=b"new")
    _touch_with_age(old_transcript, now_ts, age_days=61, payload=b"t")
    _touch_with_age(old_artifact, now_ts, age_days=91, payload=b"a")

    result = enforce_local_retention(
        storage,
        policy=RetentionPolicy(audio_days=30, transcript_days=60, artifact_days=90),
        now_ts=now_ts,
    )

    assert result.deleted_files == 3
    assert result.reclaimed_bytes == len(b"old") + len(b"t") + len(b"a")
    assert fresh_audio.exists()
    assert not old_audio.exists()
    assert not old_transcript.exists()
    assert not old_artifact.exists()


def test_load_retention_policy_reads_env(monkeypatch):
    monkeypatch.setenv("PLC_RETENTION_AUDIO_DAYS", "10")
    monkeypatch.setenv("PLC_RETENTION_TRANSCRIPT_DAYS", "20")
    monkeypatch.setenv("PLC_RETENTION_ARTIFACT_DAYS", "30")

    policy = load_retention_policy()
    assert policy.audio_days == 10
    assert policy.transcript_days == 20
    assert policy.artifact_days == 30


def test_load_retention_policy_rejects_invalid_env(monkeypatch):
    monkeypatch.setenv("PLC_RETENTION_AUDIO_DAYS", "oops")
    with pytest.raises(RuntimeError, match="PLC_RETENTION_AUDIO_DAYS must be an integer"):
        load_retention_policy()
