"""Trusted coordinator identity and isolated project admission for M2.3."""

from __future__ import annotations

import os
import re
import sqlite3
import stat
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, NoReturn

_CAPTURE_POLICIES = {"DISABLED": 0, "STRUCTURED_ONLY": 1, "FULL_EPISODE": 2}
_ALIAS_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SCHEMA_VERSION = 1


class AdmissionError(ValueError):
    """Stable project-admission failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> NoReturn:
    raise AdmissionError(code, message)


def _canonical_uuid(value: str, *, code: str) -> str:
    try:
        parsed = uuid.UUID(value)
    except (TypeError, ValueError, AttributeError):
        _fail(code, "Identity is not a canonical UUID")
    if str(parsed) != value:
        _fail(code, "Identity is not canonical")
    return value


def _has_symlink_component(path: Path) -> bool:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            if current.is_symlink():
                return True
        except OSError:
            return True
    return False


def _canonical_existing_directory(value: str | Path, *, code: str) -> Path:
    path = Path(value)
    if not path.is_absolute() or _has_symlink_component(path):
        _fail(code, "Path must be absolute, canonical, and symlink-free")
    try:
        resolved = path.resolve(strict=True)
        info = resolved.stat(follow_symlinks=False)
    except OSError:
        _fail(code, "Path is unavailable")
    if path != resolved or not stat.S_ISDIR(info.st_mode):
        _fail(code, "Path must name one canonical directory")
    return resolved


def _git(*args: str, cwd: Path) -> str:
    try:
        completed = subprocess.run(
            ("git", *args),
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        _fail("PROJECT_NOT_ADMITTED", "Project is not an available Git worktree")
    result = completed.stdout.strip()
    if not result:
        _fail("PROJECT_NOT_ADMITTED", "Project identity is unavailable")
    return result


def _git_identity(project_root: Path) -> tuple[Path, Path, os.stat_result, os.stat_result]:
    top = _canonical_existing_directory(_git("rev-parse", "--show-toplevel", cwd=project_root), code="PROJECT_IDENTITY_MISMATCH")
    if top != project_root:
        _fail("PROJECT_IDENTITY_MISMATCH", "Admission requires the exact worktree root")
    common_raw = Path(_git("rev-parse", "--git-common-dir", cwd=project_root))
    common_candidate = common_raw if common_raw.is_absolute() else project_root / common_raw
    common = common_candidate.resolve(strict=True)
    if _has_symlink_component(common) or not common.is_dir():
        _fail("PROJECT_IDENTITY_MISMATCH", "Git common directory is not trustworthy")
    return top, common, top.stat(follow_symlinks=False), common.stat(follow_symlinks=False)


@dataclass(frozen=True)
class TrustedLaunchContext:
    principal_id: str
    hermes_home: Path
    profile_id: str
    session_id: str

    @classmethod
    def from_environment(cls, environment: Mapping[str, str]) -> "TrustedLaunchContext":
        required = (
            "AETHER_COORDINATOR_PRINCIPAL",
            "HERMES_HOME",
            "AETHER_PROFILE",
            "AETHER_SESSION_ID",
        )
        if any(not environment.get(name) for name in required):
            _fail("PRINCIPAL_UNAUTHENTICATED", "Coordinator trusted launch context is incomplete")
        principal_id = _canonical_uuid(environment[required[0]], code="PRINCIPAL_UNAUTHENTICATED")
        session_id = _canonical_uuid(environment[required[3]], code="PRINCIPAL_UNAUTHENTICATED")
        home = _canonical_existing_directory(environment[required[1]], code="PRINCIPAL_UNAUTHENTICATED")
        profile = environment[required[2]]
        if not _ALIAS_RE.fullmatch(profile):
            _fail("PRINCIPAL_UNAUTHENTICATED", "Coordinator profile identity is invalid")
        return cls(principal_id=principal_id, hermes_home=home, profile_id=profile, session_id=session_id)


@dataclass(frozen=True)
class ProjectPlacement:
    placement_id: str
    project_root: Path


@dataclass(frozen=True)
class ProjectAdmission:
    project_id: str
    project_root: Path
    repository_root: Path
    profile_id: str
    safe_alias: str | None
    capture_policy: str
    consent_authority_ref: str
    placements: tuple[ProjectPlacement, ...]


class ProjectAdmissionRegistry:
    """SQLite admission registry stored outside admitted project roots."""

    def __init__(self, root: Path) -> None:
        if root.is_symlink():
            _fail("PROJECT_IDENTITY_MISMATCH", "Admission state root cannot be a symlink")
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(root, 0o700)
        self.root = root.resolve(strict=True)
        self.path = self.root / "admissions.sqlite3"
        self._migrate()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _migrate(self) -> None:
        try:
            with self._connect() as connection:
                version = int(connection.execute("PRAGMA user_version").fetchone()[0])
                if version > _SCHEMA_VERSION:
                    _fail("PROJECT_IDENTITY_MISMATCH", "Admission schema is newer than this build")
                if version == 0:
                    connection.execute("BEGIN IMMEDIATE")
                    connection.execute(
                        """CREATE TABLE projects (
                            project_id TEXT PRIMARY KEY,
                            principal_id TEXT NOT NULL,
                            hermes_home TEXT NOT NULL,
                            profile_id TEXT NOT NULL,
                            repository_root TEXT NOT NULL,
                            repository_device INTEGER NOT NULL,
                            repository_inode INTEGER NOT NULL,
                            safe_alias TEXT,
                            capture_policy TEXT NOT NULL,
                            consent_authority_ref TEXT NOT NULL,
                            UNIQUE(principal_id, hermes_home, profile_id, repository_root)
                        )"""
                    )
                    connection.execute(
                        """CREATE TABLE placements (
                            placement_id TEXT PRIMARY KEY,
                            project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
                            project_root TEXT NOT NULL,
                            root_device INTEGER NOT NULL,
                            root_inode INTEGER NOT NULL,
                            UNIQUE(project_id, project_root)
                        )"""
                    )
                    connection.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")
                    connection.commit()
            os.chmod(self.path, 0o600)
        except AdmissionError:
            raise
        except sqlite3.Error:
            _fail("PROJECT_IDENTITY_MISMATCH", "Admission store could not be initialized safely")

    @staticmethod
    def _validate_inputs(safe_alias: str | None, capture_policy: str, consent_authority_ref: str) -> None:
        if safe_alias is not None and not _ALIAS_RE.fullmatch(safe_alias):
            _fail("PROJECT_NOT_ADMITTED", "Project safe alias is invalid")
        if capture_policy not in _CAPTURE_POLICIES:
            _fail("PROJECT_NOT_ADMITTED", "Capture policy is invalid")
        if not consent_authority_ref or len(consent_authority_ref.encode("utf-8")) > 512:
            _fail("PROJECT_NOT_ADMITTED", "Consent authority reference is invalid")

    def admit(
        self,
        *,
        context: TrustedLaunchContext,
        project_root: Path,
        safe_alias: str | None,
        capture_policy: str,
        consent_authority_ref: str,
    ) -> ProjectAdmission:
        if not isinstance(context, TrustedLaunchContext):
            _fail("PRINCIPAL_UNAUTHENTICATED", "Coordinator trusted launch context is required")
        self._validate_inputs(safe_alias, capture_policy, consent_authority_ref)
        root = _canonical_existing_directory(project_root, code="PROJECT_NOT_ADMITTED")
        top, common, root_info, common_info = _git_identity(root)
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    """SELECT * FROM projects
                       WHERE principal_id=? AND hermes_home=? AND profile_id=? AND repository_root=?""",
                    (context.principal_id, str(context.hermes_home), context.profile_id, str(common)),
                ).fetchone()
                if row is None:
                    project_id = str(uuid.uuid4())
                    connection.execute(
                        "INSERT INTO projects VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            project_id,
                            context.principal_id,
                            str(context.hermes_home),
                            context.profile_id,
                            str(common),
                            common_info.st_dev,
                            common_info.st_ino,
                            safe_alias,
                            capture_policy,
                            consent_authority_ref,
                        ),
                    )
                else:
                    project_id = row["project_id"]
                    if _CAPTURE_POLICIES[capture_policy] > _CAPTURE_POLICIES[row["capture_policy"]]:
                        _fail("CAPTURE_POLICY_ESCALATION", "Capture policy cannot be escalated by replay")
                placement = connection.execute(
                    "SELECT placement_id FROM placements WHERE project_id=? AND project_root=?",
                    (project_id, str(top)),
                ).fetchone()
                if placement is None:
                    connection.execute(
                        "INSERT INTO placements VALUES (?, ?, ?, ?, ?)",
                        (str(uuid.uuid4()), project_id, str(top), root_info.st_dev, root_info.st_ino),
                    )
                connection.commit()
        except AdmissionError:
            raise
        except sqlite3.Error:
            _fail("PROJECT_NOT_ADMITTED", "Project admission could not be committed")
        return self.inspect(context=context, project_id=project_id)

    def inspect(self, *, context: TrustedLaunchContext, project_id: str) -> ProjectAdmission:
        if not isinstance(context, TrustedLaunchContext):
            _fail("PRINCIPAL_UNAUTHENTICATED", "Coordinator trusted launch context is required")
        _canonical_uuid(project_id, code="PROJECT_NOT_ADMITTED")
        with self._connect() as connection:
            row = connection.execute(
                """SELECT * FROM projects WHERE project_id=? AND principal_id=?
                   AND hermes_home=? AND profile_id=?""",
                (project_id, context.principal_id, str(context.hermes_home), context.profile_id),
            ).fetchone()
            if row is None:
                _fail("PROJECT_NOT_ADMITTED", "No project is admitted for this coordinator")
            placements = connection.execute(
                "SELECT * FROM placements WHERE project_id=? ORDER BY placement_id", (project_id,)
            ).fetchall()
        try:
            common = Path(row["repository_root"]).resolve(strict=True)
            common_info = common.stat(follow_symlinks=False)
        except OSError:
            _fail("PROJECT_IDENTITY_MISMATCH", "Admitted repository identity is unavailable")
        if (common_info.st_dev, common_info.st_ino) != (row["repository_device"], row["repository_inode"]):
            _fail("PROJECT_IDENTITY_MISMATCH", "Admitted repository identity changed")
        admitted_placements: list[ProjectPlacement] = []
        for placement in placements:
            try:
                root = Path(placement["project_root"]).resolve(strict=True)
                root_info = root.stat(follow_symlinks=False)
                _, observed_common, _, _ = _git_identity(root)
            except (OSError, AdmissionError):
                _fail("PROJECT_IDENTITY_MISMATCH", "Admitted worktree identity changed")
            if (
                (root_info.st_dev, root_info.st_ino) != (placement["root_device"], placement["root_inode"])
                or observed_common != common
            ):
                _fail("PROJECT_IDENTITY_MISMATCH", "Admitted worktree identity changed")
            admitted_placements.append(ProjectPlacement(placement["placement_id"], root))
        primary = admitted_placements[0].project_root
        return ProjectAdmission(
            project_id=row["project_id"],
            project_root=primary,
            repository_root=common,
            profile_id=row["profile_id"],
            safe_alias=row["safe_alias"],
            capture_policy=row["capture_policy"],
            consent_authority_ref=row["consent_authority_ref"],
            placements=tuple(admitted_placements),
        )
