import json
from pathlib import Path

import pytest

from pipeline.run_pipeline import PipelineContext, _summary

SNAPSHOT_DIR = Path(__file__).resolve().parent / "snapshots"
TRANSCRIPT = "Sample transcript for deterministic summary snapshot coverage."
GENERATED_AT = "2026-01-01T00:00:00Z"

PRESET_IDS = [
    "exam-mode",
    "beginner-mode",
    "research-mode",
    "concept-map-mode",
    "neurodivergent-friendly-mode",
]


def _normalized_summary(preset_id: str) -> dict:
    context = PipelineContext(
        course_id="snapshot-course",
        lecture_id="snapshot-lecture",
        preset_id=preset_id,
        generated_at=GENERATED_AT,
        thread_refs=["thread-a", "thread-b"],
    )
    payload = _summary(context, TRANSCRIPT)
    return {
        "artifactType": payload["artifactType"],
        "presetId": payload["presetId"],
        "overview": payload["overview"],
        "sections": payload["sections"],
    }


@pytest.mark.parametrize("preset_id", PRESET_IDS)
def test_summary_matches_golden_snapshot(preset_id: str):
    snapshot_path = SNAPSHOT_DIR / f"summary.{preset_id}.json"
    expected = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert _normalized_summary(preset_id) == expected
