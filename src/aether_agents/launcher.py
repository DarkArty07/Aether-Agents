"""Packaged launcher and exact project binding for Aether's Morfeo profile.

Normative source: ``specs/001-aether-v1-productization/tasks-rc4.md`` (LG-CLI).
Validates local state, resolves exact project identity, scrubs conflicting environment
residue, and executes or reports the Morfeo TUI launch plan.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import tomllib
from collections.abc import Sequence
from pathlib import Path
from typing import Any, NoReturn, cast

from aether_agents.observation.context import ProjectRegistry, canonical_project_id
from aether_agents.paths import data_root, state_root
from aether_agents.project_marker import ProjectMarkerValidationError, validate_project_marker

__all__ = [
    "REQUIRED_TOOLSETS",
    "ActivationError",
    "_resolve_target_python",
    "_resolve_target_source_root",
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


_NO_EXPLICIT_TERMINAL_CWD = frozenset({"", ".", "./", "auto", "cwd"})

#: The alignment gate must interpret ``config.yaml`` with the grammar the selected
#: runtime applies, but the launcher's own environment is the wheel's declared
#: dependencies alone (``jsonschema``) and carries no YAML interpreter.  The document is
#: therefore interpreted by the *target runtime* interpreter in a bounded, isolated,
#: read-only subprocess.  This fixed child reads one path and prints one small status
#: object: the profile, environment values, secrets and parser exception text never leave
#: the child.
_TERMINAL_CWD_PROBE = """
import json
import sys

status = {"status": "absent"}
try:
    import yaml
except Exception:
    status = {"status": "unavailable"}
else:
    try:
        with open(sys.argv[1], "rb") as handle:
            document = yaml.safe_load(handle)
    except Exception:
        status = {"status": "malformed"}
    else:
        if isinstance(document, dict):
            terminal = document.get("terminal")
            if isinstance(terminal, dict):
                configured = terminal.get("cwd")
                if configured is not None:
                    value = configured if isinstance(configured, str) else str(configured)
                    status = {"status": "value", "cwd": value}
print(json.dumps(status))
"""

_TERMINAL_CWD_PROBE_TIMEOUT_SECONDS = 10
_TERMINAL_CWD_PROBE_ENV_KEYS = ("PATH", "SYSTEMROOT", "TMPDIR", "TEMP", "TMP")

_TERMINAL_CWD_UNVERIFIABLE = (
    "Morfeo terminal.cwd cannot be verified: the selected Hermes runtime provides no YAML "
    "interpreter"
)


def _refuse_terminal_cwd(reason: str) -> NoReturn:
    """Refuse visibly when the alignment check cannot be answered at all."""
    raise ActivationError(f"{_TERMINAL_CWD_UNVERIFIABLE} ({reason})")


def _configured_terminal_cwd(target_python: Path, config: Path) -> str | None:
    """Interpret optional ``terminal.cwd`` with the selected runtime's YAML grammar.

    ``config.yaml`` is a YAML document, and the runtime that consumes it interprets it
    that way (``hermes_cli.config`` loads it through PyYAML's safe loader).  The
    alignment gate therefore has to read the same document the runtime reads: flow-style
    mappings, quoting and ``#`` handling are decided by the grammar, not by the textual
    shape of a line, so a line scanner can only report "not seen" for forms it does not
    recognise instead of the *verified absence* the gate needs.

    The launcher cannot import that grammar itself: its own environment is the wheel's
    declared dependency set, which has no YAML interpreter.  The interpretation is
    delegated to the selected target runtime through ``target_python`` — a fixed,
    isolated (``-I``/``-B``, minimal environment, safe cwd, short timeout), read-only
    child that returns only a status and, when one exists, the configured value.

    ``None`` means "no explicit cwd is configured": the key is absent, ``null``, or one
    of the sentinels the runtime itself treats as unset.  A document the loader cannot
    parse is reported the same way rather than as a new launcher-level refusal class —
    the runtime raises its own error for those same bytes, and that is the error the
    operator must see.  A runtime that provides no YAML interpreter is different: the
    gate refuses visibly instead of reporting an absence it could not verify.
    """
    environment = {
        key: value for key, value in os.environ.items() if key in _TERMINAL_CWD_PROBE_ENV_KEYS
    }
    probe_cwd: Path | str
    try:
        if target_python.parent.is_dir():
            probe_cwd = target_python.parent
        else:
            probe_cwd = tempfile.gettempdir()
    except OSError:
        probe_cwd = tempfile.gettempdir()

    try:
        completed = subprocess.run(
            [
                os.fspath(target_python),
                "-I",
                "-B",
                "-c",
                _TERMINAL_CWD_PROBE,
                os.fspath(config),
            ],
            capture_output=True,
            text=True,
            timeout=_TERMINAL_CWD_PROBE_TIMEOUT_SECONDS,
            env=environment,
            cwd=probe_cwd,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.TimeoutExpired):
        _refuse_terminal_cwd("the target runtime interpreter could not run the probe")

    if completed.returncode != 0:
        _refuse_terminal_cwd("the target runtime interpreter reported a probe failure")

    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        _refuse_terminal_cwd("the target runtime interpreter reported no interpretation")
    try:
        reported = json.loads(lines[-1])
    except json.JSONDecodeError:
        _refuse_terminal_cwd("the target runtime interpreter reported an unreadable interpretation")
    if not isinstance(reported, dict):
        _refuse_terminal_cwd("the target runtime interpreter reported an unreadable interpretation")
    status = reported.get("status")
    if status == "unavailable":
        _refuse_terminal_cwd("no YAML interpreter is importable in the target runtime")
    if status in ("absent", "malformed"):
        return None
    if status != "value":
        _refuse_terminal_cwd("the target runtime interpreter reported an unusable status")
    configured = reported.get("cwd")
    if not isinstance(configured, str):
        _refuse_terminal_cwd("the target runtime interpreter reported no usable value")
    if configured.strip() in _NO_EXPLICIT_TERMINAL_CWD:
        return None
    return configured


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
        return repo, env_pid

    # (3) Current repository marker or nearest parent only when registry and marker agree
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
            return repo_candidate, marker_pid
        raise ActivationError(
            f"project registry and repository marker do not agree for project {marker_pid}"
        )

    projects = registry._load()
    if len(projects) == 1:
        raise ActivationError(
            "current directory is not an initialized Aether project; "
            "run 'git init' and 'aether init' to initialize"
        )
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


def _probe_venv_interpreter(python_path: Path, target_venvs: Sequence[Path]) -> bool:
    """Verify in an isolated subprocess that python_path reports sys.prefix and purelib inside the same target venv."""
    probe_code = (
        "import sys, sysconfig\n"
        "print(sys.prefix)\n"
        "print(sysconfig.get_paths().get('purelib', ''))\n"
    )
    env = {
        k: v for k, v in os.environ.items() if k in ("PATH", "SYSTEMROOT", "TMPDIR", "TEMP", "TMP")
    }
    probe_cwd: Path | str
    try:
        if python_path.parent.is_dir():
            probe_cwd = python_path.parent
        else:
            probe_cwd = tempfile.gettempdir()
    except OSError:
        probe_cwd = tempfile.gettempdir()

    try:
        proc = subprocess.run(
            [os.fspath(python_path), "-I", "-c", probe_code],
            capture_output=True,
            text=True,
            timeout=5,
            env=env,
            cwd=probe_cwd,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False

    if proc.returncode != 0:
        return False

    lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    if len(lines) < 2:
        return False

    raw_prefix = Path(lines[0])
    raw_purelib = Path(lines[1])
    try:
        reported_prefix = raw_prefix.resolve()
    except OSError:
        reported_prefix = raw_prefix
    try:
        reported_purelib = raw_purelib.resolve()
    except OSError:
        reported_purelib = raw_purelib

    for target in target_venvs:
        try:
            target_resolved = target.resolve()
        except OSError:
            target_resolved = target

        prefix_ok = (
            raw_prefix == target
            or raw_prefix.is_relative_to(target)
            or reported_prefix == target_resolved
            or reported_prefix.is_relative_to(target_resolved)
        )
        purelib_ok = raw_purelib.is_relative_to(target) or reported_purelib.is_relative_to(
            target_resolved
        )
        if prefix_ok and purelib_ok:
            return True

    return False


def _resolve_target_python(hermes: Path, runtime_root: Path | None = None) -> Path:
    """Resolve and verify the target release Python interpreter paired with the Hermes executable.

    Returns the absolute lexical path within the target release venv (without dereferencing
    leaf symlinks to base interpreters) after proving in a bounded isolated subprocess that
    the interpreter reports sys.prefix and purelib within the target venv.
    """
    target_venvs: list[Path] = []
    if hermes.parent.name in ("bin", "Scripts"):
        target_venvs.append(hermes.parent.parent)
    else:
        target_venvs.append(hermes.parent)

    resolved_hermes = hermes.resolve()
    if resolved_hermes != hermes:
        if resolved_hermes.parent.name in ("bin", "Scripts"):
            target_venvs.append(resolved_hermes.parent.parent)
        else:
            target_venvs.append(resolved_hermes.parent)

    if runtime_root is not None:
        target_venvs.append(runtime_root / "current" / "venv")
        target_venvs.append(runtime_root / "venv")

    resolved_targets: list[Path] = []
    for t in target_venvs:
        try:
            resolved_targets.append(t.resolve())
        except OSError:
            resolved_targets.append(t)

    candidates: list[Path] = []
    for name in ("python", "python3", "python.exe", "python3.exe"):
        candidates.append(hermes.parent / name)
    if resolved_hermes.parent != hermes.parent:
        for name in ("python", "python3", "python.exe", "python3.exe"):
            candidates.append(resolved_hermes.parent / name)
    if runtime_root is not None:
        for name in ("python", "python3", "python.exe", "python3.exe"):
            candidates.append(runtime_root / "current" / "venv" / "bin" / name)
            candidates.append(runtime_root / "venv" / "bin" / name)

    for cand in candidates:
        lexical_cand = Path(os.path.abspath(os.fspath(cand)))
        try:
            if not (lexical_cand.is_file() and os.access(lexical_cand, os.X_OK)):
                continue
            cand_venv = (
                lexical_cand.parent.parent.resolve()
                if lexical_cand.parent.name in ("bin", "Scripts")
                else lexical_cand.parent.resolve()
            )
            if not any(
                cand_venv == target or cand_venv.is_relative_to(target)
                for target in resolved_targets
            ):
                continue
        except OSError:
            continue

        if _probe_venv_interpreter(lexical_cand, target_venvs):
            return lexical_cand

    # Check fallback sys.executable only if it proves to be inside target_venvs
    current_exe = Path(os.path.abspath(sys.executable))
    try:
        exe_venv = (
            current_exe.parent.parent.resolve()
            if current_exe.parent.name in ("bin", "Scripts")
            else current_exe.parent.resolve()
        )
        if any(
            exe_venv == target or exe_venv.is_relative_to(target) for target in resolved_targets
        ):
            if _probe_venv_interpreter(current_exe, target_venvs):
                return current_exe
    except OSError:
        pass

    raise ActivationError(
        f"Target release Python interpreter for '{hermes}' could not be verified inside "
        f"target venv (checked candidates: {[str(c) for c in candidates]})"
    )


def _resolve_target_source_root(hermes: Path, runtime_root: Path | None, repo: Path) -> Path | None:
    """Resolve the target release hermes-source root directory if present."""
    candidates: list[Path] = []
    if runtime_root is not None:
        candidates.append(runtime_root / "hermes-source")
    candidates.append(data_root() / "runtime" / "current" / "hermes-source")

    # Releases structure: <release_dir>/venv/bin/hermes -> <release_dir>/hermes-source
    candidates.append(hermes.parent.parent / "hermes-source")
    candidates.append(hermes.parent.parent.parent / "hermes-source")

    resolved_hermes = hermes.resolve()
    candidates.append(resolved_hermes.parent.parent / "hermes-source")
    candidates.append(resolved_hermes.parent.parent.parent / "hermes-source")

    # Local checkout structures
    candidates.append(repo / "home" / "hermes-source")
    candidates.append(repo / "hermes-source")

    for cand in candidates:
        try:
            if cand.is_dir():
                return cand.resolve()
        except OSError:
            continue
    return None


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

    # ``terminal.cwd`` is interpreted with the selected runtime's own grammar (see
    # ``_configured_terminal_cwd``), so the gate needs that runtime's interpreter.  Not
    # being able to obtain one is a refusal, not an abstention: "no contradictory cwd" is
    # only meaningful once the document can actually be interpreted.
    try:
        target_python = _resolve_target_python(
            hermes,
            _absolute_env_path("AETHER_RUNTIME_ROOT"),
        )
    except ActivationError as exc:
        raise ActivationError(
            f"{_TERMINAL_CWD_UNVERIFIABLE} (the target runtime interpreter is unavailable)"
        ) from exc

    configured_terminal_cwd = _configured_terminal_cwd(target_python, config)
    if configured_terminal_cwd is not None:
        expanded_terminal_cwd = Path(os.path.expanduser(configured_terminal_cwd)).resolve()
        if expanded_terminal_cwd != repo.resolve():
            raise ActivationError(
                f"Morfeo terminal.cwd ({configured_terminal_cwd}) contradicts selected project ({repo})"
            )

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

    runtime_root = _absolute_env_path("AETHER_RUNTIME_ROOT")
    try:
        target_python = _resolve_target_python(
            Path(str(report["hermes_executable"])),
            runtime_root,
        )
    except ActivationError as exc:
        print(f"aether: {exc}", file=sys.stderr)
        return 2

    target_source_root = _resolve_target_source_root(
        Path(str(report["hermes_executable"])),
        runtime_root,
        Path(str(report["repo_root"])),
    )

    environment = dict(os.environ)
    keys_to_drop = [
        k
        for k in environment
        if k.startswith("PYTHON")
        or k == "VIRTUAL_ENV"
        or k == "HERMES_PROFILE"
        or k == "HERMES_BIN"
        or k == "HERMES_CWD"
        or k == "TERMINAL_CWD"
        or k == "MESSAGING_CWD"
        or k == "HERMES_PYTHON"
        or k == "HERMES_PYTHON_SRC_ROOT"
        or k == "_HERMES_GATEWAY"
        or k == "HERMES_UI_SESSION_ID"
        or k == "HERMES_ACTION_ID"
        or k.startswith("HERMES_TUI")
        or k.startswith("HERMES_SESSION")
        or k.startswith("HERMES_RPC")
        or k.startswith("HERMES_GATEWAY")
        or k.startswith("HERMES_DESKTOP")
        or k.startswith("HERMES_COMPUTE_HOST")
        or k.startswith("HERMES_PARENT")
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
    environment["HERMES_PYTHON"] = str(target_python)
    if target_source_root is not None:
        environment["HERMES_PYTHON_SRC_ROOT"] = str(target_source_root)

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
