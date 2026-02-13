from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

pytest.importorskip("fastapi")
try:
    from fastapi.testclient import TestClient
except RuntimeError as exc:  # pragma: no cover - dependency guard
    if "httpx" in str(exc):
        TestClient = None
    else:
        raise

if TestClient is None:
    pytestmark = pytest.mark.skip(reason="fastapi.testclient requires httpx")

import backend.app as app_module


class MetricsDB:
    def __init__(self, jobs):
        self.jobs = jobs

    def fetch_jobs(self, *, limit=None, offset=None, lecture_id=None):
        return self.jobs[:limit]


class HealthyRedis:
    def llen(self, _key: str) -> int:
        return 3


class BrokenRedis:
    def llen(self, _key: str) -> int:
        raise RuntimeError("queue unavailable")


def _build_job(status: str, duration_ms: int) -> dict:
    start = datetime(2026, 2, 13, 12, 0, 0, tzinfo=timezone.utc)
    end = start + timedelta(milliseconds=duration_ms)
    return {
        "id": f"job-{status}-{duration_ms}",
        "status": status,
        "created_at": start.isoformat(),
        "updated_at": end.isoformat(),
        "result": {},
    }


def test_operational_metrics_happy_path(monkeypatch):
    jobs = [
        _build_job("completed", 1000),
        _build_job("completed", 2000),
        _build_job("failed", 2500),
    ]
    monkeypatch.setattr(app_module, "get_database", lambda: MetricsDB(jobs))
    monkeypatch.setattr(app_module.Redis, "from_url", lambda _url: HealthyRedis())

    client = TestClient(app_module.app)
    response = client.get("/metrics/operational?window=100")

    assert response.status_code == 200
    payload = response.json()
    assert payload["jobs"]["total"] == 3
    assert payload["jobs"]["failed"] == 1
    assert payload["jobs"]["replayed"] == 0
    assert payload["jobs"]["failureRate"] == pytest.approx(0.3333, rel=0, abs=1e-4)
    assert payload["jobs"]["latencyMs"]["p50"] == 1500
    assert payload["jobs"]["latencyMs"]["p95"] == 2000
    assert payload["queue"]["status"] == "ok"
    assert payload["queue"]["depth"] == 3


def test_operational_metrics_reports_queue_errors(monkeypatch):
    jobs = [_build_job("completed", 300)]
    monkeypatch.setattr(app_module, "get_database", lambda: MetricsDB(jobs))
    monkeypatch.setattr(app_module.Redis, "from_url", lambda _url: BrokenRedis())

    client = TestClient(app_module.app)
    response = client.get("/metrics/operational")

    assert response.status_code == 503
    payload = response.json()
    assert payload["queue"]["status"] == "error"
    assert "queue unavailable" in payload["queue"]["error"]


def test_operational_metrics_skips_queue_in_inline_mode(monkeypatch):
    jobs = [_build_job("completed", 300)]
    monkeypatch.setenv("PLC_INLINE_JOBS", "true")
    monkeypatch.setattr(app_module, "get_database", lambda: MetricsDB(jobs))

    client = TestClient(app_module.app)
    response = client.get("/metrics/operational")

    assert response.status_code == 200
    payload = response.json()
    assert payload["queue"]["status"] == "skipped"
    assert payload["queue"]["depth"] == 0


def test_operational_metrics_counts_replayed_jobs(monkeypatch):
    job = _build_job("completed", 300)
    job["result"] = {"replayOfJobId": "job-old"}
    monkeypatch.setattr(app_module, "get_database", lambda: MetricsDB([job]))
    monkeypatch.setattr(app_module.Redis, "from_url", lambda _url: HealthyRedis())

    client = TestClient(app_module.app)
    response = client.get("/metrics/operational")

    assert response.status_code == 200
    payload = response.json()
    assert payload["jobs"]["replayed"] == 1
