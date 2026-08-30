"""Project-keyed configuration fingerprints and their key epochs.

Normative decision: OBS-D-028, enforced by OBS-FR-058 and OBS-FR-083.

Plain SHA-256 of a small catalog or a common system prompt is vulnerable to offline
dictionary enumeration if a summary is copied elsewhere. Content-derived configuration
values therefore use project-keyed, field-domain-separated HMAC-SHA-256. Artifact and
runtime hashes remain ordinary SHA-256 because they are already opaque digests of
content the observer does not hold.

Key material never enters journal events, summaries, logs, public provenance, release
artifacts, repositories, or unprotected exports.
"""

from __future__ import annotations

import hmac
import os
import secrets
import stat
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Final

from aether_agents.observation.contracts import canonical_digest, canonical_json_bytes
from aether_agents.observation.identity import fingerprint_key_id
from aether_agents.paths import (
    FILE_MODE,
    ObservationPaths,
    UnsafeObservationPath,
    _open_private_directory,
    atomic_private_write,
    ensure_private_dir,
    read_private_bytes,
)

__all__ = [
    "FINGERPRINT_DOMAIN",
    "FingerprintKeyring",
    "KeyEpochChange",
    "configuration_fingerprint_id",
    "keyed_fingerprint",
]

#: Domain separator. The trailing NUL keeps the domain, the field name, and the value
#: unambiguously separated so no two fields can collide by concatenation.
FINGERPRINT_DOMAIN: Final = b"aether-observation/v1\0"

KEY_BYTES: Final = 32


def keyed_fingerprint(key: bytes, field_name: str, value: Any) -> str:
    """HMAC-SHA-256 over ``domain || field_name || NUL || canonical_json(value)``."""
    if len(key) != KEY_BYTES:
        raise ValueError("fingerprint keys are exactly 32 bytes")
    message = FINGERPRINT_DOMAIN + field_name.encode("utf-8") + b"\0" + canonical_json_bytes(value)
    return hmac.new(key, message, sha256).hexdigest()


def configuration_fingerprint_id(fields: dict[str, Any]) -> str:
    """Identity of one configuration record.

    Derived from already-keyed fingerprints and bounded non-secret values, so it is an
    ordinary SHA-256 and carries no dictionary-enumeration risk of its own.
    """
    return canonical_digest({"aether.observation.configuration.v1": fields})


@dataclass(frozen=True, slots=True)
class KeyEpochChange:
    """A comparison boundary, never a configuration delta.

    ``reason`` is ``created``, ``rotated``, or ``key_lost``. The reducer turns this into
    an explicit coverage boundary so a rotation is not misread as a changed model,
    prompt, skill set, or tool surface.
    """

    previous_key_id: str | None
    key_id: str
    reason: str


class FingerprintKeyring:
    """Owns one project's HMAC key epochs.

    The current epoch is selected by a non-secret pointer file that changes atomically;
    old key files are retained so historical events stay comparable within their epoch.
    """

    def __init__(self, paths: ObservationPaths) -> None:
        self._paths = paths
        self._key: bytes | None = None
        self._key_id: str | None = None
        self._last_change: KeyEpochChange | None = None

    # -- lifecycle ----------------------------------------------------------------
    @property
    def key_id(self) -> str:
        """The active non-secret key epoch identifier."""
        if self._key_id is None:
            self.load_or_create()
        assert self._key_id is not None
        return self._key_id

    @property
    def last_change(self) -> KeyEpochChange | None:
        return self._last_change

    def load_or_create(self) -> str:
        """Resolve the active epoch, creating one on first use or after key loss."""
        if self._key_id is not None:
            return self._key_id
        ensure_private_dir(self._paths.keys)
        pointer = self._paths.key_pointer
        recorded: str | None = None
        pointer_unreadable = False
        try:
            recorded = read_private_bytes(pointer).decode("utf-8").strip() or None
        except FileNotFoundError:
            recorded = None
        except (OSError, UnicodeError, ValueError):
            pointer_unreadable = True

        if recorded:
            key = self._read_key(recorded)
            if key is not None:
                self._key, self._key_id = key, recorded
                return recorded
            # OBS-D-028: detected key loss starts a new epoch and records a boundary.
            return self._install_new_key(previous=recorded, reason="key_lost")
        if pointer_unreadable:
            return self._install_new_key(previous=None, reason="key_lost")
        return self._install_new_key(previous=None, reason="created")

    def rotate(self) -> KeyEpochChange:
        """Owner-requested rotation. Old events remain valid inside their own epoch."""
        previous = self.load_or_create()
        self._install_new_key(previous=previous, reason="rotated")
        assert self._last_change is not None
        return self._last_change

    # -- fingerprints -------------------------------------------------------------
    def fingerprint(self, field_name: str, value: Any) -> str:
        """Compute one project-keyed, domain-separated field fingerprint."""
        self.load_or_create()
        assert self._key is not None
        return keyed_fingerprint(self._key, field_name, value)

    def fingerprint_optional(self, field_name: str, value: Any) -> str | None:
        """Return ``None`` for an unavailable source value instead of hashing nothing."""
        if value is None:
            return None
        return self.fingerprint(field_name, value)

    # -- internals ----------------------------------------------------------------
    def _read_key(self, key_id: str) -> bytes | None:
        try:
            path = self._paths.key_file(key_id)
            data = read_private_bytes(path)
        except (OSError, ValueError):
            return None
        if len(data) != KEY_BYTES or fingerprint_key_id(data) != key_id:
            return None
        return data

    def _install_new_key(self, *, previous: str | None, reason: str) -> str:
        key = secrets.token_bytes(KEY_BYTES)
        key_id = fingerprint_key_id(key)
        path = self._paths.key_file(key_id)
        ensure_private_dir(self._paths.keys)

        # Create with owner-only permissions from the first byte written, never after.
        parent_descriptor = _open_private_directory(self._paths.keys)
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
                raise UnsafeObservationPath("fingerprint key is not a private regular file")
            created_identity = (opened.st_dev, opened.st_ino)
            os.fchmod(descriptor, FILE_MODE)
            view = memoryview(key)
            written = 0
            while written < len(key):
                count = os.write(descriptor, view[written:])
                if count <= 0:
                    raise OSError("fingerprint key write made no progress")
                written += count
            os.fsync(descriptor)

            persisted = os.fstat(descriptor)
            named = os.stat(path.name, dir_fd=parent_descriptor, follow_symlinks=False)
            if (
                not stat.S_ISREG(persisted.st_mode)
                or persisted.st_nlink != 1
                or (named.st_dev, named.st_ino) != (persisted.st_dev, persisted.st_ino)
                or stat.S_IMODE(persisted.st_mode) != FILE_MODE
            ):
                raise UnsafeObservationPath("fingerprint key changed while writing")
            verification_descriptor = _open_private_directory(self._paths.keys)
            try:
                verified_parent = os.fstat(verification_descriptor)
                opened_parent = os.fstat(parent_descriptor)
                if (verified_parent.st_dev, verified_parent.st_ino) != (
                    opened_parent.st_dev,
                    opened_parent.st_ino,
                ):
                    raise UnsafeObservationPath("fingerprint key parent changed while writing")
            finally:
                os.close(verification_descriptor)
            os.fsync(parent_descriptor)
            installed = True
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if created_identity is not None and not installed:
                try:
                    remaining = os.stat(
                        path.name,
                        dir_fd=parent_descriptor,
                        follow_symlinks=False,
                    )
                    if (remaining.st_dev, remaining.st_ino) == created_identity:
                        os.unlink(path.name, dir_fd=parent_descriptor)
                        os.fsync(parent_descriptor)
                except OSError:
                    pass
            os.close(parent_descriptor)

        self._write_pointer_atomically(key_id)
        self._key, self._key_id = key, key_id
        self._last_change = KeyEpochChange(previous_key_id=previous, key_id=key_id, reason=reason)
        return key_id

    def _write_pointer_atomically(self, key_id: str) -> None:
        atomic_private_write(self._paths.key_pointer, (key_id + "\n").encode("utf-8"))
