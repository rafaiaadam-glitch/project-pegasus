import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from pipeline.run_pipeline import ARTIFACT_SCHEMA_DIR, _validate


def test_llm_summary_schema_validation() -> None:
    payload = {
        "id": "summary-1",
        "courseId": "course-001",
        "lectureId": "lecture-001",
        "presetId": "exam-mode",
        "artifactType": "summary",
        "generatedAt": "2024-01-01T00:00:00Z",
        "version": "0.1",
        "sections": [],
    }
    with pytest.raises(ValueError):
        _validate(payload, "summary.schema.json", ARTIFACT_SCHEMA_DIR)
