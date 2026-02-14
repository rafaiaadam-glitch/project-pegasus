"""CLI-focused tests for run_pipeline argument parsing and progress logging."""

from pathlib import Path

from pipeline.run_pipeline import _parse_args


def test_parse_args_progress_log_and_quiet(monkeypatch):
    """CLI should parse progress logging and quiet mode flags."""
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_pipeline.py",
            "--input",
            "pipeline/inputs/sample-transcript.txt",
            "--progress-log-file",
            "pipeline/output/test.log",
            "--quiet",
        ],
    )

    args = _parse_args()

    assert args.quiet is True
    assert args.progress_log_file == Path("pipeline/output/test.log")


def test_parse_args_progress_log_defaults(monkeypatch):
    """CLI should keep progress logging disabled by default."""
    monkeypatch.setattr("sys.argv", ["run_pipeline.py"])

    args = _parse_args()

    assert args.quiet is False
    assert args.progress_log_file is None
    assert args.continuity_threshold is None


def test_parse_args_continuity_threshold(monkeypatch):
    """CLI should parse an optional continuity threshold."""
    monkeypatch.setattr(
        "sys.argv",
        ["run_pipeline.py", "--continuity-threshold", "0.72"],
    )

    args = _parse_args()

    assert args.continuity_threshold == 0.72
