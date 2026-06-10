"""Artifact validation against bundled JSON schemas.

Provides ``validate_artifact`` for validating artifact dicts against their
JSON schemas, and ``ValidationError`` for reporting schema violations.

Requirements: 08-REQ-1.*, 08-REQ-4.*
"""

from __future__ import annotations

import importlib.resources
import json
from typing import Any

import jsonschema

# Schema file mapping (08-REQ-1.4)
_SCHEMA_MAP: dict[str, str] = {
    "requirements": "requirements.v1.json",
    "test_spec": "test_spec.v1.json",
    "tasks": "tasks.v1.json",
}

# Cache for loaded schemas to avoid repeated file I/O
_schema_cache: dict[str, dict[str, Any]] = {}


class ValidationError(Exception):
    """Raised when artifact content does not conform to its JSON schema.

    Attributes:
        artifact_name: The name of the artifact that failed validation.
        errors: A list of human-readable error description strings.

    Requirements: 08-REQ-4.1, 08-REQ-4.2
    """

    def __init__(self, artifact_name: str, errors: list[str]) -> None:
        self.artifact_name = artifact_name
        self.errors = errors
        super().__init__(
            f"Artifact '{artifact_name}' failed validation: "
            + "; ".join(errors)
        )


def _load_schema(schema_filename: str) -> dict[str, Any]:
    """Load and parse a JSON schema file from the bundled schemas directory.

    Uses ``importlib.resources`` for reliable package-relative file access.
    Caches loaded schemas to avoid repeated I/O.

    Args:
        schema_filename: The filename of the schema (e.g. ``"requirements.v1.json"``).

    Returns:
        The parsed JSON schema as a dict.

    Requirements: 08-REQ-2.2
    """
    if schema_filename in _schema_cache:
        return _schema_cache[schema_filename]

    schema_files = importlib.resources.files("afspec.schemas")
    data = schema_files.joinpath(schema_filename).read_text(encoding="utf-8")
    schema = json.loads(data)
    _schema_cache[schema_filename] = schema
    return schema


def validate_artifact(artifact_name: str, content: dict[str, Any]) -> None:
    """Validate a single artifact dict against its JSON schema.

    Args:
        artifact_name: One of ``"requirements"``, ``"test_spec"``, ``"tasks"``.
        content: The artifact content dict to validate.

    Returns:
        None if validation passes.

    Raises:
        ValueError: If *artifact_name* is not one of the recognized names.
        ValidationError: If *content* does not conform to the schema.

    Requirements: 08-REQ-1.1 through 08-REQ-1.4, 08-REQ-1.E1, 08-REQ-1.E2
    """
    if artifact_name not in _SCHEMA_MAP:
        valid_names = sorted(_SCHEMA_MAP.keys())
        raise ValueError(
            f"Unknown artifact name {artifact_name!r}; "
            f"valid names are: {', '.join(valid_names)}"
        )

    schema_filename = _SCHEMA_MAP[artifact_name]
    schema = _load_schema(schema_filename)

    validator = jsonschema.Draft202012Validator(schema)
    errors = list(validator.iter_errors(content))

    if errors:
        error_messages = [e.message for e in errors]
        raise ValidationError(artifact_name, error_messages)
