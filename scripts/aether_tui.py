#!/usr/bin/env python3
"""Canonical, reproducible TUI launcher for Aether's Morfeo profile."""

from __future__ import annotations

import json
import os
import re
import sys
import tomllib
import uuid
from collections.abc import Sequence
from pathlib import Path
from typing import cast

REQUIRED_TOOLSETS = frozenset({"file", "kanban"})
_RESERVED_ARGS = frozenset(
    {
        "--cli",
        "--ignore-rules",
        "--ignore-user-config",
        "--in",
        "--profile",
        "--safe-mode",
        "--toolsets",
        "--tui",
        "-p",
        "-t",
    }
)


class ActivationError(RuntimeError):
    """The local Aether runtime cannot satisfy the launcher contract."""


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


class _UnsupportedProjectSchema(ValueError):
    """The direct-launch adapter cannot safely evaluate a changed canonical schema."""


_SCHEMA_KEYWORDS = frozenset(
    {
        "$id",
        "$schema",
        "additionalProperties",
        "allOf",
        "const",
        "else",
        "enum",
        "format",
        "if",
        "maxLength",
        "minLength",
        "not",
        "pattern",
        "properties",
        "required",
        "then",
        "title",
        "type",
    }
)


def _schema_matches(value: object, schema: object) -> bool:
    """Evaluate every JSON Schema keyword used by the canonical project marker schema.

    This intentionally small adapter keeps the direct source launcher stdlib-only. It
    loads the same canonical schema as the package validator and fails closed if the
    schema gains a keyword this adapter cannot evaluate.
    """
    if isinstance(schema, bool):
        return schema
    if not isinstance(schema, dict):
        raise _UnsupportedProjectSchema("schema node must be an object or boolean")
    unknown = set(schema) - _SCHEMA_KEYWORDS
    if unknown:
        raise _UnsupportedProjectSchema("schema contains unsupported validation keywords")

    expected_type = schema.get("type")
    if expected_type is not None:
        if expected_type == "object":
            if not isinstance(value, dict):
                return False
        elif expected_type == "string":
            if not isinstance(value, str):
                return False
        else:
            raise _UnsupportedProjectSchema("schema contains an unsupported type")

    if "const" in schema and value != schema["const"]:
        return False
    if "enum" in schema:
        allowed = schema["enum"]
        if not isinstance(allowed, list):
            raise _UnsupportedProjectSchema("schema enum must be an array")
        if value not in allowed:
            return False

    if isinstance(value, str):
        minimum = schema.get("minLength")
        maximum = schema.get("maxLength")
        if not isinstance(minimum, int) or isinstance(minimum, bool):
            if minimum is not None:
                raise _UnsupportedProjectSchema("schema minLength must be an integer")
        elif len(value) < minimum:
            return False
        if not isinstance(maximum, int) or isinstance(maximum, bool):
            if maximum is not None:
                raise _UnsupportedProjectSchema("schema maxLength must be an integer")
        elif len(value) > maximum:
            return False
        pattern = schema.get("pattern")
        if pattern is not None:
            if not isinstance(pattern, str):
                raise _UnsupportedProjectSchema("schema pattern must be a string")
            try:
                if re.search(pattern, value) is None:
                    return False
            except re.error as exc:
                raise _UnsupportedProjectSchema("schema pattern is invalid") from exc
        format_name = schema.get("format")
        if format_name is not None:
            if format_name != "uuid":
                raise _UnsupportedProjectSchema("schema contains an unsupported format")
            try:
                uuid.UUID(value)
            except ValueError:
                return False

    if isinstance(value, dict):
        if "required" in schema:
            required = schema["required"]
            if not isinstance(required, list) or not all(
                isinstance(name, str) for name in required
            ):
                raise _UnsupportedProjectSchema("schema required must be an array of strings")
            if any(name not in value for name in required):
                return False
        properties: dict[object, object] = {}
        if "properties" in schema:
            candidate_properties = schema["properties"]
            if not isinstance(candidate_properties, dict):
                raise _UnsupportedProjectSchema("schema properties must be an object")
            properties = candidate_properties
            for name, child_schema in properties.items():
                if not isinstance(name, str):
                    raise _UnsupportedProjectSchema("schema property name must be a string")
                if name in value and not _schema_matches(value[name], child_schema):
                    return False
        additional = schema.get("additionalProperties", True)
        if additional is not True and additional is not False:
            raise _UnsupportedProjectSchema("schema additionalProperties must be boolean")
        if additional is False and any(name not in properties for name in value):
            return False

    if "allOf" in schema:
        all_of = schema["allOf"]
        if not isinstance(all_of, list):
            raise _UnsupportedProjectSchema("schema allOf must be an array")
        if any(not _schema_matches(value, child_schema) for child_schema in all_of):
            return False
    if "if" in schema:
        condition = _schema_matches(value, schema["if"])
        branch = schema.get("then") if condition else schema.get("else")
        if branch is not None and not _schema_matches(value, branch):
            return False
    if "not" in schema and _schema_matches(value, schema["not"]):
        return False
    return True


def _validate_project_marker(payload: object) -> dict[str, object]:
    """Validate the marker directly against its canonical source schema.

    The launcher remains usable with only the standard library, unlike the packaged
    validator. Its adapter is schema-driven and fails closed if it cannot maintain
    complete parity with the canonical policy.
    """
    try:
        schema_path = (
            _repo_root()
            / "specs"
            / "001-aether-v1-productization"
            / "contracts"
            / "project.schema.json"
        )
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ActivationError("portable Aether project marker schema is unavailable") from exc
    try:
        valid = _schema_matches(payload, schema)
    except _UnsupportedProjectSchema as exc:
        raise ActivationError("portable Aether project marker schema is unsupported") from exc
    if not isinstance(payload, dict) or not valid:
        raise ActivationError(
            "portable Aether project marker does not conform to the canonical schema"
        )
    return payload


def _top_level_toolsets(config: Path) -> set[str]:
    """Read the simple top-level ``toolsets`` YAML list without PyYAML."""
    toolsets: set[str] = set()
    collecting = False
    for raw_line in config.read_text(encoding="utf-8").splitlines():
        if raw_line == "toolsets:":
            collecting = True
            continue
        if not collecting:
            continue
        if raw_line.startswith("  - "):
            value = raw_line[4:].strip()
            if value:
                toolsets.add(value)
            continue
        if raw_line and not raw_line[0].isspace():
            break
    return toolsets


def _portable_project_id(repo: Path) -> str:
    marker = repo / ".aether" / "project.toml"
    if not marker.is_file():
        raise ActivationError(f"portable Aether project marker does not exist: {marker}")
    try:
        payload = tomllib.loads(marker.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise ActivationError("portable Aether project marker is unreadable") from exc
    validated = _validate_project_marker(payload)
    project_id = validated["project_id"]
    if not isinstance(project_id, str):  # schema validation proves this; preserve a typed boundary.
        raise ActivationError("portable Aether project marker has no valid project_id")
    return project_id


def _validate_extra_args(args: Sequence[str]) -> None:
    for arg in args:
        option = arg.split("=", 1)[0]
        if option in _RESERVED_ARGS:
            raise ActivationError(f"{option} is controlled by the canonical Morfeo launcher")


def inspect_activation(extra_args: Sequence[str] = ()) -> dict[str, object]:
    """Validate local state and return the deterministic activation contract."""
    _validate_extra_args(extra_args)
    repo = _repo_root()
    profile = repo / "home" / "profiles" / "morfeo"
    config = profile / "config.yaml"
    soul = profile / "SOUL.md"
    hermes = repo / "home" / ".venv-hermes" / "bin" / "hermes"

    if not (repo / "AGENTS.md").is_file():
        raise ActivationError(f"Aether repository marker does not exist: {repo / 'AGENTS.md'}")
    if not profile.is_dir():
        raise ActivationError(f"Morfeo profile directory does not exist: {profile}")
    if not config.is_file():
        raise ActivationError(f"Morfeo config does not exist: {config}")
    if not soul.is_file():
        raise ActivationError(f"Morfeo SOUL does not exist: {soul}")
    if not hermes.is_file() or not os.access(hermes, os.X_OK):
        raise ActivationError(f"Hermes executable is not executable: {hermes}")

    configured = _top_level_toolsets(config)
    missing = sorted(REQUIRED_TOOLSETS - configured)
    if missing:
        raise ActivationError("missing required Morfeo toolsets: " + ", ".join(missing))

    repo = repo.resolve()
    project_id = _portable_project_id(repo)
    profile = profile.resolve()
    hermes = hermes.resolve()
    command = [str(hermes), "--tui", "--in", str(repo), *extra_args]
    return {
        "result": "ready",
        "repo_root": str(repo),
        "project_id": project_id,
        "hermes_home": str(profile),
        "cwd": str(repo),
        "hermes_executable": str(hermes),
        "required_toolsets": sorted(REQUIRED_TOOLSETS),
        "command": command,
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    check = False
    if "--check" in args:
        args.remove("--check")
        check = True

    try:
        report = inspect_activation(args)
    except (ActivationError, OSError, UnicodeError) as exc:
        print(f"aether: {exc}", file=sys.stderr)
        return 2

    if check:
        print(json.dumps(report, sort_keys=True))
        return 0

    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    environment.pop("HERMES_PROFILE", None)
    environment["HERMES_HOME"] = str(report["hermes_home"])
    environment["AETHER_PROJECT_ID"] = str(report["project_id"])
    environment["PWD"] = str(report["repo_root"])
    command = list(cast(list[str], report["command"]))
    executable = str(report["hermes_executable"])
    target = Path(str(report["repo_root"]))
    os.chdir(target)
    os.execve(executable, command, environment)
    raise AssertionError("os.execve returned unexpectedly")


if __name__ == "__main__":
    raise SystemExit(main())
