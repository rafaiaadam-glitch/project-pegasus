#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from google.cloud import speech

def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _convert_to_wav(input_path: Path) -> Path:
    """Convert any input file to LINEAR16 WAV (16kHz mono) via ffmpeg.

    Returns the converted path on success. Falls back to the original path when
    conversion fails so callers can decide how to handle provider errors.
    """
    output_path = input_path.with_suffix(".wav")

    if input_path.suffix.lower() == ".wav":
        return input_path

    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(input_path),
                "-ar",
                "16000",
                "-ac",
                "1",
                "-c:a",
                "pcm_s16le",
                str(output_path),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return output_path
    except (subprocess.CalledProcessError, FileNotFoundError):
        return input_path

def _load_whisper():
    """
    Lazy-load the whisper module for local transcription.
    This function is imported by backend/jobs.py for transcription jobs.
    """
    try:
        return importlib.import_module("whisper")
    except ImportError as e:
        raise ImportError(
            "Whisper is not installed. Install it with: pip install openai-whisper"
        ) from e

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Transcribe lecture audio using Google Cloud Speech-to-Text."
    )
    parser.add_argument("--input", required=True, help="Path to audio file.")
    parser.add_argument("--lecture-id", required=True, help="Lecture identifier.")
    parser.add_argument("--storage-dir", default="storage", help="Base storage directory.")
    parser.add_argument("--language", default="en-US", help="Language code (e.g., 'en-US').")
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=16000,
        help="Audio sample rate in Hz (default: 16000)."
    )
    parser.add_argument(
        "--encoding",
        default="LINEAR16",
        choices=["LINEAR16", "FLAC", "MP3", "OGG_OPUS", "WEBM_OPUS"],
        help="Audio encoding format (default: LINEAR16)."
    )
    return parser

def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    raw_input_path = Path(args.input).expanduser().resolve()
    if not raw_input_path.exists():
        raise FileNotFoundError(f"Audio file not found: {raw_input_path}")

    # --- ADD THIS: Convert audio before processing ---
    input_path = _convert_to_wav(raw_input_path)
    print(f"Processing audio file: {input_path}")
    # -----------------------------------------------

    # Initialize Google Cloud Speech Client
    try:
        client = speech.SpeechClient()
    except Exception as e:
        print(f"Error initializing Google Cloud Speech client: {e}")
        print("Please ensure GOOGLE_APPLICATION_CREDENTIALS is set correctly.")
        return 1

    with open(input_path, "rb") as audio_file:
        content = audio_file.read()

    audio = speech.RecognitionAudio(content=content)

    # Map encoding string to Google Cloud Speech enum
    encoding_map = {
        "LINEAR16": speech.RecognitionConfig.AudioEncoding.LINEAR16,
        "FLAC": speech.RecognitionConfig.AudioEncoding.FLAC,
        "MP3": speech.RecognitionConfig.AudioEncoding.MP3,
        "OGG_OPUS": speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
        "WEBM_OPUS": speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
    }

    config = speech.RecognitionConfig(
        encoding=encoding_map[args.encoding],
        sample_rate_hertz=args.sample_rate,
        language_code=args.language,
        enable_word_time_offsets=True,
        enable_automatic_punctuation=True,
    )

    print(f"Transcribing {input_path} via Google Cloud STT...")

    try:
        response = client.recognize(config=config, audio=audio)
    except Exception as e:
        print(f"Error during transcription: {e}")
        print("If you encounter encoding errors, the audio file may need to be converted.")
        print("Try: ffmpeg -i input.mp3 -ar 16000 -ac 1 -c:a pcm_s16le output.wav")
        return 1

    if not response.results:
        print("Warning: No transcription results returned. The audio may be empty or incompatible.")
        response_results = []
    else:
        response_results = response.results

    segments = []
    full_text_parts = []

    for result in response_results:
        if not result.alternatives:
            continue

        alternative = result.alternatives[0]
        full_text_parts.append(alternative.transcript)

        # Mapping Google results to your existing segment schema
        # Fix: Properly handle empty words list
        if alternative.words:
            start_time = alternative.words[0].start_time.total_seconds()
            end_time = alternative.words[-1].end_time.total_seconds()
        else:
            start_time = 0.0
            end_time = 0.0


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
