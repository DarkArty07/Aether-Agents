"""Schema and privacy validation for laboratory inputs and evidence."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from jsonschema import Draft202012Validator

from .resources import fixture_manifest_resource, resource_bytes, resource_json, scenario_resource

_FORBIDDEN_KEYS = {
    "environment", "credentials", "prompt", "response", "command", "stdout", "stderr",
    "files", "diff", "logs", "events", "raw", "transcript", "terminal_output",
}
_FORBIDDEN_KEY_PARTS = (
    "credential", "secret", "prompt", "response", "stdout", "stderr", "command",
    "event", "file", "diff", "log", "transcript", "token",
)


@lru_cache(maxsize=None)
def _validator(name: str) -> Draft202012Validator:
    return Draft202012Validator(resource_json(f"schemas/{name}.schema.json"))


def _assert_no_forbidden_keys(value: Any) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized = str(key).casefold()
            if normalized in _FORBIDDEN_KEYS or any(part in normalized for part in _FORBIDDEN_KEY_PARTS):
                raise ValueError("evidence contains a forbidden content field")
            _assert_no_forbidden_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            _assert_no_forbidden_keys(nested)


def _validate(value: Any, schema: str, label: str) -> None:
    errors = sorted(_validator(schema).iter_errors(value), key=lambda error: tuple(error.path))
    if errors:
        raise ValueError(f"{label} failed schema validation")


def validate_scenario(value: Any) -> None:
    _validate(value, "scenario", "scenario")


def validate_fixture_manifest(value: Any) -> None:
    _validate(value, "fixture-manifest", "fixture manifest")


def validate_evidence(value: Any) -> None:
    _assert_no_forbidden_keys(value)
    _validate(value, "evidence", "evidence")
    if isinstance(value, dict) and value.get("kind") == "observation":
        calls = value.get("calls", [])
        expected = {"status": 2048, "changes": 2048, "diagnose": 4096}
        for call in calls:
            action = call.get("action")
            if call.get("limit") != expected.get(action) or call.get("bytes", 0) > expected[action]:
                raise ValueError("observation output exceeded its action limit")


def schema_bytes(name: str) -> bytes:
    filename = name if name.endswith(".schema.json") else f"{name}.schema.json"
    if filename not in {"scenario.schema.json", "fixture-manifest.schema.json", "evidence.schema.json"}:
        raise ValueError("unknown laboratory schema")
    return resource_bytes(f"schemas/{filename}")


def scenario_bytes(identifier: str) -> bytes:
    filename = identifier if identifier.endswith(".json") else f"{identifier}.json"
    if not re.fullmatch(r"e2e-[0-9]{2}\.json", filename):
        raise ValueError("unknown laboratory scenario")
    return scenario_resource(filename)


def fixture_manifest() -> dict[str, Any]:
    value = fixture_manifest_resource()
    import json

    payload = json.loads(value)
    validate_fixture_manifest(payload)
    return payload
