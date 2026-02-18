from pipeline.thread_continuity import continuity_gate_passes, score_thread_continuity


def test_score_thread_continuity_with_cross_lecture_updates():
    threads = [
        {"id": "t-1", "lectureRefs": ["l-1", "l-2"]},
        {"id": "t-2", "lectureRefs": ["l-2"]},
    ]
    occurrences = [
        {"threadId": "t-1", "confidence": 0.8},
        {"threadId": "t-2", "confidence": 0.9},
    ]
    updates = [{"threadId": "t-1"}]

    metrics = score_thread_continuity(threads, occurrences, updates)

    assert metrics["coverage"] == 1.0
    assert metrics["crossLectureRate"] == 0.5
    assert metrics["evidenceConfidence"] == 0.85
    assert metrics["updateDensity"] == 1.0
    assert metrics["score"] == 0.82
    assert continuity_gate_passes(metrics)


def test_score_thread_continuity_without_valid_thread_ids_returns_zeros():
    metrics = score_thread_continuity([{}, {"id": ""}], [], [])

    assert metrics == {
        "coverage": 0.0,
        "crossLectureRate": 0.0,
        "evidenceConfidence": 0.0,
        "updateDensity": 0.0,
        "score": 0.0,
    }
    assert not continuity_gate_passes(metrics)


def test_score_thread_continuity_ignores_unknown_or_malformed_records():
    threads = [
        {"id": "t-1", "lectureRefs": ["l-1", "l-2"]},
        {"id": "t-2", "lectureRefs": ["l-1"]},
        {"lectureRefs": ["l-1", "l-2"]},
    ]
    occurrences = [
        {"threadId": "t-1", "confidence": 0.8},
        {"threadId": "unknown", "confidence": 0.95},
        {"threadId": None, "confidence": "bad"},
    ]
    updates = [{"threadId": "t-1"}, {"threadId": "unknown"}]

    metrics = score_thread_continuity(threads, occurrences, updates)

    assert metrics["coverage"] == 0.5
    assert metrics["crossLectureRate"] == 0.5
    assert metrics["evidenceConfidence"] == 0.875
    assert metrics["updateDensity"] == 1.0
    assert metrics["score"] == 0.65
    assert continuity_gate_passes(metrics, threshold=0.65)
    assert not continuity_gate_passes(metrics, threshold=0.651)
