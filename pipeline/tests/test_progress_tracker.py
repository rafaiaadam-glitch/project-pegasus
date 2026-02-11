"""Tests for progress_tracker.py"""

import time
import pytest
from io import StringIO
import sys

from pipeline.progress_tracker import ProgressTracker, StepInfo


def test_step_info_duration():
    """Test StepInfo duration calculation."""
    step = StepInfo(name="test", status="pending")
    assert step.duration is None

    step.start_time = 100.0
    step.end_time = 105.5
    assert step.duration == 5.5


def test_progress_tracker_init():
    """Test ProgressTracker initialization."""
    tracker = ProgressTracker(total_steps=5, verbose=False)
    assert tracker.total_steps == 5
    assert tracker.verbose is False
    assert len(tracker.steps) == 0


def test_start_step():
    """Test starting a step."""
    tracker = ProgressTracker(total_steps=3, verbose=False)
    tracker.start_step("step1")

    assert len(tracker.steps) == 1
    assert tracker.steps[0].name == "step1"
    assert tracker.steps[0].status == "running"
    assert tracker.steps[0].start_time is not None
    assert tracker._current_step == "step1"


def test_complete_step():
    """Test completing a step."""
    tracker = ProgressTracker(total_steps=3, verbose=False)
    tracker.start_step("step1")
    time.sleep(0.01)  # Small delay
    tracker.complete_step("step1")

    step = tracker.steps[0]
    assert step.status == "completed"
    assert step.end_time is not None
    assert step.duration is not None
    assert step.duration > 0
    assert tracker._current_step is None


def test_report_error():
    """Test reporting an error for a step."""
    tracker = ProgressTracker(total_steps=3, verbose=False)
    tracker.start_step("step1")
    tracker.report_error("step1", "Something went wrong")

    step = tracker.steps[0]
    assert step.status == "failed"
    assert step.error_message == "Something went wrong"
    assert step.end_time is not None


def test_complete_unknown_step():
    """Test completing a step that doesn't exist."""
    tracker = ProgressTracker(total_steps=3, verbose=False)

    # Should not raise, just handle gracefully
    tracker.complete_step("unknown_step")
    assert len(tracker.steps) == 0


def test_get_summary():
    """Test summary generation."""
    tracker = ProgressTracker(total_steps=3, verbose=False)

    tracker.start_step("step1")
    tracker.complete_step("step1")

    tracker.start_step("step2")
    tracker.report_error("step2", "Error occurred")

    tracker.start_step("step3")
    tracker.complete_step("step3")

    summary = tracker.get_summary()

    assert "PIPELINE EXECUTION SUMMARY" in summary
    assert "step1" in summary
    assert "step2" in summary
    assert "step3" in summary
    assert "DONE" in summary
    assert "FAIL" in summary
    assert "2 succeeded, 1 failed" in summary


def test_verbose_output(capsys):
    """Test verbose output to console."""
    tracker = ProgressTracker(total_steps=2, verbose=True)

    tracker.start_step("test_step")
    captured = capsys.readouterr()
    assert "[0/2] Starting: test_step..." in captured.out

    tracker.complete_step("test_step")
    captured = capsys.readouterr()
    assert "✓ test_step" in captured.out


def test_print_summary(capsys):
    """Test printing summary to console."""
    tracker = ProgressTracker(total_steps=1, verbose=True)
    tracker.start_step("step1")
    tracker.complete_step("step1")

    tracker.print_summary()
    captured = capsys.readouterr()

    assert "PIPELINE EXECUTION SUMMARY" in captured.out
    assert "step1" in captured.out


def test_multiple_steps_workflow():
    """Test complete workflow with multiple steps."""
    tracker = ProgressTracker(total_steps=3, verbose=False)

    # Step 1: success
    tracker.start_step("generation")
    time.sleep(0.01)
    tracker.complete_step("generation")

    # Step 2: success
    tracker.start_step("validation")
    time.sleep(0.01)
    tracker.complete_step("validation")

    # Step 3: success
    tracker.start_step("export")
    time.sleep(0.01)
    tracker.complete_step("export")

    assert len(tracker.steps) == 3
    assert all(step.status == "completed" for step in tracker.steps)
    assert all(step.duration > 0 for step in tracker.steps)

    summary = tracker.get_summary()
    assert "3 succeeded, 0 failed" in summary


def test_error_handling_workflow():
    """Test workflow with errors."""
    tracker = ProgressTracker(total_steps=3, verbose=False)

    tracker.start_step("step1")
    tracker.complete_step("step1")

    tracker.start_step("step2")
    tracker.report_error("step2", "Network timeout")

    tracker.start_step("step3")
    tracker.complete_step("step3")

    summary = tracker.get_summary()
    assert "2 succeeded, 1 failed" in summary
    assert "Network timeout" in summary
