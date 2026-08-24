"""Atomic, release-locked lifecycle for the Aether observer.

This module is deliberately Hermes-import free.  It owns only product release state;
native project/session/observation state remains outside every release directory and is
therefore preserved across update and rollback.
"""

from __future__ import annotations

import ast
import configparser
import email.parser
import hashlib
import importlib.resources
import io
import json
import os
import re
import secrets
import shutil
import sqlite3
import stat
import subprocess
import tarfile
import tempfile
import threading
import zipfile
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path, PurePosixPath
from typing import Any, Iterator

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError, ValidationError

from aether_agents.observation.checkpoint import AuthorityContext
from aether_agents.observation.contracts import (
    EVENT_SCHEMA_VERSION,
    MANIFEST_SCHEMA_VERSION,
    READ_MODEL_SCHEMA,
    SUMMARY_SCHEMA_VERSION,
    SUPPORTED_EVENT_SCHEMA_VERSIONS,
    validate_summary,
)
from aether_agents.observation.identity import summary_id as canonical_summary_id
from aether_agents.observation.privacy import assert_clean
from aether_agents.paths import (
    DIR_MODE,
    FILE_MODE,
    UnsafeObservationPath,
    _open_private_directory,
    ensure_private_dir,
    harden_file,
    read_private_bytes,
)

__all__ = [
    "AetherPrebuildIdentity",
    "HERMES_BASELINE",
    "CheckoutEvidence",
    "DoctorResult",
    "HermesBaseline",
    "IntegrityError",
    "LifecycleManager",
    "OBSERVATION_COMPATIBILITY",
    "PreparedRelease",
    "ReleaseRecord",
    "ReleaseStore",
    "ValidatedReleaseLock",
    "UninstallResult",
    "verify_clean_checkout",
    "load_aether_prebuild_identity",
    "load_release_lock",
]


class IntegrityError(RuntimeError):
    """A candidate or local transition cannot be proven coherent."""


@dataclass(frozen=True, slots=True)
class HermesBaseline:
    repository: str
    tag: str
    tag_object: str
    commit: str
    distribution: str
    version: str
    python_requires: str
    observer_entry_point: str


HERMES_BASELINE = HermesBaseline(
    repository="https://github.com/NousResearch/hermes-agent.git",
    tag="v2026.8.18",
    tag_object="9f13bbbf8423427e159c78066356ca0e27ca6b74",
    commit="e624e9fde561e1add9388384012b295fde669ade",
    distribution="hermes-agent",
    version="0.20.4",
    python_requires=">=3.11,<3.14",
    observer_entry_point=(
        "aether-contract-observer=aether_agents.observation.capture.hermes_plugin"
    ),
)


OBSERVER_ENTRY_POINT: dict[str, str] = {
    "plugin_name": "aether-contract-observer",
    "group": "hermes_agent.plugins",
    "target": "aether_agents.observation.capture.hermes_plugin",
}


@dataclass(frozen=True, slots=True)
class AetherPrebuildIdentity:
    """Non-circular Aether source tuple authenticated before wheel installation."""

    distribution: str
    package_version: str
    git_tag: str
    git_commit: str
    python_requires: str
    observer: dict[str, str]

    @classmethod
    def from_record(cls, value: Any) -> "AetherPrebuildIdentity":
        expected = {
            "distribution",
            "package_version",
            "git_tag",
            "git_commit",
            "python_requires",
            "observer",
        }
        if not isinstance(value, dict) or set(value) != expected:
            raise IntegrityError("Aether prebuild identity shape is invalid")
        if value.get("distribution") != "aether-agents":
            raise IntegrityError("Aether prebuild distribution mismatch")
        package_version = value.get("package_version")
        if not isinstance(package_version, str) or not _VERSION_RE.fullmatch(package_version):
            raise IntegrityError("Aether prebuild package version is invalid")
        git_tag = value.get("git_tag")
        if not isinstance(git_tag, str) or not re.fullmatch(
            r"v[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z][0-9A-Za-z.-]*)?", git_tag
        ):
            raise IntegrityError("Aether prebuild Git tag is invalid")
        git_commit = value.get("git_commit")
        if not isinstance(git_commit, str) or not re.fullmatch(
            r"[0-9a-f]{40}(?:[0-9a-f]{24})?", git_commit
        ):
            raise IntegrityError("Aether prebuild Git commit is invalid")
        if value.get("python_requires") != HERMES_BASELINE.python_requires:
            raise IntegrityError("Aether prebuild Python range mismatch")
        if value.get("observer") != OBSERVER_ENTRY_POINT:
            raise IntegrityError("Aether prebuild observer tuple mismatch")
        return cls(
            distribution="aether-agents",
            package_version=package_version,
            git_tag=git_tag,
            git_commit=git_commit,
            python_requires=HERMES_BASELINE.python_requires,
            observer=dict(OBSERVER_ENTRY_POINT),
        )

    def to_record(self) -> dict[str, Any]:
        return {
            "distribution": self.distribution,
            "package_version": self.package_version,
            "git_tag": self.git_tag,
            "git_commit": self.git_commit,
            "python_requires": self.python_requires,
            "observer": dict(self.observer),
        }

    @property
    def digest(self) -> str:
        encoded = json.dumps(self.to_record(), sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class ValidatedReleaseLock:
    """Fully validated external lock plus the local materialization boundary."""

    path: Path
    raw_bytes: bytes
    sha256: str
    aether_identity: AetherPrebuildIdentity
    observer_requirements_sha256: str
    hermes_source_tree_sha256: str
    profile_bundle_sha256: str
    observation_compatibility: dict[str, Any]


def _release_lock_schema() -> dict[str, Any]:
    packaged = importlib.resources.files("aether_agents").joinpath(
        "resources/schemas/release-lock.schema.json"
    )
    try:
        data = packaged.read_bytes()
    except (FileNotFoundError, OSError):
        # Editable source checkouts do not materialize Hatch force-includes.  This is
        # the same canonical file which Hatch places at ``packaged`` in a wheel.
        source = (
            Path(__file__).resolve().parents[2]
            / "specs"
            / "001-aether-v1-productization"
            / "contracts"
            / "release-lock.schema.json"
        )
        try:
            try:
                data = read_private_bytes(source)
            except (OSError, ValueError) as error:
                raise IntegrityError("packaged profile resource is unreadable") from error
        except OSError as error:
            raise IntegrityError("packaged release-lock schema is unavailable") from error
    try:
        schema = json.loads(data)
        Draft202012Validator.check_schema(schema)
    except (json.JSONDecodeError, UnicodeError, SchemaError) as error:
        raise IntegrityError("packaged release-lock schema is invalid") from error
    if not isinstance(schema, dict):
        raise IntegrityError("packaged release-lock schema is invalid")
    return schema


def _read_release_lock_bytes(path: Path | str) -> tuple[Path, bytes]:
    candidate = Path(path).expanduser()
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(candidate, flags)
    except OSError as error:
        raise IntegrityError("release lock is unavailable or unsafe") from error
    try:
        status = os.fstat(descriptor)
        if not stat.S_ISREG(status.st_mode) or status.st_size > 1024 * 1024:
            raise IntegrityError("release lock must be one bounded regular file")
        blocks: list[bytes] = []
        remaining = status.st_size
        while remaining:
            block = os.read(descriptor, min(65536, remaining))
            if not block:
                raise IntegrityError("release lock changed while being read")
            blocks.append(block)
            remaining -= len(block)
        if os.read(descriptor, 1):
            raise IntegrityError("release lock changed while being read")
        return candidate.absolute(), b"".join(blocks)
    finally:
        os.close(descriptor)


def load_release_lock(path: Path | str) -> ValidatedReleaseLock:
    """Validate every schema-3 field and the exact A1/Hermes semantic tuple."""

    candidate, raw_bytes = _read_release_lock_bytes(path)
    try:
        payload = json.loads(raw_bytes)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise IntegrityError("release lock is unavailable or malformed") from error
    schema = _release_lock_schema()
    errors = sorted(
        Draft202012Validator(
            schema,
            format_checker=FormatChecker(),
        ).iter_errors(payload),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        raise IntegrityError("release lock schema is invalid")
    assert isinstance(payload, dict)
    aether = payload.get("aether")
    assert isinstance(aether, dict)
    display_version = aether.get("version")
    if not isinstance(display_version, str) or not _VERSION_RE.fullmatch(display_version):
        raise IntegrityError("release lock Aether version is invalid")
    observation_compatibility = _validate_observation_compatibility(
        aether.get("observation_compatibility")
    )
    identity = AetherPrebuildIdentity.from_record(
        {key: aether[key] for key in AetherPrebuildIdentity.__dataclass_fields__}
    )
    observer_requirements_sha256 = aether.get("observer_requirements_sha256")
    assert isinstance(observer_requirements_sha256, str)
    hermes = payload.get("hermes")
    assert isinstance(hermes, dict)
    expected_hermes = {
        "source_mode": "upstream",
        "repository": HERMES_BASELINE.repository.removesuffix(".git"),
        "version": HERMES_BASELINE.version,
        "tag": HERMES_BASELINE.tag,
        "commit": HERMES_BASELINE.commit,
        "python_requires": HERMES_BASELINE.python_requires,
    }
    if any(hermes.get(key) != value for key, value in expected_hermes.items()):
        raise IntegrityError("release lock does not select the exact Hermes baseline")
    hermes_source_tree_sha256 = hermes.get("source_tree_sha256")
    assert isinstance(hermes_source_tree_sha256, str)
    profile_bundle = payload.get("profile_bundle")
    assert isinstance(profile_bundle, dict)
    if profile_bundle.get("version") != "1":
        raise IntegrityError("release lock profile bundle version mismatch")
    profile_bundle_sha256 = profile_bundle.get("sha256")
    assert isinstance(profile_bundle_sha256, str)
    return ValidatedReleaseLock(
        path=candidate,
        raw_bytes=raw_bytes,
        sha256=hashlib.sha256(raw_bytes).hexdigest(),
        aether_identity=identity,
        observer_requirements_sha256=observer_requirements_sha256,
        hermes_source_tree_sha256=hermes_source_tree_sha256,
        profile_bundle_sha256=profile_bundle_sha256,
        observation_compatibility=observation_compatibility,
    )


def load_aether_prebuild_identity(path: Path | str) -> AetherPrebuildIdentity:
    """Return the Aether tuple only after validating the complete release lock."""

    return load_release_lock(path).aether_identity


# A1-FR-021d: this is the one exact compatibility declaration carried by every
# schema-3 local release record.  Lists intentionally mirror the JSON release-lock
# contract instead of using a looser internal representation.
OBSERVATION_COMPATIBILITY: dict[str, Any] = {
    "event_write_version": EVENT_SCHEMA_VERSION,
    "event_read_versions": list(SUPPORTED_EVENT_SCHEMA_VERSIONS),
    "summary_write_version": SUMMARY_SCHEMA_VERSION,
    "summary_read_versions": [SUMMARY_SCHEMA_VERSION],
    "segment_manifest_write_version": MANIFEST_SCHEMA_VERSION,
    "segment_manifest_read_versions": [MANIFEST_SCHEMA_VERSION],
    "projection_schema_version": READ_MODEL_SCHEMA,
}


def _compatibility_copy() -> dict[str, Any]:
    return json.loads(json.dumps(OBSERVATION_COMPATIBILITY))


def _validate_observation_compatibility(value: Any) -> dict[str, Any]:
    """Validate one target-owned schema declaration without assuming local versions."""

    expected_keys = {
        "event_write_version",
        "event_read_versions",
        "summary_write_version",
        "summary_read_versions",
        "segment_manifest_write_version",
        "segment_manifest_read_versions",
        "projection_schema_version",
    }
    if not isinstance(value, dict) or set(value) != expected_keys:
        raise IntegrityError("observation compatibility declaration mismatch")
    patterns = {
        "event": re.compile(r"^aether\.observation\.event\.v[1-9][0-9]*$", re.ASCII),
        "summary": re.compile(r"^aether\.observation\.summary\.v[1-9][0-9]*$", re.ASCII),
        "segment_manifest": re.compile(
            r"^aether\.observation\.segment-manifest\.v[1-9][0-9]*$",
            re.ASCII,
        ),
    }
    for prefix, pattern in patterns.items():
        write = value.get(f"{prefix}_write_version")
        reads = value.get(f"{prefix}_read_versions")
        if (
            not isinstance(write, str)
            or pattern.fullmatch(write) is None
            or not isinstance(reads, list)
            or not reads
            or any(not isinstance(item, str) or pattern.fullmatch(item) is None for item in reads)
            or len(set(reads)) != len(reads)
            or write not in reads
        ):
            raise IntegrityError("observation compatibility write version is not readable")
    projection = value.get("projection_schema_version")
    if (
        not isinstance(projection, str)
        or re.fullmatch(
            r"aether\.observation\.projection\.v[1-9][0-9]*",
            projection,
            re.ASCII,
        )
        is None
    ):
        raise IntegrityError("observation compatibility projection version is invalid")
    return json.loads(json.dumps(value))


def _projection_schema_ordinal(compatibility: dict[str, Any]) -> int:
    projection = _validate_observation_compatibility(compatibility)["projection_schema_version"]
    return int(projection.rsplit(".v", 1)[1])


@dataclass(frozen=True, slots=True)
class CheckoutEvidence:
    path: Path
    tag: str
    tag_object: str | None
    commit: str
    clean: bool


def _git(checkout: Path, *arguments: str, check: bool = True) -> str:
    completed = subprocess.run(
        ["git", "-C", str(checkout), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    if check and completed.returncode != 0:
        raise IntegrityError(
            f"Hermes checkout inspection failed ({arguments[0]} exit {completed.returncode})"
        )
    return completed.stdout.strip()


def verify_clean_checkout(
    checkout: Path | str,
    *,
    expected_tag: str = HERMES_BASELINE.tag,
    expected_commit: str = HERMES_BASELINE.commit,
    expected_tag_object: str | None = None,
) -> CheckoutEvidence:
    """Prove a checkout is the requested immutable tag/commit and is clean."""

    path = Path(checkout).resolve(strict=True)
    if not path.is_dir():
        raise IntegrityError("Hermes checkout is not a directory")
    commit = _git(path, "rev-parse", "HEAD")
    if commit != expected_commit:
        raise IntegrityError(
            f"Hermes checkout commit mismatch: expected {expected_commit}, got {commit}"
        )
    tag_commit = _git(path, "rev-list", "-n", "1", expected_tag)
    if tag_commit != expected_commit:
        raise IntegrityError("Hermes tag does not dereference to the expected commit")
    tag_object_output = _git(path, "rev-parse", f"{expected_tag}^{{tag}}", check=False)
    tag_object = tag_object_output or None
    if expected_tag_object is not None and tag_object != expected_tag_object:
        raise IntegrityError("Hermes annotated tag object mismatch")
    dirty = _git(path, "status", "--porcelain=v1", "--untracked-files=all")
    if dirty:
        raise IntegrityError("Hermes checkout is dirty")
    return CheckoutEvidence(
        path=path,
        tag=expected_tag,
        tag_object=tag_object,
        commit=commit,
        clean=True,
    )


_VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[A-Za-z0-9_.-]{0,48})?$")
_RELEASE_ID_RE = re.compile(r"^[0-9A-Za-z][0-9A-Za-z_.-]{0,95}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_TRANSITION_ID_RE = re.compile(r"^trn_[0-9a-f]{32}$")
_PROJECT_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.ASCII,
)
_PROJECTION_POINTER_NAME_RE = re.compile(
    r"^aether\.observation\.projection\.v[1-9][0-9]*\.sqlite3$",
    re.ASCII,
)
_PROFILE_ROLES = ("morfeo", "supervisor", "implementer")
_OBSERVER_RUNTIME_DEPENDENCIES = {"jsonschema": "4.26.0"}
_OBSERVER_LOCKED_DISTRIBUTIONS = {
    "attrs": "26.1.0",
    "jsonschema": "4.26.0",
    "jsonschema-specifications": "2025.9.1",
    "referencing": "0.37.0",
    "rpds-py": "2026.6.3",
    "typing-extensions": "4.16.0",
}
_OWNERSHIP_MARKER = "installation.json"
_LOCAL_LOCKS_GUARD = threading.Lock()
_LOCAL_LOCKS: dict[str, threading.RLock] = {}
_LOCK_STATE = threading.local()
_CAS_UNSET = object()


def _observer_locked_distributions_for_version(
    version: tuple[int, int],
) -> dict[str, str]:
    """Return the hash-locked closure whose markers apply to one interpreter."""

    if version not in {(3, 11), (3, 12), (3, 13)}:
        raise IntegrityError("observer dependency interpreter version is unsupported")
    effective = dict(_OBSERVER_LOCKED_DISTRIBUTIONS)
    if version >= (3, 13):
        effective.pop("typing-extensions")
    return effective


def _observer_locked_distributions_for_python(python: Path) -> dict[str, str]:
    """Evaluate the packaged requirement markers against the target environment."""

    try:
        completed = subprocess.run(
            [
                str(python),
                "-c",
                "import sys;print(f'{sys.version_info.major}.{sys.version_info.minor}')",
            ],
            check=False,
            capture_output=True,
            text=True,
            env=_isolated_subprocess_environment(),
        )
    except OSError as error:
        raise IntegrityError("observer dependency interpreter is unavailable") from error
    match = re.fullmatch(r"(?P<major>[0-9]+)\.(?P<minor>[0-9]+)\n?", completed.stdout)
    if completed.returncode != 0 or match is None:
        raise IntegrityError("observer dependency interpreter version is unavailable")
    version = (int(match.group("major")), int(match.group("minor")))
    return _observer_locked_distributions_for_version(version)


def _local_mutation_lock(key: str) -> threading.RLock:
    with _LOCAL_LOCKS_GUARD:
        return _LOCAL_LOCKS.setdefault(key, threading.RLock())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _validate_observer_requirements(data: bytes) -> dict[str, str]:
    """Validate the packaged pip lock with a deliberately closed grammar."""

    if not data or len(data) > 128 * 1024 or not data.endswith(b"\n"):
        raise IntegrityError("observer dependency lock is malformed")
    try:
        text = data.decode("ascii")
    except UnicodeError as error:
        raise IntegrityError("observer dependency lock is malformed") from error
    logical: list[str] = []
    pending = ""
    for physical in text.splitlines():
        stripped = physical.strip()
        if not stripped or stripped.startswith("#"):
            if pending:
                raise IntegrityError("observer dependency lock continuation is malformed")
            continue
        continued = stripped.endswith("\\")
        part = stripped[:-1].rstrip() if continued else stripped
        pending = f"{pending} {part}".strip()
        if not continued:
            logical.append(pending)
            pending = ""
    if pending:
        raise IntegrityError("observer dependency lock continuation is malformed")

    observed: dict[str, str] = {}
    pattern = re.compile(
        r"(?P<name>[a-z0-9][a-z0-9-]*)==(?P<version>[0-9A-Za-z][0-9A-Za-z._-]*)"
        r"(?: ; (?P<marker>python_full_version < '3\.13'))?"
        r"(?P<hashes>(?: --hash=sha256:[0-9a-f]{64})+)",
        re.ASCII,
    )
    for requirement in logical:
        match = pattern.fullmatch(requirement)
        if match is None:
            raise IntegrityError("observer dependency lock is not fully hash-bound")
        name = match.group("name")
        if name in observed:
            raise IntegrityError("observer dependency lock has duplicate distributions")
        marker = match.group("marker")
        if (name == "typing-extensions") != (marker is not None):
            raise IntegrityError("observer dependency lock marker mismatch")
        observed[name] = match.group("version")
    if observed != _OBSERVER_LOCKED_DISTRIBUTIONS:
        raise IntegrityError("observer dependency lock closure mismatch")
    return observed


def _remove_hermes_editable_build_debris(source: Path) -> None:
    """Remove only setuptools metadata created by the verified editable build."""

    debris = source / "hermes_agent.egg-info"
    if not debris.exists() and not debris.is_symlink():
        return
    if debris.is_symlink() or not debris.is_dir():
        raise IntegrityError("Hermes editable build debris is unsafe")
    for child in debris.iterdir():
        if (
            child.is_symlink()
            or not child.is_file()
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", child.name)
        ):
            raise IntegrityError("Hermes editable build debris is unsafe")
    _remove_private_tree(debris)
    _fsync_directory(source)


def _wheel_observation_compatibility(source: bytes) -> dict[str, Any]:
    """Read literal target schema identities without importing untrusted wheel code."""

    wanted = {
        "EVENT_SCHEMA_VERSION",
        "SUMMARY_SCHEMA_VERSION",
        "MANIFEST_SCHEMA_VERSION",
        "SUPPORTED_EVENT_SCHEMA_VERSIONS",
        "READ_MODEL_SCHEMA",
    }
    try:
        tree = ast.parse(source.decode("utf-8"))
    except (SyntaxError, UnicodeError) as error:
        raise IntegrityError("candidate observation compatibility source is malformed") from error
    values: dict[str, Any] = {}
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        value_node = node.value
        for target in targets:
            if not isinstance(target, ast.Name) or target.id not in wanted:
                continue
            if target.id in values or value_node is None:
                raise IntegrityError("candidate observation compatibility is ambiguous")
            try:
                values[target.id] = ast.literal_eval(value_node)
            except (TypeError, ValueError) as error:
                raise IntegrityError(
                    "candidate observation compatibility must use literal identities"
                ) from error
    if set(values) != wanted:
        raise IntegrityError("candidate observation compatibility declaration is incomplete")
    event_reads = values["SUPPORTED_EVENT_SCHEMA_VERSIONS"]
    if not isinstance(event_reads, tuple):
        raise IntegrityError("candidate event read set must be a literal tuple")
    return _validate_observation_compatibility(
        {
            "event_write_version": values["EVENT_SCHEMA_VERSION"],
            "event_read_versions": list(event_reads),
            "summary_write_version": values["SUMMARY_SCHEMA_VERSION"],
            "summary_read_versions": [values["SUMMARY_SCHEMA_VERSION"]],
            "segment_manifest_write_version": values["MANIFEST_SCHEMA_VERSION"],
            "segment_manifest_read_versions": [values["MANIFEST_SCHEMA_VERSION"]],
            "projection_schema_version": values["READ_MODEL_SCHEMA"],
        }
    )


def _tree_sha256(root: Path) -> str:
    """Digest a confined regular-file tree by relative path and file bytes."""

    rows: list[tuple[str, str]] = []
    for directory, names, files in os.walk(root, followlinks=False):
        current = Path(directory)
        if current.is_symlink():
            raise IntegrityError("release source tree contains a symlink directory")
        names[:] = sorted(name for name in names if name != "__pycache__")
        for name in sorted(files):
            path = current / name
            if path.is_symlink() or not path.is_file():
                raise IntegrityError("release source tree contains a non-regular file")
            relative = path.relative_to(root).as_posix()
            rows.append((relative, _sha256(path)))
    encoded = json.dumps(rows, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def _archive_member_path(name: str) -> PurePosixPath:
    """Parse one Git archive path with a closed, platform-independent grammar."""

    if (
        not name
        or len(name.encode("utf-8")) > 4096
        or "\\" in name
        or any(ord(character) < 0x20 or ord(character) == 0x7F for character in name)
    ):
        raise IntegrityError("Hermes source archive contains an invalid path")
    relative = PurePosixPath(name)
    if relative.is_absolute() or any(
        part in {"", ".", ".."}
        or len(part.encode("utf-8")) > 255
        or not re.fullmatch(r"[ -~]+", part, re.ASCII)
        for part in relative.parts
    ):
        raise IntegrityError("Hermes source archive path escapes its release root")
    return relative


def _extract_git_archive(archive: bytes, destination: Path) -> None:
    """Extract only confined regular files/directories from an authenticated archive."""

    if destination.exists() or destination.is_symlink():
        raise IntegrityError("Hermes source archive destination already exists")
    try:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as source:
            members = source.getmembers()
            validated: list[tuple[tarfile.TarInfo, PurePosixPath]] = []
            observed: set[str] = set()
            for member in members:
                relative = _archive_member_path(member.name.rstrip("/"))
                canonical = relative.as_posix()
                if canonical in observed:
                    raise IntegrityError("Hermes source archive contains duplicate paths")
                observed.add(canonical)
                if not (member.isdir() or member.isreg()):
                    raise IntegrityError("Hermes source archive contains a non-regular member")
                # ``git archive`` applies its conventional 0002 tar umask: Git
                # 100644/100755 entries appear as 0664/0775 in the archive.
                if member.isreg() and stat.S_IMODE(member.mode) not in (0o664, 0o775):
                    raise IntegrityError("Hermes source archive contains an invalid file mode")
                validated.append((member, relative))

            _extract_validated_members(source, validated, destination)
    except IntegrityError:
        raise
    except (OSError, tarfile.TarError) as error:
        raise IntegrityError("Hermes source archive extraction failed") from error


def _extract_validated_members(
    source: tarfile.TarFile,
    validated: list[tuple[tarfile.TarInfo, PurePosixPath]],
    destination: Path,
) -> None:
    """Extract validated members below retained directory descriptors only."""

    if os.name != "posix":  # pragma: no cover - exercised by platform CI
        destination.mkdir(mode=DIR_MODE)
        for member, relative in validated:
            target = destination.joinpath(*relative.parts)
            if member.isdir():
                target.mkdir(mode=DIR_MODE, parents=True, exist_ok=True)
                continue
            target.parent.mkdir(mode=DIR_MODE, parents=True, exist_ok=True)
            extracted = source.extractfile(member)
            if extracted is None:
                raise IntegrityError("Hermes source archive file is unreadable")
            LifecycleManager._write_durable(target, extracted.read())
        return

    parent_descriptor = _open_private_directory(destination.parent)
    root_descriptor: int | None = None
    try:
        _verify_directory_identity(destination.parent, parent_descriptor)
        os.mkdir(destination.name, DIR_MODE, dir_fd=parent_descriptor)
        root_descriptor = _open_child_directory(parent_descriptor, destination.name)
        os.fchmod(root_descriptor, DIR_MODE)
        _verify_directory_identity(destination.parent, parent_descriptor)
        for member, relative in validated:
            current = os.dup(root_descriptor)
            try:
                directory_parts = relative.parts if member.isdir() else relative.parts[:-1]
                for component in directory_parts:
                    child = _open_or_create_child_directory(current, component)
                    os.close(current)
                    current = child
                if member.isdir():
                    os.fsync(current)
                    continue
                extracted = source.extractfile(member)
                if extracted is None:
                    raise IntegrityError("Hermes source archive file is unreadable")
                name = _safe_entry_name(relative.parts[-1])
                mode = 0o700 if stat.S_IMODE(member.mode) == 0o775 else FILE_MODE
                flags = (
                    os.O_WRONLY
                    | os.O_CREAT
                    | os.O_EXCL
                    | getattr(os, "O_NOFOLLOW", 0)
                    | getattr(os, "O_CLOEXEC", 0)
                )
                descriptor = os.open(name, flags, mode, dir_fd=current)
                try:
                    opened = os.fstat(descriptor)
                    named = os.stat(name, dir_fd=current, follow_symlinks=False)
                    if (
                        not stat.S_ISREG(opened.st_mode)
                        or opened.st_nlink != 1
                        or (named.st_dev, named.st_ino) != (opened.st_dev, opened.st_ino)
                    ):
                        raise UnsafeObservationPath("Hermes archive target changed while opening")
                    os.fchmod(descriptor, mode)
                    remaining = member.size
                    while remaining:
                        block = extracted.read(min(1024 * 1024, remaining))
                        if not block:
                            raise IntegrityError("Hermes source archive file is truncated")
                        _write_descriptor(descriptor, block)
                        remaining -= len(block)
                    if extracted.read(1):
                        raise IntegrityError("Hermes source archive file exceeds declared size")
                    os.fsync(descriptor)
                    persisted = os.fstat(descriptor)
                    named = os.stat(name, dir_fd=current, follow_symlinks=False)
                    if persisted.st_nlink != 1 or (named.st_dev, named.st_ino) != (
                        persisted.st_dev,
                        persisted.st_ino,
                    ):
                        raise UnsafeObservationPath("Hermes archive target changed while writing")
                finally:
                    os.close(descriptor)
                os.fsync(current)
            finally:
                os.close(current)
        os.fsync(root_descriptor)
        _verify_directory_identity(destination, root_descriptor)
        os.fsync(parent_descriptor)
        _verify_directory_identity(destination.parent, parent_descriptor)
    finally:
        if root_descriptor is not None:
            os.close(root_descriptor)
        os.close(parent_descriptor)


def _materialize_git_archive(checkout: Path, commit: str, destination: Path) -> None:
    """Materialize exactly the bytes tracked by one already-verified Git commit."""

    try:
        completed = subprocess.run(
            ["git", "-C", str(checkout), "archive", "--format=tar", commit],
            check=False,
            capture_output=True,
            env=_isolated_subprocess_environment(),
        )
    except OSError as error:
        raise IntegrityError("Hermes source archive tool is unavailable") from error
    if completed.returncode != 0:
        raise IntegrityError(f"Hermes source archive failed (git exit {completed.returncode})")
    _extract_git_archive(completed.stdout, destination)


def _assert_plain_path(path: Path, *, kind: str) -> None:
    if path.is_symlink():
        raise IntegrityError(f"{kind} must not be a symlink")
    if path.exists() and kind == "directory" and not path.is_dir():
        raise IntegrityError(f"{kind} is not a directory")


def _fsync_directory(directory: Path) -> None:
    if os.name != "posix":
        return
    descriptor = _open_private_directory(directory)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _isolated_subprocess_environment() -> dict[str, str]:
    """Prevent ambient package-manager/Python policy from changing a candidate."""

    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("UV_", "PIP_", "PYTHON"))
    }
    environment.pop("VIRTUAL_ENV", None)
    environment.pop("CONDA_PREFIX", None)
    return environment


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    data = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    _atomic_lifecycle_write(path, data, temporary_name=f".{path.name}.{os.getpid()}.tmp")


def _atomic_bytes(path: Path, data: bytes) -> None:
    """Durably replace one private product-owned file without following aliases."""

    token = secrets.token_hex(4)
    if re.fullmatch(r"[a-f0-9]{8}", token) is None:
        raise UnsafeObservationPath("lifecycle temporary token is invalid")
    _atomic_lifecycle_write(
        path,
        data,
        temporary_name=f".{path.name}.{os.getpid()}.{token}.tmp",
    )


def _atomic_lifecycle_write(path: Path, data: bytes, *, temporary_name: str) -> None:
    """Install bytes relative to one retained, inode-verified parent descriptor."""

    path = Path(path)
    if not isinstance(data, bytes):
        raise TypeError("lifecycle atomic data must be bytes")
    if path.name in {"", ".", ".."} or "/" in temporary_name:
        raise UnsafeObservationPath("lifecycle atomic target has an unsafe name")
    ensure_private_dir(path.parent)
    if os.name != "posix":  # pragma: no cover - exercised by platform CI
        temporary = path.with_name(temporary_name)
        descriptor: int | None = None
        created = False
        try:
            descriptor = os.open(
                temporary,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                FILE_MODE,
            )
            created = True
            _write_descriptor(descriptor, data)
            os.fsync(descriptor)
            os.close(descriptor)
            descriptor = None
            os.replace(temporary, path)
            created = False
            harden_file(path)
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if created:
                temporary.unlink(missing_ok=True)
        return

    parent_descriptor = _open_private_directory(path.parent)
    descriptor: int | None = None
    created_identity: tuple[int, int] | None = None
    installed = False
    try:
        flags = (
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_CLOEXEC", 0)
        )
        descriptor = os.open(
            temporary_name,
            flags,
            FILE_MODE,
            dir_fd=parent_descriptor,
        )
        opened = os.fstat(descriptor)
        named = os.stat(
            temporary_name,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_nlink != 1
            or not stat.S_ISREG(named.st_mode)
            or named.st_nlink != 1
            or (named.st_dev, named.st_ino) != (opened.st_dev, opened.st_ino)
        ):
            raise UnsafeObservationPath("lifecycle temporary is not a private regular file")
        created_identity = (opened.st_dev, opened.st_ino)
        os.fchmod(descriptor, FILE_MODE)
        _write_descriptor(descriptor, data)
        os.fsync(descriptor)

        persisted = os.fstat(descriptor)
        named = os.stat(
            temporary_name,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
        if (
            not stat.S_ISREG(persisted.st_mode)
            or persisted.st_nlink != 1
            or stat.S_IMODE(persisted.st_mode) != FILE_MODE
            or (named.st_dev, named.st_ino) != (persisted.st_dev, persisted.st_ino)
        ):
            raise UnsafeObservationPath("lifecycle temporary changed while writing")
        _verify_directory_identity(path.parent, parent_descriptor)
        os.replace(
            temporary_name,
            path.name,
            src_dir_fd=parent_descriptor,
            dst_dir_fd=parent_descriptor,
        )
        installed = True
        installed_info = os.stat(
            path.name,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
        if (
            not stat.S_ISREG(installed_info.st_mode)
            or installed_info.st_nlink != 1
            or (installed_info.st_dev, installed_info.st_ino) != created_identity
        ):
            raise UnsafeObservationPath("lifecycle target changed during replace")
        _verify_directory_identity(path.parent, parent_descriptor)
        os.fsync(parent_descriptor)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if created_identity is not None and not installed:
            try:
                remaining = os.stat(
                    temporary_name,
                    dir_fd=parent_descriptor,
                    follow_symlinks=False,
                )
                if (remaining.st_dev, remaining.st_ino) == created_identity:
                    os.unlink(temporary_name, dir_fd=parent_descriptor)
                    try:
                        os.fsync(parent_descriptor)
                    except OSError:
                        pass
            except OSError:
                pass
        os.close(parent_descriptor)


def _write_descriptor(descriptor: int, data: bytes) -> None:
    offset = 0
    while offset < len(data):
        written = os.write(descriptor, data[offset:])
        if written <= 0:
            raise OSError("lifecycle atomic write made no progress")
        offset += written


def _verify_directory_identity(path: Path, descriptor: int) -> None:
    verification_descriptor = _open_private_directory(path)
    try:
        verified = os.fstat(verification_descriptor)
        retained = os.fstat(descriptor)
        if (verified.st_dev, verified.st_ino) != (retained.st_dev, retained.st_ino):
            raise UnsafeObservationPath("lifecycle atomic parent changed")
    finally:
        os.close(verification_descriptor)


def _safe_entry_name(name: str) -> str:
    if not isinstance(name, str) or name in {"", ".", ".."} or Path(name).name != name:
        raise UnsafeObservationPath("lifecycle entry name escapes its directory")
    return name


def _open_child_directory(parent_descriptor: int, name: str) -> int:
    name = _safe_entry_name(name)
    flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    descriptor = os.open(name, flags, dir_fd=parent_descriptor)
    try:
        opened = os.fstat(descriptor)
        named = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
        if (
            not stat.S_ISDIR(opened.st_mode)
            or not stat.S_ISDIR(named.st_mode)
            or (named.st_dev, named.st_ino) != (opened.st_dev, opened.st_ino)
        ):
            raise UnsafeObservationPath("lifecycle directory entry changed while opening")
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _open_or_create_child_directory(parent_descriptor: int, name: str) -> int:
    name = _safe_entry_name(name)
    try:
        os.mkdir(name, DIR_MODE, dir_fd=parent_descriptor)
    except FileExistsError:
        pass
    descriptor = _open_child_directory(parent_descriptor, name)
    os.fchmod(descriptor, DIR_MODE)
    return descriptor


def _create_private_directory(path: Path) -> Path:
    """Create one exclusive directory relative to a retained private parent."""

    path = Path(path)
    _safe_entry_name(path.name)
    ensure_private_dir(path.parent)
    if os.name != "posix":  # pragma: no cover - exercised by platform CI
        path.mkdir(mode=DIR_MODE)
        return path
    parent_descriptor = _open_private_directory(path.parent)
    descriptor: int | None = None
    created = False
    try:
        _verify_directory_identity(path.parent, parent_descriptor)
        os.mkdir(path.name, DIR_MODE, dir_fd=parent_descriptor)
        created = True
        descriptor = _open_child_directory(parent_descriptor, path.name)
        os.fchmod(descriptor, DIR_MODE)
        _verify_directory_identity(path.parent, parent_descriptor)
        os.fsync(parent_descriptor)
        return path
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if created:
            try:
                named = os.stat(path.name, dir_fd=parent_descriptor, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                if not stat.S_ISDIR(named.st_mode):
                    raise UnsafeObservationPath("created lifecycle directory changed")
        os.close(parent_descriptor)


def _unlink_private_file(path: Path, *, missing_ok: bool = False) -> bool:
    """Unlink one singly-linked regular file relative to its retained parent."""

    path = Path(path)
    _safe_entry_name(path.name)
    if os.name != "posix":  # pragma: no cover - exercised by platform CI
        try:
            path.unlink()
        except FileNotFoundError:
            if not missing_ok:
                raise
            return False
        return True
    parent_descriptor = _open_private_directory(path.parent)
    try:
        try:
            named = os.stat(path.name, dir_fd=parent_descriptor, follow_symlinks=False)
        except FileNotFoundError:
            if not missing_ok:
                raise
            _verify_directory_identity(path.parent, parent_descriptor)
            return False
        if not stat.S_ISREG(named.st_mode) or named.st_nlink != 1:
            raise UnsafeObservationPath("lifecycle unlink target is not a private regular file")
        identity = (named.st_dev, named.st_ino)
        verification = os.stat(path.name, dir_fd=parent_descriptor, follow_symlinks=False)
        if (verification.st_dev, verification.st_ino) != identity or verification.st_nlink != 1:
            raise UnsafeObservationPath("lifecycle unlink target changed")
        _verify_directory_identity(path.parent, parent_descriptor)
        os.unlink(path.name, dir_fd=parent_descriptor)
        os.fsync(parent_descriptor)
        _verify_directory_identity(path.parent, parent_descriptor)
        return True
    finally:
        os.close(parent_descriptor)


def _remove_directory_contents(descriptor: int) -> None:
    for name in os.listdir(descriptor):
        _safe_entry_name(name)
        try:
            named = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
        except FileNotFoundError:
            continue
        if stat.S_ISDIR(named.st_mode):
            child = _open_child_directory(descriptor, name)
            try:
                identity = os.fstat(child)
                _remove_directory_contents(child)
                current = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
                if (current.st_dev, current.st_ino) != (identity.st_dev, identity.st_ino):
                    raise UnsafeObservationPath("lifecycle directory changed before removal")
                os.rmdir(name, dir_fd=descriptor)
            finally:
                os.close(child)
            continue
        # Unlinking a non-directory entry relative to the retained descriptor never
        # follows a symlink or hard link to mutate its target bytes.
        current = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
        if (current.st_dev, current.st_ino) != (named.st_dev, named.st_ino):
            raise UnsafeObservationPath("lifecycle entry changed before removal")
        os.unlink(name, dir_fd=descriptor)
    os.fsync(descriptor)


def _remove_private_tree(path: Path, *, missing_ok: bool = False) -> bool:
    """Recursively remove a directory without resolving any descendant alias."""

    path = Path(path)
    _safe_entry_name(path.name)
    if os.name != "posix":  # pragma: no cover - exercised by platform CI
        if not path.exists():
            if missing_ok:
                return False
            raise FileNotFoundError(path)
        if path.is_symlink() or not path.is_dir():
            raise UnsafeObservationPath("lifecycle tree target is not a real directory")
        shutil.rmtree(path)
        return True
    parent_descriptor = _open_private_directory(path.parent)
    child_descriptor: int | None = None
    try:
        try:
            child_descriptor = _open_child_directory(parent_descriptor, path.name)
        except FileNotFoundError:
            if not missing_ok:
                raise
            _verify_directory_identity(path.parent, parent_descriptor)
            return False
        child_identity = os.fstat(child_descriptor)
        _verify_directory_identity(path.parent, parent_descriptor)
        _verify_directory_identity(path, child_descriptor)
        _remove_directory_contents(child_descriptor)
        _verify_directory_identity(path, child_descriptor)
        current = os.stat(path.name, dir_fd=parent_descriptor, follow_symlinks=False)
        if (current.st_dev, current.st_ino) != (child_identity.st_dev, child_identity.st_ino):
            raise UnsafeObservationPath("lifecycle tree changed before removal")
        os.rmdir(path.name, dir_fd=parent_descriptor)
        os.fsync(parent_descriptor)
        _verify_directory_identity(path.parent, parent_descriptor)
        return True
    finally:
        if child_descriptor is not None:
            os.close(child_descriptor)
        os.close(parent_descriptor)


def _harden_private_tree(root: Path) -> None:
    descriptor = _open_private_directory(root)
    try:
        _harden_tree_descriptor(descriptor)
        _verify_directory_identity(root, descriptor)
    finally:
        os.close(descriptor)


def _harden_tree_descriptor(descriptor: int) -> None:
    os.fchmod(descriptor, DIR_MODE)
    for name in os.listdir(descriptor):
        _safe_entry_name(name)
        named = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
        if stat.S_ISLNK(named.st_mode):
            continue
        if stat.S_ISDIR(named.st_mode):
            child = _open_child_directory(descriptor, name)
            try:
                _harden_tree_descriptor(child)
            finally:
                os.close(child)
            continue
        if not stat.S_ISREG(named.st_mode) or named.st_nlink != 1:
            raise UnsafeObservationPath("release tree contains an unsafe entry")
        flags = (
            os.O_RDONLY
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NONBLOCK", 0)
        )
        child = os.open(name, flags, dir_fd=descriptor)
        try:
            opened = os.fstat(child)
            if (opened.st_dev, opened.st_ino) != (
                named.st_dev,
                named.st_ino,
            ) or opened.st_nlink != 1:
                raise UnsafeObservationPath("release tree entry changed while hardening")
            os.fchmod(child, 0o700 if stat.S_IMODE(opened.st_mode) & 0o111 else FILE_MODE)
        finally:
            os.close(child)
    os.fsync(descriptor)


@dataclass(frozen=True, slots=True)
class PreparedRelease:
    version: str
    wheel: Path
    wheel_sha256: str
    stage: Path
    hermes_tag: str
    hermes_commit: str
    aether_identity: dict[str, Any]
    prebuild_identity: str
    installed_file_fingerprint: str
    observation_compatibility: dict[str, Any] = field(default_factory=_compatibility_copy)

    @property
    def release_id(self) -> str:
        return f"{self.version}-{self.wheel_sha256[:16]}"


@dataclass(frozen=True, slots=True)
class ReleaseRecord:
    schema_version: int
    release_id: str
    version: str
    wheel_filename: str
    wheel_sha256: str
    hermes_tag: str
    hermes_commit: str
    observer_entry_point: str
    previous_release_id: str | None
    authority_context: dict[str, Any]
    aether_identity: dict[str, Any] | None = None
    prebuild_identity: str | None = None
    installed_file_fingerprint: str | None = None
    observation_compatibility: dict[str, Any] = field(default_factory=_compatibility_copy)
    observer: dict[str, str] = field(default_factory=lambda: dict(OBSERVER_ENTRY_POINT))

    @classmethod
    def from_json(cls, payload: Any) -> "ReleaseRecord":
        if not isinstance(payload, dict):
            raise IntegrityError("malformed active release record")
        payload = dict(payload)
        if payload.get("schema_version") == 1 and "authority_context" not in payload:
            payload["authority_context"] = AuthorityContext.unavailable().to_record()
        if payload.get("schema_version") in (1, 2):
            payload.setdefault("aether_identity", None)
            payload.setdefault("prebuild_identity", None)
            payload.setdefault("installed_file_fingerprint", None)
            payload.setdefault("observation_compatibility", _compatibility_copy())
            payload.setdefault("observer", dict(OBSERVER_ENTRY_POINT))
        try:
            record = cls(**payload)
        except (TypeError, KeyError, ValueError) as error:
            raise IntegrityError("malformed active release record") from error
        record.validate()
        return record

    def validate(self) -> None:
        if type(self.schema_version) is not int or self.schema_version not in (1, 2, 3):
            raise IntegrityError("unsupported active release schema")
        if not isinstance(self.release_id, str) or not _RELEASE_ID_RE.fullmatch(self.release_id):
            raise IntegrityError("invalid active release id")
        if not isinstance(self.version, str) or not _VERSION_RE.fullmatch(self.version):
            raise IntegrityError("invalid release version")
        if not isinstance(self.wheel_sha256, str) or not _SHA256_RE.fullmatch(self.wheel_sha256):
            raise IntegrityError("invalid wheel digest")
        if (
            not isinstance(self.wheel_filename, str)
            or not self.wheel_filename
            or self.wheel_filename != Path(self.wheel_filename).name
            or "/" in self.wheel_filename
            or "\\" in self.wheel_filename
            or any(ord(character) < 0x20 for character in self.wheel_filename)
        ):
            raise IntegrityError("invalid wheel filename")
        if self.hermes_tag != HERMES_BASELINE.tag:
            raise IntegrityError("active release uses a different Hermes tag")
        if self.hermes_commit != HERMES_BASELINE.commit:
            raise IntegrityError("active release uses a different Hermes commit")
        if self.observer_entry_point != HERMES_BASELINE.observer_entry_point:
            raise IntegrityError("observer entry point mismatch")
        if self.observer != OBSERVER_ENTRY_POINT:
            raise IntegrityError("observer entry point tuple mismatch")
        _validate_observation_compatibility(self.observation_compatibility)
        if self.schema_version == 3:
            identity = AetherPrebuildIdentity.from_record(self.aether_identity)
            if not isinstance(self.prebuild_identity, str) or not _SHA256_RE.fullmatch(
                self.prebuild_identity
            ):
                raise IntegrityError("invalid prebuild identity")
            if identity.digest != self.prebuild_identity:
                raise IntegrityError("prebuild identity digest mismatch")
            if identity.package_version != self.version:
                raise IntegrityError("prebuild identity version mismatch")
            if not isinstance(self.installed_file_fingerprint, str) or not _SHA256_RE.fullmatch(
                self.installed_file_fingerprint
            ):
                raise IntegrityError("invalid installed-file fingerprint")
        elif any(
            value is not None
            for value in (
                self.aether_identity,
                self.prebuild_identity,
                self.installed_file_fingerprint,
            )
        ):
            raise IntegrityError("legacy release cannot declare Aether build identity")
        try:
            authority = AuthorityContext.from_record(self.authority_context)
        except (AttributeError, TypeError, ValueError) as error:
            raise IntegrityError("active release authority context is invalid") from error
        if self.schema_version == 1:
            if authority != AuthorityContext.unavailable():
                raise IntegrityError("legacy release cannot grant authority")
        elif authority != AuthorityContext.for_active_release(self.release_id):
            raise IntegrityError("active release authority context mismatch")
        if self.previous_release_id is not None and (
            not isinstance(self.previous_release_id, str)
            or not _RELEASE_ID_RE.fullmatch(self.previous_release_id)
        ):
            raise IntegrityError("invalid previous release id")


class ReleaseStore:
    """Versioned release store with one fsync-bounded active record."""

    def __init__(
        self,
        root: Path | str,
        *,
        state_root: Path | str | None = None,
    ) -> None:
        candidate = Path(root).expanduser()
        if not candidate.is_absolute():
            raise IntegrityError("lifecycle data root must be absolute")
        mutable = Path(state_root).expanduser() if state_root is not None else candidate
        if not mutable.is_absolute():
            raise IntegrityError("lifecycle state root must be absolute")
        _assert_plain_path(candidate, kind="data root")
        _assert_plain_path(mutable, kind="state root")
        self.root = candidate
        self.state_root = mutable

    @property
    def releases(self) -> Path:
        return self.root / "releases"

    @property
    def active_pointer(self) -> Path:
        return self.root / "active.json"

    @property
    def transitions(self) -> Path:
        return self.state_root / "transitions"

    @property
    def profile_homes(self) -> Path:
        """Persistent, explicitly product-scoped Hermes homes for all roles."""

        return self.root / "profiles"

    def profile_home(self, role: str) -> Path:
        if role not in _PROFILE_ROLES:
            raise IntegrityError("unknown managed profile")
        return self.profile_homes / role

    @property
    def ownership_marker(self) -> Path:
        return self.root / _OWNERSHIP_MARKER

    @property
    def state_ownership_marker(self) -> Path:
        return self.state_root / _OWNERSHIP_MARKER

    @property
    def mutation_lock_file(self) -> Path:
        # The lock survives purge so a process that was already waiting cannot acquire
        # a deleted inode and recreate product state behind the completed uninstall.
        return self.state_root.parent / f".{self.state_root.name}.lifecycle.lock"

    @staticmethod
    def _acquire_platform_lock(descriptor: int) -> None:
        if os.name == "posix":
            import fcntl

            fcntl.flock(descriptor, fcntl.LOCK_EX)
            return
        if os.name == "nt":  # pragma: no cover - exercised by platform CI
            import msvcrt

            if os.fstat(descriptor).st_size == 0:
                os.write(descriptor, b"\0")
                os.fsync(descriptor)
            os.lseek(descriptor, 0, os.SEEK_SET)
            try:
                msvcrt.locking(descriptor, msvcrt.LK_LOCK, 1)
            except OSError as error:
                raise IntegrityError("lifecycle mutation lock is unavailable") from error
            return
        raise IntegrityError("platform has no safe lifecycle mutation lock")

    @staticmethod
    def _release_platform_lock(descriptor: int) -> None:
        if os.name == "posix":
            import fcntl

            fcntl.flock(descriptor, fcntl.LOCK_UN)
        elif os.name == "nt":  # pragma: no cover - exercised by platform CI
            import msvcrt

            os.lseek(descriptor, 0, os.SEEK_SET)
            msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)

    def _open_mutation_lock(self) -> int:
        lock_file = self.mutation_lock_file
        parent_descriptor: int | None = None
        descriptor: int | None = None
        acquired = False
        successful = False
        try:
            ensure_private_dir(lock_file.parent)
            flags = (
                os.O_RDWR | os.O_CREAT | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
            )
            if os.name == "posix":
                parent_descriptor = _open_private_directory(lock_file.parent)
                descriptor = os.open(
                    lock_file.name,
                    flags,
                    FILE_MODE,
                    dir_fd=parent_descriptor,
                )
                named = os.stat(
                    lock_file.name,
                    dir_fd=parent_descriptor,
                    follow_symlinks=False,
                )
            else:  # pragma: no cover - exercised by platform CI
                descriptor = os.open(lock_file, flags, FILE_MODE)
                named = os.stat(lock_file, follow_symlinks=False)
            status = os.fstat(descriptor)
            if (
                not stat.S_ISREG(status.st_mode)
                or status.st_nlink != 1
                or not stat.S_ISREG(named.st_mode)
                or named.st_nlink != 1
                or (named.st_dev, named.st_ino) != (status.st_dev, status.st_ino)
                or (os.name == "posix" and status.st_uid != os.getuid())
            ):
                raise IntegrityError("lifecycle mutation lock is not a private regular file")
            if os.name == "posix":
                os.fchmod(descriptor, FILE_MODE)
            self._acquire_platform_lock(descriptor)
            acquired = True
            if parent_descriptor is not None:
                _verify_directory_identity(lock_file.parent, parent_descriptor)
                named = os.stat(
                    lock_file.name,
                    dir_fd=parent_descriptor,
                    follow_symlinks=False,
                )
            else:  # pragma: no cover - exercised by platform CI
                named = os.stat(lock_file, follow_symlinks=False)
            locked = os.fstat(descriptor)
            if (
                not stat.S_ISREG(named.st_mode)
                or named.st_nlink != 1
                or (named.st_dev, named.st_ino) != (locked.st_dev, locked.st_ino)
                or (os.name == "posix" and named.st_uid != os.getuid())
                or (os.name == "posix" and stat.S_IMODE(locked.st_mode) != FILE_MODE)
            ):
                raise IntegrityError("lifecycle mutation lock changed while acquiring it")
            successful = True
            return descriptor
        except (OSError, UnsafeObservationPath) as error:
            raise IntegrityError("lifecycle mutation lock cannot be opened safely") from error
        except BaseException:
            raise
        finally:
            if parent_descriptor is not None:
                os.close(parent_descriptor)
            if not successful and descriptor is not None:
                try:
                    if acquired:
                        self._release_platform_lock(descriptor)
                finally:
                    os.close(descriptor)

    @contextmanager
    def mutation_lock(self) -> Iterator[None]:
        """Serialize every lifecycle mutation across threads and processes."""

        key = str(self.mutation_lock_file.absolute())
        local_lock = _local_mutation_lock(key)
        with local_lock:
            depths = getattr(_LOCK_STATE, "depths", None)
            if depths is None:
                depths = {}
                _LOCK_STATE.depths = depths
            if key in depths:
                depths[key] += 1
                try:
                    yield
                finally:
                    depths[key] -= 1
                return
            descriptor = self._open_mutation_lock()
            depths[key] = 1
            try:
                yield
            finally:
                del depths[key]
                try:
                    self._release_platform_lock(descriptor)
                finally:
                    os.close(descriptor)

    def _ensure_owned_root(self) -> None:
        roots = {
            self.root: self.ownership_marker,
            self.state_root: self.state_ownership_marker,
        }
        for root, marker in roots.items():
            ensure_private_dir(root)
            if marker.exists():
                if marker.is_symlink():
                    raise IntegrityError("Aether ownership marker must not be a symlink")
                try:
                    payload = json.loads(read_private_bytes(marker).decode("utf-8"))
                except (OSError, UnicodeError, ValueError) as error:
                    raise IntegrityError("Aether ownership marker is unreadable") from error
                if payload != {"product": "aether-agents", "schema_version": 1}:
                    raise IntegrityError("Aether root is not owned by this installation")
            else:
                _atomic_json(marker, {"product": "aether-agents", "schema_version": 1})
        self.assert_owned()

    def assert_owned(self) -> None:
        roots = {
            self.root: self.ownership_marker,
            self.state_root: self.state_ownership_marker,
        }
        for root, marker in roots.items():
            if not marker.is_file() or marker.is_symlink():
                raise IntegrityError("Aether root is not owned by this installation")
            if os.name == "posix":
                try:
                    root_status = root.stat()
                    marker_status = marker.stat()
                except OSError as error:
                    raise IntegrityError("Aether root ownership cannot be inspected") from error
                if (
                    root_status.st_uid != os.getuid()
                    or marker_status.st_uid != os.getuid()
                    or stat.S_IMODE(marker_status.st_mode) != FILE_MODE
                ):
                    raise IntegrityError("Aether root ownership or permissions mismatch")
            try:
                payload = json.loads(read_private_bytes(marker).decode("utf-8"))
            except (OSError, UnicodeError, ValueError) as error:
                raise IntegrityError("Aether ownership marker is unreadable") from error
            if payload != {"product": "aether-agents", "schema_version": 1}:
                raise IntegrityError("Aether root is not owned by this installation")

    def release_path(self, release_id: str) -> Path:
        if not _RELEASE_ID_RE.fullmatch(release_id):
            raise IntegrityError("invalid release id path component")
        path = self.releases / release_id
        if path.is_symlink():
            raise IntegrityError("release path must not be a symlink")
        return path

    def _validate_prepared(self, prepared: PreparedRelease) -> None:
        if not _VERSION_RE.fullmatch(prepared.version):
            raise IntegrityError("invalid prepared release version")
        if not _SHA256_RE.fullmatch(prepared.wheel_sha256):
            raise IntegrityError("invalid prepared wheel digest")
        if prepared.hermes_tag != HERMES_BASELINE.tag:
            raise IntegrityError("prepared release uses a different Hermes tag")
        if prepared.hermes_commit != HERMES_BASELINE.commit:
            raise IntegrityError("prepared release uses a different Hermes commit")
        _validate_observation_compatibility(prepared.observation_compatibility)
        identity = AetherPrebuildIdentity.from_record(prepared.aether_identity)
        if identity.package_version != prepared.version:
            raise IntegrityError("prepared release Aether version mismatch")
        if prepared.prebuild_identity != identity.digest:
            raise IntegrityError("prepared release prebuild identity is invalid")
        if not isinstance(prepared.installed_file_fingerprint, str) or not _SHA256_RE.fullmatch(
            prepared.installed_file_fingerprint
        ):
            raise IntegrityError("prepared release installed-file fingerprint is invalid")
        if not prepared.wheel.is_file() or prepared.wheel.is_symlink():
            raise IntegrityError("prepared wheel is not a regular file")
        try:
            prepared_wheel_bytes = read_private_bytes(prepared.wheel)
        except (OSError, ValueError) as error:
            raise IntegrityError("prepared wheel is unreadable") from error
        if hashlib.sha256(prepared_wheel_bytes).hexdigest() != prepared.wheel_sha256:
            raise IntegrityError("prepared wheel digest mismatch")
        if not prepared.stage.is_dir() or prepared.stage.is_symlink():
            raise IntegrityError("prepared release stage is invalid")
        for environment in ("manager", "runtime"):
            marker = prepared.stage / environment / "aether-wheel.sha256"
            if marker.is_symlink() or not marker.is_file():
                raise IntegrityError(f"{environment} wheel identity is missing")
            try:
                observed = read_private_bytes(marker).decode("ascii").strip()
            except (OSError, UnicodeError, ValueError) as error:
                raise IntegrityError(f"{environment} wheel identity is unreadable") from error
            if observed != prepared.wheel_sha256:
                raise IntegrityError(f"{environment} wheel identity mismatch")

    def register(self, prepared: PreparedRelease) -> ReleaseRecord:
        """Durably register a verified candidate without making it active."""

        with self.mutation_lock():
            return self._register_locked(prepared)

    def _register_locked(self, prepared: PreparedRelease) -> ReleaseRecord:
        """Register while the caller retains :meth:`mutation_lock`."""

        self._validate_prepared(prepared)
        previous = self.active(required=False)
        record = ReleaseRecord(
            schema_version=3,
            release_id=prepared.release_id,
            version=prepared.version,
            wheel_filename=prepared.wheel.name,
            wheel_sha256=prepared.wheel_sha256,
            hermes_tag=prepared.hermes_tag,
            hermes_commit=prepared.hermes_commit,
            observer_entry_point=HERMES_BASELINE.observer_entry_point,
            previous_release_id=previous.release_id if previous else None,
            authority_context=AuthorityContext.for_active_release(prepared.release_id).to_record(),
            aether_identity=json.loads(json.dumps(prepared.aether_identity)),
            prebuild_identity=prepared.prebuild_identity,
            installed_file_fingerprint=prepared.installed_file_fingerprint,
            observation_compatibility=_validate_observation_compatibility(
                prepared.observation_compatibility
            ),
            observer=dict(OBSERVER_ENTRY_POINT),
        )
        record.validate()
        self._ensure_owned_root()
        ensure_private_dir(self.releases)
        destination = self.release_path(record.release_id)
        if destination.exists():
            try:
                same_prepared_path = prepared.stage.resolve(strict=True) == destination.resolve(
                    strict=True
                )
            except OSError:
                same_prepared_path = False
            if same_prepared_path and not (destination / "record.json").exists():
                # Versioned virtual environments are not relocatable: their console
                # scripts bind the creation path.  A release is therefore staged at
                # its final immutable, non-active path and becomes authoritative only
                # when the fsync-bounded active record is replaced.
                _atomic_json(destination / "record.json", asdict(record))
                self._harden_tree(destination)
                _fsync_directory(self.releases)
            else:
                existing = self._read_release(record.release_id)
                if (
                    existing.version != record.version
                    or existing.wheel_sha256 != record.wheel_sha256
                    or existing.hermes_commit != record.hermes_commit
                    or existing.aether_identity != record.aether_identity
                    or existing.prebuild_identity != record.prebuild_identity
                    or existing.installed_file_fingerprint != record.installed_file_fingerprint
                    or existing.observation_compatibility != record.observation_compatibility
                    or existing.observer != record.observer
                ):
                    raise IntegrityError("existing release id has different identity")
                record = ReleaseRecord(
                    **{
                        **asdict(existing),
                        "previous_release_id": record.previous_release_id,
                    }
                )
        else:
            _atomic_json(prepared.stage / "record.json", asdict(record))
            os.replace(prepared.stage, destination)
            _fsync_directory(self.releases)
            self._harden_tree(destination)
        return record

    def activate(self, prepared: PreparedRelease) -> ReleaseRecord:
        """Compatibility primitive: register and atomically select a candidate."""

        with self.mutation_lock():
            record = self._register_locked(prepared)
            self._commit_active(record)
            return record

    def _harden_tree(self, root: Path) -> None:
        if os.name == "posix":
            _harden_private_tree(root)
            return
        for directory, names, files in os.walk(root, followlinks=False):
            current = Path(directory)
            if current.is_symlink():
                raise IntegrityError("release tree contains a symlink directory")
            if os.name == "posix":
                current.chmod(DIR_MODE)
            for name in (*names, *files):
                path = current / name
                if path.is_symlink():
                    # ``uv venv`` intentionally creates interpreter/lib symlinks.
                    # The stage itself and every product-owned boundary above it were
                    # created with exclusive names; do not follow or chmod these links.
                    continue
                if path.is_file():
                    if os.name == "posix":
                        current_mode = stat.S_IMODE(path.stat().st_mode)
                        path.chmod(0o700 if current_mode & 0o111 else FILE_MODE)

    def _commit_active(
        self,
        record: ReleaseRecord,
        *,
        expected_active_release_id: str | None | object = _CAS_UNSET,
    ) -> None:
        with self.mutation_lock():
            record.validate()
            if expected_active_release_id is not _CAS_UNSET:
                current = self.active(required=False)
                current_id = current.release_id if current is not None else None
                if current_id != expected_active_release_id:
                    raise IntegrityError(
                        "active release changed concurrently; stale transition refused"
                    )
            _atomic_json(self.active_pointer, asdict(record))

    def _read_release(self, release_id: str) -> ReleaseRecord:
        path = self.release_path(release_id)
        try:
            payload = json.loads(read_private_bytes(path / "record.json").decode("utf-8"))
        except (OSError, UnicodeError, ValueError) as error:
            raise IntegrityError("release record is unreadable") from error
        record = ReleaseRecord.from_json(payload)
        if record.release_id != release_id:
            raise IntegrityError("release directory identity mismatch")
        return record

    def active(self, *, required: bool = True) -> ReleaseRecord | None:
        if not self.active_pointer.exists():
            if required:
                raise IntegrityError("no active release")
            return None
        if self.active_pointer.is_symlink():
            raise IntegrityError("active release pointer must not be a symlink")
        try:
            payload = json.loads(read_private_bytes(self.active_pointer).decode("utf-8"))
        except (OSError, UnicodeError, ValueError) as error:
            raise IntegrityError("active release pointer is unreadable") from error
        record = ReleaseRecord.from_json(payload)
        installed = self._read_release(record.release_id)
        if (
            installed.version != record.version
            or installed.wheel_sha256 != record.wheel_sha256
            or installed.hermes_commit != record.hermes_commit
            or installed.authority_context != record.authority_context
            or installed.aether_identity != record.aether_identity
            or installed.prebuild_identity != record.prebuild_identity
            or installed.installed_file_fingerprint != record.installed_file_fingerprint
            or installed.observation_compatibility != record.observation_compatibility
            or installed.observer != record.observer
        ):
            raise IntegrityError("active pointer and installed release disagree")
        return record

    def activate_existing(
        self,
        release_id: str,
        *,
        expected_active_release_id: str | None | object = _CAS_UNSET,
    ) -> ReleaseRecord:
        with self.mutation_lock():
            record = self._read_release(release_id)
            current = self.active(required=False)
            predecessor = current.release_id if current is not None else None
            if predecessor == record.release_id:
                predecessor = record.previous_release_id
            record = replace(record, previous_release_id=predecessor)
            self._commit_active(
                record,
                expected_active_release_id=expected_active_release_id,
            )
            return record

    def begin_transition(
        self,
        *,
        kind: str,
        from_release_id: str | None,
        to_release_id: str,
    ) -> Path:
        with self.mutation_lock():
            return self._begin_transition_locked(
                kind=kind,
                from_release_id=from_release_id,
                to_release_id=to_release_id,
            )

    def _begin_transition_locked(
        self,
        *,
        kind: str,
        from_release_id: str | None,
        to_release_id: str,
    ) -> Path:
        if kind not in {"install", "update", "rollback"}:
            raise IntegrityError("unsupported lifecycle transition kind")
        if from_release_id is not None and not _RELEASE_ID_RE.fullmatch(from_release_id):
            raise IntegrityError("invalid transition source release")
        if not _RELEASE_ID_RE.fullmatch(to_release_id):
            raise IntegrityError("invalid transition target release")
        self._ensure_owned_root()
        ensure_private_dir(self.transitions)
        from_previous_release_id: str | None = None
        if from_release_id is not None:
            try:
                active = self.active(required=False)
            except IntegrityError:
                active = None
            if active is not None and active.release_id == from_release_id:
                from_previous_release_id = active.previous_release_id
        transition_id = "trn_" + secrets.token_hex(16)
        path = self.transitions / f"{transition_id}.json"
        _atomic_json(
            path,
            {
                "schema_version": 2,
                "transition_id": transition_id,
                "kind": kind,
                "state": "pending",
                "from_release_id": from_release_id,
                "from_previous_release_id": from_previous_release_id,
                "to_release_id": to_release_id,
                "failure_code": None,
            },
        )
        return path

    @staticmethod
    def _read_transition(path: Path) -> dict[str, Any]:
        if path.is_symlink() or not path.is_file():
            raise IntegrityError("transition journal is not a regular file")
        try:
            payload = json.loads(read_private_bytes(path).decode("utf-8"))
        except (OSError, UnicodeError, ValueError) as error:
            raise IntegrityError("transition journal is unreadable") from error
        if not isinstance(payload, dict):
            raise IntegrityError("transition journal schema is invalid")
        schema_version = payload.get("schema_version")
        expected_keys = {
            "schema_version",
            "transition_id",
            "kind",
            "state",
            "from_release_id",
            "to_release_id",
            "failure_code",
        }
        if schema_version == 2:
            expected_keys.add("from_previous_release_id")
        if set(payload) != expected_keys or schema_version not in (1, 2):
            raise IntegrityError("transition journal schema is invalid")
        transition_id = payload.get("transition_id")
        if not isinstance(transition_id, str) or not _TRANSITION_ID_RE.fullmatch(transition_id):
            raise IntegrityError("transition journal id is invalid")
        if path.name != f"{transition_id}.json":
            raise IntegrityError("transition journal filename disagrees with its id")
        if payload.get("kind") not in {"install", "update", "rollback"}:
            raise IntegrityError("transition journal kind is invalid")
        if payload.get("state") not in {"pending", "committed", "failed", "recovered"}:
            raise IntegrityError("transition journal state is invalid")
        source = payload.get("from_release_id")
        target = payload.get("to_release_id")
        if source is not None and (
            not isinstance(source, str) or not _RELEASE_ID_RE.fullmatch(source)
        ):
            raise IntegrityError("transition journal source is invalid")
        source_previous = payload.get("from_previous_release_id")
        if source_previous is not None and (
            schema_version != 2
            or source is None
            or not isinstance(source_previous, str)
            or not _RELEASE_ID_RE.fullmatch(source_previous)
        ):
            raise IntegrityError("transition journal source predecessor is invalid")
        if not isinstance(target, str) or not _RELEASE_ID_RE.fullmatch(target):
            raise IntegrityError("transition journal target is invalid")
        failure = payload.get("failure_code")
        if failure is not None and (
            not isinstance(failure, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]{0,95}", failure)
        ):
            raise IntegrityError("transition journal failure code is invalid")
        if (payload["state"] == "failed") != (failure is not None):
            raise IntegrityError("transition journal state/failure coherence is invalid")
        return payload

    def finish_transition(self, path: Path, *, state: str, failure_code: str | None = None) -> None:
        with self.mutation_lock():
            self._finish_transition_locked(
                path,
                state=state,
                failure_code=failure_code,
            )

    def _finish_transition_locked(
        self, path: Path, *, state: str, failure_code: str | None = None
    ) -> None:
        if path.parent != self.transitions:
            raise IntegrityError("transition journal is outside the lifecycle root")
        if state not in {"committed", "failed", "recovered"}:
            raise IntegrityError("invalid terminal transition state")
        if (state == "failed") != (failure_code is not None):
            raise IntegrityError("terminal transition failure code is incoherent")
        payload = self._read_transition(path)
        if payload["state"] != "pending":
            raise IntegrityError("transition journal is already terminal")
        payload["state"] = state
        payload["failure_code"] = failure_code
        _atomic_json(path, payload)

    def records(self) -> tuple[ReleaseRecord, ...]:
        """Return every coherent installed release without following foreign paths."""

        if not self.releases.exists():
            return ()
        _assert_plain_path(self.releases, kind="directory")
        records: list[ReleaseRecord] = []
        for child in sorted(self.releases.iterdir(), key=lambda item: item.name):
            if child.is_symlink() or not child.is_dir():
                continue
            if not _RELEASE_ID_RE.fullmatch(child.name):
                continue
            records.append(self._read_release(child.name))
        return tuple(records)

    def recover(self) -> dict[str, int]:
        """Remove only provably non-authoritative transition debris.

        Persistent state (including observations and unknown newer bytes) is never
        traversed.  A directory with a durable release record is retained even when
        inactive; an active pointer must validate before cleanup begins.
        """

        with self.mutation_lock():
            return self._recover_locked()

    def _recover_locked(self) -> dict[str, int]:
        """Recover while the caller retains :meth:`mutation_lock`."""

        active: ReleaseRecord | None
        try:
            active = self.active(required=False)
        except IntegrityError:
            active = None
        active_id = active.release_id if active is not None else None
        active_release_restored = 0
        recovered_transitions = 0

        pending: list[tuple[Path, dict[str, Any]]] = []
        if self.transitions.exists():
            _assert_plain_path(self.transitions, kind="directory")
            for path in sorted(self.transitions.glob("trn_*.json")):
                try:
                    payload = self._read_transition(path)
                except IntegrityError:
                    continue
                if payload["state"] == "pending":
                    pending.append((path, payload))
        if pending:
            path, payload = pending[-1]
            source_id = payload["from_release_id"]
            if source_id is None:
                self.active_pointer.unlink(missing_ok=True)
                _fsync_directory(self.root)
                active_id = None
                active_release_restored = 1
            else:
                source = self._read_release(source_id)
                if payload.get("schema_version") == 2:
                    source = replace(
                        source,
                        previous_release_id=payload.get("from_previous_release_id"),
                    )
                self._commit_active(source)
                active_id = source.release_id
                active_release_restored = 1
            self._finish_transition_locked(path, state="recovered")
            recovered_transitions = 1
        elif self.active_pointer.exists() and active is None:
            # With no transition proof there is no safe release to guess.  Make the
            # partial pointer visibly inactive; coherent recorded releases remain.
            self.active_pointer.unlink(missing_ok=True)
            _fsync_directory(self.root)
        removed_releases = 0
        removed_temps = 0
        if self.releases.exists():
            _assert_plain_path(self.releases, kind="directory")
            for child in self.releases.iterdir():
                if child.is_symlink() or not child.is_dir():
                    continue
                if child.name == active_id or not _RELEASE_ID_RE.fullmatch(child.name):
                    continue
                if (child / "record.json").is_file():
                    continue
                shutil.rmtree(child)
                removed_releases += 1
            if removed_releases:
                _fsync_directory(self.releases)
        temp_pattern = re.compile(r"^\.active\.json\.[0-9]+\.tmp$")
        if self.root.exists():
            for child in self.root.iterdir():
                if child.is_symlink() or not child.is_file():
                    continue
                if temp_pattern.fullmatch(child.name):
                    child.unlink()
                    removed_temps += 1
            if removed_temps:
                _fsync_directory(self.root)
        result = {
            "incomplete_releases_removed": removed_releases,
            "pointer_temps_removed": removed_temps,
        }
        if active_release_restored:
            result["active_release_restored"] = active_release_restored
        if recovered_transitions:
            result["pending_transitions_recovered"] = recovered_transitions
        return result

    def rollback(
        self,
        *,
        expected_active_release_id: str | None | object = _CAS_UNSET,
    ) -> ReleaseRecord:
        with self.mutation_lock():
            current = self.active()
            assert current is not None
            expected = (
                current.release_id
                if expected_active_release_id is _CAS_UNSET
                else expected_active_release_id
            )
            if current.previous_release_id is None:
                raise IntegrityError("active release has no rollback target")
            return self.activate_existing(
                current.previous_release_id,
                expected_active_release_id=expected,
            )


@dataclass(frozen=True, slots=True)
class DoctorResult:
    ready: bool
    active_release_id: str | None
    codes: tuple[str, ...]
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class UninstallResult:
    purged: bool
    preserved_observations: bool


class LifecycleManager:
    """Hermes-independent doctor/update/rollback/uninstall orchestration."""

    def __init__(self, *, store: ReleaseStore, python_executable: Path) -> None:
        self.store = store
        self.python_executable = Path(python_executable)

    @staticmethod
    def _manager_authority_remediation() -> str:
        return (
            "run 'aether doctor', then 'aether reconcile --to active' or invoke "
            "'aether rollback' through the verified active manager"
        )

    def _active_manager_authority_locked(
        self,
    ) -> tuple[ReleaseRecord, Path, dict[str, Any]]:
        """Authenticate the manager environment owned by the active release.

        Version text is deliberately insufficient.  The active record, immutable wheel
        bytes, environment marker, packaged fingerprint, and installed-file fingerprint
        must all agree before this interpreter can be used as a mutation authority or a
        dispatch target.  Runtime/Hermes health is not part of this proof so a verified
        manager can still diagnose or roll back a broken runtime.
        """

        active = self.store.active()
        assert active is not None
        release = self.store.release_path(active.release_id)
        expected_fingerprint = active.installed_file_fingerprint
        if not isinstance(expected_fingerprint, str) or not _SHA256_RE.fullmatch(
            expected_fingerprint
        ):
            raise IntegrityError("active manager installed-file identity is unavailable")

        try:
            manifest = json.loads(read_private_bytes(release / "release.json").decode("utf-8"))
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as error:
            raise IntegrityError("active manager release evidence is unreadable") from error
        if (
            not isinstance(manifest, dict)
            or manifest.get("version") != active.version
            or manifest.get("wheel_filename") != active.wheel_filename
            or manifest.get("wheel_sha256") != active.wheel_sha256
            or manifest.get("installed_file_fingerprint") != expected_fingerprint
            or manifest.get("observation_compatibility") != active.observation_compatibility
        ):
            raise IntegrityError("active manager release evidence mismatch")

        artifact = release / "artifacts" / active.wheel_filename
        try:
            artifact_bytes = read_private_bytes(artifact)
        except (OSError, ValueError) as error:
            raise IntegrityError("active manager wheel artifact is unreadable") from error
        if hashlib.sha256(artifact_bytes).hexdigest() != active.wheel_sha256:
            raise IntegrityError("active manager wheel artifact identity mismatch")
        wheel_identity = self._inspect_wheel_bytes(artifact_bytes)
        if (
            wheel_identity.get("version") != active.version
            or wheel_identity.get("installed_file_fingerprint") != expected_fingerprint
            or wheel_identity.get("observation_compatibility") != active.observation_compatibility
        ):
            raise IntegrityError("active manager packaged identity mismatch")

        marker = release / "manager" / "aether-wheel.sha256"
        try:
            marker_digest = read_private_bytes(marker).decode("ascii").strip()
        except (OSError, UnicodeError, ValueError) as error:
            raise IntegrityError("active manager environment identity is unreadable") from error
        if marker_digest != active.wheel_sha256:
            raise IntegrityError("active manager environment identity mismatch")

        manager_python = self._environment_python(release / "manager")
        installed = self._installed_aether_identity(manager_python)
        if (
            installed.get("version") != active.version
            or installed.get("fingerprint") != expected_fingerprint
            or installed.get("observation_compatibility") != active.observation_compatibility
            or installed.get("observation_schema_sha256")
            != manifest.get("observation_schema_sha256")
        ):
            raise IntegrityError("active manager installed identity mismatch")
        return active, manager_python, installed

    def active_manager_dispatch_target(self) -> tuple[ReleaseRecord, Path] | None:
        """Return one authenticated dispatch target, or ``None`` before bootstrap."""

        with self.store.mutation_lock():
            if self.store.active(required=False) is None:
                return None
            active, manager_python, _identity = self._active_manager_authority_locked()
            return active, manager_python

    def _assert_executing_active_manager_locked(self) -> ReleaseRecord:
        active, manager_python, expected_identity = self._active_manager_authority_locked()
        executing_path = os.path.normcase(os.path.abspath(os.fspath(self.python_executable)))
        active_path = os.path.normcase(os.path.abspath(os.fspath(manager_python)))
        if executing_path != active_path:
            raise IntegrityError(
                "executing process is not the active manager; "
                + self._manager_authority_remediation()
            )
        executing_identity = self._installed_aether_identity(self.python_executable)
        if executing_identity != expected_identity:
            raise IntegrityError(
                "executing active manager identity changed; "
                + self._manager_authority_remediation()
            )
        return active

    def executing_active_manager(self) -> ReleaseRecord:
        """Prove this exact logical interpreter is the active release manager."""

        with self.store.mutation_lock():
            return self._assert_executing_active_manager_locked()

    def executing_manager_is_release_scoped(self) -> bool:
        """Return whether this interpreter belongs to any managed release manager.

        This lexical check intentionally does not resolve the venv's Python symlink:
        resolving it would collapse every environment onto the same system interpreter.
        It is used only to prevent a stale managed manager from redispatching recursively;
        authority still comes exclusively from the full fingerprint proof above.
        """

        executable = Path(os.path.abspath(os.fspath(self.python_executable)))
        releases = Path(os.path.abspath(os.fspath(self.store.releases)))
        try:
            relative = executable.relative_to(releases)
        except ValueError:
            return False
        expected_tail = (
            ("manager", "Scripts", "python.exe")
            if os.name == "nt"
            else ("manager", "bin", "python")
        )
        return (
            len(relative.parts) == 1 + len(expected_tail)
            and _RELEASE_ID_RE.fullmatch(relative.parts[0]) is not None
            and relative.parts[1:] == expected_tail
        )

    @staticmethod
    def _projection_pointer_value(value: Any, *, nullable: bool) -> str | None:
        if value is None and nullable:
            return None
        if not isinstance(value, str) or _PROJECTION_POINTER_NAME_RE.fullmatch(value) is None:
            raise IntegrityError("projection transition returned an invalid pointer identity")
        return value

    def _run_projection_transition_locked(
        self,
        record: ReleaseRecord,
        *,
        operation: str,
        expected_pointers: dict[str, str | None] | None = None,
    ) -> dict[str, Any]:
        """Execute projection work with the authenticated target release's code."""

        if operation not in {"prepare", "select", "unselect"}:
            raise IntegrityError("unsupported projection transition operation")
        compatibility = _validate_observation_compatibility(record.observation_compatibility)
        target_schema = compatibility["projection_schema_version"]
        manager_python = self._environment_python(
            self.store.release_path(record.release_id) / "manager"
        )
        request: dict[str, Any] = {
            "operation": operation,
            "state_root": str(self.store.state_root),
            "expected_schema": target_schema,
        }
        if operation == "prepare":
            if expected_pointers is not None:
                raise IntegrityError("prepare cannot receive projection pointer expectations")
        else:
            if operation == "select" and expected_pointers is None:
                raise IntegrityError("projection selection requires pointer expectations")
            if expected_pointers is None:
                request["expected_pointers"] = None
            else:
                if any(
                    _PROJECT_UUID_RE.fullmatch(project_id) is None
                    or self._projection_pointer_value(pointer, nullable=True) != pointer
                    for project_id, pointer in expected_pointers.items()
                ):
                    raise IntegrityError("projection pointer expectation is invalid")
                request["expected_pointers"] = dict(sorted(expected_pointers.items()))
        encoded = json.dumps(request, sort_keys=True, separators=(",", ":"))
        try:
            completed = subprocess.run(
                [
                    str(manager_python),
                    "-m",
                    "aether_agents.observation.projection_transition",
                ],
                input=encoded,
                check=False,
                capture_output=True,
                text=True,
                env=_isolated_subprocess_environment(),
            )
        except OSError as error:
            raise IntegrityError(
                "target projection transition interpreter is unavailable"
            ) from error
        if completed.returncode != 0:
            raise IntegrityError(
                f"projection transition failed ({operation} exit {completed.returncode})"
            )
        try:
            payload = json.loads(completed.stdout)
        except (UnicodeError, json.JSONDecodeError) as error:
            raise IntegrityError("projection transition returned malformed output") from error
        if not isinstance(payload, dict):
            raise IntegrityError("projection transition returned malformed output")
        common = {"operation", "target_schema", "project_count", "projects"}
        expected_keys = common | (
            {"selected_count"}
            if operation == "select"
            else {"unselected_count"}
            if operation == "unselect"
            else set()
        )
        if (
            set(payload) != expected_keys
            or payload.get("operation") != operation
            or payload.get("target_schema") != target_schema
            or type(payload.get("project_count")) is not int
            or payload["project_count"] < 0
            or not isinstance(payload.get("projects"), list)
            or payload["project_count"] != len(payload["projects"])
        ):
            raise IntegrityError("projection transition output is incoherent")
        rows: list[dict[str, Any]] = payload["projects"]
        project_ids: list[str] = []
        for row in rows:
            if not isinstance(row, dict):
                raise IntegrityError("projection transition project output is malformed")
            project_id = row.get("project_id")
            if not isinstance(project_id, str) or _PROJECT_UUID_RE.fullmatch(project_id) is None:
                raise IntegrityError("projection transition project identity is invalid")
            project_ids.append(project_id)
            if operation == "prepare":
                count_keys = {
                    "segments_seen",
                    "lines_seen",
                    "events_inserted",
                    "duplicate_events",
                    "quarantined_events",
                    "corrupt_segments",
                    "unclean_epochs",
                }
                if set(row) != {"project_id", "expected_pointer"} | count_keys:
                    raise IntegrityError("projection preparation output is malformed")
                self._projection_pointer_value(row["expected_pointer"], nullable=True)
                if any(type(row[key]) is not int or row[key] < 0 for key in count_keys):
                    raise IntegrityError("projection preparation counts are invalid")
            else:
                if set(row) != {"project_id", "previous_pointer", "selected_pointer"}:
                    raise IntegrityError("projection selection output is malformed")
                self._projection_pointer_value(row["previous_pointer"], nullable=True)
                self._projection_pointer_value(row["selected_pointer"], nullable=True)
                if operation == "unselect":
                    desired_pointer = (
                        None if expected_pointers is None else expected_pointers.get(project_id)
                    )
                    if row["selected_pointer"] != desired_pointer:
                        raise IntegrityError("projection deactivation output is incoherent")
        if project_ids != sorted(project_ids) or len(set(project_ids)) != len(project_ids):
            raise IntegrityError("projection transition project set is ambiguous")
        if expected_pointers is not None and set(project_ids) != set(expected_pointers):
            raise IntegrityError("projection transition project set changed")
        if operation != "prepare":
            count_key = "selected_count" if operation == "select" else "unselected_count"
            if (
                type(payload.get(count_key)) is not int
                or payload[count_key] < 0
                or payload[count_key] > len(rows)
                or (operation == "select" and payload[count_key] != len(rows))
            ):
                raise IntegrityError("projection transition selection count is invalid")
        return payload

    def _prepare_release_projections_locked(
        self,
        record: ReleaseRecord,
    ) -> dict[str, str | None]:
        result = self._run_projection_transition_locked(record, operation="prepare")
        return {row["project_id"]: row["expected_pointer"] for row in result["projects"]}

    def _select_release_projections_locked(
        self,
        record: ReleaseRecord,
        expected_pointers: dict[str, str | None],
    ) -> None:
        self._run_projection_transition_locked(
            record,
            operation="select",
            expected_pointers=expected_pointers,
        )

    def _reconcile_release_projections_locked(self, record: ReleaseRecord) -> None:
        expected = self._prepare_release_projections_locked(record)
        self._select_release_projections_locked(record, expected)

    def _deactivate_release_projections_locked(self, record: ReleaseRecord) -> None:
        self._run_projection_transition_locked(
            record,
            operation="unselect",
            expected_pointers=None,
        )

    def recover(self) -> dict[str, int]:
        """Recover bounded transition debris and re-prove any restored active release."""

        with self.store.mutation_lock():
            if self.store.active(required=False) is not None:
                self._assert_executing_active_manager_locked()
            return self._recover_locked()

    def recover_for_rollback(self) -> dict[str, int]:
        """Recover transition structure without requiring a healthy active runtime."""

        with self.store.mutation_lock():
            self._assert_executing_active_manager_locked()
            return self.store._recover_locked()

    def _recover_locked(self) -> dict[str, int]:
        result = self.store._recover_locked()
        active = self.store.active(required=False)
        if active is not None:
            self.validate_release(active.release_id)
            self._materialize_profile_homes(active)
            self._validate_profile_homes(active)
            self._reconcile_release_projections_locked(active)
        else:
            # A pending initial install can crash after profile materialization but
            # before (or just after) the active pointer switch.  No active release
            # means no observer authority: remove only Aether-owned activation bytes.
            self._deactivate_profile_homes()
        return result

    def _capture_expected_active(self) -> str | None | object:
        try:
            active = self.store.active(required=False)
        except IntegrityError:
            return _CAS_UNSET
        return active.release_id if active is not None else None

    def _assert_expected_active_locked(
        self, expected_active_release_id: str | None | object
    ) -> str | None:
        active = self.store.active(required=False)
        active_id = active.release_id if active is not None else None
        if expected_active_release_id is not _CAS_UNSET and active_id != expected_active_release_id:
            raise IntegrityError("active release changed concurrently; stale transition refused")
        return active_id

    @staticmethod
    def _resolve_wheel(wheel: Path | str) -> Path:
        candidate = Path(wheel).expanduser()
        if candidate.is_symlink():
            raise IntegrityError("Aether wheel must not be a symlink")
        try:
            source_wheel = candidate.resolve(strict=True)
        except OSError as error:
            raise IntegrityError("Aether wheel is unavailable") from error
        if not source_wheel.is_file():
            raise IntegrityError("Aether wheel must be a regular file")
        return source_wheel

    def inspect_candidate(
        self,
        *,
        wheel: Path | str,
        hermes_checkout: Path | str,
        release_lock: Path | str,
    ) -> dict[str, str]:
        """Return content-free identity only after verifying both local inputs."""

        source_wheel = self._resolve_wheel(wheel)
        evidence = verify_clean_checkout(
            hermes_checkout,
            expected_tag=HERMES_BASELINE.tag,
            expected_commit=HERMES_BASELINE.commit,
            expected_tag_object=HERMES_BASELINE.tag_object,
        )
        metadata = self._inspect_wheel(source_wheel)
        validated_lock = load_release_lock(release_lock)
        self._validate_aether_identity(validated_lock.aether_identity, metadata)
        self._validate_observer_lock_binding(validated_lock, metadata)
        with tempfile.TemporaryDirectory(prefix="aether-hermes-source-") as temporary:
            materialized = Path(temporary) / "source"
            _materialize_git_archive(evidence.path, evidence.commit, materialized)
            if _tree_sha256(materialized) != validated_lock.hermes_source_tree_sha256:
                raise IntegrityError("release lock Hermes source digest mismatch")
        return {
            "version": metadata["version"],
            "wheel_filename": source_wheel.name,
            "wheel_sha256": _sha256(source_wheel),
        }

    @staticmethod
    def _validate_aether_identity(
        identity: AetherPrebuildIdentity,
        wheel_identity: dict[str, Any],
    ) -> None:
        """Prove the external six-field tuple agrees with inspectable wheel metadata."""

        if (
            wheel_identity.get("distribution") != identity.distribution
            or wheel_identity.get("version") != identity.package_version
            or wheel_identity.get("python_requires") != identity.python_requires
            or wheel_identity.get("observer") != identity.observer
        ):
            raise IntegrityError("Aether release-lock identity disagrees with wheel metadata")

    @staticmethod
    def _validate_observer_lock_binding(
        release_lock: ValidatedReleaseLock,
        wheel_identity: dict[str, Any],
    ) -> None:
        if (
            wheel_identity.get("observer_requirements_sha256")
            != release_lock.observer_requirements_sha256
        ):
            raise IntegrityError("Aether release-lock observer dependency digest mismatch")
        if (
            wheel_identity.get("observation_compatibility")
            != release_lock.observation_compatibility
        ):
            raise IntegrityError(
                "Aether release-lock observation compatibility disagrees with wheel"
            )

    @staticmethod
    def _profile_source(role: str) -> Path:
        if role not in _PROFILE_ROLES:
            raise IntegrityError("unknown managed profile")
        return Path(__file__).parent / "resources" / "profiles" / role / "config.yaml"

    def _materialize_profile_bundle(self, stage: Path) -> str:
        profiles: dict[str, dict[str, str]] = {}
        profiles_root = stage / "profiles"
        _create_private_directory(profiles_root)
        for role in _PROFILE_ROLES:
            source = self._profile_source(role)
            if source.is_symlink() or not source.is_file():
                raise IntegrityError("packaged profile resource is unavailable")
            try:
                data = read_private_bytes(source)
            except (OSError, ValueError) as error:
                raise IntegrityError("packaged profile resource is unreadable") from error
            target_dir = profiles_root / role
            _create_private_directory(target_dir)
            target = target_dir / "config.yaml"
            self._write_durable(target, data)
            profiles[role] = {
                "path": f"profiles/{role}/config.yaml",
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        manifest = {
            "schema_version": 1,
            "observer_entry_point": HERMES_BASELINE.observer_entry_point,
            "roles": list(_PROFILE_ROLES),
            "profiles": profiles,
        }
        manifest_path = stage / "profile-bundle.json"
        _atomic_json(manifest_path, manifest)
        return _sha256(manifest_path)

    def _capture_profile_product_state(self) -> dict[Path, bytes | None]:
        """Snapshot only the two Aether-owned files in each persistent role home."""

        snapshot: dict[Path, bytes | None] = {}
        for role in _PROFILE_ROLES:
            home = self.store.profile_home(role)
            if home.is_symlink():
                raise IntegrityError("managed profile home must not be a symlink")
            for name in ("config.yaml", "aether-observer.json"):
                path = home / name
                if path.is_symlink():
                    raise IntegrityError("managed profile product file must not be a symlink")
                try:
                    snapshot[path] = read_private_bytes(path) if path.is_file() else None
                except (OSError, ValueError) as error:
                    raise IntegrityError("managed profile product file is unreadable") from error
        return snapshot

    @staticmethod
    def _restore_profile_product_state(snapshot: dict[Path, bytes | None]) -> None:
        for path, data in snapshot.items():
            if data is None:
                _unlink_private_file(path, missing_ok=True)
                if path.parent.exists():
                    _fsync_directory(path.parent)
            else:
                _atomic_bytes(path, data)

    @staticmethod
    def _profile_activation(record: ReleaseRecord, role: str) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "role": role,
            "release_id": record.release_id,
            "wheel_sha256": record.wheel_sha256,
            "prebuild_identity": record.prebuild_identity,
            "installed_file_fingerprint": record.installed_file_fingerprint,
            "observer": dict(record.observer),
        }

    def _materialize_profile_homes(self, record: ReleaseRecord) -> None:
        """Activate one immutable bundle in three explicit, disposable-capable homes."""

        release = self.store.release_path(record.release_id)
        ensure_private_dir(self.store.profile_homes)
        for role in _PROFILE_ROLES:
            source = release / "profiles" / role / "config.yaml"
            if source.is_symlink() or not source.is_file():
                raise IntegrityError("managed profile configuration is missing")
            home = self.store.profile_home(role)
            if home.is_symlink():
                raise IntegrityError("managed profile home must not be a symlink")
            ensure_private_dir(home)
            try:
                source_bytes = read_private_bytes(source)
            except (OSError, ValueError) as error:
                raise IntegrityError("managed profile configuration is unreadable") from error
            _atomic_bytes(home / "config.yaml", source_bytes)
            _atomic_json(home / "aether-observer.json", self._profile_activation(record, role))
        _fsync_directory(self.store.profile_homes)

    def _validate_profile_homes(self, record: ReleaseRecord) -> None:
        release = self.store.release_path(record.release_id)
        if self.store.profile_homes.is_symlink() or not self.store.profile_homes.is_dir():
            raise IntegrityError("managed profile homes are unavailable")
        for role in _PROFILE_ROLES:
            home = self.store.profile_home(role)
            source = release / "profiles" / role / "config.yaml"
            config = home / "config.yaml"
            activation = home / "aether-observer.json"
            if any(path.is_symlink() for path in (home, config, activation)):
                raise IntegrityError("managed profile activation contains a symlink")
            if not home.is_dir() or not config.is_file() or not activation.is_file():
                raise IntegrityError("managed profile activation is incomplete")
            try:
                config_bytes = read_private_bytes(config)
                source_bytes = read_private_bytes(source)
                activation_bytes = read_private_bytes(activation)
            except (OSError, ValueError) as error:
                raise IntegrityError("managed profile activation is unreadable") from error
            if config_bytes != source_bytes:
                raise IntegrityError("managed profile activation configuration drift")
            try:
                payload = json.loads(activation_bytes.decode("utf-8"))
            except (UnicodeError, json.JSONDecodeError) as error:
                raise IntegrityError("managed profile activation is unreadable") from error
            if payload != self._profile_activation(record, role):
                raise IntegrityError("managed profile activation identity mismatch")
            if os.name == "posix" and (
                stat.S_IMODE(home.stat().st_mode) != DIR_MODE
                or stat.S_IMODE(config.stat().st_mode) != FILE_MODE
                or stat.S_IMODE(activation.stat().st_mode) != FILE_MODE
            ):
                raise IntegrityError("managed profile activation permissions mismatch")

    def _deactivate_profile_homes(self) -> None:
        """Remove only Aether-owned activation bytes; retain unknown role state."""

        if not self.store.profile_homes.exists():
            return
        if self.store.profile_homes.is_symlink() or not self.store.profile_homes.is_dir():
            raise IntegrityError("managed profile homes are unsafe to deactivate")
        for role in _PROFILE_ROLES:
            home = self.store.profile_home(role)
            if not home.exists():
                continue
            if home.is_symlink() or not home.is_dir():
                raise IntegrityError("managed profile home is unsafe to deactivate")
            activation = home / "aether-observer.json"
            if activation.exists() or activation.is_symlink():
                activation.unlink()
            config = home / "config.yaml"
            source = self._profile_source(role)
            if (
                config.is_file()
                and not config.is_symlink()
                and source.is_file()
                and not source.is_symlink()
            ):
                try:
                    product_owned = read_private_bytes(config) == read_private_bytes(source)
                except (OSError, ValueError) as error:
                    raise IntegrityError("managed profile configuration is unreadable") from error
                if product_owned:
                    config.unlink()
            _fsync_directory(home)
        _fsync_directory(self.store.profile_homes)

    def prepare_release(
        self,
        *,
        wheel: Path | str,
        hermes_checkout: Path | str,
        release_lock: Path | str,
    ) -> PreparedRelease:
        """Build two isolated environments from one immutable wheel.

        The public Hermes checkout is verified before any candidate environment is
        created.  Failure leaves the candidate below ``staging/`` for bounded local
        diagnosis and never changes ``active.json``.
        """

        with self.store.mutation_lock():
            return self._prepare_release_locked(
                wheel=wheel,
                hermes_checkout=hermes_checkout,
                release_lock=release_lock,
            )

    def _prepare_release_locked(
        self,
        *,
        wheel: Path | str,
        hermes_checkout: Path | str,
        release_lock: Path | str,
    ) -> PreparedRelease:
        """Prepare while the caller retains the lifecycle mutation lock."""

        source_wheel = self._resolve_wheel(wheel)
        evidence = verify_clean_checkout(
            hermes_checkout,
            expected_tag=HERMES_BASELINE.tag,
            expected_commit=HERMES_BASELINE.commit,
            expected_tag_object=HERMES_BASELINE.tag_object,
        )
        metadata = self._inspect_wheel(source_wheel)
        validated_lock = load_release_lock(release_lock)
        aether_identity = validated_lock.aether_identity
        self._validate_aether_identity(aether_identity, metadata)
        self._validate_observer_lock_binding(validated_lock, metadata)
        version = metadata["version"]
        digest = _sha256(source_wheel)
        stage_parent = self.store.releases
        ensure_private_dir(stage_parent)
        release_id = f"{version}-{digest[:16]}"
        stage = self.store.release_path(release_id)
        try:
            _create_private_directory(stage)
        except FileExistsError as error:
            raise IntegrityError(
                "candidate release path already exists; inspect or activate it explicitly"
            ) from error
        artifact_dir = stage / "artifacts"
        _create_private_directory(artifact_dir)
        staged_wheel = artifact_dir / source_wheel.name
        self._copy_durable(source_wheel, staged_wheel, expected_sha256=digest)
        self._write_durable(stage / "release-lock.json", validated_lock.raw_bytes)
        observer_requirements = artifact_dir / "observer-requirements.txt"
        self._write_durable(observer_requirements, metadata["observer_requirements"])

        # The exact public Hermes release intentionally refuses wheel/sdist builds.
        # Materialize only the bytes tracked by the authenticated commit.  A clean
        # worktree says nothing about ignored ``.env`` or editable-install debris,
        # so copying the worktree is never an acceptable release boundary.
        hermes_source = stage / "hermes-source"
        _materialize_git_archive(evidence.path, evidence.commit, hermes_source)
        hermes_source_sha256 = _tree_sha256(hermes_source)
        if hermes_source_sha256 != validated_lock.hermes_source_tree_sha256:
            raise IntegrityError("release lock Hermes source digest mismatch")

        manager = stage / "manager"
        runtime = stage / "runtime"
        self._run_uv("--no-config", "venv", "--python", str(self.python_executable), str(manager))
        self._run_uv("--no-config", "venv", "--python", str(self.python_executable), str(runtime))
        manager_python = self._environment_python(manager)
        runtime_python = self._environment_python(runtime)
        self._install_observer_dependencies(manager_python, observer_requirements)
        self._run_uv(
            "--no-config",
            "pip",
            "install",
            "--python",
            str(manager_python),
            "--no-deps",
            str(staged_wheel),
        )
        hermes_dependency_evidence = self._install_hermes_from_lock(
            hermes_source,
            runtime_python,
            artifact_dir / "hermes-requirements.txt",
        )
        self._install_observer_dependencies(
            runtime_python,
            observer_requirements,
            synchronize=False,
        )
        self._run_uv(
            "--no-config",
            "pip",
            "install",
            "--python",
            str(runtime_python),
            "--no-deps",
            str(staged_wheel),
        )

        self._verify_installed_environment(manager_python, runtime=False)
        self._verify_installed_environment(runtime_python, runtime=True)

        manager_identity = self._installed_aether_identity(manager_python)
        runtime_identity = self._installed_aether_identity(runtime_python)
        if manager_identity != runtime_identity:
            raise IntegrityError("manager/runtime installed-file identity mismatch")
        if manager_identity["version"] != version:
            raise IntegrityError("installed Aether version differs from wheel metadata")
        if manager_identity["fingerprint"] != metadata["installed_file_fingerprint"]:
            raise IntegrityError("installed Aether identity differs from staged wheel")
        if (
            manager_identity["observation_compatibility"] != metadata["observation_compatibility"]
            or manager_identity["observation_schema_sha256"]
            != metadata["observation_schema_sha256"]
        ):
            raise IntegrityError("installed observation contract differs from staged wheel")
        for environment_python in (manager_python, runtime_python):
            for distribution, expected_version in _observer_locked_distributions_for_python(
                environment_python
            ).items():
                observed_version = self._installed_distribution_version(
                    environment_python, distribution
                )
                if observed_version != expected_version:
                    raise IntegrityError("installed observer runtime dependency mismatch")
        hermes_version = self._installed_distribution_version(
            runtime_python, HERMES_BASELINE.distribution
        )
        if hermes_version != HERMES_BASELINE.version:
            raise IntegrityError("installed Hermes distribution version mismatch")

        for environment in (manager, runtime):
            marker = environment / "aether-wheel.sha256"
            self._write_durable(marker, (digest + "\n").encode("ascii"))
        profile_bundle_sha256 = self._materialize_profile_bundle(stage)
        if profile_bundle_sha256 != validated_lock.profile_bundle_sha256:
            raise IntegrityError("release lock profile bundle digest mismatch")
        release_manifest = {
            "schema_version": 3,
            "version": version,
            "wheel_filename": source_wheel.name,
            "wheel_sha256": digest,
            "installed_file_fingerprint": manager_identity["fingerprint"],
            "aether_identity": aether_identity.to_record(),
            "prebuild_identity": aether_identity.digest,
            "observer": metadata["observer"],
            "observation_compatibility": metadata["observation_compatibility"],
            "observation_schema_sha256": metadata["observation_schema_sha256"],
            "hermes_repository": HERMES_BASELINE.repository,
            "hermes_tag": evidence.tag,
            "hermes_tag_object": evidence.tag_object,
            "hermes_commit": evidence.commit,
            "hermes_version": hermes_version,
            "hermes_source_sha256": hermes_source_sha256,
            "locked_hermes_source_tree_sha256": (validated_lock.hermes_source_tree_sha256),
            "release_lock_sha256": validated_lock.sha256,
            "hermes_uv_lock_sha256": hermes_dependency_evidence["uv_lock_sha256"],
            "hermes_requirements_sha256": hermes_dependency_evidence["requirements_sha256"],
            "observer_runtime_dependencies": dict(_OBSERVER_RUNTIME_DEPENDENCIES),
            "observer_locked_distributions": dict(_OBSERVER_LOCKED_DISTRIBUTIONS),
            "observer_requirements_sha256": metadata["observer_requirements_sha256"],
            "observer_entry_point": HERMES_BASELINE.observer_entry_point,
            "profile_bundle_sha256": profile_bundle_sha256,
            "authority_context": AuthorityContext.for_active_release(release_id).to_record(),
        }
        _atomic_json(stage / "release.json", release_manifest)
        self.store._harden_tree(stage)
        _fsync_directory(stage_parent)
        return PreparedRelease(
            version=version,
            wheel=staged_wheel,
            wheel_sha256=digest,
            stage=stage,
            hermes_tag=evidence.tag,
            hermes_commit=evidence.commit,
            aether_identity=aether_identity.to_record(),
            prebuild_identity=aether_identity.digest,
            installed_file_fingerprint=metadata["installed_file_fingerprint"],
            observation_compatibility=metadata["observation_compatibility"],
        )

    def install(
        self,
        *,
        wheel: Path | str,
        hermes_checkout: Path | str,
        release_lock: Path | str,
        expected_active_release_id: str | None | object = _CAS_UNSET,
    ) -> ReleaseRecord:
        """Prepare, verify and atomically activate one release."""

        expected = (
            self._capture_expected_active()
            if expected_active_release_id is _CAS_UNSET
            else expected_active_release_id
        )
        with self.store.mutation_lock():
            if self.store.active(required=False) is not None:
                self._assert_executing_active_manager_locked()
            self._recover_locked()
            if expected is _CAS_UNSET:
                expected = self._assert_expected_active_locked(_CAS_UNSET)
            else:
                self._assert_expected_active_locked(expected)
            record = self.store._register_locked(
                self._prepare_release_locked(
                    wheel=wheel,
                    hermes_checkout=hermes_checkout,
                    release_lock=release_lock,
                )
            )
            return self._activate_existing_locked(
                record.release_id,
                transition_kind="install",
                expected_active_release_id=expected,
            )

    def update(
        self,
        *,
        wheel: Path | str,
        hermes_checkout: Path | str,
        release_lock: Path | str,
        expected_active_release_id: str | None | object = _CAS_UNSET,
    ) -> ReleaseRecord:
        """Stage a complete candidate before changing the active record."""

        expected = (
            self._capture_expected_active()
            if expected_active_release_id is _CAS_UNSET
            else expected_active_release_id
        )
        with self.store.mutation_lock():
            self._assert_executing_active_manager_locked()
            self._recover_locked()
            if expected is _CAS_UNSET:
                expected = self._assert_expected_active_locked(_CAS_UNSET)
            else:
                self._assert_expected_active_locked(expected)
            record = self.store._register_locked(
                self._prepare_release_locked(
                    wheel=wheel,
                    hermes_checkout=hermes_checkout,
                    release_lock=release_lock,
                )
            )
            return self._activate_existing_locked(
                record.release_id,
                transition_kind="update",
                expected_active_release_id=expected,
            )

    def _validate_profile_bundle(self, release: Path, release_manifest: dict[str, Any]) -> None:
        manifest_path = release / "profile-bundle.json"
        if manifest_path.is_symlink() or not manifest_path.is_file():
            raise IntegrityError("managed profile bundle manifest is missing")
        if os.name == "posix" and stat.S_IMODE(manifest_path.stat().st_mode) != FILE_MODE:
            raise IntegrityError("managed profile bundle permissions mismatch")
        expected_digest = release_manifest.get("profile_bundle_sha256")
        if not isinstance(expected_digest, str) or not _SHA256_RE.fullmatch(expected_digest):
            raise IntegrityError("managed profile bundle identity is missing")
        try:
            manifest_bytes = read_private_bytes(manifest_path)
            profile_manifest = json.loads(manifest_bytes.decode("utf-8"))
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as error:
            raise IntegrityError("managed profile bundle manifest is unreadable") from error
        if hashlib.sha256(manifest_bytes).hexdigest() != expected_digest:
            raise IntegrityError("managed profile bundle digest mismatch")
        if (
            not isinstance(profile_manifest, dict)
            or profile_manifest.get("schema_version") != 1
            or profile_manifest.get("roles") != list(_PROFILE_ROLES)
            or profile_manifest.get("observer_entry_point") != HERMES_BASELINE.observer_entry_point
            or set(profile_manifest)
            != {
                "schema_version",
                "observer_entry_point",
                "roles",
                "profiles",
            }
        ):
            raise IntegrityError("managed profile bundle contract mismatch")
        profiles = profile_manifest.get("profiles")
        if not isinstance(profiles, dict) or set(profiles) != set(_PROFILE_ROLES):
            raise IntegrityError("managed profile role set mismatch")
        profiles_root = release / "profiles"
        if profiles_root.is_symlink() or not profiles_root.is_dir():
            raise IntegrityError("managed profile directory is invalid")
        if os.name == "posix" and stat.S_IMODE(profiles_root.stat().st_mode) != DIR_MODE:
            raise IntegrityError("managed profile directory permissions mismatch")
        children = tuple(profiles_root.iterdir())
        observed_roles = {child.name for child in children}
        if observed_roles != set(_PROFILE_ROLES):
            raise IntegrityError("managed profile directory set mismatch")
        for role in _PROFILE_ROLES:
            expected_path = f"profiles/{role}/config.yaml"
            details = profiles.get(role)
            if not isinstance(details, dict) or set(details) != {"path", "sha256"}:
                raise IntegrityError("managed profile evidence is malformed")
            if details.get("path") != expected_path:
                raise IntegrityError("managed profile path mismatch")
            source = self._profile_source(role)
            role_root = profiles_root / role
            target = release / expected_path
            if (
                role_root.is_symlink()
                or not role_root.is_dir()
                or source.is_symlink()
                or not source.is_file()
                or target.is_symlink()
                or not target.is_file()
            ):
                raise IntegrityError("managed profile configuration is missing")
            if {child.name for child in role_root.iterdir()} != {"config.yaml"}:
                raise IntegrityError("managed profile contains unknown product bytes")
            if os.name == "posix" and (
                stat.S_IMODE(role_root.stat().st_mode) != DIR_MODE
                or stat.S_IMODE(target.stat().st_mode) != FILE_MODE
            ):
                raise IntegrityError("managed profile configuration permissions mismatch")
            try:
                expected_bytes = read_private_bytes(source)
                observed_bytes = read_private_bytes(target)
            except (OSError, ValueError) as error:
                raise IntegrityError("managed profile configuration is unreadable") from error
            if observed_bytes != expected_bytes:
                raise IntegrityError("managed profile configuration drift")
            digest = hashlib.sha256(expected_bytes).hexdigest()
            if details.get("sha256") != digest:
                raise IntegrityError("managed profile configuration digest mismatch")

    def validate_release(self, release_id: str) -> ReleaseRecord:
        """Re-prove every activation boundary for an installed release."""

        record = self.store._read_release(release_id)
        release = self.store.release_path(release_id)
        manifest_path = release / "release.json"
        if manifest_path.is_symlink() or not manifest_path.is_file():
            raise IntegrityError("release installation evidence is missing")
        try:
            manifest = json.loads(read_private_bytes(manifest_path).decode("utf-8"))
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as error:
            raise IntegrityError("release installation evidence is unreadable") from error
        if not isinstance(manifest, dict):
            raise IntegrityError("release installation evidence is malformed")
        expected_fields = {
            "version": record.version,
            "wheel_filename": record.wheel_filename,
            "wheel_sha256": record.wheel_sha256,
            "hermes_repository": HERMES_BASELINE.repository,
            "hermes_tag": HERMES_BASELINE.tag,
            "hermes_tag_object": HERMES_BASELINE.tag_object,
            "hermes_commit": HERMES_BASELINE.commit,
            "hermes_version": HERMES_BASELINE.version,
            "observer_entry_point": HERMES_BASELINE.observer_entry_point,
            "observer": dict(record.observer),
            "aether_identity": record.aether_identity,
            "prebuild_identity": record.prebuild_identity,
            "installed_file_fingerprint": record.installed_file_fingerprint,
            "observation_compatibility": record.observation_compatibility,
            "observer_runtime_dependencies": dict(_OBSERVER_RUNTIME_DEPENDENCIES),
            "observer_locked_distributions": dict(_OBSERVER_LOCKED_DISTRIBUTIONS),
            "authority_context": record.authority_context,
        }
        expected_manifest_keys = set(expected_fields) | {
            "schema_version",
            "profile_bundle_sha256",
            "observation_schema_sha256",
            "hermes_source_sha256",
            "locked_hermes_source_tree_sha256",
            "hermes_uv_lock_sha256",
            "hermes_requirements_sha256",
            "release_lock_sha256",
            "observer_requirements_sha256",
        }
        if (
            set(manifest) != expected_manifest_keys
            or manifest.get("schema_version") != 3
            or any(manifest.get(key) != value for key, value in expected_fields.items())
        ):
            if manifest.get("observation_compatibility") != record.observation_compatibility:
                raise IntegrityError("observation compatibility declaration mismatch")
            raise IntegrityError("release installation evidence disagrees with its record")
        release_lock_sha256 = manifest.get("release_lock_sha256")
        release_lock_path = release / "release-lock.json"
        if (
            not isinstance(release_lock_sha256, str)
            or not _SHA256_RE.fullmatch(release_lock_sha256)
            or release_lock_path.is_symlink()
            or not release_lock_path.is_file()
            or _sha256(release_lock_path) != release_lock_sha256
        ):
            raise IntegrityError("release lock digest mismatch")
        validated_lock = load_release_lock(release_lock_path)
        if (
            validated_lock.sha256 != release_lock_sha256
            or validated_lock.aether_identity.to_record() != record.aether_identity
        ):
            raise IntegrityError("release lock identity mismatch")
        observer_requirements_sha256 = manifest.get("observer_requirements_sha256")
        observer_requirements = release / "artifacts" / "observer-requirements.txt"
        if (
            not isinstance(observer_requirements_sha256, str)
            or not _SHA256_RE.fullmatch(observer_requirements_sha256)
            or observer_requirements_sha256 != validated_lock.observer_requirements_sha256
            or observer_requirements.is_symlink()
            or not observer_requirements.is_file()
            or _sha256(observer_requirements) != observer_requirements_sha256
        ):
            raise IntegrityError("observer dependency lock digest mismatch")
        _validate_observer_requirements(observer_requirements.read_bytes())
        _validate_observation_compatibility(manifest.get("observation_compatibility"))
        aether_identity = AetherPrebuildIdentity.from_record(manifest.get("aether_identity"))
        if aether_identity.digest != record.prebuild_identity:
            raise IntegrityError("prebuild identity digest mismatch")
        fingerprint = manifest.get("installed_file_fingerprint")
        if not isinstance(fingerprint, str) or not _SHA256_RE.fullmatch(fingerprint):
            raise IntegrityError("installed-file fingerprint evidence is missing")
        if fingerprint != record.installed_file_fingerprint:
            raise IntegrityError("installed-file fingerprint evidence mismatch")
        schema_sha256 = manifest.get("observation_schema_sha256")
        if (
            not isinstance(schema_sha256, dict)
            or set(schema_sha256) != {"event", "summary", "manifest"}
            or any(
                not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest)
                for digest in schema_sha256.values()
            )
        ):
            raise IntegrityError("observation schema identity evidence is malformed")
        hermes_source_sha256 = manifest.get("hermes_source_sha256")
        if not isinstance(hermes_source_sha256, str) or not _SHA256_RE.fullmatch(
            hermes_source_sha256
        ):
            raise IntegrityError("Hermes source identity evidence is malformed")
        hermes_source = release / "hermes-source"
        if hermes_source.is_symlink() or not hermes_source.is_dir():
            raise IntegrityError("Hermes release source is unavailable")
        if _tree_sha256(hermes_source) != hermes_source_sha256:
            raise IntegrityError("Hermes source digest mismatch")
        locked_source_sha256 = manifest.get("locked_hermes_source_tree_sha256")
        if (
            not isinstance(locked_source_sha256, str)
            or not _SHA256_RE.fullmatch(locked_source_sha256)
            or locked_source_sha256 != hermes_source_sha256
            or locked_source_sha256 != validated_lock.hermes_source_tree_sha256
        ):
            raise IntegrityError("release lock Hermes source digest mismatch")
        lock_sha256 = manifest.get("hermes_uv_lock_sha256")
        requirements_sha256 = manifest.get("hermes_requirements_sha256")
        hermes_lock = hermes_source / "uv.lock"
        requirements = release / "artifacts" / "hermes-requirements.txt"
        if (
            not isinstance(lock_sha256, str)
            or not _SHA256_RE.fullmatch(lock_sha256)
            or hermes_lock.is_symlink()
            or not hermes_lock.is_file()
            or _sha256(hermes_lock) != lock_sha256
        ):
            raise IntegrityError("Hermes dependency lock identity mismatch")
        if (
            not isinstance(requirements_sha256, str)
            or not _SHA256_RE.fullmatch(requirements_sha256)
            or requirements.is_symlink()
            or not requirements.is_file()
            or _sha256(requirements) != requirements_sha256
        ):
            raise IntegrityError("Hermes frozen dependency export identity mismatch")
        artifact = release / "artifacts" / record.wheel_filename
        if artifact.is_symlink() or not artifact.is_file():
            raise IntegrityError("installed wheel artifact is missing")
        try:
            artifact_bytes = read_private_bytes(artifact)
        except (OSError, ValueError) as error:
            raise IntegrityError("installed wheel artifact is unreadable") from error
        if hashlib.sha256(artifact_bytes).hexdigest() != record.wheel_sha256:
            raise IntegrityError("installed wheel artifact digest mismatch")
        wheel_identity = self._inspect_wheel_bytes(artifact_bytes)
        self._validate_aether_identity(aether_identity, wheel_identity)
        self._validate_observer_lock_binding(validated_lock, wheel_identity)
        if (
            wheel_identity["installed_file_fingerprint"] != record.installed_file_fingerprint
            or wheel_identity["observation_compatibility"] != record.observation_compatibility
            or wheel_identity["observation_schema_sha256"] != schema_sha256
            or wheel_identity["observer"] != OBSERVER_ENTRY_POINT
        ):
            raise IntegrityError("staged wheel observation identity mismatch")
        self._validate_profile_bundle(release, manifest)
        if manifest.get("profile_bundle_sha256") != validated_lock.profile_bundle_sha256:
            raise IntegrityError("release lock profile bundle digest mismatch")

        identities: list[dict[str, Any]] = []
        for environment_name in ("manager", "runtime"):
            environment = release / environment_name
            marker = environment / "aether-wheel.sha256"
            if marker.is_symlink() or not marker.is_file():
                raise IntegrityError(f"{environment_name} wheel identity is missing")
            try:
                marker_digest = read_private_bytes(marker).decode("ascii").strip()
            except (OSError, UnicodeError, ValueError) as error:
                raise IntegrityError(f"{environment_name} wheel identity is unreadable") from error
            if marker_digest != record.wheel_sha256:
                raise IntegrityError(f"{environment_name} wheel identity mismatch")
            identity = self._installed_aether_identity(self._environment_python(environment))
            if identity["version"] != record.version:
                raise IntegrityError("installed Aether version mismatch")
            if identity["fingerprint"] != fingerprint:
                raise IntegrityError("installed-file fingerprint mismatch")
            if (
                identity["observation_compatibility"] != record.observation_compatibility
                or identity["observation_schema_sha256"] != schema_sha256
            ):
                raise IntegrityError("installed observation compatibility mismatch")
            identities.append(identity)
        if identities[0] != identities[1]:
            raise IntegrityError("manager/runtime installed identity mismatch")
        hermes_version = self._installed_distribution_version(
            self._environment_python(release / "runtime"),
            HERMES_BASELINE.distribution,
        )
        if hermes_version != HERMES_BASELINE.version:
            raise IntegrityError("installed Hermes distribution version mismatch")
        for environment_name in ("manager", "runtime"):
            environment_python = self._environment_python(release / environment_name)
            for distribution, expected_version in _observer_locked_distributions_for_python(
                environment_python
            ).items():
                observed_version = self._installed_distribution_version(
                    environment_python, distribution
                )
                if observed_version != expected_version:
                    raise IntegrityError("installed observer runtime dependency mismatch")
        return record

    def activate_existing(
        self,
        release_id: str,
        *,
        transition_kind: str = "update",
        expected_active_release_id: str | None | object = _CAS_UNSET,
    ) -> ReleaseRecord:
        """Validate, journal, switch, revalidate, or restore the prior release."""

        expected = (
            self._capture_expected_active()
            if expected_active_release_id is _CAS_UNSET
            else expected_active_release_id
        )
        with self.store.mutation_lock():
            active = self.store.active(required=False)
            if active is None:
                if transition_kind != "install":
                    raise IntegrityError("no active manager can authorize this transition")
            else:
                self._assert_executing_active_manager_locked()
            if transition_kind == "rollback":
                self.store._recover_locked()
            else:
                self._recover_locked()
            if expected is _CAS_UNSET:
                expected = self._assert_expected_active_locked(_CAS_UNSET)
            return self._activate_existing_locked(
                release_id,
                transition_kind=transition_kind,
                expected_active_release_id=expected,
            )

    def _activate_existing_locked(
        self,
        release_id: str,
        *,
        transition_kind: str,
        expected_active_release_id: str | None | object,
    ) -> ReleaseRecord:
        self._assert_expected_active_locked(expected_active_release_id)
        target = self.validate_release(release_id)
        previous = self.store.active(required=False)
        if previous is not None and transition_kind != "rollback":
            self.validate_release(previous.release_id)
            if _projection_schema_ordinal(
                target.observation_compatibility
            ) < _projection_schema_ordinal(previous.observation_compatibility):
                raise IntegrityError("projection schema downgrade requires explicit rollback")
        profile_snapshot = self._capture_profile_product_state()
        transition = self.store._begin_transition_locked(
            kind=transition_kind,
            from_release_id=previous.release_id if previous is not None else None,
            to_release_id=target.release_id,
        )
        predecessor = previous.release_id if previous is not None else None
        if predecessor == target.release_id:
            predecessor = target.previous_release_id
        activation_target = replace(target, previous_release_id=predecessor)
        projection_expectations: dict[str, str | None] | None = None
        try:
            # The target's own reducer builds/replays its versioned projection while
            # the active record still names the source release.  Prepare never
            # publishes a pointer, so interruption here cannot expose target semantics.
            projection_expectations = self._prepare_release_projections_locked(activation_target)
            self._materialize_profile_homes(activation_target)
            self._validate_profile_homes(activation_target)
            self.store._commit_active(
                activation_target,
                expected_active_release_id=expected_active_release_id,
            )
            self.validate_release(target.release_id)
            selected = self.store.active()
            assert selected is not None
            self._select_release_projections_locked(selected, projection_expectations)
            self._validate_profile_homes(selected)
        except BaseException as transition_error:
            compensation_error: BaseException | None = None
            try:
                try:
                    observed = self.store.active(required=False)
                except IntegrityError:
                    observed = None
                if observed is not None and observed.release_id == target.release_id:
                    if previous is None:
                        self.store.active_pointer.unlink(missing_ok=True)
                        _fsync_directory(self.store.root)
                    else:
                        self.store._commit_active(
                            previous,
                            expected_active_release_id=target.release_id,
                        )
                        self.validate_release(previous.release_id)
                self._restore_profile_product_state(profile_snapshot)
                if previous is not None:
                    self._reconcile_release_projections_locked(previous)
                elif projection_expectations is not None:
                    # Restore the exact pre-select identities under target-local CAS;
                    # neither the target nor an opaque original DB is opened.
                    self._run_projection_transition_locked(
                        activation_target,
                        operation="unselect",
                        expected_pointers=projection_expectations,
                    )
            except BaseException as error:
                compensation_error = error
            if compensation_error is None:
                self.store._finish_transition_locked(
                    transition,
                    state="failed",
                    failure_code="TRANSITION_VALIDATION_FAILED",
                )
            if compensation_error is not None:
                raise IntegrityError(
                    "lifecycle transition compensation failed"
                ) from compensation_error
            raise transition_error
        self.store._finish_transition_locked(transition, state="committed")
        return selected

    @staticmethod
    def _inspect_wheel(wheel: Path | io.BytesIO) -> dict[str, Any]:
        try:
            with zipfile.ZipFile(wheel) as archive:
                metadata_names = [
                    name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
                ]
                entries_names = [
                    name
                    for name in archive.namelist()
                    if name.endswith(".dist-info/entry_points.txt")
                ]
                wheel_names = [
                    name for name in archive.namelist() if name.endswith(".dist-info/WHEEL")
                ]
                if len(metadata_names) != 1 or len(entries_names) != 1 or len(wheel_names) != 1:
                    raise IntegrityError("Aether wheel metadata is ambiguous")
                metadata_name = metadata_names[0]
                entries_name = entries_names[0]
                wheel_name = wheel_names[0]
                metadata = email.parser.BytesParser().parsebytes(archive.read(metadata_name))
                wheel_metadata = email.parser.BytesParser().parsebytes(archive.read(wheel_name))
                parser = configparser.ConfigParser()
                parser.read_string(archive.read(entries_name).decode("utf-8"))
                observer_requirement_names = [
                    name
                    for name in archive.namelist()
                    if name == "aether_agents/resources/observer-requirements.txt"
                ]
                if len(observer_requirement_names) != 1:
                    raise IntegrityError("candidate observer dependency lock is missing")
                observer_requirements = archive.read(observer_requirement_names[0])
                _validate_observer_requirements(observer_requirements)
                compatibility_members = [
                    name
                    for name in archive.namelist()
                    if name == "aether_agents/observation/contracts.py"
                ]
                if len(compatibility_members) != 1:
                    raise IntegrityError(
                        "candidate observation compatibility declaration is missing"
                    )
                observation_compatibility = _wheel_observation_compatibility(
                    archive.read(compatibility_members[0])
                )
                schema_members: dict[str, str] = {}
                schema_payloads: dict[str, dict[str, Any]] = {}
                for key, filename in {
                    "event": "observation-event.schema.json",
                    "summary": "observation-summary.schema.json",
                    "manifest": "observation-segment-manifest.schema.json",
                }.items():
                    matches = [
                        name
                        for name in archive.namelist()
                        if name == f"aether_agents/resources/schemas/{filename}"
                    ]
                    if len(matches) != 1:
                        raise IntegrityError("candidate observation schema set is incomplete")
                    data = archive.read(matches[0])
                    schema_members[key] = hashlib.sha256(data).hexdigest()
                    parsed = json.loads(data)
                    if not isinstance(parsed, dict):
                        raise IntegrityError("candidate observation schema is malformed")
                    schema_payloads[key] = parsed

                rows = []
                for name in archive.namelist():
                    if name.startswith("aether_agents/") or name in {
                        metadata_name,
                        wheel_name,
                        entries_name,
                    }:
                        if not name.endswith("/"):
                            rows.append((name, hashlib.sha256(archive.read(name)).hexdigest()))
        except IntegrityError:
            raise
        except (
            configparser.Error,
            OSError,
            KeyError,
            UnicodeError,
            json.JSONDecodeError,
            zipfile.BadZipFile,
        ) as error:
            raise IntegrityError("Aether wheel metadata is incomplete") from error
        if metadata.get("Name", "").lower().replace("_", "-") != "aether-agents":
            raise IntegrityError("candidate distribution is not aether-agents")
        version = metadata.get("Version", "")
        if not _VERSION_RE.fullmatch(version):
            raise IntegrityError("candidate wheel version is invalid")
        python_requires = metadata.get("Requires-Python", "").replace(" ", "")
        if set(python_requires.split(",")) != {">=3.11", "<3.14"}:
            raise IntegrityError("candidate Python compatibility mismatch")
        requirements = {
            value.replace(" ", "") for value in metadata.get_all("Requires-Dist", failobj=[])
        }
        expected_requirements = {
            f"{name}=={version}" for name, version in sorted(_OBSERVER_RUNTIME_DEPENDENCIES.items())
        }
        if requirements != expected_requirements:
            raise IntegrityError("candidate runtime dependencies mismatch")
        if (
            wheel_metadata.get("Wheel-Version") != "1.0"
            or wheel_metadata.get("Root-Is-Purelib", "").lower() != "true"
            or wheel_metadata.get_all("Tag", failobj=[]) != ["py3-none-any"]
            or wheel_metadata.get("Generator") != "hatchling 1.27.0"
        ):
            raise IntegrityError("candidate wheel compatibility metadata mismatch")
        if set(parser.sections()) != {"console_scripts", "hermes_agent.plugins"}:
            raise IntegrityError("candidate entry-point groups mismatch")
        if dict(parser["console_scripts"]) != {"aether": "aether_agents.cli:main"}:
            raise IntegrityError("candidate public CLI entry point mismatch")
        if dict(parser["hermes_agent.plugins"]) != {
            "aether-contract-observer": OBSERVER_ENTRY_POINT["target"]
        }:
            raise IntegrityError("candidate observer entry-point set mismatch")
        try:
            target = parser["hermes_agent.plugins"]["aether-contract-observer"]
        except (configparser.Error, KeyError) as error:
            raise IntegrityError("candidate observer entry point is missing") from error
        observed = f"aether-contract-observer={target}"
        if observed != HERMES_BASELINE.observer_entry_point:
            raise IntegrityError("candidate observer entry point target mismatch")
        schema_versions = {
            key: payload.get("properties", {}).get("schema_version", {}).get("const")
            for key, payload in schema_payloads.items()
        }
        if schema_versions != {
            "event": observation_compatibility["event_write_version"],
            "summary": observation_compatibility["summary_write_version"],
            "manifest": observation_compatibility["segment_manifest_write_version"],
        }:
            raise IntegrityError("candidate packaged schema version mismatch")
        entrypoints = [[OBSERVER_ENTRY_POINT["plugin_name"], OBSERVER_ENTRY_POINT["target"]]]
        fingerprint_blob = json.dumps(
            {"files": sorted(rows), "entrypoints": entrypoints},
            sort_keys=True,
        ).encode()
        fingerprint = hashlib.sha256(fingerprint_blob).hexdigest()
        return {
            "distribution": "aether-agents",
            "version": version,
            "python_requires": HERMES_BASELINE.python_requires,
            "entry_point": observed,
            "observer": dict(OBSERVER_ENTRY_POINT),
            "observation_compatibility": observation_compatibility,
            "observation_schema_sha256": schema_members,
            "observer_requirements": observer_requirements,
            "observer_requirements_sha256": hashlib.sha256(observer_requirements).hexdigest(),
            "installed_file_fingerprint": fingerprint,
        }

    @staticmethod
    def _inspect_wheel_bytes(data: bytes) -> dict[str, Any]:
        """Inspect already no-follow-read wheel bytes without reopening a path."""

        return LifecycleManager._inspect_wheel(io.BytesIO(data))

    @staticmethod
    def _environment_python(environment: Path) -> Path:
        candidate = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        if not candidate.is_file():
            raise IntegrityError("candidate environment has no Python executable")
        return candidate

    def _install_observer_dependencies(
        self,
        python: Path,
        requirements: Path,
        *,
        synchronize: bool = True,
    ) -> None:
        """Apply the candidate wheel's hash-bound dependency closure."""

        if requirements.is_symlink() or not requirements.is_file():
            raise IntegrityError("observer dependency lock is unavailable")
        _validate_observer_requirements(requirements.read_bytes())
        command = [
            "--no-config",
            "pip",
            "sync" if synchronize else "install",
            "--require-hashes",
            "--strict",
            "--python",
            str(python),
        ]
        if synchronize:
            command.append(str(requirements))
        else:
            command.extend(("--requirement", str(requirements)))
        self._run_uv(*command)

    def _verify_installed_environment(self, python: Path, *, runtime: bool) -> None:
        """Run package consistency/import checks before a candidate can be recorded."""

        self._run_uv("--no-config", "pip", "check", "--python", str(python))
        script = """
import importlib.metadata as metadata
import aether_agents
entries = [
    entry for entry in metadata.entry_points().select(group='hermes_agent.plugins')
    if entry.name == 'aether-contract-observer'
]
if len(entries) != 1 or not callable(getattr(entries[0].load(), 'register', None)):
    raise SystemExit(3)
"""
        if runtime:
            script = "import hermes_cli\n" + script
        try:
            completed = subprocess.run(
                [str(python), "-c", script],
                check=False,
                capture_output=True,
                text=True,
                env=_isolated_subprocess_environment(),
            )
        except OSError as error:
            raise IntegrityError("candidate import probe interpreter is unavailable") from error
        if completed.returncode != 0:
            raise IntegrityError("candidate import/plugin probe failed")

    def _install_hermes_from_lock(
        self,
        source: Path,
        python: Path,
        requirements_output: Path,
    ) -> dict[str, str]:
        """Sync the exact tracked Hermes lock, then install only its local project."""

        lock = source / "uv.lock"
        if lock.is_symlink() or not lock.is_file():
            raise IntegrityError("tracked Hermes dependency lock is unavailable")
        if source.is_symlink() or not source.is_dir():
            raise IntegrityError("Hermes release source is unsafe")
        try:
            source_root = source.resolve(strict=True)
            output_parent = requirements_output.parent.resolve(strict=True)
        except OSError as error:
            raise IntegrityError("Hermes dependency export path is unavailable") from error
        if output_parent == source_root or output_parent.is_relative_to(source_root):
            raise IntegrityError("Hermes dependency export must not mutate authenticated source")
        if requirements_output.exists() or requirements_output.is_symlink():
            raise IntegrityError("Hermes dependency export already exists")
        lock_sha256 = _sha256(lock)
        source_sha256 = _tree_sha256(source)
        self._run_uv(
            "--no-config",
            "export",
            "--frozen",
            "--no-dev",
            "--no-emit-project",
            "--format",
            "requirements.txt",
            "--output-file",
            str(requirements_output),
            cwd=source,
        )
        if requirements_output.is_symlink() or not requirements_output.is_file():
            raise IntegrityError("Hermes frozen dependency export is unavailable")
        harden_file(requirements_output)
        requirements_sha256 = _sha256(requirements_output)
        self._run_uv(
            "--no-config",
            "pip",
            "sync",
            "--require-hashes",
            "--strict",
            "--python",
            str(python),
            str(requirements_output),
            cwd=source,
        )
        self._run_uv(
            "--no-config",
            "pip",
            "install",
            "--python",
            str(python),
            "--editable",
            str(source),
            "--no-deps",
            cwd=source,
        )
        _remove_hermes_editable_build_debris(source)
        if _sha256(lock) != lock_sha256 or _tree_sha256(source) != source_sha256:
            raise IntegrityError("Hermes authenticated source changed during installation")
        return {
            "uv_lock_sha256": lock_sha256,
            "requirements_sha256": requirements_sha256,
        }

    @staticmethod
    def _run_uv(*arguments: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        if cwd is not None and (not cwd.is_absolute() or cwd.is_symlink() or not cwd.is_dir()):
            raise IntegrityError("candidate environment working directory is unsafe")
        try:
            completed = subprocess.run(
                ["uv", *arguments],
                cwd=cwd,
                check=False,
                capture_output=True,
                text=True,
                env=_isolated_subprocess_environment(),
            )
        except OSError as error:
            raise IntegrityError("candidate environment tool is unavailable") from error
        if completed.returncode != 0:
            raise IntegrityError(
                f"candidate environment operation failed ({arguments[0]} exit "
                f"{completed.returncode})"
            )
        return completed

    @staticmethod
    def _installed_distribution_version(python: Path, distribution: str) -> str:
        try:
            completed = subprocess.run(
                [
                    str(python),
                    "-c",
                    "import importlib.metadata as m,sys;print(m.version(sys.argv[1]))",
                    distribution,
                ],
                check=False,
                capture_output=True,
                text=True,
                env=_isolated_subprocess_environment(),
            )
        except OSError as error:
            raise IntegrityError("installed distribution interpreter is unavailable") from error
        if completed.returncode != 0:
            raise IntegrityError("installed distribution metadata is unavailable")
        return completed.stdout.strip()

    @staticmethod
    def _installed_aether_identity(python: Path) -> dict[str, Any]:
        script = """
import hashlib, importlib.metadata as m, json
from aether_agents.observation import contracts as c
from aether_agents.observation.reduce import upcast as u
d = m.distribution('aether-agents')
rows = []
for item in d.files or ():
    name = str(item)
    if not (
        name.startswith('aether_agents/')
        or name.endswith('.dist-info/METADATA')
        or name.endswith('.dist-info/WHEEL')
        or name.endswith('.dist-info/entry_points.txt')
    ):
        continue
    path = d.locate_file(item)
    if path.is_file():
        rows.append((name, hashlib.sha256(path.read_bytes()).hexdigest()))
entrypoints = sorted(
    (ep.name, ep.value) for ep in m.entry_points().select(group='hermes_agent.plugins')
    if ep.dist and ep.dist.metadata['Name'].lower().replace('_', '-') == 'aether-agents'
)
console_scripts = sorted(
    (ep.name, ep.value) for ep in m.entry_points().select(group='console_scripts')
    if ep.dist and ep.dist.metadata['Name'].lower().replace('_', '-') == 'aether-agents'
)
blob = json.dumps({'files': sorted(rows), 'entrypoints': entrypoints}, sort_keys=True).encode()
schema_sha256 = {name: hashlib.sha256(c.schema_bytes(name)).hexdigest() for name in ('event', 'summary', 'manifest')}
schema_versions = {
    name: json.loads(c.schema_bytes(name))['properties']['schema_version']['const']
    for name in ('event', 'summary', 'manifest')
}
compatibility = {
    'event_write_version': c.EVENT_SCHEMA_VERSION,
    'event_read_versions': list(u.READ_SET),
    'summary_write_version': c.SUMMARY_SCHEMA_VERSION,
    'summary_read_versions': [c.SUMMARY_SCHEMA_VERSION],
    'segment_manifest_write_version': c.MANIFEST_SCHEMA_VERSION,
    'segment_manifest_read_versions': [c.MANIFEST_SCHEMA_VERSION],
    'projection_schema_version': c.READ_MODEL_SCHEMA,
}
print(json.dumps({
    'version': d.version,
    'fingerprint': hashlib.sha256(blob).hexdigest(),
    'entrypoints': entrypoints,
    'console_scripts': console_scripts,
    'observation_compatibility': compatibility,
    'observation_schema_sha256': schema_sha256,
    'schema_versions': schema_versions,
}, sort_keys=True))
"""
        try:
            completed = subprocess.run(
                [str(python), "-c", script],
                check=False,
                capture_output=True,
                text=True,
                env=_isolated_subprocess_environment(),
            )
        except OSError as error:
            raise IntegrityError("installed Aether interpreter is unavailable") from error
        if completed.returncode != 0:
            raise IntegrityError("installed Aether identity cannot be inspected")
        try:
            identity = json.loads(completed.stdout)
        except (json.JSONDecodeError, UnicodeError) as error:
            raise IntegrityError("installed Aether identity is malformed") from error
        expected = [
            ["aether-contract-observer", HERMES_BASELINE.observer_entry_point.split("=", 1)[1]]
        ]
        if (
            not isinstance(identity, dict)
            or identity.get("entrypoints") != expected
            or identity.get("console_scripts") != [["aether", "aether_agents.cli:main"]]
        ):
            raise IntegrityError("installed observer entry point mismatch")
        version = identity.get("version")
        fingerprint = identity.get("fingerprint")
        if not isinstance(version, str) or not _VERSION_RE.fullmatch(version):
            raise IntegrityError("installed Aether version is malformed")
        if not isinstance(fingerprint, str) or not _SHA256_RE.fullmatch(fingerprint):
            raise IntegrityError("installed Aether fingerprint is malformed")
        try:
            compatibility = _validate_observation_compatibility(
                identity.get("observation_compatibility")
            )
        except IntegrityError as error:
            raise IntegrityError("installed observation compatibility mismatch") from error
        schema_versions = identity.get("schema_versions")
        if schema_versions != {
            "event": compatibility["event_write_version"],
            "summary": compatibility["summary_write_version"],
            "manifest": compatibility["segment_manifest_write_version"],
        }:
            raise IntegrityError("installed observation schema version mismatch")
        schema_sha256 = identity.get("observation_schema_sha256")
        if (
            not isinstance(schema_sha256, dict)
            or set(schema_sha256) != {"event", "summary", "manifest"}
            or any(
                not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest)
                for digest in schema_sha256.values()
            )
        ):
            raise IntegrityError("installed observation schema identity is malformed")
        return {
            "version": version,
            "fingerprint": fingerprint,
            "observation_compatibility": compatibility,
            "observation_schema_sha256": dict(schema_sha256),
        }

    @staticmethod
    def _write_durable(path: Path, data: bytes) -> None:
        """Create one durable candidate without crossing a mutable path alias."""

        if path.name in {"", ".", ".."}:
            raise UnsafeObservationPath("candidate target has an unsafe name")
        if os.name != "posix":  # pragma: no cover - exercised by platform CI
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, FILE_MODE)
            try:
                _write_descriptor(descriptor, data)
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            harden_file(path)
            return

        parent_descriptor = _open_private_directory(path.parent)
        descriptor: int | None = None
        created_identity: tuple[int, int] | None = None
        complete = False
        try:
            flags = (
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | getattr(os, "O_CLOEXEC", 0)
                | getattr(os, "O_NOFOLLOW", 0)
            )
            descriptor = os.open(path.name, flags, FILE_MODE, dir_fd=parent_descriptor)
            opened = os.fstat(descriptor)
            named = os.stat(path.name, dir_fd=parent_descriptor, follow_symlinks=False)
            if (
                not stat.S_ISREG(opened.st_mode)
                or opened.st_nlink != 1
                or not stat.S_ISREG(named.st_mode)
                or named.st_nlink != 1
                or (named.st_dev, named.st_ino) != (opened.st_dev, opened.st_ino)
            ):
                raise UnsafeObservationPath("candidate target is not a private regular file")
            created_identity = (opened.st_dev, opened.st_ino)
            os.fchmod(descriptor, FILE_MODE)
            _write_descriptor(descriptor, data)
            os.fsync(descriptor)
            persisted = os.fstat(descriptor)
            named = os.stat(path.name, dir_fd=parent_descriptor, follow_symlinks=False)
            if (
                persisted.st_nlink != 1
                or stat.S_IMODE(persisted.st_mode) != FILE_MODE
                or (named.st_dev, named.st_ino) != (persisted.st_dev, persisted.st_ino)
            ):
                raise UnsafeObservationPath("candidate target changed while writing")
            _verify_directory_identity(path.parent, parent_descriptor)
            os.fsync(parent_descriptor)
            complete = True
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if created_identity is not None and not complete:
                try:
                    remaining = os.stat(
                        path.name,
                        dir_fd=parent_descriptor,
                        follow_symlinks=False,
                    )
                    if (remaining.st_dev, remaining.st_ino) == created_identity:
                        os.unlink(path.name, dir_fd=parent_descriptor)
                        try:
                            os.fsync(parent_descriptor)
                        except OSError:
                            pass
                except OSError:
                    pass
            os.close(parent_descriptor)

    @classmethod
    def _copy_durable(cls, source: Path, target: Path, *, expected_sha256: str) -> None:
        """Copy stable external artifact bytes already bound to an expected digest."""

        try:
            data = read_private_bytes(source)
        except (OSError, ValueError) as error:
            raise IntegrityError("candidate artifact source is unreadable") from error
        if hashlib.sha256(data).hexdigest() != expected_sha256:
            raise IntegrityError("candidate artifact changed before durable copy")
        cls._write_durable(target, data)

    @staticmethod
    def _projection_integrity_ok(path: Path) -> bool:
        """Inspect one projection read-only without trusting a replacement symlink."""

        if path.is_symlink() or not path.is_file():
            return False
        try:
            before = os.stat(path, follow_symlinks=False)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                return False
            connection = sqlite3.connect(
                f"{path.resolve(strict=True).as_uri()}?mode=ro",
                uri=True,
            )
        except (OSError, sqlite3.Error):
            return False
        try:
            rows = connection.execute("PRAGMA quick_check").fetchall()
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_schema WHERE type = 'table'"
                ).fetchall()
                if isinstance(row[0], str)
            }
            after = os.stat(path, follow_symlinks=False)
            return (
                rows == [("ok",)]
                and {"observation_event", "observation_summary", "ingest_cursor"} <= tables
                and stat.S_ISREG(after.st_mode)
                and (before.st_dev, before.st_ino) == (after.st_dev, after.st_ino)
            )
        except (OSError, sqlite3.Error):
            return False
        finally:
            connection.close()

    @staticmethod
    def _summary_coverage(path: Path) -> bool | None:
        """Return coverage completeness for one canonical, private summary."""

        if path.is_symlink() or not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                return None
            validate_summary(payload)
            assert_clean(payload)
            if path.name != f"{payload['summary_id']}.json":
                return None
            if canonical_summary_id(payload) != payload["summary_id"]:
                return None
            coverage = payload["coverage"]
        except (
            OSError,
            UnicodeError,
            ValidationError,
            ValueError,
            KeyError,
            TypeError,
            json.JSONDecodeError,
        ):
            return None
        return coverage["complete"] if isinstance(coverage, dict) else None

    def _observer_state_details(self) -> tuple[dict[str, int], bool]:
        observations = self.store.state_root / "observations"
        details = {
            "health_counter_classes": 0,
            "health_counter_total": 0,
            "journal_file_count": 0,
            "project_count": 0,
            "projection_file_count": 0,
            "quarantine_file_count": 0,
            "projection_integrity_failures": 0,
            "summary_file_count": 0,
            "incomplete_summary_count": 0,
            "invalid_summary_count": 0,
        }
        permissions_ok = True
        if not observations.exists():
            return details, permissions_ok
        if observations.is_symlink() or not observations.is_dir():
            return details, False
        projects = observations / "projects"
        if projects.is_dir() and not projects.is_symlink():
            details["project_count"] = sum(
                1 for child in projects.iterdir() if child.is_dir() and not child.is_symlink()
            )
        health = observations / "health" / "counters.json"
        if health.is_file() and not health.is_symlink():
            try:
                payload = json.loads(health.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                payload = None
            if isinstance(payload, dict):
                values = [
                    value
                    for value in payload.values()
                    if isinstance(value, int) and not isinstance(value, bool) and value >= 0
                ]
                details["health_counter_classes"] = len(values)
                details["health_counter_total"] = sum(values)
        for directory, names, files in os.walk(observations, followlinks=False):
            current = Path(directory)
            relative_parts = current.relative_to(observations).parts
            if current.is_symlink():
                permissions_ok = False
                names[:] = []
                continue
            if os.name == "posix" and stat.S_IMODE(current.stat().st_mode) != DIR_MODE:
                permissions_ok = False
            for name in names:
                if (current / name).is_symlink():
                    permissions_ok = False
            for name in files:
                path = current / name
                if path.is_symlink():
                    permissions_ok = False
                    continue
                if os.name == "posix" and stat.S_IMODE(path.stat().st_mode) != FILE_MODE:
                    permissions_ok = False
                if "journal" in relative_parts:
                    details["journal_file_count"] += 1
                if "projections" in relative_parts and path.suffix == ".sqlite3":
                    details["projection_file_count"] += 1
                    if not self._projection_integrity_ok(path):
                        details["projection_integrity_failures"] += 1
                if "quarantine" in relative_parts:
                    details["quarantine_file_count"] += 1
                if "summaries" in relative_parts and path.suffix == ".json":
                    details["summary_file_count"] += 1
                    complete = self._summary_coverage(path)
                    if complete is None:
                        details["invalid_summary_count"] += 1
                    elif not complete:
                        details["incomplete_summary_count"] += 1
        return details, permissions_ok

    def _observer_hook_probe(self, runtime_python: Path) -> tuple[dict[str, int], bool]:
        """Load/unload the installed entry point in an isolated disposable profile."""

        details = {
            "expected_callbacks": 22,
            "registered_callbacks": 0,
            "remaining_callbacks": 0,
        }
        script = r"""
import importlib.metadata as metadata
import json
import os
from hermes_cli.plugins import PluginContext, PluginManager, PluginManifest

entrypoints = [
    ep for ep in metadata.entry_points().select(group="hermes_agent.plugins")
    if ep.name == "aether-contract-observer"
]
if len(entrypoints) != 1:
    raise RuntimeError("observer entry point is not unique")
module = entrypoints[0].load()
manager = PluginManager(scope_key=os.environ["HERMES_HOME"])
manifest = PluginManifest(
    name="aether-contract-observer",
    key="aether-contract-observer",
    source="entrypoint",
)
module.register(PluginContext(manifest, manager))
registered = sum(len(callbacks) for callbacks in manager._hooks.values())
unloaded = manager.unload(manifest)
remaining = sum(len(callbacks) for callbacks in manager._hooks.values())
print(json.dumps({"registered": registered, "remaining": remaining, "unloaded": unloaded}))
"""
        try:
            with tempfile.TemporaryDirectory(prefix="aether-doctor-") as temporary:
                disposable = Path(temporary)
                environment = _isolated_subprocess_environment()
                for name in (
                    "AETHER_PROJECT_ID",
                    "AETHER_OBSERVATION_TRACE_ID",
                    "HERMES_DELEGATED_CHILD_CONTEXT",
                    "HERMES_KANBAN_TASK",
                ):
                    environment.pop(name, None)
                environment.update(
                    {
                        "HOME": str(disposable / "home"),
                        "HERMES_HOME": str(disposable / "profile"),
                        "XDG_DATA_HOME": str(disposable / "data"),
                        "XDG_STATE_HOME": str(disposable / "state"),
                    }
                )
                completed = subprocess.run(
                    [str(runtime_python), "-c", script],
                    check=False,
                    capture_output=True,
                    text=True,
                    cwd=disposable,
                    env=environment,
                )
        except OSError:
            return details, False
        if completed.returncode != 0:
            return details, False
        try:
            payload = json.loads(completed.stdout)
        except (UnicodeError, json.JSONDecodeError):
            return details, False
        if not isinstance(payload, dict):
            return details, False
        registered = payload.get("registered")
        remaining = payload.get("remaining")
        if (
            not isinstance(registered, int)
            or isinstance(registered, bool)
            or registered < 0
            or not isinstance(remaining, int)
            or isinstance(remaining, bool)
            or remaining < 0
        ):
            return details, False
        details["registered_callbacks"] = registered
        details["remaining_callbacks"] = remaining
        return details, registered == details["expected_callbacks"] and remaining == 0 and bool(
            payload.get("unloaded")
        )

    def _transition_details(self) -> tuple[dict[str, int], bool]:
        details = {"journal_count": 0, "pending_count": 0}
        permissions_ok = True
        transitions = self.store.transitions
        if not transitions.exists():
            return details, permissions_ok
        if transitions.is_symlink() or not transitions.is_dir():
            return details, False
        if os.name == "posix" and stat.S_IMODE(transitions.stat().st_mode) != DIR_MODE:
            permissions_ok = False
        for path in transitions.iterdir():
            if path.is_symlink() or not path.is_file():
                permissions_ok = False
                continue
            if not path.name.startswith("trn_") or path.suffix != ".json":
                continue
            details["journal_count"] += 1
            if os.name == "posix" and stat.S_IMODE(path.stat().st_mode) != FILE_MODE:
                permissions_ok = False
            try:
                payload = self.store._read_transition(path)
            except IntegrityError:
                permissions_ok = False
                continue
            if payload["state"] == "pending":
                details["pending_count"] += 1
        return details, permissions_ok

    def doctor(self) -> DoctorResult:
        with self.store.mutation_lock():
            return self._doctor_locked()

    def _doctor_locked(self) -> DoctorResult:
        codes: list[str] = []
        try:
            observer_state, observer_permissions_ok = self._observer_state_details()
        except OSError:
            observer_state = {
                "health_counter_classes": 0,
                "health_counter_total": 0,
                "journal_file_count": 0,
                "project_count": 0,
                "projection_file_count": 0,
                "quarantine_file_count": 0,
                "projection_integrity_failures": 0,
                "summary_file_count": 0,
                "incomplete_summary_count": 0,
                "invalid_summary_count": 0,
            }
            observer_permissions_ok = False
        try:
            transition_state, transition_permissions_ok = self._transition_details()
        except OSError:
            transition_state = {"journal_count": 0, "pending_count": 0}
            transition_permissions_ok = False
        details: dict[str, Any] = {
            "observer_state": observer_state,
            "profile_count": 0,
            "transition_journal": transition_state,
        }
        if not observer_permissions_ok:
            codes.append("OBSERVATION_PERMISSION_MISMATCH")
        if observer_state["projection_integrity_failures"]:
            codes.append("READ_MODEL_INVALID")
        if observer_state["invalid_summary_count"]:
            codes.append("COVERAGE_SUMMARY_INVALID")
        if not transition_permissions_ok:
            codes.append("TRANSITION_JOURNAL_INVALID")
        try:
            active = self.store.active()
        except IntegrityError:
            codes.append("ACTIVE_RELEASE_INVALID")
            return DoctorResult(False, None, tuple(dict.fromkeys(codes)), details)
        assert active is not None
        details["active_version"] = active.version
        try:
            self.store.assert_owned()
        except IntegrityError:
            codes.append("STATE_OWNERSHIP_INVALID")
        release = self.store.release_path(active.release_id)
        release_manifest: dict[str, Any] = {}
        try:
            candidate_manifest = json.loads(
                read_private_bytes(release / "release.json").decode("utf-8")
            )
            if not isinstance(candidate_manifest, dict):
                raise ValueError("release manifest is not an object")
            release_manifest = candidate_manifest
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
            codes.append("INSTALLATION_EVIDENCE_MISSING")
        else:
            artifact = release / "artifacts" / active.wheel_filename
            try:
                artifact_matches = hashlib.sha256(read_private_bytes(artifact)).hexdigest() == (
                    active.wheel_sha256
                )
            except (OSError, ValueError):
                artifact_matches = False
            if not artifact_matches:
                codes.append("WHEEL_ARTIFACT_MISMATCH")
            try:
                self._validate_profile_bundle(release, release_manifest)
            except IntegrityError:
                codes.append("PROFILE_BUNDLE_INVALID")
            else:
                try:
                    self._validate_profile_homes(active)
                except IntegrityError:
                    codes.append("PROFILE_ACTIVATION_INVALID")
                else:
                    details["profile_count"] = len(_PROFILE_ROLES)
        expected_fingerprint = release_manifest.get("installed_file_fingerprint")
        if not isinstance(expected_fingerprint, str) or not _SHA256_RE.fullmatch(
            expected_fingerprint
        ):
            codes.append("INSTALLATION_EVIDENCE_MISSING")
        identities: list[str] = []
        installed_identities: list[dict[str, str]] = []
        for environment in ("manager", "runtime"):
            marker = release / environment / "aether-wheel.sha256"
            if marker.is_symlink() or not marker.is_file():
                codes.append(f"{environment.upper()}_WHEEL_IDENTITY_MISSING")
                continue
            try:
                value = read_private_bytes(marker).decode("ascii").strip()
            except (OSError, UnicodeError, ValueError):
                codes.append(f"{environment.upper()}_WHEEL_IDENTITY_MISSING")
                continue
            identities.append(value)
            if value != active.wheel_sha256:
                codes.append("WHEEL_IDENTITY_MISMATCH")
            try:
                python = self._environment_python(release / environment)
                installed = self._installed_aether_identity(python)
            except IntegrityError:
                codes.append(f"{environment.upper()}_INSTALLATION_INVALID")
                continue
            installed_identities.append(installed)
            if installed["version"] != active.version:
                codes.append("INSTALLED_VERSION_MISMATCH")
            if (
                expected_fingerprint is not None
                and installed["fingerprint"] != expected_fingerprint
            ):
                codes.append("INSTALLED_FILE_FINGERPRINT_MISMATCH")
        if len(set(identities)) > 1 and "WHEEL_IDENTITY_MISMATCH" not in codes:
            codes.append("WHEEL_IDENTITY_MISMATCH")
        if len({identity["fingerprint"] for identity in installed_identities}) > 1:
            codes.append("INSTALLED_FILE_FINGERPRINT_MISMATCH")
        try:
            executing_manager = self._installed_aether_identity(self.python_executable)
        except IntegrityError:
            codes.append("EXECUTING_MANAGER_INVALID")
        else:
            if executing_manager["version"] != active.version:
                codes.append("EXECUTING_MANAGER_VERSION_MISMATCH")
            if (
                isinstance(expected_fingerprint, str)
                and executing_manager["fingerprint"] != expected_fingerprint
            ):
                codes.append("EXECUTING_MANAGER_FINGERPRINT_MISMATCH")
        try:
            runtime_python = self._environment_python(release / "runtime")
            hermes_version = self._installed_distribution_version(
                runtime_python, HERMES_BASELINE.distribution
            )
        except IntegrityError:
            codes.append("HERMES_RUNTIME_INVALID")
        else:
            if hermes_version != HERMES_BASELINE.version:
                codes.append("HERMES_BASELINE_MISMATCH")
            hook_probe, hooks_ok = self._observer_hook_probe(runtime_python)
            details["hook_probe"] = hook_probe
            if not hooks_ok:
                codes.append("OBSERVER_HOOK_PROBE_FAILED")
        if active.hermes_commit != HERMES_BASELINE.commit:
            codes.append("HERMES_BASELINE_MISMATCH")
        if active.observer_entry_point != HERMES_BASELINE.observer_entry_point:
            codes.append("OBSERVER_ENTRY_POINT_MISMATCH")
        try:
            self.validate_release(active.release_id)
        except IntegrityError:
            codes.append("ACTIVE_RELEASE_REVALIDATION_FAILED")
        if os.name == "posix":
            permission_targets = {
                self.store.root: DIR_MODE,
                self.store.state_root: DIR_MODE,
                self.store.active_pointer: FILE_MODE,
            }
            for path, expected in permission_targets.items():
                try:
                    observed = stat.S_IMODE(path.stat().st_mode)
                except OSError:
                    codes.append("STATE_PERMISSION_UNAVAILABLE")
                    continue
                if observed != expected:
                    codes.append("STATE_PERMISSION_MISMATCH")
        return DoctorResult(
            not codes,
            active.release_id,
            tuple(dict.fromkeys(codes)),
            details,
        )

    def rollback(
        self,
        *,
        expected_active_release_id: str | None | object = _CAS_UNSET,
    ) -> ReleaseRecord:
        expected = (
            self._capture_expected_active()
            if expected_active_release_id is _CAS_UNSET
            else expected_active_release_id
        )
        with self.store.mutation_lock():
            self._assert_executing_active_manager_locked()
            # Rollback is the recovery path for an active runtime that no longer
            # imports.  Recover transition journals structurally, then validate the
            # known-good target; never require the broken source runtime to execute.
            self.store._recover_locked()
            if expected is _CAS_UNSET:
                expected = self._assert_expected_active_locked(_CAS_UNSET)
            self._assert_expected_active_locked(expected)
            current = self.store.active()
            assert current is not None
            if current.previous_release_id is None:
                raise IntegrityError("active release has no rollback target")
            return self._activate_existing_locked(
                current.previous_release_id,
                transition_kind="rollback",
                expected_active_release_id=expected,
            )

    def uninstall(self, *, purge: bool, confirmed: bool) -> UninstallResult:
        if purge and not confirmed:
            raise IntegrityError("purge requires explicit confirmation")
        for root in {self.store.root, self.store.state_root}:
            self._assert_destructive_scope(root)
        if self.store.root.exists() or self.store.state_root.exists():
            self.store.assert_owned()
        with self.store.mutation_lock():
            self._assert_executing_active_manager_locked()
            for root in {self.store.root, self.store.state_root}:
                self._assert_destructive_scope(root)
            return self._uninstall_locked(purge=purge)

    def _uninstall_locked(self, *, purge: bool) -> UninstallResult:
        data_root = self.store.root
        state_root = self.store.state_root
        if data_root.exists() or state_root.exists():
            self.store.assert_owned()
        if purge:
            for root in {data_root, state_root}:
                if not root.exists():
                    continue
                shutil.rmtree(root)
                _fsync_directory(root.parent)
            return UninstallResult(True, False)
        active = self.store.active()
        assert active is not None
        self._deactivate_release_projections_locked(active)
        self._deactivate_profile_homes()
        self.store.active_pointer.unlink(missing_ok=True)
        for product_path in (
            self.store.releases,
            data_root / "staging",
            self.store.transitions,
            state_root / "staging",
        ):
            if product_path.exists():
                _assert_plain_path(product_path, kind="directory")
                shutil.rmtree(product_path)
        for root in {data_root, state_root}:
            if root.exists():
                _fsync_directory(root)
        return UninstallResult(False, (state_root / "observations").exists())

    @staticmethod
    def _assert_destructive_scope(root: Path) -> None:
        if not root.is_absolute() or root == Path(root.anchor):
            raise IntegrityError("destructive lifecycle root is too broad")
        if root.name != "aether":
            raise IntegrityError("destructive lifecycle root must be the Aether state root")
        if root.is_symlink():
            raise IntegrityError("destructive lifecycle root must not be a symlink")
        if root.exists():
            try:
                resolved = root.resolve(strict=True)
            except OSError as error:
                raise IntegrityError("destructive lifecycle root is not resolvable") from error
            if resolved != root.absolute():
                raise IntegrityError("destructive lifecycle root has a symlinked ancestor")
