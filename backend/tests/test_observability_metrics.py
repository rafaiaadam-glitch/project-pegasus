from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    try:
        from starlette.testclient import TestClient
    except Exception:  # pragma: no cover
        TestClient = None

if TestClient is None:
    pytest.skip("TestClient dependencies are unavailable", allow_module_level=True)

import backend.app as app_module
import backend.jobs as jobs_module
from backend.observability import METRICS


class FakeDB:
    def __init__(self) -> None:
        self.jobs: dict[str, dict] = {}

    def fetch_jobs(self, lecture_id=None, limit=None, offset=None):
        rows = list(self.jobs.values())
        if lecture_id:
            rows = [row for row in rows if row.get("lecture_id") == lecture_id]
        if offset:
            rows = rows[offset:]
        if limit is not None:
            rows = rows[:limit]
        return rows

    def create_job(self, payload: dict) -> None:
        self.jobs[payload["id"]] = payload

    def update_job(self, job_id: str, status=None, result=None, error=None, updated_at=None) -> None:
        job = self.jobs[job_id]
        if status is not None:
            job["status"] = status
        if result is not None:
            job["result"] = result
        if error is not None:
            job["error"] = error
        if updated_at is not None:
            job["updated_at"] = updated_at

    def fetch_job(self, job_id: str):
        return self.jobs.get(job_id)


def test_ops_metrics_reports_queue_depth(monkeypatch):
    fake_db = FakeDB()
    fake_db.jobs = {
        "a": {"id": "a", "status": "queued"},
        "b": {"id": "b", "status": "running"},
        "c": {"id": "c", "status": "failed"},
        "d": {"id": "d", "status": "completed"},
    }

    METRICS.reset()
    monkeypatch.setattr(app_module, "get_database", lambda: fake_db)

    client = TestClient(app_module.app)
    response = client.get("/ops/metrics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["metrics"]["queueDepth"] == {"queued": 1, "running": 1, "failed": 1}


def test_job_metrics_track_status_latency_and_retries(monkeypatch):
    fake_db = FakeDB()
    fake_db.create_job(
        {
            "id": "job-1",
            "lecture_id": "lecture-1",
            "job_type": "generation",
            "status": "queued",
            "result": None,
            "error": None,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
    )

    METRICS.reset()
    monkeypatch.setattr(jobs_module, "get_database", lambda: fake_db)

    jobs_module._update_job("job-1", "running", job_type="generation")
    time.sleep(0.01)
    jobs_module._update_job("job-1", "failed", error="boom", job_type="generation")
    METRICS.increment_retry("generation")

    snapshot = METRICS.snapshot(queue_depth={"queued": 0, "running": 0, "failed": 1})
    assert snapshot["jobStatusEvents"]["generation"]["running"] >= 1
    assert snapshot["jobStatusEvents"]["generation"]["failed"] >= 1
    assert snapshot["jobFailures"]["generation"] >= 1
    assert snapshot["jobLatencyMs"]["generation"]["count"] >= 1
    assert snapshot["jobLatencyMs"]["generation"]["p95Ms"] >= 0
    assert snapshot["jobRetries"]["generation"] == 1


def test_ops_metrics_prometheus_format(monkeypatch):
    fake_db = FakeDB()
    fake_db.jobs = {
        "a": {"id": "a", "status": "queued", "job_type": "generation"},
        "b": {"id": "b", "status": "failed", "job_type": "generation"},
    }

    METRICS.reset()
    METRICS.increment_job_status("generation", "queued")
    METRICS.increment_job_status("generation", "failed")
    METRICS.increment_job_failure("generation")
    METRICS.increment_retry("generation")
    METRICS.observe_job_latency("generation", 100.0)
    METRICS.observe_job_latency("generation", 123.0)
    METRICS.observe_job_latency("generation", 200.0)

    monkeypatch.setattr(app_module, "get_database", lambda: fake_db)

    client = TestClient(app_module.app)
    response = client.get("/ops/metrics/prometheus")

    assert response.status_code == 200
    text = response.text
    assert "# TYPE pegasus_queue_depth gauge" in text
    assert 'pegasus_queue_depth{status="queued"} 1' in text
    assert 'pegasus_queue_depth{status="failed"} 1' in text
    assert 'pegasus_job_failures_total{job_type="generation"} 1' in text
    assert 'pegasus_job_retries_total{job_type="generation"} 1' in text
    assert 'pegasus_job_latency_ms_avg{job_type="generation"} 141.0' in text
    assert 'pegasus_job_latency_ms_p95{job_type="generation"} 200.0' in text
