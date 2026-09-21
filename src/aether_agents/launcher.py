"""Packaged launcher and exact project binding for Aether's Morfeo profile.

Normative source: ``specs/001-aether-v1-productization/tasks-rc4.md`` (LG-CLI).
Validates local state, resolves exact project identity, scrubs conflicting environment
residue, and executes or reports the Morfeo TUI launch plan.
"""

from __future__ import annotations

import json
import os
import sys
import tomllib
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

from aether_agents.observation.context import ProjectRegistry, canonical_project_id
from aether_agents.paths import data_root, state_root
from aether_agents.project_marker import ProjectMarkerValidationError, validate_project_marker

__all__ = [
    "REQUIRED_TOOLSETS",
    "ActivationError",
    "inspect_activation",
    "main",
]

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


def _is_empty_path(val: str | Path | None) -> bool:
    if val is None:
        return False
    if isinstance(val, str):
        return not val.strip()
    raw_paths = getattr(val, "_raw_paths", None)
    if raw_paths is not None:
        return any(p == "" or (isinstance(p, str) and not p.strip()) for p in raw_paths)
    return not str(val).strip()


def _absolute_env_path(name: str) -> Path | None:
    """Return one explicit deployment path without guessing relative locations."""
    if name not in os.environ:
        return None
    raw = os.environ.get(name, "").strip()
    if not raw:
        raise ActivationError(f"{name} must not be empty")
    path = Path(raw).expanduser()
    if not path.is_absolute():
        raise ActivationError(f"{name} must be an absolute path")
    return path


def _validate_project_marker(payload: object) -> dict[str, Any]:
    try:
        return validate_project_marker(payload)
    except ProjectMarkerValidationError as exc:
        raise ActivationError(
            "portable Aether project marker does not conform to the canonical schema"
        ) from exc


def _portable_project_id(repo: Path) -> str:
    marker = repo / ".aether" / "project.toml"
    if not marker.is_file():
        raise ActivationError(f"portable Aether project marker does not exist: {marker}")
    try:
        payload = tomllib.loads(marker.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise ActivationError("portable Aether project marker is unreadable") from exc
    validated = _validate_project_marker(payload)
    project_id = validated.get("project_id")
    if not isinstance(project_id, str):
        raise ActivationError("portable Aether project marker has no valid project_id")
    return project_id


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


def _validate_extra_args(args: Sequence[str]) -> None:
    for arg in args:
        option = arg.split("=", 1)[0]
        if option in _RESERVED_ARGS:
            raise ActivationError(f"{option} is controlled by the canonical Morfeo launcher")


def _registry(hermes_root: Path | None = None) -> ProjectRegistry:
    if hermes_root is not None:
        candidate = hermes_root.parent
        if (candidate / "projects" / "registry.json").is_file():
            return ProjectRegistry(root=candidate)
        if (candidate / "aether" / "projects" / "registry.json").is_file():
            return ProjectRegistry(root=candidate / "aether")
    return ProjectRegistry()


def _resolve_project(project_arg: str | Path | None = None) -> tuple[Path, str]:
    """Resolve exact project binding according to LG-CLI decision 6."""
    hermes_root = _absolute_env_path("AETHER_HERMES_ROOT")
    registry = _registry(hermes_root)

    # (1) Explicit --project PATH or AETHER_PROJECT_ROOT
    if project_arg is not None or "AETHER_PROJECT_ROOT" in os.environ:
        if project_arg is not None:
            if _is_empty_path(project_arg):
                raise ActivationError("project path must not be empty")
            repo = Path(project_arg).expanduser().resolve()
        else:
            raw_root = os.environ.get("AETHER_PROJECT_ROOT", "").strip()
            if not raw_root:
                raise ActivationError("AETHER_PROJECT_ROOT must not be empty")
            repo_env = _absolute_env_path("AETHER_PROJECT_ROOT")
            if repo_env is None:
                raise ActivationError("AETHER_PROJECT_ROOT must not be empty")
            repo = repo_env.resolve()

        if not (repo / "AGENTS.md").is_file():
            raise ActivationError(f"Aether repository marker does not exist: {repo / 'AGENTS.md'}")
        project_id = _portable_project_id(repo)

        if "AETHER_PROJECT_ID" in os.environ:
            env_pid_raw = os.environ.get("AETHER_PROJECT_ID", "").strip()
            if not env_pid_raw:
                raise ActivationError("AETHER_PROJECT_ID must not be empty")
            env_pid = canonical_project_id(env_pid_raw)
            if env_pid is None:
                raise ActivationError(
                    f"AETHER_PROJECT_ID {env_pid_raw} is not a valid canonical UUID"
                )
            if env_pid != project_id:
                raise ActivationError(
                    f"explicit AETHER_PROJECT_ID {env_pid_raw} conflicts with project marker {project_id}"
                )

        if registry.knows(project_id):
            registered = registry.project_path(project_id)
            if registered is not None and registered.resolve() != repo:
                raise ActivationError(
                    f"project ID {project_id} conflicts with registered path: {registered}"
                )

        return repo, project_id

    # (2) Explicit verified AETHER_PROJECT_ID when registry and portable marker agree
    if "AETHER_PROJECT_ID" in os.environ:
        raw_pid = os.environ.get("AETHER_PROJECT_ID", "").strip()
        if not raw_pid:
            raise ActivationError("AETHER_PROJECT_ID must not be empty")
        env_pid = canonical_project_id(raw_pid)
        if env_pid is None:
            raise ActivationError(f"AETHER_PROJECT_ID {raw_pid} is not a valid canonical UUID")
        if not registry.knows(env_pid):
            raise ActivationError(
                f"AETHER_PROJECT_ID {env_pid} is not registered in the project registry"
            )
        loc = registry.project_path(env_pid)
        if loc is None or not loc.is_dir():
            raise ActivationError(f"registered project path for {env_pid} does not exist: {loc}")
        if not registry.verify_with_marker(env_pid):
            raise ActivationError(
                f"project registry and portable marker do not agree for {env_pid}"
            )
        repo = loc.resolve()
        if not (repo / "AGENTS.md").is_file():
            raise ActivationError(f"Aether repository marker does not exist: {repo / 'AGENTS.md'}")
        return repo, env_pid

    # (3) Current repository marker or sole registered project only when registry and marker agree
    cursor = Path.cwd().resolve()
    repo_candidate: Path | None = None
    for candidate in (cursor, *cursor.parents):
        if (candidate / ".aether" / "project.toml").is_file():
            repo_candidate = candidate
            break

    if repo_candidate is not None:
        marker_pid = _portable_project_id(repo_candidate)
        reg_path = registry.project_path(marker_pid)
        if (
            registry.knows(marker_pid)
            and reg_path is not None
            and reg_path.resolve() == repo_candidate.resolve()
            and registry.verify_with_marker(marker_pid)
        ):
            if not (repo_candidate / "AGENTS.md").is_file():
                raise ActivationError(
                    f"Aether repository marker does not exist: {repo_candidate / 'AGENTS.md'}"
                )
            return repo_candidate, marker_pid
        raise ActivationError(
            f"project registry and repository marker do not agree for project {marker_pid}"
        )

    projects = registry._load()
    if len(projects) == 1:
        sole_pid = next(iter(projects.keys()))
        if not registry.verify_with_marker(sole_pid):
            raise ActivationError(
                f"project registry and marker do not agree for the sole registered project {sole_pid}"
            )
        loc = registry.project_path(sole_pid)
        assert loc is not None
        repo = loc.resolve()
        if not (repo / "AGENTS.md").is_file():
            raise ActivationError(f"Aether repository marker does not exist: {repo / 'AGENTS.md'}")
        return repo, sole_pid
    if len(projects) == 0:
        raise ActivationError("no Aether project found and project registry is empty")
    raise ActivationError(
        f"ambiguous project identity: multiple projects registered ({len(projects)}) and no project specified"
    )


def _resolve_component_paths(repo: Path) -> tuple[Path, Path, Path]:
    hermes_root = _absolute_env_path("AETHER_HERMES_ROOT")
    runtime_root = _absolute_env_path("AETHER_RUNTIME_ROOT")

    if hermes_root is not None:
        profile = hermes_root / "profiles" / "morfeo"
    elif (state_root() / "hermes" / "profiles" / "morfeo").is_dir():
        profile = state_root() / "hermes" / "profiles" / "morfeo"
    elif (repo / "home" / "profiles" / "morfeo").is_dir():
        profile = repo / "home" / "profiles" / "morfeo"
    else:
        profile = state_root() / "hermes" / "profiles" / "morfeo"

    if runtime_root is not None:
        hermes = runtime_root / "venv" / "bin" / "hermes"
        tui_dir = runtime_root / "tui"
    elif (data_root() / "runtime" / "current" / "venv" / "bin" / "hermes").is_file():
        hermes = data_root() / "runtime" / "current" / "venv" / "bin" / "hermes"
        tui_dir = data_root() / "runtime" / "current" / "tui"
    elif (repo / "home" / ".venv-hermes" / "bin" / "hermes").is_file():
        hermes = repo / "home" / ".venv-hermes" / "bin" / "hermes"
        tui_dir = (
            repo / "home" / "tui"
            if (repo / "home" / "tui").is_dir()
            else (
                repo / "home" / ".venv-hermes" / "tui"
                if (repo / "home" / ".venv-hermes" / "tui").is_dir()
                else repo / "home" / "tui"
            )
        )
    else:
        hermes = data_root() / "runtime" / "current" / "venv" / "bin" / "hermes"
        tui_dir = data_root() / "runtime" / "current" / "tui"

    return profile, hermes, tui_dir


def inspect_activation(
    extra_args: Sequence[str] = (),
    *,
    project: str | Path | None = None,
) -> dict[str, Any]:
    """Validate local state and return the deterministic activation contract."""
    args = list(extra_args)
    if project is None:
        cleaned_extra: list[str] = []
        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "--project":
                if i + 1 < len(args):
                    project = args[i + 1]
                    i += 2
                    continue
            elif arg.startswith("--project="):
                project = arg.split("=", 1)[1]
                i += 1
                continue
            cleaned_extra.append(arg)
            i += 1
        args = cleaned_extra

    if project is not None and _is_empty_path(project):
        raise ActivationError("project path must not be empty")

    args = [a for a in args if a not in ("--json", "--check")]
    expanded_args: list[str] = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--resume":
            expanded_args.append(arg)
            if i + 1 >= len(args) or args[i + 1].startswith("-"):
                expanded_args.append("latest")
            else:
                expanded_args.append(args[i + 1])
                i += 1
            i += 1
            continue
        expanded_args.append(arg)
        i += 1
    args = expanded_args
    _validate_extra_args(args)
    repo, project_id = _resolve_project(project)
    profile, hermes, tui_dir = _resolve_component_paths(repo)

    config = profile / "config.yaml"
    soul = profile / "SOUL.md"

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
    if not tui_dir.is_dir():
        raise ActivationError(f"Morfeo TUI directory does not exist: {tui_dir}")

    configured = _top_level_toolsets(config)
    missing = sorted(REQUIRED_TOOLSETS - configured)
    if missing:
        raise ActivationError("missing required Morfeo toolsets: " + ", ".join(missing))

    repo = repo.resolve()
    profile = profile.resolve()
    hermes = hermes.resolve()
    tui_dir = tui_dir.resolve()

    command = [str(hermes), "--tui", "--in", str(repo), *args]
    return {
        "result": "ready",
        "project_id": project_id,
        "repo_root": str(repo),
        "hermes_home": str(profile),
        "cwd": str(repo),
        "hermes_executable": str(hermes),
        "required_toolsets": sorted(REQUIRED_TOOLSETS),
        "command": command,
        "tui_dir": str(tui_dir),
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    json_mode = False
    if "--json" in args:
        args.remove("--json")
        json_mode = True
    if "--check" in args:
        args.remove("--check")
        json_mode = True

    project_arg: str | None = None
    cleaned_args: list[str] = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--project":
            if i + 1 >= len(args):
                print("aether: error: --project requires an argument", file=sys.stderr)
                return 2
            project_arg = args[i + 1]
            i += 2
            continue
        if arg.startswith("--project="):
            project_arg = arg.split("=", 1)[1]
            i += 1
            continue
        cleaned_args.append(arg)
        i += 1

    try:
        report = inspect_activation(cleaned_args, project=project_arg)
    except (ActivationError, OSError, UnicodeError) as exc:
        print(f"aether: {exc}", file=sys.stderr)
        return 2

    if json_mode:
        print(json.dumps(report, sort_keys=True))
        return 0

    environment = dict(os.environ)
    keys_to_drop = [
        k
        for k in environment
        if k.startswith("PYTHON")
        or k == "HERMES_PROFILE"
        or k.startswith("HERMES_TUI")
        or k == "HERMES_SESSION_ID"
        or k.startswith("HERMES_KANBAN_")
        or k.startswith("HERMES_TASK")
        or k.startswith("HERMES_CRON_")
    ]
    for k in keys_to_drop:
        environment.pop(k, None)

    environment["HERMES_HOME"] = str(report["hermes_home"])
    environment["AETHER_PROJECT_ID"] = str(report["project_id"])
    environment["PWD"] = str(report["repo_root"])
    environment["HERMES_TUI_DIR"] = str(report["tui_dir"])

    command = list(cast(list[str], report["command"]))
    executable = str(report["hermes_executable"])
    target = Path(str(report["repo_root"]))
    try:
        os.chdir(target)
        os.execve(executable, command, environment)
    except OSError as exc:
        print(f"aether: {exc}", file=sys.stderr)
        return 2
    raise AssertionError("os.execve returned unexpectedly")


if __name__ == "__main__":
    sys.exit(main())
