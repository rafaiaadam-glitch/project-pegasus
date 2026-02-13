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


class _NoopDatabase:
    def healthcheck(self) -> None:
        return None


def test_app_startup_lifespan_validates_runtime_environment(monkeypatch, tmp_path):
    observed: list[str] = []

    def _fake_validate_runtime_environment(service: str) -> None:
        observed.append(service)

    monkeypatch.setenv("DATABASE_URL", "postgres://example")
    monkeypatch.setenv("PLC_INLINE_JOBS", "true")
    monkeypatch.setenv("PLC_STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setattr(app_module, "validate_runtime_environment", _fake_validate_runtime_environment)
    monkeypatch.setattr(app_module, "get_database", lambda: _NoopDatabase())
    monkeypatch.setattr(app_module, "STORAGE_DIR", (tmp_path / "storage"))

    with TestClient(app_module.app) as client:
        response = client.get("/health/live")

    assert response.status_code == 200
    assert observed == ["api"]
