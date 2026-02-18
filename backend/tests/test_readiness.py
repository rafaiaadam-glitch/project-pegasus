from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

pytest.importorskip("fastapi")
try:
    from fastapi.testclient import TestClient
except RuntimeError as exc:  # pragma: no cover - dependency guard for CI/runtime
    if "httpx" in str(exc):
        TestClient = None
    else:
        raise

if TestClient is None:
    pytestmark = pytest.mark.skip(reason="fastapi.testclient requires httpx")

import backend.app as app_module


class HealthyDB:
    def healthcheck(self) -> None:
        return None


class BrokenDB:
    def healthcheck(self) -> None:
        raise RuntimeError("db unavailable")


class HealthyRedis:
    def ping(self) -> bool:
        return True


class BrokenRedis:
    def ping(self) -> bool:
        raise RuntimeError("redis unavailable")


def test_readiness_ok(monkeypatch, tmp_path):
    monkeypatch.setenv("PLC_STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setattr(app_module, "STORAGE_DIR", (tmp_path / "storage"))
    monkeypatch.setattr(app_module, "get_database", lambda: HealthyDB())
    monkeypatch.setattr(app_module.Redis, "from_url", lambda _url: HealthyRedis())

    client = TestClient(app_module.app)
    response = client.get("/health/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["checks"]["database"]["status"] == "ok"
    assert payload["checks"]["queue"]["status"] == "ok"
    assert payload["checks"]["storage"]["status"] == "ok"


def test_readiness_reports_dependency_errors(monkeypatch, tmp_path):
    monkeypatch.setenv("PLC_STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setattr(app_module, "STORAGE_DIR", (tmp_path / "storage"))
    monkeypatch.setattr(app_module, "get_database", lambda: BrokenDB())
    monkeypatch.setattr(app_module.Redis, "from_url", lambda _url: BrokenRedis())

    client = TestClient(app_module.app)
    response = client.get("/health/ready")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["checks"]["database"]["status"] == "error"
    assert payload["checks"]["queue"]["status"] == "error"
    assert payload["checks"]["storage"]["status"] == "ok"


def test_readiness_skips_queue_when_inline_jobs_enabled(monkeypatch, tmp_path):
    monkeypatch.setenv("PLC_STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setenv("PLC_INLINE_JOBS", "true")
    monkeypatch.setattr(app_module, "STORAGE_DIR", (tmp_path / "storage"))
    monkeypatch.setattr(app_module, "get_database", lambda: HealthyDB())

    client = TestClient(app_module.app)
    response = client.get("/health/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["checks"]["queue"]["status"] == "skipped"
