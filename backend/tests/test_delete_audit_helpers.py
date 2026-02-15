from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

import backend.app as app_module


class _FailingAuditDB:
    def create_deletion_audit_event(self, _payload: dict) -> None:
        raise RuntimeError("audit write unavailable")


class _DeleteOnlyDB:
    def __init__(self) -> None:
        self.lectures = {
            "lecture-1": {
                "id": "lecture-1",
                "audio_path": None,
                "transcript_path": None,
            }
        }

    def fetch_lecture(self, lecture_id: str):
        return self.lectures.get(lecture_id)

    def fetch_artifacts(self, _lecture_id: str):
        return []

    def fetch_exports(self, _lecture_id: str):
        return []

    def fetch_threads(self, _lecture_id: str):
        return []

    def delete_lecture_records(self, lecture_id: str):
        self.lectures.pop(lecture_id, None)
        return {"artifacts": 0, "exports": 0, "jobs": 0, "lectures": 1}


def _request(actor: str = ""):
    headers = {"x-actor-id": actor} if actor else {}
    return SimpleNamespace(headers=headers, state=SimpleNamespace(request_id="req-1"))


def test_record_deletion_audit_event_is_non_blocking_when_write_fails(caplog):
    app_module._record_deletion_audit_event(
        _FailingAuditDB(),
        request=_request(actor="qa-user"),
        entity_type="lecture",
        entity_id="lecture-1",
        purge_storage=True,
        deleted_counts={"lectures": 1},
    )

    assert "deletion.audit_write_failed" in caplog.text


def test_delete_lecture_data_uses_supplied_db_without_get_database(monkeypatch):
    db = _DeleteOnlyDB()
    monkeypatch.setattr(app_module, "get_database", lambda: (_ for _ in ()).throw(RuntimeError("should not be called")))

    payload = app_module._delete_lecture_data("lecture-1", purge_storage=False, db=db)

    assert payload["deleted"]["lectures"] == 1
