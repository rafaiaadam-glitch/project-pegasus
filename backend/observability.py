from __future__ import annotations

import threading
from collections import defaultdict
from typing import Any


class InMemoryMetricsStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._job_status_events: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._job_failures: dict[str, int] = defaultdict(int)
        self._job_latency: dict[str, dict[str, float]] = defaultdict(
            lambda: {"count": 0.0, "sum_ms": 0.0, "max_ms": 0.0}
        )
        self._retry_events: dict[str, int] = defaultdict(int)
        # Thinking model specific metrics
        self._thinking_latency: dict[str, dict[str, float]] = defaultdict(
            lambda: {"count": 0.0, "sum_seconds": 0.0, "max_seconds": 0.0}
        )
        self._thinking_errors: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    def reset(self) -> None:
        with self._lock:
            self._job_status_events.clear()
            self._job_failures.clear()
            self._job_latency.clear()
            self._retry_events.clear()
            self._thinking_latency.clear()
            self._thinking_errors.clear()

    def increment_job_status(self, job_type: str, status: str) -> None:
        normalized_type = (job_type or "unknown").strip() or "unknown"
        normalized_status = (status or "unknown").strip() or "unknown"
        with self._lock:
            self._job_status_events[normalized_type][normalized_status] += 1

    def increment_job_failure(self, job_type: str) -> None:
        normalized_type = (job_type or "unknown").strip() or "unknown"
        with self._lock:
            self._job_failures[normalized_type] += 1

    def observe_job_latency(self, job_type: str, duration_ms: float) -> None:
        normalized_type = (job_type or "unknown").strip() or "unknown"
        with self._lock:
            metric = self._job_latency[normalized_type]
            metric["count"] += 1
            metric["sum_ms"] += max(0.0, duration_ms)
            metric["max_ms"] = max(metric["max_ms"], max(0.0, duration_ms))

    def increment_retry(self, job_type: str) -> None:
        normalized_type = (job_type or "unknown").strip() or "unknown"
        with self._lock:
            self._retry_events[normalized_type] += 1

    def observe_thinking_latency(self, model: str, duration_seconds: float, status: str = "success") -> None:
        """Track latency specifically for reasoning/thinking models"""
        key = f"{model}:{status}"
        with self._lock:
            metric = self._thinking_latency[key]
            metric["count"] += 1
            metric["sum_seconds"] += max(0.0, duration_seconds)
            metric["max_seconds"] = max(metric["max_seconds"], max(0.0, duration_seconds))

    def increment_thinking_error(self, model: str, error_code: str) -> None:
        """Track reasoning-specific failures"""
        with self._lock:
            self._thinking_errors[model][error_code] += 1

    def snapshot(self, queue_depth: dict[str, int] | None = None) -> dict[str, Any]:
        with self._lock:
            latency: dict[str, dict[str, float]] = {}
            for job_type, metric in self._job_latency.items():
                count = metric["count"]
                avg_ms = (metric["sum_ms"] / count) if count > 0 else 0.0
                latency[job_type] = {
                    "count": int(count),
                    "avgMs": round(avg_ms, 2),
                    "maxMs": round(metric["max_ms"], 2),
                }

            # Process thinking latency metrics
            thinking_latency: dict[str, dict[str, float]] = {}
            for key, metric in self._thinking_latency.items():
                count = metric["count"]
                avg_seconds = (metric["sum_seconds"] / count) if count > 0 else 0.0
                thinking_latency[key] = {
                    "count": int(count),
                    "avgSeconds": round(avg_seconds, 2),
                    "maxSeconds": round(metric["max_seconds"], 2),
                }

            return {
                "queueDepth": queue_depth or {},
                "jobStatusEvents": {
                    key: dict(value) for key, value in self._job_status_events.items()
                },
                "jobFailures": dict(self._job_failures),
                "jobLatencyMs": latency,
                "jobRetries": dict(self._retry_events),
                "thinkingLatency": thinking_latency,
                "thinkingErrors": {key: dict(value) for key, value in self._thinking_errors.items()},
            }


def _escape_label(value: str) -> str:
    return value.replace("\\", r"\\").replace('"', r'\"')


def render_prometheus_metrics(snapshot: dict[str, Any]) -> str:
    lines: list[str] = []

    lines.append("# HELP pegasus_queue_depth Number of jobs currently in each queue status.")
    lines.append("# TYPE pegasus_queue_depth gauge")
    for status, count in sorted((snapshot.get("queueDepth") or {}).items()):
        lines.append(f'pegasus_queue_depth{{status="{_escape_label(str(status))}"}} {int(count)}')

    lines.append("# HELP pegasus_job_status_events_total Total observed job status events.")
    lines.append("# TYPE pegasus_job_status_events_total counter")
    for job_type, statuses in sorted((snapshot.get("jobStatusEvents") or {}).items()):
        for status, count in sorted((statuses or {}).items()):
            lines.append(
                "pegasus_job_status_events_total"
                f'{{job_type="{_escape_label(str(job_type))}",status="{_escape_label(str(status))}"}} {int(count)}'
            )

    lines.append("# HELP pegasus_job_failures_total Total observed failed jobs by type.")
    lines.append("# TYPE pegasus_job_failures_total counter")
    for job_type, count in sorted((snapshot.get("jobFailures") or {}).items()):
        lines.append(f'pegasus_job_failures_total{{job_type="{_escape_label(str(job_type))}"}} {int(count)}')

    lines.append("# HELP pegasus_job_retries_total Total replay retry requests by job type.")
    lines.append("# TYPE pegasus_job_retries_total counter")
    for job_type, count in sorted((snapshot.get("jobRetries") or {}).items()):
        lines.append(f'pegasus_job_retries_total{{job_type="{_escape_label(str(job_type))}"}} {int(count)}')

    lines.append("# HELP pegasus_job_latency_ms_avg Average observed job latency in milliseconds.")
    lines.append("# TYPE pegasus_job_latency_ms_avg gauge")
    lines.append("# HELP pegasus_job_latency_ms_max Maximum observed job latency in milliseconds.")
    lines.append("# TYPE pegasus_job_latency_ms_max gauge")
    for job_type, values in sorted((snapshot.get("jobLatencyMs") or {}).items()):
        avg_ms = float((values or {}).get("avgMs") or 0.0)
        max_ms = float((values or {}).get("maxMs") or 0.0)
        lines.append(f'pegasus_job_latency_ms_avg{{job_type="{_escape_label(str(job_type))}"}} {avg_ms}')
        lines.append(f'pegasus_job_latency_ms_max{{job_type="{_escape_label(str(job_type))}"}} {max_ms}')

    # Thinking model metrics (Gemini 3 Pro reasoning tracking)
    lines.append("# HELP pegasus_thinking_duration_seconds_avg Average reasoning model latency in seconds.")
    lines.append("# TYPE pegasus_thinking_duration_seconds_avg gauge")
    lines.append("# HELP pegasus_thinking_duration_seconds_max Maximum reasoning model latency in seconds.")
    lines.append("# TYPE pegasus_thinking_duration_seconds_max gauge")
    lines.append("# HELP pegasus_thinking_requests_total Total reasoning model requests by status.")
    lines.append("# TYPE pegasus_thinking_requests_total counter")
    for key, values in sorted((snapshot.get("thinkingLatency") or {}).items()):
        # key format: "model:status" (e.g., "gemini-3-pro-preview:success")
        avg_seconds = float((values or {}).get("avgSeconds") or 0.0)
        max_seconds = float((values or {}).get("maxSeconds") or 0.0)
        count = int((values or {}).get("count") or 0)

        # Parse model and status from key
        parts = key.split(":", 1)
        model_label = _escape_label(parts[0]) if parts else "unknown"
        status_label = _escape_label(parts[1]) if len(parts) > 1 else "unknown"

        labels = f'model="{model_label}",status="{status_label}"'
        lines.append(f'pegasus_thinking_duration_seconds_avg{{{labels}}} {avg_seconds}')
        lines.append(f'pegasus_thinking_duration_seconds_max{{{labels}}} {max_seconds}')
        lines.append(f'pegasus_thinking_requests_total{{{labels}}} {count}')

    lines.append("# HELP pegasus_thinking_errors_total Total reasoning model errors by type.")
    lines.append("# TYPE pegasus_thinking_errors_total counter")
    for model, error_codes in sorted((snapshot.get("thinkingErrors") or {}).items()):
        for error_code, count in sorted((error_codes or {}).items()):
            lines.append(
                f'pegasus_thinking_errors_total{{model="{_escape_label(str(model))}",'
                f'error_code="{_escape_label(str(error_code))}"}} {int(count)}'
            )

    return "\n".join(lines) + "\n"


METRICS = InMemoryMetricsStore()
