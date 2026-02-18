from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from backend.runtime_config import validate_runtime_environment


def test_requires_database_url_for_api(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="DATABASE_URL must be set"):
        validate_runtime_environment("api", env={})


def test_requires_redis_url_when_inline_jobs_disabled():
    env = {
        "DATABASE_URL": "postgres://example",
        "PLC_INLINE_JOBS": "false",
        "REDIS_URL": "   ",
    }

    with pytest.raises(RuntimeError, match="REDIS_URL must be set when queue-backed jobs are enabled"):
        validate_runtime_environment("api", env=env)


def test_worker_requires_redis_url_even_if_inline_flag_is_true():
    env = {
        "DATABASE_URL": "postgres://example",
        "PLC_INLINE_JOBS": "true",
        "REDIS_URL": "",
    }

    with pytest.raises(RuntimeError, match="REDIS_URL must be set when queue-backed jobs are enabled"):
        validate_runtime_environment("worker", env=env)


def test_inline_api_allows_missing_redis_url_with_valid_database_and_local_storage(tmp_path):
    env = {
        "DATABASE_URL": "postgres://example",
        "PLC_INLINE_JOBS": "true",
        "PLC_STORAGE_DIR": str(tmp_path / "storage"),
    }

    validate_runtime_environment("api", env=env)


def test_surfaces_storage_validation_errors():
    env = {
        "DATABASE_URL": "postgres://example",
        "STORAGE_MODE": "s3",
        "S3_PREFIX": "",
    }

    with pytest.raises(RuntimeError, match="S3_BUCKET must be set for S3 storage"):
        validate_runtime_environment("api", env=env)


def test_rejects_invalid_write_rate_limit_values():
    env = {
        "DATABASE_URL": "postgres://example",
        "PLC_WRITE_RATE_LIMIT_MAX_REQUESTS": "NaN",
    }

    with pytest.raises(RuntimeError, match="PLC_WRITE_RATE_LIMIT_MAX_REQUESTS must be an integer"):
        validate_runtime_environment("api", env=env)


def test_rejects_invalid_idempotency_ttl_values():
    env = {
        "DATABASE_URL": "postgres://example",
        "PLC_IDEMPOTENCY_TTL_SEC": "NaN",
    }

    with pytest.raises(RuntimeError, match="PLC_IDEMPOTENCY_TTL_SEC must be an integer"):
        validate_runtime_environment("api", env=env)
