"""Thread continuity scoring utilities.

This module provides a lightweight quality gate that estimates whether thread
records remain consistent and reusable across lectures.
"""

from __future__ import annotations

from typing import Any, Dict, List, Set


DEFAULT_CONTINUITY_THRESHOLD = 0.6


def _clamp_0_1(value: float) -> float:
    return max(0.0, min(1.0, value))


def score_thread_continuity(
    threads: List[Dict[str, Any]],
    occurrences: List[Dict[str, Any]],
    updates: List[Dict[str, Any]],
) -> Dict[str, float]:
    """Compute continuity metrics and a composite continuity score.

    The score combines:
    - Coverage: % of valid threads referenced by at least one occurrence.
    - Cross-lecture continuity: % of valid threads seen in more than one lecture.
    - Evidence confidence: mean confidence from thread occurrences.
    - Update density: % of multi-lecture threads with at least one update.
    """

    valid_thread_ids: Set[str] = {
        str(thread["id"])
        for thread in threads
        if isinstance(thread, dict) and isinstance(thread.get("id"), str) and thread.get("id")
    }
    if not valid_thread_ids:
        return {
            "coverage": 0.0,
            "crossLectureRate": 0.0,
            "evidenceConfidence": 0.0,
            "updateDensity": 0.0,
            "score": 0.0,
        }

    refs_by_occurrence = {
        str(record.get("threadId"))
        for record in occurrences
        if isinstance(record, dict)
        and isinstance(record.get("threadId"), str)
        and record.get("threadId")
    }
    coverage = len(valid_thread_ids & refs_by_occurrence) / len(valid_thread_ids)

    multi_lecture_ids = {
        str(thread["id"])
        for thread in threads
        if isinstance(thread, dict)
        and isinstance(thread.get("id"), str)
        and thread.get("id")
        and len({str(ref) for ref in thread.get("lectureRefs", []) if ref}) > 1
    }
    cross_lecture_rate = len(multi_lecture_ids) / len(valid_thread_ids)

    confidences = [
        float(record.get("confidence"))
        for record in occurrences
        if isinstance(record, dict) and isinstance(record.get("confidence"), (int, float))
    ]
    evidence_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    updated_thread_ids = {
        str(record.get("threadId"))
        for record in updates
        if isinstance(record, dict)
        and isinstance(record.get("threadId"), str)
        and record.get("threadId")
    }
    if multi_lecture_ids:
        update_density = len(multi_lecture_ids & updated_thread_ids) / len(multi_lecture_ids)
    else:
        update_density = 0.0

    score = (
        (0.35 * coverage)
        + (0.30 * cross_lecture_rate)
        + (0.20 * evidence_confidence)
        + (0.15 * update_density)
    )

    return {
        "coverage": round(_clamp_0_1(coverage), 4),
        "crossLectureRate": round(_clamp_0_1(cross_lecture_rate), 4),
        "evidenceConfidence": round(_clamp_0_1(evidence_confidence), 4),
        "updateDensity": round(_clamp_0_1(update_density), 4),
        "score": round(_clamp_0_1(score), 4),
    }


def continuity_gate_passes(metrics: Dict[str, float], threshold: float = DEFAULT_CONTINUITY_THRESHOLD) -> bool:
    """Return whether the computed continuity score passes the threshold."""

    score = float(metrics.get("score", 0.0))
    return score >= _clamp_0_1(float(threshold))
