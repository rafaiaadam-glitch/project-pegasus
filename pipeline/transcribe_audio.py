#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Transcribe lecture audio into timestamped segments."
    )
    parser.add_argument("--input", required=True, help="Path to audio file.")
    parser.add_argument("--lecture-id", required=True, help="Lecture identifier.")
    parser.add_argument(
        "--model",
        default="base",
        help="Whisper model name (if whisper is installed).",
    )
    parser.add_argument(
        "--storage-dir",
        default="storage",
        help="Base storage directory for transcript output.",
    )
    parser.add_argument(
        "--language",
        default=None,
        help="Optional language hint (e.g., 'en').",
    )
    return parser


def _load_whisper():
    spec = importlib.util.find_spec("whisper")
    if spec is None:
        raise RuntimeError(
            "Whisper is not installed. Install openai-whisper to run transcription:\n"
            "  pip install -U openai-whisper\n"
            "Ensure ffmpeg is available on PATH."
        )
    return importlib.import_module("whisper")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Audio file not found: {input_path}")

    whisper = _load_whisper()
    model = whisper.load_model(args.model)
    result = model.transcribe(str(input_path), language=args.language)

    segments = [
        {
            "startSec": float(segment["start"]),
            "endSec": float(segment["end"]),
            "text": segment["text"].strip(),
        }
        for segment in result.get("segments", [])
    ]

    transcript_payload = {
        "lectureId": args.lecture_id,
        "createdAt": _iso_now(),
        "language": result.get("language"),
        "text": result.get("text", "").strip(),
        "segments": segments,
        "engine": {
            "provider": "whisper",
            "model": args.model,
        },
    }

    storage_root = Path(args.storage_dir).expanduser().resolve()
    transcript_dir = storage_root / "transcripts"
    transcript_dir.mkdir(parents=True, exist_ok=True)
    output_path = transcript_dir / f"{args.lecture_id}.json"
    output_path.write_text(json.dumps(transcript_payload, indent=2), encoding="utf-8")

    print(f"Wrote transcript: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
