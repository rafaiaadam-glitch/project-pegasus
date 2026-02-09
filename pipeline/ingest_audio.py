#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_for_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ingest lecture audio and write durable storage + metadata."
    )
    parser.add_argument("--input", required=True, help="Path to audio file.")
    parser.add_argument("--course-id", required=True, help="Course identifier.")
    parser.add_argument("--lecture-id", required=True, help="Lecture identifier.")
    parser.add_argument("--preset-id", required=True, help="Preset selected pre-recording.")
    parser.add_argument("--title", required=True, help="Lecture title.")
    parser.add_argument(
        "--recorded-at",
        default=None,
        help="ISO 8601 timestamp; defaults to now (UTC).",
    )
    parser.add_argument(
        "--duration-sec",
        type=int,
        default=None,
        help="Lecture duration in seconds, if known.",
    )
    parser.add_argument(
        "--source-type",
        choices=("upload", "record"),
        default="upload",
        help="How the audio was captured.",
    )
    parser.add_argument(
        "--storage-dir",
        default="storage",
        help="Base storage directory for audio + metadata.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Audio file not found: {input_path}")

    storage_root = Path(args.storage_dir).expanduser().resolve()
    audio_dir = storage_root / "audio"
    metadata_dir = storage_root / "metadata"
    _ensure_dir(audio_dir)
    _ensure_dir(metadata_dir)

    ext = input_path.suffix or ".bin"
    stored_audio_path = audio_dir / f"{args.lecture_id}{ext}"
    shutil.copy2(input_path, stored_audio_path)

    checksum = _sha256_for_file(stored_audio_path)
    size_bytes = os.path.getsize(stored_audio_path)
    recorded_at = args.recorded_at or _iso_now()

    lecture_record = {
        "id": args.lecture_id,
        "courseId": args.course_id,
        "presetId": args.preset_id,
        "title": args.title,
        "recordedAt": recorded_at,
        "durationSec": args.duration_sec or 0,
        "audioSource": {
            "sourceType": args.source_type,
            "originalFilename": input_path.name,
            "storagePath": str(stored_audio_path),
            "sizeBytes": size_bytes,
            "checksumSha256": checksum,
        },
        "status": "uploaded",
        "artifacts": [],
        "createdAt": _iso_now(),
        "updatedAt": _iso_now(),
    }

    metadata_path = metadata_dir / f"{args.lecture_id}.json"
    metadata_path.write_text(json.dumps(lecture_record, indent=2), encoding="utf-8")

    print(f"Stored audio: {stored_audio_path}")
    print(f"Wrote metadata: {metadata_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
