from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class RetentionPolicy:
    audio_days: int
    transcript_days: int
    artifact_days: int


@dataclass(frozen=True)
class RetentionResult:
    deleted_files: int
    deleted_dirs: int
    reclaimed_bytes: int


def _parse_positive_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer.") from exc
    if value < 0:
        raise RuntimeError(f"{name} must be zero or greater.")
    return value


def load_retention_policy() -> RetentionPolicy:
    return RetentionPolicy(
        audio_days=_parse_positive_int("PLC_RETENTION_AUDIO_DAYS", 30),
        transcript_days=_parse_positive_int("PLC_RETENTION_TRANSCRIPT_DAYS", 60),
        artifact_days=_parse_positive_int("PLC_RETENTION_ARTIFACT_DAYS", 90),
    )


def _is_expired(path: Path, now_ts: float, ttl_days: int) -> bool:
    ttl_seconds = ttl_days * 24 * 60 * 60
    age_seconds = now_ts - path.stat().st_mtime
    return age_seconds > ttl_seconds


def _iter_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    return (p for p in root.rglob("*") if p.is_file())


def _cleanup_empty_dirs(root: Path) -> int:
    if not root.exists():
        return 0
    removed = 0
    for path in sorted((p for p in root.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        try:
            path.rmdir()
            removed += 1
        except OSError:
            continue
    return removed


def enforce_local_retention(storage_dir: Path, policy: RetentionPolicy | None = None, now_ts: float | None = None) -> RetentionResult:
    cfg = policy or load_retention_policy()
    now = now_ts if now_ts is not None else time.time()

    targets = [
        (storage_dir / "audio", cfg.audio_days),
        (storage_dir / "transcripts", cfg.transcript_days),
        (storage_dir / "artifacts", cfg.artifact_days),
    ]

    deleted_files = 0
    reclaimed_bytes = 0

    for root, ttl_days in targets:
        for file_path in _iter_files(root):
            if not _is_expired(file_path, now, ttl_days):
                continue
            size = file_path.stat().st_size
            file_path.unlink(missing_ok=True)
            deleted_files += 1
            reclaimed_bytes += size

    deleted_dirs = sum(_cleanup_empty_dirs(root) for root, _ in targets)

    return RetentionResult(
        deleted_files=deleted_files,
        deleted_dirs=deleted_dirs,
        reclaimed_bytes=reclaimed_bytes,
    )
