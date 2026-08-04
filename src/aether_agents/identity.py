"""Project-scoped coordination identity and shared validation error."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from os import PathLike
from pathlib import Path
from typing import Any

_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]{7,127}$")
_NAME = re.compile(r"^[a-z][a-z0-9._:/-]{0,127}$")


class ValidationError(ValueError):
    """Raised when a coordination value is malformed."""


class IdentityError(ValidationError):
    """Raised when a project, profile, or execution identity is invalid."""


class IdentityMismatchError(IdentityError):
    """Raised when an asserted or recorded identity differs from the active one."""


class ExecutionDomain(str, Enum):
    """Explicit boundary between real and synthetic execution."""

    LIVE = "live"
    SYNTHETIC = "synthetic"


def _name(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _NAME.fullmatch(value) or value != value.strip():
        raise ValidationError(f"invalid {label}")
    return value


def _id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value) or value != value.strip():
        raise ValidationError(f"invalid {label}")
    return value


def _fields(value: Any, expected: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValidationError(f"invalid {label} fields")


@dataclass(frozen=True, slots=True)
class Principal:
    project_id: str
    owner_id: str
    actor_id: str

    def __post_init__(self) -> None:
        project = _id(self.project_id, "project")
        owner = _name(self.owner_id, "owner")
        actor = _name(self.actor_id, "actor")
        if owner == actor:
            raise ValidationError("owner and actor must remain separate")
        object.__setattr__(self, "project_id", project)
        object.__setattr__(self, "owner_id", owner)
        object.__setattr__(self, "actor_id", actor)

    def to_dict(self) -> dict[str, str]:
        return {"project_id": self.project_id, "owner_id": self.owner_id, "actor_id": self.actor_id}

    @classmethod
    def from_dict(cls, value: Any) -> Principal:
        _fields(value, {"project_id", "owner_id", "actor_id"}, "principal")
        return cls(value["project_id"], value["owner_id"], value["actor_id"])


def _canonical_directory(value: str | PathLike[str], label: str) -> Path:
    if not isinstance(value, (str, PathLike)):
        raise IdentityError(f"invalid {label}")
    try:
        candidate = Path(value).expanduser()
    except (OSError, TypeError, ValueError) as exc:
        raise IdentityError(f"invalid {label}") from exc
    if not candidate.is_absolute():
        raise IdentityError(f"{label} must be absolute")
    try:
        canonical = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise IdentityError(f"{label} does not exist") from exc
    if not canonical.is_dir():
        raise IdentityError(f"{label} is not a directory")
    return canonical


def _path_identity(prefix: str, path: Path) -> str:
    digest = sha256(str(path).encode("utf-8", errors="strict")).hexdigest()
    return f"{prefix}:sha256:{digest}"


@dataclass(frozen=True, slots=True)
class ProjectIdentity:
    """Canonical project directory and its process-local stable identity."""

    root: Path
    project_id: str
    repository: bool

    def __post_init__(self) -> None:
        canonical = _canonical_directory(self.root, "project root")
        repository = (canonical / ".git").exists()
        if canonical != self.root or not isinstance(self.repository, bool) or self.repository != repository:
            raise IdentityError("invalid project identity root")
        if self.project_id != _path_identity("project", canonical):
            raise IdentityError("invalid project identity digest")


@dataclass(frozen=True, slots=True)
class ProfileIdentity:
    """Canonical Hermes profile directory, separate from project identity."""

    home: Path
    profile_id: str
    name: str

    def __post_init__(self) -> None:
        canonical = _canonical_directory(self.home, "profile home")
        try:
            name = _name(canonical.name, "profile")
        except ValidationError as exc:
            raise IdentityError("invalid profile name") from exc
        if canonical != self.home or self.name != name:
            raise IdentityError("invalid profile identity home")
        if self.profile_id != _path_identity("profile", canonical):
            raise IdentityError("invalid profile identity digest")


@dataclass(frozen=True, slots=True)
class IdentityBinding:
    """Exact product identity bound to an explicit execution domain."""

    project: ProjectIdentity
    profile: ProfileIdentity
    execution_domain: ExecutionDomain


def resolve_project_identity(
    project_root: str | PathLike[str], *, require_repository: bool = True
) -> ProjectIdentity:
    """Resolve one absolute project root without creating or repairing it."""

    root = _canonical_directory(project_root, "project root")
    repository = (root / ".git").exists()
    if require_repository and not repository:
        raise IdentityError("project root is not a repository")
    return ProjectIdentity(root=root, project_id=_path_identity("project", root), repository=repository)


def resolve_profile_identity(hermes_home: str | PathLike[str]) -> ProfileIdentity:
    """Resolve an existing Hermes profile/home directory without fallback."""

    home = _canonical_directory(hermes_home, "profile home")
    try:
        name = _name(home.name, "profile")
    except ValidationError as exc:
        raise IdentityError("invalid profile name") from exc
    return ProfileIdentity(home=home, profile_id=_path_identity("profile", home), name=name)


def confirm_recorded_project_root(recorded_root: Any, active: ProjectIdentity) -> Path:
    """Treat persisted project_root as an assertion, never as current authority."""

    if not isinstance(active, ProjectIdentity):
        raise IdentityError("invalid active project identity")
    recorded = resolve_project_identity(recorded_root, require_repository=active.repository)
    if recorded != active:
        raise IdentityMismatchError("recorded project root does not match active project")
    return active.root


def bind_identity(
    *,
    project_root: str | PathLike[str],
    hermes_home: str | PathLike[str],
    execution_domain: ExecutionDomain,
    allowed_project_roots: tuple[str | PathLike[str], ...] = (),
) -> IdentityBinding:
    """Bind project, profile, and execution domain with optional allowlisting."""

    if not isinstance(execution_domain, ExecutionDomain):
        raise IdentityError("execution domain must be explicit")
    project = resolve_project_identity(project_root)
    if allowed_project_roots:
        allowed = {
            resolve_project_identity(candidate).root
            for candidate in allowed_project_roots
        }
        if project.root not in allowed:
            raise IdentityMismatchError("project root is not allowlisted")
    return IdentityBinding(
        project=project,
        profile=resolve_profile_identity(hermes_home),
        execution_domain=execution_domain,
    )


__all__ = [
    "ExecutionDomain",
    "IdentityBinding",
    "IdentityError",
    "IdentityMismatchError",
    "Principal",
    "ProfileIdentity",
    "ProjectIdentity",
    "ValidationError",
    "bind_identity",
    "confirm_recorded_project_root",
    "resolve_profile_identity",
    "resolve_project_identity",
]
