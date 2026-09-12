"""Disposable write-context construction and the pre-write writer gate.

Aether's disposable laboratories must never construct a writer context that resolves
into an operator's live board.  Two reviewed constructors exist:

* single-board probes call :func:`isolated_hermes_env`, which scrubs inherited
  ``HERMES_KANBAN_*`` / ``HERMES_SESSION_*`` / task, run, project and cwd identity and
  pins one disposable database and workspaces root;
* canonical multi-board Monitor probes use the accepted D15R child environment
  (``scripts/telegram_monitor_lab.child_environment``), which removes every raw Kanban
  selector and resolves canonical ``board=`` paths inside the private laboratory.

Before the first native writer, the effective home, board root, database, projects
database and workspaces a loaded writer resolves are compared with the declared private,
non-symlink, contained roots; a mismatch refuses before any write.  Native Hermes
destination precedence is unchanged: an explicit ``HERMES_KANBAN_DB`` still outranks
``HERMES_HOME``, and production workers still require that explicit pin.

The child probe run under the provisioned interpreter is the native confirmation of those
roots.  The environment-derived fallback used when that probe is unavailable models the
loaded revision's resolution exactly, including the platform-native-home branch of
``get_default_hermes_root()``: a ``HERMES_HOME`` that resolves under the native home
anchors the kanban roots on that native home (the operator's live root), never on
``HERMES_HOME`` itself.  When a mapping cannot show which branch applies, the anchored
roots are refused as unresolved instead of guessed.

This module is behavior, not authority: it neither grants permissions nor replaces the
native lifecycle.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Mapping, Sequence

_EXEC_RE = re.compile(r"\bexec\s+(?:\"([^\"]+)\"|'([^']+)'|(\S+))")

#: Inherited routing identity a disposable child must never carry.  These decide which
#: board, session, project or state tree native code reads and writes, so an inherited
#: value would send laboratory writes back into the operator's installation.
SCRUB_PREFIXES: tuple[str, ...] = ("HERMES_KANBAN_", "HERMES_SESSION_")
SCRUB_NAMES: frozenset[str] = frozenset(
    {
        "TERMINAL_CWD",
        "HERMES_CWD",
        "HERMES_DELEGATED_CHILD_CONTEXT",
        "HERMES_PROJECT_ID",
        "HERMES_TENANT",
        "AETHER_PROJECT_ID",
    }
)

#: Effective root name -> (resolver ``module:attribute``, override environment variable).
#: Each root is resolved, never assumed: the resolver is the native function the writer
#: itself calls, and the override is the exact environment variable that outranks it.
WRITER_ROOT_RESOLVERS: tuple[tuple[str, str, str], ...] = (
    ("hermes_home", "hermes_constants:get_hermes_home", "HERMES_HOME"),
    ("kanban_home", "hermes_cli.kanban_db:kanban_home", "HERMES_KANBAN_HOME"),
    ("boards_root", "hermes_cli.kanban_db:boards_root", ""),
    ("kanban_db", "hermes_cli.kanban_db:kanban_db_path", "HERMES_KANBAN_DB"),
    ("projects_db", "hermes_cli.projects_db:projects_db_path", ""),
    ("workspaces_root", "hermes_cli.kanban_db:workspaces_root", "HERMES_KANBAN_WORKSPACES_ROOT"),
)

WRITER_ROOT_NAMES: tuple[str, ...] = tuple(
    name for name, _qualified, _override in WRITER_ROOT_RESOLVERS
)


class HarnessError(RuntimeError):
    """Bounded laboratory failure shared by the lab entry points."""


def scrub_inherited_identity(environ: Mapping[str, str]) -> dict[str, str]:
    """Return a copy without inherited Kanban, session, project or cwd identity."""

    scrubbed = {
        name: value
        for name, value in environ.items()
        if not name.startswith(SCRUB_PREFIXES) and name not in SCRUB_NAMES
    }
    return scrubbed


def preflight_disposable_destinations(run_root: Path, *destinations: Path) -> tuple[Path, ...]:
    """Validate and resolve disposable destinations within the owned sandbox.

    Rejects destinations that are symlinks, contain symlinks within the sandbox,
    or resolve to locations outside the resolved run_root.
    """
    resolved_root = run_root.expanduser().resolve()
    targets = destinations or (run_root / "kanban.db", run_root / "worktrees")
    resolved_targets: list[Path] = []
    for dest in targets:
        expanded = dest.expanduser()
        if expanded.is_symlink():
            raise HarnessError(f"disposable destination cannot be a symlink: {dest}")
        resolved_dest = expanded.resolve()
        try:
            if not (resolved_dest == resolved_root or resolved_dest.is_relative_to(resolved_root)):
                raise HarnessError(
                    f"disposable destination escapes sandbox: {dest} resolves to {resolved_dest} outside {resolved_root}"
                )
        except ValueError:
            raise HarnessError(
                f"disposable destination escapes sandbox: {dest} resolves to {resolved_dest} outside {resolved_root}"
            )
        chk = expanded
        while chk != run_root and chk.resolve() != resolved_root and chk != chk.parent:
            if chk.is_symlink():
                raise HarnessError(f"disposable destination cannot contain a symlink: {dest}")
            chk = chk.parent
        resolved_targets.append(resolved_dest)
    return tuple(resolved_targets)


def isolated_hermes_env(run_root: Path, hermes_root: Path, hermes: Path) -> dict[str, str]:
    """Return the disposable Hermes environment shared by laboratory lanes."""

    preflight_disposable_destinations(run_root, run_root / "kanban.db", run_root / "worktrees")

    # The laboratory's --in directory is authoritative.  Ambient cwd and dispatcher-worker
    # identity belong to the outer process; carrying either into the isolated home/board
    # would make the canary act on a foreign task.  Callers verify the effective roots
    # through :func:`require_verified_writer_context` before the first writer.
    env = scrub_inherited_identity(os.environ)
    env.update(
        {
            "HERMES_HOME": str(hermes_root),
            "HERMES_BIN": str(hermes.resolve()),
            "HERMES_ACCEPT_HOOKS": "1",
            "HERMES_KANBAN_DB": str(run_root / "kanban.db"),
            "HERMES_KANBAN_WORKSPACES_ROOT": str(run_root / "worktrees"),
            "XDG_STATE_HOME": str(run_root / "xdg-state"),
            "XDG_DATA_HOME": str(run_root / "xdg-data"),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    return env


def _is_python_interpreter(candidate: Path) -> bool:
    """True when ``candidate`` names a Python interpreter rather than any script runner.

    The child probe is Python source, so a launcher whose shebang is a shell (or any
    other runner) must never be probed: the runner would be handed Python source, which
    can block instead of failing.
    """

    return candidate.name.casefold().startswith("python")


def native_python_for(hermes: Path | None) -> Path:
    """Resolve the interpreter belonging to the caller-supplied Hermes executable."""

    if hermes and hermes.is_file():
        try:
            launcher = hermes.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            launcher = ""
        first_line = launcher.splitlines()[0].strip() if launcher else ""
        if first_line.startswith("#!") and first_line[2:].split():
            candidate = Path(first_line[2:].split()[0])
            if candidate.name != "env" and candidate.is_file():
                return candidate
        for line in launcher.splitlines():
            match = _EXEC_RE.search(line)
            if not match:
                continue
            candidate = Path(next(value for value in match.groups() if value))
            if candidate.is_file():
                return candidate
    return Path(sys.executable)


def _platform_default_hermes_home(environ: Mapping[str, str]) -> Path | None:
    """Model ``hermes_constants._get_platform_default_hermes_home()`` for a mapping.

    POSIX uses ``$HOME/.hermes``; native Windows uses ``%LOCALAPPDATA%\\hermes``.
    ``None`` means the mapping does not carry the variable that branch reads, so the
    native home cannot be shown faithful and the caller must refuse rather than guess.
    """

    if sys.platform == "win32":
        local_appdata = environ.get("LOCALAPPDATA", "").strip()
        return Path(local_appdata) / "hermes" if local_appdata else None
    home = environ.get("HOME", "").strip()
    return Path(home) / ".hermes" if home else None


def _hermes_home_from_env(environ: Mapping[str, str]) -> Path | None:
    """Model ``hermes_constants._hermes_home_from_env()`` for a mapping."""

    value = environ.get("HERMES_HOME", "").strip()
    if value:
        return Path(value)
    return _platform_default_hermes_home(environ)


def _default_hermes_root_from_env(environ: Mapping[str, str]) -> Path | None:
    """Model ``hermes_constants.get_default_hermes_root()`` exactly for a mapping.

    A ``HERMES_HOME`` that resolves under the platform-native home anchors on that native
    home (the operator's live root), a ``<root>/profiles/<name>`` home anchors on
    ``<root>``, any other home is its own root, and an unset ``HERMES_HOME`` falls back to
    the native home.  ``None`` means the mapping cannot show which branch the loaded
    revision takes, so anchored roots are refused as unresolved instead of assumed.
    """

    native_home = _platform_default_hermes_home(environ)
    env_home = environ.get("HERMES_HOME", "")
    if not env_home:
        return native_home
    if native_home is None:
        return None
    env_path = Path(env_home)
    try:
        env_resolved = env_path.resolve()
        native_resolved = native_home.resolve()
    except OSError:
        return None
    try:
        env_resolved.relative_to(native_resolved)
    except ValueError:
        if env_path.parent.name == "profiles":
            return env_path.parent.parent
        return env_path
    return native_home


def _kanban_home_from_env(environ: Mapping[str, str], default_root: Path | None) -> Path | None:
    """Model ``hermes_cli.kanban_db.kanban_home()``: its override, else the default root."""

    override = environ.get("HERMES_KANBAN_HOME", "").strip()
    if override:
        return Path(override).expanduser()
    return default_root


def _native_root(qualified: str) -> Path | None:
    """Resolve one native root through the loaded writer module, or report unresolved."""

    module_name, _, attribute = qualified.partition(":")
    try:
        module = __import__(module_name, fromlist=[attribute])
        resolver = getattr(module, attribute, None)
        value = resolver() if callable(resolver) else None
    except Exception:  # noqa: BLE001 - an unresolvable root is reported, never guessed
        return None
    if value is None:
        return None
    try:
        return Path(str(value))
    except (TypeError, ValueError):
        return None


def _environment_root(
    name: str,
    environ: Mapping[str, str],
    hermes_home: Path | None,
    default_root: Path | None,
) -> Path | None:
    """Derive one root from the environment exactly as the native resolver would.

    ``hermes_home`` and ``default_root`` are the faithful models of
    ``get_hermes_home()`` and ``get_default_hermes_root()`` for this mapping; a ``None``
    model refuses the anchored roots as unresolved instead of assuming a value.
    """

    if name == "hermes_home":
        return hermes_home
    overrides = {root: override for root, _qualified, override in WRITER_ROOT_RESOLVERS}
    override = environ.get(overrides.get(name, ""), "").strip()
    if override:
        return Path(override).expanduser()
    if name == "projects_db":
        return hermes_home / "projects.db" if hermes_home is not None else None
    kanban_root = _kanban_home_from_env(environ, default_root)
    if name == "kanban_home":
        return kanban_root
    if kanban_root is None:
        return None
    if name == "boards_root":
        return kanban_root / "kanban" / "boards"
    if name == "kanban_db":
        return kanban_root / "kanban.db"
    if name == "workspaces_root":
        return kanban_root / "kanban" / "workspaces"
    return None


def resolve_writer_roots(
    environ: Mapping[str, str] | None = None, *, native: bool | None = None
) -> dict[str, Path | None]:
    """Resolve the effective roots a native writer would use for this context.

    Native resolvers read the current process environment, so they are authoritative
    only when ``environ`` is omitted (the in-child case).  For a mapping that describes
    another process the environment-derived form is used and the child probe
    (:func:`probe_child_writer_roots`) is the native confirmation.
    """

    env = dict(os.environ) if environ is None else dict(environ)
    use_native = (environ is None) if native is None else native
    hermes_home = _hermes_home_from_env(env)
    default_root = _default_hermes_root_from_env(env)
    roots: dict[str, Path | None] = {}
    for name, qualified, _override in WRITER_ROOT_RESOLVERS:
        value = _native_root(qualified) if use_native else None
        if value is None:
            value = _environment_root(name, env, hermes_home, default_root)
        roots[name] = value
    return roots


def _contained(resolved: Path, resolved_roots: Sequence[Path]) -> bool:
    return any(resolved == root or root in resolved.parents for root in resolved_roots)


def writer_root_problems(
    roots: Mapping[str, Path | None],
    *,
    private_roots: Sequence[Path],
) -> list[str]:
    """Return bounded codes for every root that is not private, non-symlink and contained."""

    problems: list[str] = []
    resolved_private: list[Path] = []
    for index, root in enumerate(private_roots):
        candidate = Path(root).expanduser()
        if not candidate.is_absolute():
            problems.append(f"private-root-not-absolute:{index}")
            continue
        if candidate.is_symlink():
            problems.append(f"private-root-symlink:{index}")
            continue
        try:
            resolved_private.append(candidate.resolve())
        except OSError:
            problems.append(f"private-root-unresolvable:{index}")
    for name in WRITER_ROOT_NAMES:
        value = roots.get(name)
        if value is None:
            problems.append(f"{name}-unresolved")
            continue
        candidate = Path(value).expanduser()
        if not candidate.is_absolute():
            problems.append(f"{name}-not-absolute")
            continue
        if candidate.is_symlink():
            problems.append(f"{name}-symlink")
            continue
        try:
            resolved = candidate.resolve()
        except OSError:
            problems.append(f"{name}-unresolvable")
            continue
        if not _contained(resolved, resolved_private):
            problems.append(f"{name}-escape")
    return sorted(dict.fromkeys(problems))


def verify_writer_context(
    roots: Mapping[str, Path | None],
    *,
    private_roots: Sequence[Path],
) -> dict[str, str]:
    """Refuse before the first writer when the effective roots are not disposable.

    The returned receipt is decision-only: root names and counts, never paths.
    """

    problems = writer_root_problems(roots, private_roots=private_roots)
    if problems:
        raise HarnessError("pre-write gate refused the writer context: " + ", ".join(problems))
    return {
        "verified_roots": ",".join(sorted(WRITER_ROOT_NAMES)),
        "private_root_count": str(len(tuple(private_roots))),
    }


def verify_child_writer_context(
    private_roots: Sequence[Path], *, environ: Mapping[str, str] | None = None
) -> dict[str, str]:
    """Child-side gate: resolve this process's writer roots and refuse before writing.

    Call this from inside a native child that may invoke writers; the resolution uses
    the same native modules the writers load.  A caller that only holds another
    process's environment uses :func:`require_verified_writer_context` instead.
    """

    roots = resolve_writer_roots(environ, native=environ is None)
    return verify_writer_context(roots, private_roots=private_roots)


#: Self-contained child probe: resolve the effective writer roots with the loaded native
#: modules and print them, writing nothing.  It is intentionally independent of this
#: package so any provisioned interpreter can run it.
CHILD_WRITER_ROOTS_PROBE = r"""
import importlib
import json

RESOLVERS = (
    ("hermes_home", "hermes_constants", "get_hermes_home"),
    ("kanban_home", "hermes_cli.kanban_db", "kanban_home"),
    ("boards_root", "hermes_cli.kanban_db", "boards_root"),
    ("kanban_db", "hermes_cli.kanban_db", "kanban_db_path"),
    ("projects_db", "hermes_cli.projects_db", "projects_db_path"),
    ("workspaces_root", "hermes_cli.kanban_db", "workspaces_root"),
)
payload = {"complete": True, "roots": {}}
for name, module_name, attribute in RESOLVERS:
    value = None
    try:
        module = importlib.import_module(module_name)
        resolver = getattr(module, attribute, None)
        if callable(resolver):
            value = str(resolver())
    except Exception:
        value = None
    payload["roots"][name] = value
    if value is None:
        payload["complete"] = False
print(json.dumps(payload))
"""


def probe_child_writer_roots(
    python: Path,
    environ: Mapping[str, str],
    *,
    cwd: Path | None = None,
    timeout_seconds: float = 30.0,
) -> tuple[bool, dict[str, Path | None]]:
    """Run the read-only child probe and return ``(complete, effective roots)``.

    The probe is Python source, so only an interpreter that names itself as Python is
    probed: handing it to a shell or another runner can block instead of failing, and an
    unprobed context is verified by the environment-derived form instead.  A child whose
    provisioned revision cannot resolve every root returns ``complete = False``.
    """

    if not _is_python_interpreter(Path(python)):
        return False, {}
    try:
        completed = subprocess.run(
            [str(python), "-c", CHILD_WRITER_ROOTS_PROBE],
            cwd=str(cwd) if cwd is not None else None,
            env=dict(environ),
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False, {}
    if completed.returncode != 0:
        return False, {}
    try:
        payload = json.loads(completed.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        return False, {}
    if not isinstance(payload, dict):
        return False, {}
    raw_roots = payload.get("roots")
    raw_roots = raw_roots if isinstance(raw_roots, dict) else {}
    roots: dict[str, Path | None] = {}
    for name in WRITER_ROOT_NAMES:
        value = raw_roots.get(name)
        roots[name] = Path(str(value)) if isinstance(value, str) and value.strip() else None
    complete = payload.get("complete") is True and all(
        roots.get(name) is not None for name in WRITER_ROOT_NAMES
    )
    return complete, roots


def require_verified_writer_context(
    *,
    run_root: Path,
    environ: Mapping[str, str],
    hermes_root: Path | None = None,
    python: Path | None = None,
    cwd: Path | None = None,
) -> dict[str, str]:
    """Verify a write-capable child's disposable context before its first writer.

    ``python`` is the provisioned interpreter the child will run under.  When it can
    resolve the native writer roots, those are authoritative; otherwise the
    environment-derived form is verified and the receipt records the native child probe
    as unavailable.  Either way a mismatch raises :class:`HarnessError` before launch.
    """

    private_roots: list[Path] = [Path(run_root)]
    if hermes_root is not None:
        private_roots.append(Path(hermes_root))
    if python is not None:
        complete, probed = probe_child_writer_roots(python, environ, cwd=cwd)
        if complete:
            receipt = verify_writer_context(probed, private_roots=private_roots)
            receipt["child_probe"] = "native"
            return receipt
    receipt = verify_writer_context(
        resolve_writer_roots(environ, native=False), private_roots=private_roots
    )
    receipt["child_probe"] = "unavailable"
    return receipt
