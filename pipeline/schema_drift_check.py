"""Schema drift checks between pipeline validation calls and available schema files."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN_PIPELINE_PATH = ROOT / "pipeline" / "run_pipeline.py"
SCHEMA_DIR = ROOT / "schemas"

_SCHEMA_REF_RE = re.compile(r'"([a-z0-9\-]+\.schema\.json)"')


def extract_schema_references(run_pipeline_text: str) -> set[str]:
    """Return schema filenames referenced in run_pipeline.py."""
    return set(_SCHEMA_REF_RE.findall(run_pipeline_text))


def available_schema_files(schema_dir: Path) -> set[str]:
    """Return schema filenames currently present in /schemas."""
    return {path.name for path in schema_dir.glob("*.schema.json")}


def check_schema_drift() -> tuple[set[str], set[str]]:
    """Return (missing, unreferenced) schema sets."""
    referenced = extract_schema_references(RUN_PIPELINE_PATH.read_text(encoding="utf-8"))
    available = available_schema_files(SCHEMA_DIR)
    missing = referenced - available
    unreferenced = available - referenced
    return missing, unreferenced


def main() -> int:
    missing, unreferenced = check_schema_drift()

    if missing:
        print("Schema drift detected: missing schema files referenced by pipeline:")
        for name in sorted(missing):
            print(f"  - {name}")

    if unreferenced:
        print("Schema drift warning: schema files present but not referenced in pipeline:")
        for name in sorted(unreferenced):
            print(f"  - {name}")

    if missing:
        return 1

    if unreferenced:
        print("Schema drift check passed with warnings (unreferenced schemas are allowed).")
    else:
        print("Schema drift check passed: referenced schemas match /schemas contents.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
