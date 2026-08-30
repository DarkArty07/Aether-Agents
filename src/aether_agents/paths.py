"""Product-owned filesystem layout for Aether state.

The observer computes its state root from product-owned installation context only
(``specs/002-aether-contract-observation/spec.md`` section 6): no Hermes profile
configuration key, ``HERMES_HOME`` value, ``cwd``, or plugin setting can redirect it.
The only supported inputs are the XDG environment contract and an explicit argument
passed by product code and tests.

Layout::

    <state_root>/                                     0700
      observations/
        health/counters.json                          content-free, project-agnostic
        projects/<project_uuid>/
          journal/active/prd_<epoch>.<first>-<last>.jsonl
          journal/closed/prd_<epoch>.<first>-<last>.jsonl
          journal/archive/prd_<epoch>.<first>-<last>.jsonl.gz (+ .manifest.json)
          journal/quarantine/
          locks/<producer_epoch>.lock
          keys/<fingerprint_key_id>.key                0600
          keys/current                                 non-secret pointer
          projections/<read_model_schema>.sqlite3
          projections/current                          atomic derived pointer
          summaries/
"""

from __future__ import annotations

import os
import re
import secrets
import stat
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "DIR_MODE",
    "FILE_MODE",
    "ObservationPaths",
    "UnsafeObservationPath",
    "atomic_private_write",
    "ensure_private_dir",
    "harden_file",
    "read_private_bytes",
    "data_root",
    "state_root",
]

#: Section 6.2 permissions: containing directories 0700, journal/database files 0600.
DIR_MODE = 0o700
FILE_MODE = 0o600
_PROJECT_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_PRODUCER_EPOCH_RE = re.compile(r"^prd_[a-f0-9]{32}$", re.ASCII)
_FINGERPRINT_KEY_ID_RE = re.compile(r"^fpk_[a-f0-9]{32}$", re.ASCII)
_READ_MODEL_SCHEMA_RE = re.compile(r"^aether\.observation\.projection\.v[1-9][0-9]*$", re.ASCII)
_SUMMARY_ID_RE = re.compile(r"^sum_[a-f0-9]{64}$", re.ASCII)


class UnsafeObservationPath(ValueError):
    """A path escaped its closed grammar or crossed an unsafe filesystem link."""


def state_root(explicit: Path | str | None = None) -> Path:
    """Resolve the Aether XDG state root."""
    if explicit is not None:
        root = Path(explicit).expanduser()
        if not root.is_absolute():
            raise ValueError("explicit Aether state root must be absolute")
        return root
    xdg = os.environ.get("XDG_STATE_HOME", "").strip()
    if xdg:
        configured = Path(xdg)
        if not configured.is_absolute():
            raise ValueError("XDG_STATE_HOME must be absolute")
        base = configured
    else:
        base = Path.home() / ".local" / "state"
    return base / "aether"


def data_root(explicit: Path | str | None = None) -> Path:
    """Resolve the immutable-release and persistent-profile XDG data root."""
    if explicit is not None:
        root = Path(explicit).expanduser()
        if not root.is_absolute():
            raise ValueError("explicit Aether data root must be absolute")
        return root
    xdg = os.environ.get("XDG_DATA_HOME", "").strip()
    if xdg:
        configured = Path(xdg)
        if not configured.is_absolute():
            raise ValueError("XDG_DATA_HOME must be absolute")
        base = configured
    else:
        base = Path.home() / ".local" / "share"
    return base / "aether"


def ensure_private_dir(path: Path) -> Path:
    """Create a private directory without following any existing POSIX symlink.

    Each component is opened relative to the already-verified parent directory.  This
    closes the usual check-then-use window in ``Path.mkdir(..., exist_ok=True)`` where
    an attacker can replace an observation directory with a symlink between calls.
    """
    path = Path(path)
    if os.name != "posix":  # pragma: no cover - exercised by platform CI
        path.mkdir(parents=True, exist_ok=True)
        if path.is_symlink() or not path.is_dir():
            raise UnsafeObservationPath("private directory is not a real directory")
        path.chmod(DIR_MODE)
        return path

    if any(component == ".." for component in path.parts):
        raise UnsafeObservationPath("private directory contains traversal")

    components = list(path.parts)
    if path.is_absolute():
        components = components[1:]
        current_fd = os.open(
            path.anchor,
            os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0),
        )
    else:
        current_fd = os.open(".", os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0))

    try:
        for index, component in enumerate(components):
            if component in ("", ".", ".."):
                raise UnsafeObservationPath("private directory has an unsafe component")
            created = False
            try:
                os.mkdir(component, DIR_MODE, dir_fd=current_fd)
                created = True
            except FileExistsError:
                pass
            flags = (
                os.O_RDONLY
                | os.O_DIRECTORY
                | getattr(os, "O_NOFOLLOW", 0)
                | getattr(os, "O_CLOEXEC", 0)
            )
            try:
                next_fd = os.open(component, flags, dir_fd=current_fd)
            except OSError as exc:
                try:
                    info = os.stat(component, dir_fd=current_fd, follow_symlinks=False)
                except OSError:
                    raise exc
                if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                    raise UnsafeObservationPath(
                        "private directory component is a symlink or non-directory"
                    ) from exc
                raise
            info = os.fstat(next_fd)
            if not stat.S_ISDIR(info.st_mode):
                os.close(next_fd)
                raise UnsafeObservationPath("private path component is not a directory")
            if created or index == len(components) - 1:
                os.fchmod(next_fd, DIR_MODE)
            os.close(current_fd)
            current_fd = next_fd
    finally:
        os.close(current_fd)
    return path


def harden_file(path: Path) -> None:
    """Restrict one real, singly-linked file without following a POSIX symlink."""
    if os.name != "posix":
        return
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    try:
        descriptor = os.open(path, flags)
    except FileNotFoundError:
        return
    except OSError as exc:
        try:
            info = os.stat(path, follow_symlinks=False)
        except OSError:
            raise exc
        if stat.S_ISLNK(info.st_mode):
            raise UnsafeObservationPath("private file is a symlink") from exc
        raise
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise UnsafeObservationPath("private file is not a regular file")
        if opened.st_nlink != 1:
            raise UnsafeObservationPath("private file has multiple hard links")
        named = os.stat(path, follow_symlinks=False)
        if (named.st_dev, named.st_ino) != (opened.st_dev, opened.st_ino):
            raise UnsafeObservationPath("private file changed during hardening")
        os.fchmod(descriptor, FILE_MODE)
        after = os.fstat(descriptor)
        named_after = os.stat(path, follow_symlinks=False)
        if after.st_nlink != 1 or (named_after.st_dev, named_after.st_ino) != (
            after.st_dev,
            after.st_ino,
        ):
            raise UnsafeObservationPath("private file changed during hardening")
    finally:
        os.close(descriptor)


def atomic_private_write(path: Path, data: bytes) -> None:
    """Durably replace one private file without following a predictable temp link."""
    path = Path(path)
    if not isinstance(data, bytes):
        raise TypeError("atomic private data must be bytes")
    if path.name in ("", ".", ".."):
        raise UnsafeObservationPath("atomic private target has an unsafe name")
    ensure_private_dir(path.parent)
    token = secrets.token_hex(4)
    if re.fullmatch(r"[a-f0-9]{8}", token) is None:
        raise UnsafeObservationPath("atomic private temporary token is invalid")
    temporary_name = f"{path.stem}.{token}.tmp"

    if os.name != "posix":  # pragma: no cover - exercised by platform CI
        temporary = path.parent / temporary_name
        descriptor: int | None = None
        created = False
        try:
            try:
                descriptor = os.open(
                    temporary,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    FILE_MODE,
                )
            except FileExistsError:
                raise UnsafeObservationPath("atomic private temporary already exists") from None
            created = True
            _write_all(descriptor, data)
            os.fsync(descriptor)
            os.close(descriptor)
            descriptor = None
            os.replace(temporary, path)
            created = False
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if created:
                try:
                    temporary.unlink()
                except OSError:
                    pass
        return

    directory_fd = _open_private_directory(path.parent)
    descriptor: int | None = None
    created_identity: tuple[int, int] | None = None
    installed = False
    try:
        file_flags = (
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_CLOEXEC", 0)
        )
        try:
            descriptor = os.open(
                temporary_name,
                file_flags,
                FILE_MODE,
                dir_fd=directory_fd,
            )
        except FileExistsError:
            raise UnsafeObservationPath("atomic private temporary already exists") from None
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
            raise UnsafeObservationPath("atomic private temporary is not a private file")
        created_identity = (opened.st_dev, opened.st_ino)
        os.fchmod(descriptor, FILE_MODE)
        _write_all(descriptor, data)
        os.fsync(descriptor)

        named = os.stat(temporary_name, dir_fd=directory_fd, follow_symlinks=False)
        if (
            not stat.S_ISREG(named.st_mode)
            or named.st_nlink != 1
            or (named.st_dev, named.st_ino) != created_identity
        ):
            raise UnsafeObservationPath("atomic private temporary changed before replace")
        os.replace(
            temporary_name,
            path.name,
            src_dir_fd=directory_fd,
            dst_dir_fd=directory_fd,
        )
        installed = True
        installed_info = os.stat(path.name, dir_fd=directory_fd, follow_symlinks=False)
        if (
            not stat.S_ISREG(installed_info.st_mode)
            or installed_info.st_nlink != 1
            or (installed_info.st_dev, installed_info.st_ino) != created_identity
        ):
            raise UnsafeObservationPath("atomic private target changed during replace")
        verification_descriptor = _open_private_directory(path.parent)
        try:
            verified_parent = os.fstat(verification_descriptor)
            opened_parent = os.fstat(directory_fd)
            if (verified_parent.st_dev, verified_parent.st_ino) != (
                opened_parent.st_dev,
                opened_parent.st_ino,
            ):
                raise UnsafeObservationPath("atomic private parent changed during replace")
        finally:
            os.close(verification_descriptor)
        os.fsync(directory_fd)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if created_identity is not None and not installed:
            try:
                remaining = os.stat(
                    temporary_name,
                    dir_fd=directory_fd,
                    follow_symlinks=False,
                )
                if (remaining.st_dev, remaining.st_ino) == created_identity:
                    os.unlink(temporary_name, dir_fd=directory_fd)
                    try:
                        os.fsync(directory_fd)
                    except OSError:
                        pass
            except OSError:
                pass
        os.close(directory_fd)


def _write_all(descriptor: int, data: bytes) -> None:
    view = memoryview(data)
    written = 0
    while written < len(view):
        count = os.write(descriptor, view[written:])
        if count <= 0:
            raise OSError("atomic private write made no progress")
        written += count


def read_private_bytes(path: Path) -> bytes:
    """Read one stable, singly-linked regular file without crossing an alias."""
    path = Path(path)
    if path.name in ("", ".", ".."):
        raise UnsafeObservationPath("private read target has an unsafe name")

    if os.name != "posix":  # pragma: no cover - exercised by platform CI
        before = os.stat(path, follow_symlinks=False)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise UnsafeObservationPath("private read target is not singly linked")
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_BINARY", 0))
        try:
            opened = os.fstat(descriptor)
            if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
                raise UnsafeObservationPath("private read target changed while opening")
            data = _read_all(descriptor)
            after = os.fstat(descriptor)
            named_after = os.stat(path, follow_symlinks=False)
            if (
                not stat.S_ISREG(after.st_mode)
                or after.st_nlink != 1
                or (named_after.st_dev, named_after.st_ino) != (after.st_dev, after.st_ino)
            ):
                raise UnsafeObservationPath("private read target changed while reading")
            return data
        finally:
            os.close(descriptor)

    parent_descriptor = _open_private_directory(path.parent)

    descriptor: int | None = None
    try:
        file_flags = (
            os.O_RDONLY
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NONBLOCK", 0)
        )
        try:
            descriptor = os.open(path.name, file_flags, dir_fd=parent_descriptor)
        except OSError as exc:
            try:
                named = os.stat(path.name, dir_fd=parent_descriptor, follow_symlinks=False)
            except OSError:
                raise exc
            if stat.S_ISLNK(named.st_mode) or not stat.S_ISREG(named.st_mode):
                raise UnsafeObservationPath("private read target is not a regular file") from None
            raise

        opened = os.fstat(descriptor)
        named = os.stat(path.name, dir_fd=parent_descriptor, follow_symlinks=False)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_nlink != 1
            or not stat.S_ISREG(named.st_mode)
            or named.st_nlink != 1
            or (named.st_dev, named.st_ino) != (opened.st_dev, opened.st_ino)
        ):
            raise UnsafeObservationPath("private read target is aliased or changed")

        data = _read_all(descriptor)
        after = os.fstat(descriptor)
        named_after = os.stat(path.name, dir_fd=parent_descriptor, follow_symlinks=False)
        if (
            not stat.S_ISREG(after.st_mode)
            or after.st_nlink != 1
            or not stat.S_ISREG(named_after.st_mode)
            or named_after.st_nlink != 1
            or (named_after.st_dev, named_after.st_ino) != (after.st_dev, after.st_ino)
        ):
            raise UnsafeObservationPath("private read target changed while reading")
        verification_descriptor = _open_private_directory(path.parent)
        try:
            verified_parent = os.fstat(verification_descriptor)
            opened_parent = os.fstat(parent_descriptor)
            if (verified_parent.st_dev, verified_parent.st_ino) != (
                opened_parent.st_dev,
                opened_parent.st_ino,
            ):
                raise UnsafeObservationPath("private read parent changed while reading")
        finally:
            os.close(verification_descriptor)
        return data
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(parent_descriptor)


def _open_private_directory(path: Path) -> int:
    """Open an absolute directory without following any path component."""
    path = Path(path)
    if not path.is_absolute() or any(component == ".." for component in path.parts):
        raise UnsafeObservationPath("private directory path must be absolute and confined")
    flags = (
        os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    )
    descriptor = os.open(path.anchor, flags)
    try:
        for component in path.parts[1:]:
            if component in ("", ".", ".."):
                raise UnsafeObservationPath("private directory has an unsafe component")
            try:
                child = os.open(component, flags, dir_fd=descriptor)
            except OSError as exc:
                try:
                    named = os.stat(component, dir_fd=descriptor, follow_symlinks=False)
                except OSError:
                    raise exc
                if stat.S_ISLNK(named.st_mode) or not stat.S_ISDIR(named.st_mode):
                    raise UnsafeObservationPath(
                        "private directory component is a symlink or non-directory"
                    ) from None
                raise
            try:
                opened = os.fstat(child)
                named = os.stat(component, dir_fd=descriptor, follow_symlinks=False)
                if (
                    not stat.S_ISDIR(opened.st_mode)
                    or not stat.S_ISDIR(named.st_mode)
                    or (named.st_dev, named.st_ino) != (opened.st_dev, opened.st_ino)
                ):
                    raise UnsafeObservationPath("private directory component changed while opening")
            except BaseException:
                os.close(child)
                raise
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _read_all(descriptor: int) -> bytes:
    chunks: list[bytes] = []
    while True:
        chunk = os.read(descriptor, 65536)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


def _validated_child(
    parent: Path,
    value: str,
    pattern: re.Pattern[str],
    suffix: str,
    label: str,
    expected_root: Path,
) -> Path:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise ValueError(f"invalid observation {label}")
    candidate = parent / f"{value}{suffix}"
    # The grammar above is the primary defence.  Keep an explicit common-path check so
    # future grammar changes cannot silently turn concatenation into traversal.
    expected = os.path.abspath(parent)
    actual = os.path.abspath(candidate)
    if os.path.commonpath((expected, actual)) != expected:
        raise UnsafeObservationPath(f"observation {label} escapes its directory")
    resolved_root = expected_root.resolve(strict=False)
    resolved_candidate = candidate.resolve(strict=False)
    if os.path.commonpath((str(resolved_root), str(resolved_candidate))) != str(resolved_root):
        raise UnsafeObservationPath(f"resolved observation {label} escapes the state root")
    return candidate


@dataclass(frozen=True, slots=True)
class ObservationPaths:
    """Resolved observation directories for one canonical project UUID."""

    root: Path
    project_id: str

    def __post_init__(self) -> None:
        # Project identity is also a path component. Rejecting anything except the
        # canonical lower-case UUID prevents both cross-project ambiguity and path
        # traversal even when product/test code constructs this dataclass directly.
        if not isinstance(self.project_id, str) or not _PROJECT_UUID_RE.fullmatch(self.project_id):
            raise ValueError("observation project_id must be a canonical lower-case UUID")
        if not isinstance(self.root, Path) or not self.root.is_absolute():
            raise ValueError("observation state root must be an absolute Path")

    @classmethod
    def for_project(cls, project_id: str, *, root: Path | str | None = None) -> "ObservationPaths":
        return cls(root=state_root(root), project_id=project_id)

    # -- global, project-agnostic -------------------------------------------------
    @property
    def observations(self) -> Path:
        return self.root / "observations"

    @property
    def health(self) -> Path:
        """Content-free observer-health counters (OBS-D-022): never project-scoped."""
        return self.observations / "health"

    @property
    def health_counters(self) -> Path:
        return self.health / "counters.json"

    # -- project-scoped -----------------------------------------------------------
    @property
    def project(self) -> Path:
        return self.observations / "projects" / self.project_id

    @property
    def journal(self) -> Path:
        return self.project / "journal"

    @property
    def active(self) -> Path:
        return self.journal / "active"

    @property
    def closed(self) -> Path:
        return self.journal / "closed"

    @property
    def archive(self) -> Path:
        return self.journal / "archive"

    @property
    def quarantine(self) -> Path:
        return self.journal / "quarantine"

    @property
    def locks(self) -> Path:
        return self.project / "locks"

    @property
    def keys(self) -> Path:
        return self.project / "keys"

    @property
    def key_pointer(self) -> Path:
        return self.keys / "current"

    @property
    def projections(self) -> Path:
        return self.project / "projections"

    @property
    def projection_pointer(self) -> Path:
        return self.projections / "current"

    @property
    def summaries(self) -> Path:
        return self.project / "summaries"

    def lock_file(self, producer_epoch: str) -> Path:
        return _validated_child(
            self.locks,
            producer_epoch,
            _PRODUCER_EPOCH_RE,
            ".lock",
            "producer epoch",
            self.root,
        )

    def key_file(self, fingerprint_key_id: str) -> Path:
        return _validated_child(
            self.keys,
            fingerprint_key_id,
            _FINGERPRINT_KEY_ID_RE,
            ".key",
            "fingerprint key id",
            self.root,
        )

    def projection_db(self, read_model_schema: str) -> Path:
        return _validated_child(
            self.projections,
            read_model_schema,
            _READ_MODEL_SCHEMA_RE,
            ".sqlite3",
            "read-model schema",
            self.root,
        )

    def projection_files(self, read_model_schema: str) -> tuple[Path, Path, Path]:
        """Return the DB and its only allowed SQLite WAL/SHM sidecar paths."""
        database = self.projection_db(read_model_schema)
        return (
            database,
            database.with_name(database.name + "-wal"),
            database.with_name(database.name + "-shm"),
        )

    def harden_projection_files(self, read_model_schema: str) -> None:
        """Apply the private-file contract to an existing DB and both sidecars."""
        for candidate in self.projection_files(read_model_schema):
            harden_file(candidate)

    def summary_file(self, summary_id: str) -> Path:
        return _validated_child(
            self.summaries,
            summary_id,
            _SUMMARY_ID_RE,
            ".json",
            "summary id",
            self.root,
        )

    def ensure(self) -> "ObservationPaths":
        """Create every project-scoped directory with owner-only permissions."""
        for directory in (
            self.root,
            self.observations,
            self.health,
            self.observations / "projects",
            self.project,
            self.journal,
            self.active,
            self.closed,
            self.archive,
            self.quarantine,
            self.locks,
            self.keys,
            self.projections,
            self.summaries,
        ):
            ensure_private_dir(directory)
        return self
