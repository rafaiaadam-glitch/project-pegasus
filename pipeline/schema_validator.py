#!/usr/bin/env python3
"""JSON Schema validation wrapper using jsonschema library."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import jsonschema
from jsonschema import Draft202012Validator, ValidationError


class SchemaValidator:
    """Validates payloads against JSON schemas with caching for performance."""

    def __init__(self, base_dir: Path):
        """
        Initialize validator with schema directory.

        Args:
            base_dir: Directory containing JSON schema files
        """
        self.base_dir = base_dir
        self._schema_cache: Dict[str, Dict[str, Any]] = {}

    def _load_schema(self, schema_name: str) -> Dict[str, Any]:
        """Load and cache a JSON schema."""
        if schema_name not in self._schema_cache:
            schema_path = self.base_dir / schema_name
            with schema_path.open("r", encoding="utf-8") as handle:
                self._schema_cache[schema_name] = json.load(handle)
        return self._schema_cache[schema_name]

    def validate(self, payload: Dict[str, Any], schema_name: str) -> None:
        """
        Validate a payload against a named schema.

        Args:
            payload: Data to validate
            schema_name: Name of schema file (e.g., "summary.schema.json")

        Raises:
            ValueError: If validation fails, with detailed error messages
        """
        try:
            schema = self._load_schema(schema_name)
            validator = Draft202012Validator(schema)
            validator.validate(payload)
        except ValidationError as e:
            # Format error message to match existing validation output
            error_path = ".".join(str(p) for p in e.path) if e.path else "root"
            message_lines = [f"Schema validation failed ({schema_name}):"]
            message_lines.append(f"- At '{error_path}': {e.message}")
            raise ValueError("\n".join(message_lines)) from e
        except FileNotFoundError as e:
            raise ValueError(f"Schema file not found: {schema_name}") from e
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in schema {schema_name}: {e}") from e
