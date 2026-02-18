from __future__ import annotations

import io
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

import backend.app as app_module
from backend import storage


def test_max_audio_upload_bytes_parses_integer(monkeypatch):
    monkeypatch.setenv("PLC_MAX_AUDIO_UPLOAD_MB", "5")

    assert app_module._max_audio_upload_bytes() == 5 * 1024 * 1024


def test_max_audio_upload_bytes_rejects_invalid(monkeypatch):
    monkeypatch.setenv("PLC_MAX_AUDIO_UPLOAD_MB", "abc")

    with pytest.raises(RuntimeError, match="must be an integer"):
        app_module._max_audio_upload_bytes()


def test_max_audio_upload_bytes_rejects_non_positive(monkeypatch):
    monkeypatch.setenv("PLC_MAX_AUDIO_UPLOAD_MB", "0")

    with pytest.raises(RuntimeError, match="must be a positive integer"):
        app_module._max_audio_upload_bytes()


def test_save_audio_enforces_max_bytes(monkeypatch, tmp_path):
    monkeypatch.setenv("STORAGE_MODE", "local")
    monkeypatch.setenv("PLC_STORAGE_DIR", str(tmp_path / "storage"))

    too_large = io.BytesIO(b"a" * 12)
    with pytest.raises(ValueError, match="exceeds upload limit"):
        storage.save_audio(too_large, "too-large.bin", max_bytes=10)


def test_save_audio_within_limit_succeeds(monkeypatch, tmp_path):
    monkeypatch.setenv("STORAGE_MODE", "local")
    monkeypatch.setenv("PLC_STORAGE_DIR", str(tmp_path / "storage"))

    payload = b"a" * 10
    path = storage.save_audio(io.BytesIO(payload), "ok.bin", max_bytes=10)

    assert Path(path).exists()
    assert Path(path).read_bytes() == payload
