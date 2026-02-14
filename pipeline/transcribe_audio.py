#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from google.cloud import speech

def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Transcribe lecture audio using Google Cloud Speech-to-Text."
    )
    parser.add_argument("--input", required=True, help="Path to audio file.")
    parser.add_argument("--lecture-id", required=True, help="Lecture identifier.")
    parser.add_argument("--storage-dir", default="storage", help="Base storage directory.")
    parser.add_argument("--language", default="en-US", help="Language code (e.g., 'en-US').")
    return parser

def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Audio file not found: {input_path}")

    # Initialize Google Cloud Speech Client
    client = speech.SpeechClient()

    with open(input_path, "rb") as audio_file:
        content = audio_file.read()

    audio = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(
        # Note: adjust encoding/sample_rate_hertz based on your specific audio files if known
        encoding=speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,
        sample_rate_hertz=None, 
        language_code=args.language,
        enable_word_time_offsets=True,
    )

    print(f"Transcribing {input_path} via Google Cloud STT...")
    response = client.recognize(config=config, audio=audio)

    segments = []
    full_text_parts = []
    
    for result in response.results:
        alternative = result.alternatives[0]
        full_text_parts.append(alternative.transcript)
        
        # Mapping Google results to your existing segment schema
        start_time = alternative.words[0].start_time.total_seconds() if alternative.words else 0.0
        end_time = alternative.words[-1].end_time.total_seconds() if alternative.words else 0.0
        
        segments.append({
            "startSec": float(start_time),
            "endSec": float(end_time),
            "text": alternative.transcript.strip(),
        })

    transcript_payload = {
        "lectureId": args.lecture_id,
        "createdAt": _iso_now(),
        "language": args.language,
        "text": " ".join(full_text_parts).strip(),
        "segments": segments,
        "engine": {
            "provider": "google-cloud-stt",
            "model": "latest_long",
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
    import sys
    sys.exit(main())
