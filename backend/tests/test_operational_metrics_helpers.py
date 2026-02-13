from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

import backend.app as app_module


def test_to_datetime_supports_z_suffix():
    value = app_module._to_datetime("2026-02-13T12:00:00Z")
    assert isinstance(value, datetime)
    assert value.tzinfo is not None
    assert value.utcoffset() == timezone.utc.utcoffset(value)


def test_percentile_returns_zero_for_empty_input():
    assert app_module._percentile([], 0.95) == 0.0


def test_job_latency_ms_handles_reversed_timestamps():
    job = {
        "created_at": "2026-02-13T12:00:01+00:00",
        "updated_at": "2026-02-13T12:00:00+00:00",
    }
    assert app_module._job_latency_ms(job) == 0.0
