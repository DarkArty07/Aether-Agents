"""Per-call session bindings using native workspace evidence or explicit operator setup."""

from __future__ import annotations

import hashlib
import os
import sqlite3
import subprocess
from pathlib import Path
from urllib.parse import quote

from aether_agents.observation.context import read_project_marker

from .common import (
    ROLES,
    KnowledgeError,
    atomic_json,
    clean_environment,
    git,
    load_json,
    stable_lock,
)
from .context import KnowledgeContext, resolve_context


def _binding_path(state: Path, role: str, session: str) -> Path:
    if role not in ROLES or not session or len(session) > 512:
        raise KnowledgeError("PROJECT_UNRESOLVED", "A runtime role and session are required.")
    return (
        state
        / "knowledge"
        / "bindings"
        / role
        / (hashlib.sha256(session.encode()).hexdigest() + ".json")
    )


def bind_session(
    state: Path,
    project_id: str,
    role: str,
    session: str,
    *,
    root: Path | None = None,
    replace: bool = False,
) -> KnowledgeContext:
    context = resolve_context(project_id, role, state_root=state, root=root, session_id=session)
    path = _binding_path(state, role, session)
    with stable_lock(path.with_suffix(".lock")):
        try:
            previous = load_json(path)
        except FileNotFoundError:
            previous = None
        record = {
            "schema_version": 1,
            "project_id": context.project_id,
            "role_id": role,
            "session_id": session,
            "root": str(context.root),
        }
        if previous is not None and previous != record and not replace:
            raise KnowledgeError(
                "PROJECT_CONFLICT", "An explicit binding already exists; replace it deliberately."
            )
        atomic_json(path, record)
    return context


def _apparent_git_metadata(path: Path) -> bool:
    """Report whether ``path`` or an ancestor still carries a ``.git`` entry."""
    for directory in (path, *path.parents):
        entry = directory / ".git"
        if entry.is_dir() or entry.is_file() or entry.is_symlink():
            return True
    return False


def _repository_context(path: Path) -> bool:
    """Classify one recorded workspace before an explicit binding may take precedence.

    Git metadata in this directory or an ancestor, or a Git discovery that reports a
    repository here, means the recorded workspace is real project evidence. Only a
    directory with neither is an ordinary non-Git workspace that may fall through, and
    even then an unclear probe keeps the conservative failure path instead of guessing.
    """
    if _apparent_git_metadata(path):
        return True
    try:
        completed = subprocess.run(
            [
                "git",
                "-C",
                str(path),
                "-c",
                "core.hooksPath=" + os.devnull,
                "rev-parse",
                "--git-dir",
            ],
            capture_output=True,
            timeout=20.0,
            env=clean_environment(),
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise KnowledgeError(
            "VIEW_MISMATCH", "Cannot classify the native session workspace."
        ) from exc
    return completed.returncode == 0 and bool(completed.stdout.strip())


def _native_workspace(home: Path, session: str) -> Path | None:
    """Read one exact native session row, never the active/last session or cwd.

    ``None`` means the exact session carries no usable project evidence: no recorded
    workspace, or an ordinary existing directory with no Git repository context. The
    exact-session explicit binding decides precedence then, as it does for absent or
    empty metadata. Missing, unreadable, contradictory or unusable Git evidence stays
    an error and is never silently treated as an absent workspace.
    """
    database = home / "state.db"
    if not database.is_file():
        return None
    try:
        connection = sqlite3.connect(
            "file:" + quote(str(database.absolute())) + "?mode=ro", uri=True, timeout=1
        )
        try:
            connection.execute("PRAGMA query_only=ON")
            row = connection.execute("SELECT cwd FROM sessions WHERE id = ?", (session,)).fetchone()
        finally:
            connection.close()
    except sqlite3.Error as exc:
        raise KnowledgeError(
            "PROJECT_UNRESOLVED", "Cannot verify the native session workspace."
        ) from exc
    if row is None or not isinstance(row[0], str) or not row[0]:
        return None
    candidate = Path(row[0])
    if not candidate.is_absolute():
        raise KnowledgeError("VIEW_MISMATCH", "The native session workspace is not absolute.")
    if not candidate.is_dir():
        raise KnowledgeError(
            "VIEW_MISMATCH", "The native session workspace is missing or unreadable."
        )
    if not _repository_context(candidate):
        # An ordinary directory identifies no project, so only an explicit binding can.
        return None
    # This is the workspace persisted for the exact session, not a process cwd heuristic.
    try:
        return Path(git(candidate, "rev-parse", "--show-toplevel").decode().strip()).resolve()
    except KnowledgeError as exc:
        raise KnowledgeError(
            "VIEW_MISMATCH", "The native session workspace is not a reachable Git checkout."
        ) from exc


def context_for_session(
    state: Path,
    role: str,
    session: str,
    *,
    hermes_home: Path | None = None,
    task_id: str = "",
    run_id: str = "",
) -> KnowledgeContext:
    path = _binding_path(state, role, session)
    candidates: list[KnowledgeContext] = []
    if hermes_home is not None:
        native = _native_workspace(hermes_home, session)
        if native is not None:
            marker = read_project_marker(native)
            if marker is None:
                raise KnowledgeError(
                    "PROJECT_UNRESOLVED",
                    "The native session has no verified Aether project marker.",
                )
            candidates.append(
                resolve_context(
                    str(marker.get("project_id", "")),
                    role,
                    state_root=state,
                    root=native,
                    session_id=session,
                    task_id=task_id,
                    run_id=run_id,
                )
            )
    try:
        binding = load_json(path)
    except FileNotFoundError:
        binding = None
    if binding is not None:
        if (
            not isinstance(binding, dict)
            or binding.get("session_id") != session
            or binding.get("role_id") != role
            or binding.get("schema_version") != 1
        ):
            raise KnowledgeError("PROJECT_CONFLICT", "The explicit session binding is invalid.")
        candidates.append(
            resolve_context(
                binding["project_id"],
                role,
                state_root=state,
                root=Path(binding["root"]),
                session_id=session,
                task_id=task_id,
                run_id=run_id,
            )
        )
    if not candidates:
        raise KnowledgeError(
            "PROJECT_UNRESOLVED",
            "Bind this session to a registered Aether project before querying knowledge.",
        )
    if len({(item.project_id, item.view_id) for item in candidates}) != 1:
        raise KnowledgeError("PROJECT_CONFLICT", "Native and explicit session bindings disagree.")
    return candidates[0]
