"""Complete validation of portable ``.aether/project.toml`` markers.

The project's canonical JSON Schema is the policy authority.  This module is kept
independent of Hermes so manager, observation, and source-launcher code can share
one complete validator rather than maintaining partial field checks.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

__all__ = ["ProjectMarkerValidationError", "validate_project_marker"]

_PACKAGED_SCHEMA = Path(__file__).resolve().parent / "resources" / "schemas" / "project.schema.json"
_SOURCE_SCHEMA = (
    Path(__file__).resolve().parents[2]
    / "specs"
    / "001-aether-v1-productization"
    / "contracts"
    / "project.schema.json"
)


class ProjectMarkerValidationError(ValueError):
    """The marker is not a complete instance of the canonical project schema."""


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    path = _PACKAGED_SCHEMA if _PACKAGED_SCHEMA.is_file() else _SOURCE_SCHEMA
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProjectMarkerValidationError("project marker schema is unavailable") from exc
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as exc:
        raise ProjectMarkerValidationError("project marker schema is invalid") from exc
    return Draft202012Validator(schema, format_checker=FormatChecker())


def validate_project_marker(marker: object) -> dict[str, Any]:
    """Return ``marker`` when it exactly conforms to the canonical schema.

    The error deliberately stays content-free: marker data may be read from an
    untrusted working tree and callers only need the validity decision.
    """
    if not isinstance(marker, dict):
        raise ProjectMarkerValidationError("project marker must be an object")
    errors = sorted(
        _validator().iter_errors(marker),
        key=lambda error: (tuple(str(part) for part in error.absolute_path), error.validator or ""),
    )
    if errors:
        raise ProjectMarkerValidationError(
            "project marker does not conform to the canonical schema"
        )
    return marker
