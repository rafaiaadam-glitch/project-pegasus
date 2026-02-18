"""Tests for schema_validator.py"""

import json
import pytest
from pathlib import Path

from pipeline.schema_validator import SchemaValidator


def test_schema_validator_init(schema_dir):
    """Test SchemaValidator initialization."""
    validator = SchemaValidator(schema_dir)
    assert validator.base_dir == schema_dir
    assert validator._schema_cache == {}


def test_schema_validator_loads_schema(schema_dir):
    """Test that schemas are loaded correctly."""
    validator = SchemaValidator(schema_dir)
    schema = validator._load_schema("test.schema.json")

    assert schema["type"] == "object"
    assert "id" in schema["properties"]
    assert "name" in schema["properties"]


def test_schema_validator_caches_schemas(schema_dir):
    """Test that schemas are cached after first load."""
    validator = SchemaValidator(schema_dir)

    # Load schema twice
    schema1 = validator._load_schema("test.schema.json")
    schema2 = validator._load_schema("test.schema.json")

    # Should be the same object (cached)
    assert schema1 is schema2
    assert "test.schema.json" in validator._schema_cache


def test_validate_valid_data(schema_dir):
    """Test validation with valid data."""
    validator = SchemaValidator(schema_dir)
    valid_data = {"id": "test-001", "name": "Test Item"}

    # Should not raise
    validator.validate(valid_data, "test.schema.json")


def test_validate_missing_required_field(schema_dir):
    """Test validation fails with missing required field."""
    validator = SchemaValidator(schema_dir)
    invalid_data = {"id": "test-001"}  # Missing 'name'

    with pytest.raises(ValueError) as exc_info:
        validator.validate(invalid_data, "test.schema.json")

    assert "Schema validation failed" in str(exc_info.value)
    assert "name" in str(exc_info.value).lower()


def test_validate_wrong_type(schema_dir):
    """Test validation fails with wrong data type."""
    validator = SchemaValidator(schema_dir)
    invalid_data = {"id": "test-001", "name": 123}  # name should be string

    with pytest.raises(ValueError) as exc_info:
        validator.validate(invalid_data, "test.schema.json")

    assert "Schema validation failed" in str(exc_info.value)


def test_validate_nonexistent_schema(schema_dir):
    """Test validation with nonexistent schema file."""
    validator = SchemaValidator(schema_dir)
    data = {"id": "test-001", "name": "Test"}

    with pytest.raises(ValueError) as exc_info:
        validator.validate(data, "nonexistent.schema.json")

    assert "Schema file not found" in str(exc_info.value)


def test_validate_invalid_json_schema(schema_dir, temp_dir):
    """Test handling of invalid JSON in schema file."""
    # Create invalid JSON file
    invalid_schema_path = schema_dir / "invalid.schema.json"
    with open(invalid_schema_path, "w") as f:
        f.write("{invalid json}")

    validator = SchemaValidator(schema_dir)
    data = {"id": "test", "name": "Test"}

    with pytest.raises(ValueError) as exc_info:
        validator.validate(data, "invalid.schema.json")

    assert "Invalid JSON in schema" in str(exc_info.value)
