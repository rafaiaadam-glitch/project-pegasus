#!/usr/bin/env python3
"""Progress tracking for pipeline execution with step timing and status reporting."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class StepInfo:
    """Information about a pipeline step."""

    name: str
    status: str  # "pending", "running", "completed", "failed"
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    error_message: Optional[str] = None

    @property
    def duration(self) -> Optional[float]:
        """Calculate step duration in seconds."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None


class ProgressTracker:
    """Tracks progress of pipeline execution with real-time feedback."""

    def __init__(
        self,
        total_steps: int = 0,
        verbose: bool = True,
        log_file: Optional[str] = None,
    ):
        """
        Initialize progress tracker.

        Args:
            total_steps: Expected number of steps in the pipeline
            verbose: Whether to print progress to console
            log_file: Optional path to append step logs and summary output
        """
        self.total_steps = total_steps
        self.verbose = verbose
        self.log_file = Path(log_file) if log_file else None
        self.steps: List[StepInfo] = []
        self._step_index: Dict[str, int] = {}
        self._current_step: Optional[str] = None
        self._pipeline_start = time.time()

    def _emit(self, message: str) -> None:
        """Write a progress message to stdout and/or a log file."""
        if self.verbose:
            print(message)
        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            with self.log_file.open("a", encoding="utf-8") as handle:
                handle.write(f"{message}\n")

    def start_step(self, step_name: str) -> None:
        """
        Mark a step as started.

        Args:
            step_name: Name of the step (e.g., "thread_generation")
        """
        step_num = len(self.steps)
        step = StepInfo(name=step_name, status="running", start_time=time.time())
        self.steps.append(step)
        self._step_index[step_name] = step_num
        self._current_step = step_name

        total_info = f"/{self.total_steps}" if self.total_steps > 0 else ""
        if self.verbose or self.log_file:
            self._emit(f"[{step_num}{total_info}] Starting: {step_name}...")

    def complete_step(self, step_name: str) -> None:
        """
        Mark a step as completed successfully.

        Args:
            step_name: Name of the step to complete
        """
        if step_name not in self._step_index:
            if self.verbose:
                self._emit(f"Warning: Attempting to complete unknown step '{step_name}'")
            elif self.log_file:
                self._emit(f"Warning: Attempting to complete unknown step '{step_name}'")
            return

        step = self.steps[self._step_index[step_name]]
        step.status = "completed"
        step.end_time = time.time()

        if step.duration:
            self._emit(f"✓ {step_name} ({step.duration:.1f}s)")

        self._current_step = None

    def report_error(self, step_name: str, error_message: str) -> None:
        """
        Mark a step as failed with an error message.

        Args:
            step_name: Name of the step that failed
            error_message: Description of the error
        """
        if step_name not in self._step_index:
            if self.verbose:
                self._emit(f"✗ Error in unknown step '{step_name}': {error_message}")
            elif self.log_file:
                self._emit(f"✗ Error in unknown step '{step_name}': {error_message}")
            return

        step = self.steps[self._step_index[step_name]]
        step.status = "failed"
        step.end_time = time.time()
        step.error_message = error_message

        duration_info = f" ({step.duration:.1f}s)" if step.duration else ""
        self._emit(f"✗ {step_name}{duration_info}")
        self._emit(f"  Error: {error_message}")

        self._current_step = None

    def get_summary(self) -> str:
        """
        Generate a summary report of all steps.

        Returns:
            Formatted summary string with step statuses and timings
        """
        total_duration = time.time() - self._pipeline_start
        completed = sum(1 for s in self.steps if s.status == "completed")
        failed = sum(1 for s in self.steps if s.status == "failed")

        lines = [
            "",
            "=" * 60,
            "PIPELINE EXECUTION SUMMARY",
            "=" * 60,
        ]

        for step in self.steps:
            status_icon = {
                "completed": "DONE",
                "failed": "FAIL",
                "running": "RUN ",
                "pending": "PEND",
            }.get(step.status, "????")

            duration_str = f"{step.duration:.1f}s" if step.duration else "---"
            lines.append(f"  {status_icon}         {step.name:<30} {duration_str:>8}")

            if step.error_message:
                lines.append(f"               └─ Error: {step.error_message}")

        lines.extend([
            "=" * 60,
            f"Total duration: {total_duration:.1f}s",
            f"Steps: {completed} succeeded, {failed} failed",
            "=" * 60,
        ])

        return "\n".join(lines)

    def print_summary(self) -> None:
        """Print the summary report to console."""
        summary = self.get_summary()
        if self.verbose:
            print(summary)
        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            with self.log_file.open("a", encoding="utf-8") as handle:
                handle.write(f"{summary}\n")
