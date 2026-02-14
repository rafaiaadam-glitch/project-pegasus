from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from backend import storage


class _FakeBlob:
    def __init__(self, exists: bool = True) -> None:
        self._exists = exists
        self.deleted = False

    def delete(self) -> None:
        self.deleted = True

    def exists(self) -> bool:
        return self._exists


class _FakeBucket:
    def __init__(self, blob: _FakeBlob) -> None:
        self._blob = blob

    def blob(self, _name: str) -> _FakeBlob:
        return self._blob


class _FakeClient:
    def __init__(self, blob: _FakeBlob) -> None:
        self._blob = blob

    def bucket(self, _name: str) -> _FakeBucket:
        return _FakeBucket(self._blob)


def test_delete_storage_path_supports_gs(monkeypatch):
    blob = _FakeBlob()
    monkeypatch.setattr(storage, "_gcs_client", lambda: _FakeClient(blob))

    deleted = storage.delete_storage_path("gs://bucket/path/to/file.json")

    assert deleted is True
    assert blob.deleted is True


def test_storage_path_exists_supports_gs(monkeypatch):
    blob = _FakeBlob(exists=True)
    monkeypatch.setattr(storage, "_gcs_client", lambda: _FakeClient(blob))

    assert storage.storage_path_exists("gs://bucket/path/to/file.json") is True
