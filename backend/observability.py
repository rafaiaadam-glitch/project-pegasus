from __future__ import annotations

import math
import threading
from collections import defaultdict, deque
from typing import Any


class InMemoryMetricsStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._job_status_events: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._job_failures: dict[str, int] = defaultdict(int)
        self._job_latency: dict[str, dict[str, float | deque[float]]] = defaultdict(
            lambda: {
                "count": 0.0,
                "sum_ms": 0.0,
                "max_ms": 0.0,
                "samples_ms": deque(maxlen=500),
            }
        )
        self._retry_events: dict[str, int] = defaultdict(int)

    def reset(self) -> None:
        with self._lock:
            self._job_status_events.clear()
            self._job_failures.clear()
            self._job_latency.clear()
            self._retry_events.clear()

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
        duration = max(0.0, duration_ms)
        with self._lock:
            metric = self._job_latency[normalized_type]
            metric["count"] += 1
            metric["sum_ms"] += duration
            metric["max_ms"] = max(float(metric["max_ms"]), duration)
            samples = metric["samples_ms"]
            if isinstance(samples, deque):
                samples.append(duration)

    def increment_retry(self, job_type: str) -> None:
        normalized_type = (job_type or "unknown").strip() or "unknown"
        with self._lock:
            self._retry_events[normalized_type] += 1

    def snapshot(self, queue_depth: dict[str, int] | None = None) -> dict[str, Any]:
        with self._lock:
            latency: dict[str, dict[str, float]] = {}
            for job_type, metric in self._job_latency.items():
                count = float(metric["count"])
                avg_ms = (float(metric["sum_ms"]) / count) if count > 0 else 0.0
                samples = metric.get("samples_ms")
                p95_ms = 0.0
                if isinstance(samples, deque) and samples:
                    sorted_samples = sorted(samples)
                    percentile_index = max(0, math.ceil(0.95 * len(sorted_samples)) - 1)
                    p95_ms = float(sorted_samples[percentile_index])
                latency[job_type] = {
                    "count": int(count),
                    "avgMs": round(avg_ms, 2),
                    "maxMs": round(float(metric["max_ms"]), 2),
                    "p95Ms": round(p95_ms, 2),
                }

            return {
                "queueDepth": queue_depth or {},
                "jobStatusEvents": {
                    key: dict(value) for key, value in self._job_status_events.items()
                },
                "jobFailures": dict(self._job_failures),
                "jobLatencyMs": latency,
                "jobRetries": dict(self._retry_events),
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
    lines.append("# HELP pegasus_job_latency_ms_p95 p95 observed job latency in milliseconds.")
    lines.append("# TYPE pegasus_job_latency_ms_p95 gauge")
    lines.append("# HELP pegasus_job_latency_ms_max Maximum observed job latency in milliseconds.")
    lines.append("# TYPE pegasus_job_latency_ms_max gauge")
    for job_type, values in sorted((snapshot.get("jobLatencyMs") or {}).items()):
        avg_ms = float((values or {}).get("avgMs") or 0.0)
        p95_ms = float((values or {}).get("p95Ms") or 0.0)
        max_ms = float((values or {}).get("maxMs") or 0.0)
        lines.append(f'pegasus_job_latency_ms_avg{{job_type="{_escape_label(str(job_type))}"}} {avg_ms}')
        lines.append(f'pegasus_job_latency_ms_p95{{job_type="{_escape_label(str(job_type))}"}} {p95_ms}')
        lines.append(f'pegasus_job_latency_ms_max{{job_type="{_escape_label(str(job_type))}"}} {max_ms}')

    return "\n".join(lines) + "\n"


METRICS = InMemoryMetricsStore()
