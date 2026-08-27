#!/usr/bin/env python3
"""Canonical, reproducible TUI launcher for Aether's Morfeo profile."""

from __future__ import annotations

import json
import os
import re
import sys
import tomllib
from collections.abc import Sequence
from pathlib import Path
from typing import cast

REQUIRED_TOOLSETS = frozenset({"file", "kanban"})
_PROJECT_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
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
    project_id = payload.get("project_id") if isinstance(payload, dict) else None
    if not isinstance(project_id, str) or _PROJECT_UUID_RE.fullmatch(project_id) is None:
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
