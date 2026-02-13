"""Thread continuity quality checks for cross-lecture consistency.

Usage:
    python -m pipeline.thread_continuity_check --threads-file path/to/threads.json
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ContinuityReport:
    total_threads: int
    multi_lecture_threads: int
    multi_lecture_ratio: float
    min_required_ratio: float

    @property
    def passed(self) -> bool:
        if self.total_threads == 0:
            return False
        return self.multi_lecture_ratio >= self.min_required_ratio


def _to_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        threads = payload.get("threads")
        if isinstance(threads, list):
            return [item for item in threads if isinstance(item, dict)]
    return []


def _parse_min_ratio(raw: str) -> float:
    try:
        ratio = float(raw)
    except ValueError as exc:
        raise ValueError("Minimum continuity ratio must be a float.") from exc
    if ratio < 0 or ratio > 1:
        raise ValueError("Minimum continuity ratio must be between 0 and 1.")
    return ratio


def evaluate_thread_continuity(
    threads: list[dict[str, Any]],
    min_multi_lecture_ratio: float = 0.2,
) -> ContinuityReport:
    if min_multi_lecture_ratio < 0 or min_multi_lecture_ratio > 1:
        raise ValueError("min_multi_lecture_ratio must be between 0 and 1.")

    total_threads = len(threads)
    multi_lecture_threads = 0

    for thread in threads:
        lecture_refs = thread.get("lectureRefs")
        if lecture_refs is None:
            lecture_refs = thread.get("lecture_refs")
        if not isinstance(lecture_refs, list):
            continue
        unique_refs = {str(ref).strip() for ref in lecture_refs if str(ref).strip()}
        if len(unique_refs) >= 2:
            multi_lecture_threads += 1

    ratio = 0.0 if total_threads == 0 else multi_lecture_threads / total_threads
    return ContinuityReport(
        total_threads=total_threads,
        multi_lecture_threads=multi_lecture_threads,
        multi_lecture_ratio=ratio,
        min_required_ratio=min_multi_lecture_ratio,
    )


def load_threads_from_file(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return _to_list(payload)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check thread continuity quality.")
    parser.add_argument("--threads-file", required=True, type=Path, help="Path to threads JSON file")
    parser.add_argument(
        "--min-ratio",
        type=float,
        default=None,
        help="Minimum ratio of threads that must span >=2 lectures (0..1).",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    env_ratio = os.getenv("PLC_MIN_MULTI_LECTURE_THREAD_RATIO")
    if args.min_ratio is not None:
        min_ratio = args.min_ratio
    elif env_ratio:
        min_ratio = _parse_min_ratio(env_ratio)
    else:
        min_ratio = 0.2

    threads = load_threads_from_file(args.threads_file)
    report = evaluate_thread_continuity(threads, min_multi_lecture_ratio=min_ratio)

    print(
        "Thread continuity: "
        f"{report.multi_lecture_threads}/{report.total_threads} "
        f"({report.multi_lecture_ratio:.1%}) "
        f"multi-lecture threads; required >= {report.min_required_ratio:.1%}"
    )

    if report.passed:
        return 0

    print("FAIL: Thread continuity threshold not met.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
