"""Content-free project locks for observation storage transitions.

Journal producers retain their independent epoch locks.  This module owns the
coarser lock used only by out-of-callback maintenance: ingest, compaction, recovery,
and projection-pointer publication.  The filesystem lock provides process fencing
on POSIX while the in-process lock also serializes threads and makes nested use by
the same thread safe.
"""

from __future__ import annotations

import os
import stat
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from aether_agents.paths import (
    FILE_MODE,
    ObservationPaths,
    UnsafeObservationPath,
    _open_private_directory,
    ensure_private_dir,
)

try:  # The accepted observation durability protocol is POSIX-lock based.
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX fallback is thread-local only
    fcntl = None  # type: ignore[assignment]

__all__ = ["project_lock"]


_LOCKS_GUARD = threading.Lock()
_THREAD_LOCKS: dict[str, threading.RLock] = {}
_HELD = threading.local()


def _thread_lock(path: Path) -> threading.RLock:
    key = os.fspath(path)
    with _LOCKS_GUARD:
        return _THREAD_LOCKS.setdefault(key, threading.RLock())


@contextmanager
def project_lock(paths: ObservationPaths, name: str) -> Iterator[None]:
    """Hold one bounded-name project lock across threads and processes."""
    if not name or any(
        character not in "abcdefghijklmnopqrstuvwxyz0123456789-" for character in name
    ):
        raise ValueError("invalid observation lock name")
    ensure_private_dir(paths.locks)
    lock_path = paths.locks / f"{name}.lock"
    key = os.fspath(lock_path)
    lock = _thread_lock(lock_path)

    with lock:
        held = getattr(_HELD, "paths", None)
        if held is None:
            held = set()
            _HELD.paths = held
        if key in held:
            yield
            return

        parent_descriptor: int | None = None
        descriptor: int | None = None
        acquired = False
        try:
            flags = (
                os.O_RDWR | os.O_CREAT | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
            )
            if os.name == "posix":
                parent_descriptor = _open_private_directory(paths.locks)
                descriptor = os.open(
                    lock_path.name,
                    flags,
                    FILE_MODE,
                    dir_fd=parent_descriptor,
                )
                named = os.stat(
                    lock_path.name,
                    dir_fd=parent_descriptor,
                    follow_symlinks=False,
                )
            else:  # pragma: no cover - platform CI exercises the fallback
                descriptor = os.open(lock_path, flags, FILE_MODE)
                named = os.stat(lock_path, follow_symlinks=False)
            opened = os.fstat(descriptor)
            if (
                not stat.S_ISREG(opened.st_mode)
                or opened.st_nlink != 1
                or not stat.S_ISREG(named.st_mode)
                or named.st_nlink != 1
                or (named.st_dev, named.st_ino) != (opened.st_dev, opened.st_ino)
            ):
                raise UnsafeObservationPath("observation lock is not a private regular file")
            if os.name == "posix":
                os.fchmod(descriptor, FILE_MODE)
                if opened.st_uid != os.getuid():
                    raise UnsafeObservationPath("observation lock has a foreign owner")
                verification_descriptor = _open_private_directory(paths.locks)
                try:
                    verified_parent = os.fstat(verification_descriptor)
                    opened_parent = os.fstat(parent_descriptor)
                    if (verified_parent.st_dev, verified_parent.st_ino) != (
                        opened_parent.st_dev,
                        opened_parent.st_ino,
                    ):
                        raise UnsafeObservationPath("observation lock parent changed")
                finally:
                    os.close(verification_descriptor)
            if fcntl is not None:
                fcntl.flock(descriptor, fcntl.LOCK_EX)
                acquired = True
            held.add(key)
            try:
                yield
            finally:
                held.remove(key)
                if acquired and fcntl is not None:
                    fcntl.flock(descriptor, fcntl.LOCK_UN)
                    acquired = False
        finally:
            try:
                if acquired and descriptor is not None and fcntl is not None:
                    fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                try:
                    if descriptor is not None:
                        os.close(descriptor)
                finally:
                    if parent_descriptor is not None:
                        os.close(parent_descriptor)
