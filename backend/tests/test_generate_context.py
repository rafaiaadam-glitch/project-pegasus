from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

import pytest
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

import backend.app as app_module


@dataclass
class FakeDB:
    lecture: dict | None

    def fetch_lecture(self, lecture_id: str):
        return self.lecture


def test_resolve_generation_identifiers_defaults_to_stored_values():
    db = FakeDB(
        lecture={
            "id": "lecture-1",
            "course_id": "course-1",
            "preset_id": "exam-mode",
        }
    )

    course_id, preset_id = app_module._resolve_generation_identifiers(
        db,
        "lecture-1",
        app_module.GenerateRequest(),
    )

    assert course_id == "course-1"
    assert preset_id == "exam-mode"


def test_resolve_generation_identifiers_rejects_mismatched_course():
    db = FakeDB(
        lecture={
            "id": "lecture-1",
            "course_id": "course-1",
            "preset_id": "exam-mode",
        }
    )

    with pytest.raises(HTTPException) as exc:
        app_module._resolve_generation_identifiers(
            db,
            "lecture-1",
            app_module.GenerateRequest(course_id="course-2"),
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "course_id does not match lecture."


def test_resolve_generation_identifiers_requires_preset():
    db = FakeDB(
        lecture={
            "id": "lecture-1",
            "course_id": "course-1",
            "preset_id": None,
        }
    )

    with pytest.raises(HTTPException) as exc:
        app_module._resolve_generation_identifiers(
            db,
            "lecture-1",
            app_module.GenerateRequest(course_id="course-1"),
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "preset_id is required."
