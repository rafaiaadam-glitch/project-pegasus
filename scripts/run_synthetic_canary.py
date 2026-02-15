#!/usr/bin/env python3
"""Run an end-to-end synthetic canary against Pegasus API."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
import uuid
import wave
from datetime import datetime, timezone
from io import BytesIO
from typing import Any
from urllib import error, request


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_wav_bytes(duration_sec: float = 1.2, sample_rate: int = 16000) -> bytes:
    frame_count = max(1, int(duration_sec * sample_rate))
    amplitude = 8000
    frequency_hz = 440.0

    buffer = BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        for index in range(frame_count):
            sample = int(amplitude * math.sin(2.0 * math.pi * frequency_hz * (index / sample_rate)))
            wav.writeframesraw(sample.to_bytes(2, byteorder="little", signed=True))
    return buffer.getvalue()


def _auth_headers(token: str | None) -> dict[str, str]:
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _http_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    timeout_sec: int = 30,
) -> dict[str, Any]:
    request_headers = {"Accept": "application/json", **(headers or {})}
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        request_headers["Content-Type"] = "application/json"

    req = request.Request(url, method=method, headers=request_headers, data=body)
    try:
        with request.urlopen(req, timeout=timeout_sec) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed: HTTP {exc.code} {details}") from exc


def _http_multipart(
    url: str,
    *,
    fields: dict[str, str],
    file_field: str,
    file_name: str,
    file_bytes: bytes,
    file_content_type: str,
    headers: dict[str, str] | None = None,
    timeout_sec: int = 60,
) -> dict[str, Any]:
    boundary = f"----pegasus-{uuid.uuid4().hex}"
    parts: list[bytes] = []

    for key, value in fields.items():
        parts.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode(),
                str(value).encode(),
                b"\r\n",
            ]
        )

    parts.extend(
        [
            f"--{boundary}\r\n".encode(),
            (
                f'Content-Disposition: form-data; name="{file_field}"; '
                f'filename="{file_name}"\r\n'
            ).encode(),
            f"Content-Type: {file_content_type}\r\n\r\n".encode(),
            file_bytes,
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )

    body = b"".join(parts)
    request_headers = {
        "Accept": "application/json",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        **(headers or {}),
    }

    req = request.Request(url, method="POST", headers=request_headers, data=body)
    try:
        with request.urlopen(req, timeout=timeout_sec) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"POST {url} failed: HTTP {exc.code} {details}") from exc


def _poll_job(base_url: str, job_id: str, headers: dict[str, str], *, timeout_sec: int, poll_sec: int) -> dict[str, Any]:
    deadline = time.time() + timeout_sec
    last = {}
    while time.time() < deadline:
        last = _http_json("GET", f"{base_url}/jobs/{job_id}", headers=headers)
        status = (last.get("status") or "").lower()
        if status == "completed":
            return last
        if status == "failed":
            raise RuntimeError(f"Job {job_id} failed: {last.get('error')}")
        time.sleep(poll_sec)

    raise RuntimeError(f"Job {job_id} did not complete within {timeout_sec}s. Last payload: {last}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run synthetic canary through ingest->transcribe->generate->export.")
    parser.add_argument("--base-url", default=os.getenv("PEGASUS_API_URL", "").strip())
    parser.add_argument("--api-token", default=os.getenv("PLC_WRITE_API_TOKEN", "").strip())
    parser.add_argument("--course-id", default="canary-course")
    parser.add_argument("--preset-id", default="foundational")
    parser.add_argument("--llm-provider", default=os.getenv("PEGASUS_CANARY_LLM_PROVIDER", "gemini"))
    parser.add_argument("--llm-model", default=os.getenv("PEGASUS_CANARY_LLM_MODEL", "gemini-1.5-flash"))
    parser.add_argument("--transcribe-provider", default=os.getenv("PEGASUS_CANARY_STT_PROVIDER", "google"))
    parser.add_argument("--transcribe-model", default=os.getenv("PEGASUS_CANARY_STT_MODEL", "latest_long"))
    parser.add_argument("--timeout-sec", type=int, default=900)
    parser.add_argument("--poll-sec", type=int, default=5)
    args = parser.parse_args()

    if not args.base_url:
        print("PEGASUS_API_URL (or --base-url) is required.", file=sys.stderr)
        return 2

    base_url = args.base_url.rstrip("/")
    headers = _auth_headers(args.api_token)

    lecture_id = f"canary-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
    title = f"Synthetic Canary {_iso_now()}"
    audio_bytes = _build_wav_bytes()

    started_at = time.time()
    result: dict[str, Any] = {
        "status": "running",
        "baseUrl": base_url,
        "courseId": args.course_id,
        "lectureId": lecture_id,
        "startedAt": _iso_now(),
        "stages": {},
    }

    try:
        ingest_payload = _http_multipart(
            f"{base_url}/lectures/ingest",
            fields={
                "course_id": args.course_id,
                "lecture_id": lecture_id,
                "preset_id": args.preset_id,
                "title": title,
                "course_title": "Synthetic Canary Course",
                "duration_sec": "1",
                "source_type": "synthetic_canary",
                "lecture_mode": "canary",
            },
            file_field="audio",
            file_name=f"{lecture_id}.wav",
            file_bytes=audio_bytes,
            file_content_type="audio/wav",
            headers=headers,
        )
        result["stages"]["ingest"] = ingest_payload

        transcribe_payload = _http_json(
            "POST",
            f"{base_url}/lectures/{lecture_id}/transcribe",
            headers=headers,
            payload={"provider": args.transcribe_provider, "model": args.transcribe_model},
        )
        result["stages"]["transcribe"] = _poll_job(
            base_url,
            transcribe_payload["jobId"],
            headers,
            timeout_sec=args.timeout_sec,
            poll_sec=args.poll_sec,
        )

        generate_payload = _http_json(
            "POST",
            f"{base_url}/lectures/{lecture_id}/generate",
            headers=headers,
            payload={
                "course_id": args.course_id,
                "preset_id": args.preset_id,
                "llm_provider": args.llm_provider,
                "llm_model": args.llm_model,
            },
        )
        result["stages"]["generate"] = _poll_job(
            base_url,
            generate_payload["jobId"],
            headers,
            timeout_sec=args.timeout_sec,
            poll_sec=args.poll_sec,
        )

        export_payload = _http_json(
            "POST",
            f"{base_url}/lectures/{lecture_id}/export",
            headers=headers,
        )
        result["stages"]["export"] = _poll_job(
            base_url,
            export_payload["jobId"],
            headers,
            timeout_sec=args.timeout_sec,
            poll_sec=args.poll_sec,
        )

        result["integrity"] = _http_json("GET", f"{base_url}/lectures/{lecture_id}/integrity", headers=headers)
        result["summary"] = _http_json("GET", f"{base_url}/lectures/{lecture_id}/summary", headers=headers)
        result["status"] = "ok"
        result["durationSec"] = round(time.time() - started_at, 2)
        print(json.dumps(result, indent=2))
        return 0
    except Exception as exc:
        result["status"] = "failed"
        result["durationSec"] = round(time.time() - started_at, 2)
        result["error"] = str(exc)
        print(json.dumps(result, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
