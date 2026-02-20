#!/usr/bin/env python3
"""
Canary end-to-end flow test for Pegasus staging environment.

Validates the full pipeline against a live API:
  1. Health & readiness checks
  2. Preset listing
  3. Course creation + lecture ingest (PDF upload)
  4. Transcription job kick-off & polling
  5. Generation job kick-off & polling
  6. Artifact retrieval
  7. Export job kick-off & polling
  8. Export download
  9. Cleanup (delete lecture + course)

Usage:
  export API_BASE_URL="https://pegasus-api-ui64fwvjyq-uc.a.run.app"
  export PLC_WRITE_API_TOKEN="your-staging-token"
  python3 scripts/canary_e2e_flow.py [--keep]

Options:
  --keep    Skip cleanup — leave the canary course/lecture in the database
"""

import json
import os
import ssl
import sys
import time
import uuid
import tempfile
import argparse
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

# Build a default SSL context — handles macOS Python installs that ship
# without the system CA bundle linked.
try:
    import certifi
    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CTX = ssl.create_default_context()
    # Fallback: if the default context can't verify either, disable verify
    # (acceptable for a canary test against our own staging).
    try:
        urlopen(Request("https://www.google.com"), timeout=5, context=_SSL_CTX)
    except ssl.SSLCertVerificationError:
        _SSL_CTX = ssl._create_unverified_context()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
API_BASE_URL = os.environ.get("API_BASE_URL", "").rstrip("/")
API_TOKEN = os.environ.get("PLC_WRITE_API_TOKEN", "")

POLL_INTERVAL_SEC = 5
POLL_TIMEOUT_SEC = 300  # 5 minutes max per job stage

CANARY_COURSE_ID = f"canary-{uuid.uuid4().hex[:8]}"
CANARY_LECTURE_ID = f"canary-lec-{uuid.uuid4().hex[:8]}"
CANARY_PRESET_ID = "exam-mode"
CANARY_TITLE = "Canary E2E Test Lecture"

# Counters
_pass = 0
_fail = 0
_skip = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _headers(write: bool = False) -> dict:
    h = {"Accept": "application/json"}
    if write and API_TOKEN:
        h["Authorization"] = f"Bearer {API_TOKEN}"
    return h


def _request(method: str, path: str, *, body=None, write: bool = False,
             content_type: str | None = None, raw_body: bytes | None = None,
             timeout: int = 60) -> dict | bytes:
    url = f"{API_BASE_URL}{path}"
    headers = _headers(write=write)

    if raw_body is not None:
        data = raw_body
        if content_type:
            headers["Content-Type"] = content_type
    elif body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    else:
        data = None

    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
            raw = resp.read()
            ct = resp.headers.get("Content-Type", "")
            if "json" in ct:
                return json.loads(raw)
            return raw
    except HTTPError as exc:
        error_body = exc.read().decode(errors="replace")
        raise RuntimeError(
            f"{method} {path} -> HTTP {exc.code}: {error_body}"
        ) from exc


def _multipart_upload(path: str, fields: dict, file_field: str,
                      file_path: str, file_name: str,
                      content_type: str = "application/pdf") -> dict:
    """Build and send a multipart/form-data request (stdlib only)."""
    boundary = uuid.uuid4().hex
    lines: list[bytes] = []

    for key, value in fields.items():
        lines.append(f"--{boundary}\r\n".encode())
        lines.append(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode())
        lines.append(f"{value}\r\n".encode())

    # File part
    lines.append(f"--{boundary}\r\n".encode())
    lines.append(
        f'Content-Disposition: form-data; name="{file_field}"; filename="{file_name}"\r\n'.encode()
    )
    lines.append(f"Content-Type: {content_type}\r\n\r\n".encode())
    with open(file_path, "rb") as f:
        lines.append(f.read())
    lines.append(b"\r\n")
    lines.append(f"--{boundary}--\r\n".encode())

    raw_body = b"".join(lines)
    url = f"{API_BASE_URL}{path}"
    headers = _headers(write=True)
    headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"

    req = Request(url, data=raw_body, headers=headers, method="POST")
    try:
        with urlopen(req, timeout=120, context=_SSL_CTX) as resp:
            return json.loads(resp.read())
    except HTTPError as exc:
        error_body = exc.read().decode(errors="replace")
        raise RuntimeError(
            f"POST {path} -> HTTP {exc.code}: {error_body}"
        ) from exc


def step(label: str):
    print(f"\n{'='*60}")
    print(f"  STEP: {label}")
    print(f"{'='*60}")


def check(description: str, condition: bool, detail: str = ""):
    global _pass, _fail
    if condition:
        _pass += 1
        print(f"  [PASS] {description}")
    else:
        _fail += 1
        msg = f"  [FAIL] {description}"
        if detail:
            msg += f" — {detail}"
        print(msg)


def skip(description: str, reason: str = ""):
    global _skip
    _skip += 1
    msg = f"  [SKIP] {description}"
    if reason:
        msg += f" — {reason}"
    print(msg)


def poll_job(job_id: str, stage_name: str) -> dict | None:
    """Poll a job until it reaches a terminal state or times out."""
    deadline = time.time() + POLL_TIMEOUT_SEC
    last_status = None
    while time.time() < deadline:
        try:
            job = _request("GET", f"/jobs/{job_id}")
        except Exception as exc:
            print(f"    Poll error: {exc}")
            time.sleep(POLL_INTERVAL_SEC)
            continue

        status = job.get("status", "unknown")
        if status != last_status:
            print(f"    {stage_name} job {job_id}: {status}")
            last_status = status

        if status in ("completed", "failed"):
            return job

        time.sleep(POLL_INTERVAL_SEC)

    print(f"    {stage_name} job {job_id}: TIMEOUT after {POLL_TIMEOUT_SEC}s")
    return None


def _create_dummy_pdf(path: str):
    """Create a minimal valid PDF for upload testing."""
    # Minimal PDF 1.0 with a single page containing text
    content = (
        b"%PDF-1.0\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        b"4 0 obj\n<< /Length 44 >>\nstream\n"
        b"BT /F1 12 Tf 100 700 Td (Canary test) Tj ET\n"
        b"endstream\nendobj\n"
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        b"xref\n0 6\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000266 00000 n \n"
        b"0000000360 00000 n \n"
        b"trailer\n<< /Size 6 /Root 1 0 R >>\n"
        b"startxref\n437\n%%EOF\n"
    )
    with open(path, "wb") as f:
        f.write(content)


# ---------------------------------------------------------------------------
# Test Steps
# ---------------------------------------------------------------------------
def test_health():
    step("Health Check")
    resp = _request("GET", "/health")
    check("GET /health returns status=ok", resp.get("status") == "ok", json.dumps(resp))

    resp = _request("GET", "/health/ready")
    check(
        "GET /health/ready returns status",
        resp.get("status") in ("ok", "degraded"),
        f"status={resp.get('status')}",
    )
    checks = resp.get("checks", {})
    db_status = checks.get("database", {}).get("status")
    check("Database is reachable", db_status == "ok", f"database.status={db_status}")


def test_presets():
    step("Presets")
    resp = _request("GET", "/presets")
    presets = resp.get("presets", [])
    check("GET /presets returns non-empty list", len(presets) > 0, f"count={len(presets)}")

    resp = _request("GET", f"/presets/{CANARY_PRESET_ID}")
    check(
        f"GET /presets/{CANARY_PRESET_ID} returns preset",
        resp.get("id") == CANARY_PRESET_ID,
        json.dumps(resp)[:200],
    )


def test_ingest(pdf_path: str) -> dict | None:
    step("Lecture Ingest (PDF Upload)")
    fields = {
        "course_id": CANARY_COURSE_ID,
        "lecture_id": CANARY_LECTURE_ID,
        "preset_id": CANARY_PRESET_ID,
        "title": CANARY_TITLE,
        "course_title": "Canary E2E Course",
        "source_type": "upload",
        "auto_transcribe": "true",
    }
    try:
        resp = _multipart_upload(
            "/lectures/ingest",
            fields=fields,
            file_field="file",
            file_path=pdf_path,
            file_name="canary_test.pdf",
        )
    except Exception as exc:
        check("POST /lectures/ingest succeeds", False, str(exc))
        return None

    check(
        "Ingest returns lectureId",
        resp.get("lectureId") == CANARY_LECTURE_ID,
        json.dumps(resp)[:300],
    )
    check("Ingest detects PDF fileType", resp.get("fileType") == "pdf", f"fileType={resp.get('fileType')}")
    return resp


def test_lecture_exists():
    step("Verify Lecture Record")
    resp = _request("GET", f"/lectures/{CANARY_LECTURE_ID}")
    check(
        "GET /lectures/{id} returns lecture",
        resp.get("id") == CANARY_LECTURE_ID,
        json.dumps(resp)[:200],
    )
    check(
        "Lecture status is uploaded or later",
        resp.get("status") in ("uploaded", "transcribing", "transcribed", "generating", "completed"),
        f"status={resp.get('status')}",
    )


def test_transcription() -> bool:
    step("Transcription Job")

    # Check if a transcription job was auto-enqueued during ingest
    jobs_resp = _request("GET", f"/lectures/{CANARY_LECTURE_ID}/jobs")
    jobs = jobs_resp.get("jobs", [])
    transcription_jobs = [j for j in jobs if j.get("jobType") == "transcription"]

    if transcription_jobs:
        job_id = transcription_jobs[0]["id"]
        print(f"    Found existing transcription job: {job_id}")
    else:
        # Manually trigger transcription
        print("    No auto-transcription job found, triggering manually...")
        try:
            resp = _request("POST", f"/lectures/{CANARY_LECTURE_ID}/transcribe", write=True)
            job_id = resp.get("jobId")
            check("POST /lectures/{id}/transcribe returns jobId", job_id is not None, json.dumps(resp)[:200])
        except Exception as exc:
            check("POST /lectures/{id}/transcribe succeeds", False, str(exc))
            return False

    if not job_id:
        check("Transcription job ID available", False, "no job_id")
        return False

    result = poll_job(job_id, "Transcription")
    if result is None:
        check("Transcription completes within timeout", False, "timed out")
        return False

    status = result.get("status")
    check("Transcription job completes", status == "completed", f"status={status}, error={result.get('error')}")
    return status == "completed"


def test_generation() -> bool:
    step("Generation Job")
    body = {
        "course_id": CANARY_COURSE_ID,
        "preset_id": CANARY_PRESET_ID,
    }
    try:
        resp = _request("POST", f"/lectures/{CANARY_LECTURE_ID}/generate", body=body, write=True, timeout=300)
    except Exception as exc:
        check("POST /lectures/{id}/generate succeeds", False, str(exc))
        return False

    job_id = resp.get("jobId")
    check("Generate returns jobId", job_id is not None, json.dumps(resp)[:200])

    if not job_id:
        return False

    result = poll_job(job_id, "Generation")
    if result is None:
        check("Generation completes within timeout", False, "timed out")
        return False

    status = result.get("status")
    check("Generation job completes", status == "completed", f"status={status}, error={result.get('error')}")
    return status == "completed"


def test_artifacts():
    step("Artifact Retrieval")
    resp = _request("GET", f"/lectures/{CANARY_LECTURE_ID}/artifacts")
    artifacts = resp.get("artifacts", {})
    records = resp.get("artifactRecords", [])

    check("Artifacts endpoint returns data", len(records) > 0, f"recordCount={len(records)}")

    artifact_types = [r.get("artifact_type") for r in records]
    print(f"    Artifact types found: {artifact_types}")

    for expected in ("summary", "flashcards", "exam"):
        check(
            f"Artifact '{expected}' exists",
            expected in artifact_types,
            f"available: {artifact_types}",
        )


def test_progress():
    step("Progress Tracking")
    resp = _request("GET", f"/lectures/{CANARY_LECTURE_ID}/progress")
    check(
        "Progress endpoint returns data",
        resp.get("lectureId") == CANARY_LECTURE_ID,
        json.dumps(resp)[:200],
    )
    check(
        "Progress percent > 0",
        (resp.get("progressPercent") or 0) > 0,
        f"progressPercent={resp.get('progressPercent')}",
    )


def test_export() -> bool:
    step("Export Job")
    try:
        resp = _request("POST", f"/lectures/{CANARY_LECTURE_ID}/export", write=True, timeout=180)
    except Exception as exc:
        check("POST /lectures/{id}/export succeeds", False, str(exc))
        return False

    job_id = resp.get("jobId")
    check("Export returns jobId", job_id is not None, json.dumps(resp)[:200])

    if not job_id:
        return False

    result = poll_job(job_id, "Export")
    if result is None:
        check("Export completes within timeout", False, "timed out")
        return False

    status = result.get("status")
    check("Export job completes", status == "completed", f"status={status}, error={result.get('error')}")
    return status == "completed"


def test_export_download():
    step("Export Download")
    for export_type in ("markdown",):
        try:
            resp = _request("GET", f"/exports/{CANARY_LECTURE_ID}/{export_type}")
            if isinstance(resp, bytes):
                check(f"Export '{export_type}' downloadable", len(resp) > 0, f"size={len(resp)} bytes")
            elif isinstance(resp, dict) and resp.get("downloadUrl"):
                check(f"Export '{export_type}' has download URL", True)
            else:
                check(f"Export '{export_type}' downloadable", False, f"unexpected response type: {type(resp)}")
        except Exception as exc:
            check(f"Export '{export_type}' downloadable", False, str(exc))


def test_course_progress():
    step("Course-Level Progress")
    resp = _request("GET", f"/courses/{CANARY_COURSE_ID}/progress")
    check(
        "Course progress returns data",
        resp.get("courseId") == CANARY_COURSE_ID,
        json.dumps(resp)[:200],
    )
    check(
        "Course has at least 1 lecture",
        (resp.get("lectureCount") or 0) >= 1,
        f"lectureCount={resp.get('lectureCount')}",
    )


def test_cleanup():
    step("Cleanup (delete canary data)")
    try:
        resp = _request("DELETE", f"/lectures/{CANARY_LECTURE_ID}?purge_storage=true", write=True)
        check("DELETE /lectures/{id} succeeds", "lectureId" in resp, json.dumps(resp)[:200])
    except Exception as exc:
        check("DELETE /lectures/{id} succeeds", False, str(exc))

    try:
        resp = _request("DELETE", f"/courses/{CANARY_COURSE_ID}?purge_storage=true", write=True)
        check("DELETE /courses/{id} succeeds", "courseId" in resp, json.dumps(resp)[:200])
    except Exception as exc:
        # Course might already be gone if lecture delete cascaded
        if "404" in str(exc):
            check("DELETE /courses/{id} succeeds (already gone)", True)
        else:
            check("DELETE /courses/{id} succeeds", False, str(exc))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Pegasus canary end-to-end flow test")
    parser.add_argument("--keep", action="store_true", help="Skip cleanup — keep canary data")
    args = parser.parse_args()

    if not API_BASE_URL:
        print("ERROR: Set API_BASE_URL environment variable.")
        print("  export API_BASE_URL=\"https://pegasus-api-ui64fwvjyq-uc.a.run.app\"")
        sys.exit(1)

    if not API_TOKEN:
        print("WARNING: PLC_WRITE_API_TOKEN not set — write operations may fail.\n")

    print(f"Pegasus Canary E2E Flow")
    print(f"  API:       {API_BASE_URL}")
    print(f"  Course:    {CANARY_COURSE_ID}")
    print(f"  Lecture:   {CANARY_LECTURE_ID}")
    print(f"  Preset:    {CANARY_PRESET_ID}")
    print(f"  Cleanup:   {'no (--keep)' if args.keep else 'yes'}")

    # Create a temp PDF for upload
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = os.path.join(tmpdir, "canary_test.pdf")
        _create_dummy_pdf(pdf_path)
        print(f"  Test PDF:  {pdf_path} ({os.path.getsize(pdf_path)} bytes)")

        # ---------------------------------------------------------------
        # Run steps
        # ---------------------------------------------------------------
        test_health()
        test_presets()

        ingest_result = test_ingest(pdf_path)
        if ingest_result is None:
            print("\n  Ingest failed — skipping pipeline steps.")
            skip("Transcription", "ingest failed")
            skip("Generation", "ingest failed")
            skip("Artifacts", "ingest failed")
            skip("Export", "ingest failed")
        else:
            test_lecture_exists()

            transcription_ok = test_transcription()
            if transcription_ok:
                generation_ok = test_generation()
                if generation_ok:
                    test_artifacts()
                    test_progress()
                    export_ok = test_export()
                    if export_ok:
                        test_export_download()
                    else:
                        skip("Export download", "export job failed")
                    test_course_progress()
                else:
                    skip("Artifacts", "generation failed")
                    skip("Export", "generation failed")
            else:
                skip("Generation", "transcription failed")
                skip("Artifacts", "transcription failed")
                skip("Export", "transcription failed")

        # Cleanup
        if not args.keep and ingest_result is not None:
            test_cleanup()
        elif args.keep:
            skip("Cleanup", "--keep flag set")

    # ---------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------
    total = _pass + _fail + _skip
    print(f"\n{'='*60}")
    print(f"  RESULTS: {_pass} passed, {_fail} failed, {_skip} skipped (total {total})")
    print(f"{'='*60}")

    if _fail > 0:
        print("\n  CANARY FAILED")
        sys.exit(1)
    else:
        print("\n  CANARY PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
