from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from pipeline.thread_continuity_check import evaluate_thread_continuity, load_threads_from_file


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "thread_continuity"


def test_evaluate_thread_continuity_passes_with_multi_lecture_ratio():
    threads = [
        {"id": "t1", "lectureRefs": ["l1", "l2"]},
        {"id": "t2", "lectureRefs": ["l2", "l3"]},
        {"id": "t3", "lectureRefs": ["l3"]},
    ]
    report = evaluate_thread_continuity(threads, min_multi_lecture_ratio=0.5)

    assert report.total_threads == 3
    assert report.multi_lecture_threads == 2
    assert report.multi_lecture_ratio == pytest.approx(2 / 3)
    assert report.passed is True


def test_evaluate_thread_continuity_fails_when_ratio_below_threshold():
    threads = [
        {"id": "t1", "lectureRefs": ["l1"]},
        {"id": "t2", "lectureRefs": ["l2"]},
    ]
    report = evaluate_thread_continuity(threads, min_multi_lecture_ratio=0.5)

    assert report.multi_lecture_threads == 0
    assert report.passed is False


def test_load_threads_from_file_supports_list_payload():
    path = FIXTURE_DIR / "threads.good.json"
    threads = load_threads_from_file(path)
    assert len(threads) == 4


def test_cli_passes_for_good_fixture():
    path = FIXTURE_DIR / "threads.good.json"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pipeline.thread_continuity_check",
            "--threads-file",
            str(path),
            "--min-ratio",
            "0.5",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "Thread continuity:" in result.stdout


def test_cli_fails_for_bad_fixture():
    path = FIXTURE_DIR / "threads.bad.json"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pipeline.thread_continuity_check",
            "--threads-file",
            str(path),
            "--min-ratio",
            "0.5",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "FAIL" in result.stdout
