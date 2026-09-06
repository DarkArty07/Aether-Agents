"""Verified bindings to existing Aether Projects, never a second project registry."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from aether_agents.observation.context import (
    ProjectRegistry,
    canonical_project_id,
    read_project_marker,
)

from .common import ROLES, KnowledgeError, git


@dataclass(frozen=True)
class KnowledgeContext:
    project_id: str
    root: Path
    view_id: str
    role_id: str
    source_revision: str
    session_id: str = ""
    task_id: str = ""
    run_id: str = ""


def resolve_context(
    project_id: str,
    role_id: str,
    *,
    state_root: Path | None = None,
    root: Path | None = None,
    session_id: str = "",
    task_id: str = "",
    run_id: str = "",
) -> KnowledgeContext:
    """Validate an operator/runtime binding against the marker and Git worktrees.

    A supplied UUID is a candidate, not authorization. Model tools never expose
    this function's identity arguments. Their caller resolves them from a native
    session/task binding or an explicit operator-created session binding.
    """
    identity = canonical_project_id(project_id)
    if identity is None or role_id not in ROLES:
        raise KnowledgeError("PROJECT_UNRESOLVED", "A known project and Aether role are required.")
    registry = ProjectRegistry(state_root)
    registered = registry.project_path(identity)
    if registered is None or not registry.verify_with_marker(identity):
        raise KnowledgeError("PROJECT_UNRESOLVED", "The project registry and marker do not agree.")
    registered = registered.resolve()
    candidate = (root or registered).expanduser().resolve()
    actual_root = Path(git(candidate, "rev-parse", "--show-toplevel").decode().strip()).resolve()
    if actual_root != candidate:
        raise KnowledgeError("VIEW_MISMATCH", "The binding must identify an exact repository root.")
    marker = read_project_marker(candidate)
    if marker is None or canonical_project_id(marker.get("project_id")) != identity:
        raise KnowledgeError("PROJECT_CONFLICT", "The checkout marker belongs to another project.")
    if candidate != registered:
        common = git(candidate, "rev-parse", "--path-format=absolute", "--git-common-dir").strip()
        primary_common = git(
            registered, "rev-parse", "--path-format=absolute", "--git-common-dir"
        ).strip()
        worktrees = git(registered, "worktree", "list", "--porcelain", "-z").split(b"\0")
        listed = {
            Path(item[len(b"worktree ") :].decode()).resolve()
            for item in worktrees
            if item.startswith(b"worktree ")
        }
        if common != primary_common or candidate not in listed:
            raise KnowledgeError(
                "VIEW_MISMATCH", "The checkout is not a registered project worktree."
            )
    revision = git(candidate, "rev-parse", "--verify", "HEAD^{commit}").decode().strip()
    view_id = hashlib.sha256(str(candidate).encode()).hexdigest()[:24]
    return KnowledgeContext(
        identity, candidate, view_id, role_id, revision, session_id, task_id, run_id
    )
