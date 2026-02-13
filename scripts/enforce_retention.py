#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.retention import enforce_local_retention, load_retention_policy, RetentionPolicy


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Enforce Pegasus local storage retention policy.")
    parser.add_argument("--storage-dir", default=os.getenv("PLC_STORAGE_DIR", "storage"))
    parser.add_argument("--audio-days", type=int, default=None)
    parser.add_argument("--transcript-days", type=int, default=None)
    parser.add_argument("--artifact-days", type=int, default=None)
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    policy = load_retention_policy()
    if args.audio_days is not None or args.transcript_days is not None or args.artifact_days is not None:
        policy = RetentionPolicy(
            audio_days=policy.audio_days if args.audio_days is None else args.audio_days,
            transcript_days=policy.transcript_days if args.transcript_days is None else args.transcript_days,
            artifact_days=policy.artifact_days if args.artifact_days is None else args.artifact_days,
        )

    result = enforce_local_retention(Path(args.storage_dir).resolve(), policy=policy)
    print(
        "Retention cleanup complete: "
        f"deleted_files={result.deleted_files} "
        f"deleted_dirs={result.deleted_dirs} "
        f"reclaimed_bytes={result.reclaimed_bytes}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
