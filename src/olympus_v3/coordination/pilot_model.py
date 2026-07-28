"""Immutable values and state contracts for the bounded R8 Snake pilot."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

PILOT_ID = PROJECT_ID = "snake-r8"
CANONICAL_PILOT_ROOT = Path("/home/arty/Escritorio/agentes/aether-pilots/snake-r8")
CANONICAL_CONTROL_ROOT = Path("/home/arty/Escritorio/agentes/aether-pilots/.snake-r8-control")
TASK_IDS = ("snake-spec", "snake-build", "snake-verify", "snake-review", "snake-closure")
MAX_TASKS = 8
MAX_CONCURRENCY = 1
MAX_TASK_ATTEMPTS = 2
MAX_GLOBAL_RETRIES = 3
DEADLINE_SECONDS = 45 * 60
MAX_RESULT_BYTES = 256_000
_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


class PilotError(ValueError):
    """Fail-closed pilot contract error."""


class TaskStatus(StrEnum):
    PENDING = "pending"
    INTENT_RECORDED = "intent_recorded"
    RUNNING = "running"
    CORRECTION_REQUIRED = "correction_required"
    ACCEPTED = "accepted"
    BLOCKED = "blocked"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class PilotTask:
    task_id: str
    role: str
    assignee: str
    objective: str
    depends_on: tuple[str, ...]
    permission: str
    scopes: tuple[str, ...]
    required_artifacts: tuple[str, ...]
    reviewer_of: str | None = None

    def __post_init__(self) -> None:
        values = (self.task_id, self.role, self.assignee)
        if any(not isinstance(value, str) or not _ID.fullmatch(value) for value in values):
            raise PilotError("invalid task identity")
        if self.task_id not in TASK_IDS:
            raise PilotError("fixed task vocabulary required")
        if self.assignee in {"hermes", "olympus"}:
            raise PilotError("invalid pilot assignee")
        if not isinstance(self.objective, str) or not self.objective.strip() or len(self.objective) > 4096:
            raise PilotError("invalid task objective")
        if self.permission not in {"read_only", "write"}:
            raise PilotError("invalid task permission")
        for field in (self.depends_on, self.scopes, self.required_artifacts):
            if not isinstance(field, tuple) or len(set(field)) != len(field):
                raise PilotError("invalid task collection")
        if self.task_id in self.depends_on:
            raise PilotError("self dependency")
        for path in (*self.scopes, *self.required_artifacts):
            _validate_relative(path)
        if self.reviewer_of is not None and self.reviewer_of not in TASK_IDS:
            raise PilotError("invalid review source")
        if self.permission == "read_only" and self.role not in {"review", "completion"}:
            raise PilotError("invalid read-only role")

    def payload(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "role": self.role,
            "assignee": self.assignee,
            "objective": self.objective,
            "depends_on": list(self.depends_on),
            "permission": self.permission,
            "scopes": list(self.scopes),
            "required_artifacts": list(self.required_artifacts),
            "reviewer_of": self.reviewer_of,
        }


@dataclass(frozen=True, slots=True)
class PilotManifest:
    pilot_id: str
    project_id: str
    root: str
    tasks: tuple[PilotTask, ...]
    generation: int = 1
    manifest_hash: str = ""

    def __post_init__(self) -> None:
        if self.pilot_id != PILOT_ID or self.project_id != PROJECT_ID or self.generation != 1:
            raise PilotError("fixed pilot identity required")
        root = Path(self.root)
        if not root.is_absolute() or str(root) != str(root.resolve(strict=False)):
            raise PilotError("canonical absolute pilot root required")
        if not isinstance(self.tasks, tuple) or not 1 <= len(self.tasks) <= MAX_TASKS:
            raise PilotError("invalid pilot tasks")
        ids = tuple(task.task_id for task in self.tasks)
        if ids != TASK_IDS or len(set(ids)) != len(ids):
            raise PilotError("fixed task graph required")
        known = set(ids)
        if any(dependency not in known for task in self.tasks for dependency in task.depends_on):
            raise PilotError("unknown dependency")
        _reject_cycles(self.tasks)
        implementers = {task.assignee for task in self.tasks if task.role in {"design", "implement", "verify"}}
        for task in self.tasks:
            if task.role in {"review", "completion"} and task.assignee in implementers:
                raise PilotError("independent authority required")
        digest = hashlib.sha256(self.canonical_json(include_hash=False).encode()).hexdigest()
        if self.manifest_hash and self.manifest_hash != digest:
            raise PilotError("manifest hash mismatch")
        object.__setattr__(self, "manifest_hash", digest)

    def payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        value = {
            "pilot_id": self.pilot_id,
            "project_id": self.project_id,
            "root": self.root,
            "generation": self.generation,
            "tasks": [task.payload() for task in self.tasks],
        }
        if include_hash:
            value["manifest_hash"] = self.manifest_hash
        return value

    def canonical_json(self, *, include_hash: bool = True) -> str:
        return json.dumps(self.payload(include_hash=include_hash), sort_keys=True, separators=(",", ":"))

    def task(self, task_id: str) -> PilotTask:
        try:
            return next(task for task in self.tasks if task.task_id == task_id)
        except StopIteration as exc:
            raise PilotError("unknown task") from exc


def _validate_relative(value: Any) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise PilotError("invalid relative path")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise PilotError("invalid relative path")
    return value


def resolve_inside(root: Path, relative: str, *, must_exist: bool = False) -> Path:
    _validate_relative(relative)
    canonical_root = root.resolve(strict=False)
    candidate = (canonical_root / relative).resolve(strict=must_exist)
    try:
        candidate.relative_to(canonical_root)
    except ValueError as exc:
        raise PilotError("pilot path escape") from exc
    return candidate


def snapshot_product(root: Path) -> dict[str, str]:
    """Hash all regular product files, rejecting symlinks and control paths."""
    root = Path(root).resolve(strict=False)
    snapshot: dict[str, str] = {}
    if not root.exists():
        return snapshot
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise PilotError("product symlink rejected")
        if path.is_file():
            snapshot[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return snapshot


def validate_pilot_root(
    root: Path,
    *,
    create: bool = False,
    expected_root: Path = CANONICAL_PILOT_ROOT,
) -> Path:
    root = Path(root)
    expected_root = Path(expected_root)
    if not root.is_absolute() or root != root.resolve(strict=False):
        raise PilotError("canonical pilot root required")
    if root != expected_root:
        raise PilotError("fixed pilot root required")
    if root.exists() and root.is_symlink():
        raise PilotError("symlink pilot root rejected")
    if create:
        root.mkdir(parents=True, exist_ok=True)
    return root


def _reject_cycles(tasks: tuple[PilotTask, ...]) -> None:
    graph = {task.task_id: task.depends_on for task in tasks}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visiting:
            raise PilotError("dependency cycle")
        if task_id in visited:
            return
        visiting.add(task_id)
        for dependency in graph[task_id]:
            visit(dependency)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in graph:
        visit(task_id)


__all__ = [
    "CANONICAL_CONTROL_ROOT",
    "CANONICAL_PILOT_ROOT",
    "DEADLINE_SECONDS",
    "MAX_CONCURRENCY",
    "MAX_GLOBAL_RETRIES",
    "MAX_RESULT_BYTES",
    "MAX_TASK_ATTEMPTS",
    "MAX_TASKS",
    "PILOT_ID",
    "PROJECT_ID",
    "PilotError",
    "PilotManifest",
    "PilotTask",
    "TASK_IDS",
    "TaskStatus",
    "resolve_inside",
    "snapshot_product",
    "validate_pilot_root",
]
