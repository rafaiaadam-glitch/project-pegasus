from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from backend import storage


def test_storage_mode_must_be_supported(monkeypatch):
    monkeypatch.setenv("STORAGE_MODE", "unsupported")

    with pytest.raises(RuntimeError, match="STORAGE_MODE must be either 'local', 's3', or 'gcs'"):
        storage._config()


def test_s3_storage_requires_bucket(monkeypatch):
    monkeypatch.setenv("STORAGE_MODE", "s3")
    monkeypatch.delenv("S3_BUCKET", raising=False)

    with pytest.raises(RuntimeError, match="S3_BUCKET must be set for S3 storage"):
        storage._config()


def test_s3_storage_requires_non_empty_prefix(monkeypatch):
    monkeypatch.setenv("STORAGE_MODE", "s3")
    monkeypatch.setenv("S3_BUCKET", "pegasus-test")
    monkeypatch.setenv("S3_PREFIX", "")

    with pytest.raises(RuntimeError, match="S3_PREFIX must be a non-empty path segment"):
        storage._config()




def test_gcs_storage_requires_bucket(monkeypatch):
    monkeypatch.setenv("STORAGE_MODE", "gcs")
    monkeypatch.delenv("GCS_BUCKET", raising=False)

    with pytest.raises(RuntimeError, match="GCS_BUCKET must be set for GCS storage"):
        storage._config()


def test_gcs_storage_requires_non_empty_prefix(monkeypatch):
    monkeypatch.setenv("STORAGE_MODE", "gcs")
    monkeypatch.setenv("GCS_BUCKET", "pegasus-test")
    monkeypatch.setenv("GCS_PREFIX", "")

    with pytest.raises(RuntimeError, match="GCS_PREFIX must be a non-empty path segment"):
        storage._config()

def test_local_storage_default_config(monkeypatch, tmp_path):
    monkeypatch.delenv("STORAGE_MODE", raising=False)
    monkeypatch.setenv("PLC_STORAGE_DIR", str(tmp_path / "storage"))

    cfg = storage._config()

    assert cfg.mode == "local"
    assert str(cfg.local_dir).endswith("storage")
