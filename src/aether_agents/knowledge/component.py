"""Explicit optional-component installation; never called from tool registration."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from aether_agents.paths import data_root, ensure_private_dir

from .common import GRAPHIFY_VERSION, KnowledgeError, atomic_json, clean_environment, stable_lock
from .graphify import GraphifyBackend
from .service import KnowledgeService


def configure(
    service: KnowledgeService,
    python: Path,
    *,
    ownership: str = "external",
    lock_id: str | None = None,
) -> dict[str, Any]:
    python = python.expanduser().absolute()
    probe = GraphifyBackend(python).probe()
    if probe.get("version") != GRAPHIFY_VERSION:
        raise KnowledgeError(
            "COMPONENT_UNAVAILABLE", "The Graphify version differs from the qualified adapter."
        )
    config = {
        "schema_version": 1,
        "enabled": True,
        "python": str(python),
        "graphify_version": GRAPHIFY_VERSION,
        "timeout_seconds": 60,
        "ownership": ownership,
        "lock_id": lock_id,
        "python_version": probe["python"],
        "semantic_enabled": False,
    }
    atomic_json(service.config_path, config)
    return {
        "ok": True,
        "component": config,
        "warning": "This configures the component only; enable the packaged plugin in each intended profile separately.",
    }


def disable(service: KnowledgeService) -> dict[str, Any]:
    config = service.configuration()
    config.update(schema_version=1, enabled=False)
    atomic_json(service.config_path, config)
    return {"ok": True, "enabled": False, "notes_preserved": True}


def install(service: KnowledgeService, *, destination_root: Path | None = None) -> dict[str, Any]:
    """Install original upstream packages into a locked, versioned Python 3.11 env."""
    if os.name != "posix":
        raise KnowledgeError(
            "PLATFORM_UNSUPPORTED", "The managed component currently supports POSIX installations."
        )
    requirements = Path(__file__).parents[1] / "resources" / "graphify" / "requirements.txt"
    if not requirements.is_file():
        raise KnowledgeError(
            "COMPONENT_UNAVAILABLE", "The wheel does not contain its component lock."
        )
    digest = hashlib.sha256(requirements.read_bytes()).hexdigest()
    component_root = (destination_root or data_root()) / "components" / "graphify" / digest[:24]
    ensure_private_dir(component_root)
    interpreter = component_root / "venv" / "bin" / "python"
    with stable_lock(component_root / "install.lock", timeout=10):
        receipt = component_root / "installed.json"
        if receipt.is_file() and interpreter.is_file():
            installed = json.loads(receipt.read_text())
            if installed.get("requirements_sha256") == digest:
                return configure(service, interpreter, ownership="managed", lock_id=digest)
        try:
            located = subprocess.run(
                ["uv", "python", "find", "--no-python-downloads", "3.11"],
                capture_output=True,
                timeout=15,
                env=clean_environment(Path.home()),
                check=False,
            )
            base_python = located.stdout.decode().strip()
            if (
                located.returncode
                or not Path(base_python).is_absolute()
                or not Path(base_python).is_file()
            ):
                raise KnowledgeError(
                    "COMPONENT_UNAVAILABLE", "Install a local Python 3.11 interpreter first."
                )
        except (OSError, UnicodeError, subprocess.TimeoutExpired) as exc:
            raise KnowledgeError(
                "COMPONENT_UNAVAILABLE", "Cannot locate uv and a local Python 3.11 interpreter."
            ) from exc
        with tempfile.TemporaryDirectory(prefix="aether-component-install-") as scratch:
            environment = clean_environment(Path(scratch))
            commands = (
                [
                    "uv",
                    "venv",
                    "--python",
                    base_python,
                    "--no-python-downloads",
                    str(component_root / "venv"),
                ],
                [
                    "uv",
                    "pip",
                    "install",
                    "--python",
                    str(interpreter),
                    "--require-hashes",
                    "--index-url",
                    "https://pypi.org/simple",
                    "--no-config",
                    "-r",
                    str(requirements),
                ],
            )
            for command in commands:
                try:
                    completed = subprocess.run(
                        command,
                        capture_output=True,
                        timeout=240,
                        env=environment,
                        cwd=scratch,
                        check=False,
                    )
                except (OSError, subprocess.TimeoutExpired) as exc:
                    raise KnowledgeError(
                        "COMPONENT_UNAVAILABLE",
                        "The isolated component installation could not finish.",
                    ) from exc
                if completed.returncode:
                    # Do not publish arbitrary installer output containing local paths or secrets.
                    raise KnowledgeError(
                        "COMPONENT_UNAVAILABLE",
                        "Component installation failed; uv and local Python 3.11 are required.",
                    )
        GraphifyBackend(interpreter).probe()
        atomic_json(
            receipt,
            {
                "graphify_version": GRAPHIFY_VERSION,
                "requirements_sha256": digest,
                "source": "PyPI distributions verified by the packaged hash lock",
            },
        )
        return configure(service, interpreter, ownership="managed", lock_id=digest)
