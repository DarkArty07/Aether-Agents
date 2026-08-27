"""Resource resolution for the formal laboratory.

The package resources are the installed copy of the canonical bytes in the top-level
``lab/`` area.  This module is stdlib-only so importing :mod:`aether_agents.lab` never
requires Hermes or any runtime profile.
"""

from __future__ import annotations

import importlib.resources
import json
from pathlib import Path
from typing import Any

_PACKAGE_ROOT = importlib.resources.files("aether_agents").joinpath("resources", "lab")


def resource_bytes(relative: str) -> bytes:
    candidate = _PACKAGE_ROOT.joinpath(*relative.split("/"))
    try:
        return candidate.read_bytes()
    except FileNotFoundError:
        # Source checkouts keep one canonical top-level lab tree; the build
        # backend copies it into package resources for installed wheels.
        return source_root().joinpath("lab", *relative.split("/")).read_bytes()


def resource_text(relative: str) -> str:
    return resource_bytes(relative).decode("utf-8")


def resource_json(relative: str) -> Any:
    return json.loads(resource_text(relative))


def source_root() -> Path:
    """Return the checkout root when running from source, otherwise the package root."""
    candidate = Path(__file__).resolve().parents[3]
    return candidate if (candidate / "pyproject.toml").is_file() else Path.cwd()


def scenario_resource(identifier: str) -> bytes:
    filename = identifier if identifier.endswith(".json") else f"{identifier}.json"
    return resource_bytes(f"scenarios/{filename}")


def schema_resource(name: str) -> bytes:
    filename = name if name.endswith(".schema.json") else f"{name}.schema.json"
    return resource_bytes(f"schemas/{filename}")


def fixture_manifest_resource() -> bytes:
    return resource_bytes("fixtures/manifest.json")
