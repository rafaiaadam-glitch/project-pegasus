from pathlib import Path

from pipeline.schema_drift_check import available_schema_files, extract_schema_references


def test_extract_schema_references_parses_validate_calls():
    sample = ' _validate(payload, "summary.schema.json", ARTIFACT_SCHEMA_DIR)\n_validate(t, "thread.schema.json", THREAD_SCHEMA_DIR) '
    assert extract_schema_references(sample) == {"summary.schema.json", "thread.schema.json"}


def test_available_schema_files_lists_schema_dir(tmp_path: Path):
    (tmp_path / "summary.schema.json").write_text("{}", encoding="utf-8")
    (tmp_path / "thread.schema.json").write_text("{}", encoding="utf-8")
    (tmp_path / "note.txt").write_text("x", encoding="utf-8")

    assert available_schema_files(tmp_path) == {"summary.schema.json", "thread.schema.json"}
