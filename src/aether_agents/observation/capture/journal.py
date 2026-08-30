"""Append-only per-process journal segments — the durable source of observation truth.

Normative sources: spec section 6.2, OBS-D-025, OBS-D-027, OBS-D-029, OBS-D-031,
OBS-FR-080, OBS-FR-082, OBS-FR-084, OBS-FR-086.

Durability contract, stated exactly as the design accepts it: the synchronous path does
allowlist projection, canonical serialization, and one bounded append-only ``write(2)``.
It never calls ``fsync``. That makes a segment **process-crash** recoverable on the
ordinary local filesystem path, and it deliberately does **not** claim power-loss
durability — a supervised flusher outside the agent path owns ``fsync``, and any loss
becomes visible coverage rather than hidden latency.

Unclean tails are detected by ownership, not by inspecting sequence numbers: a producer
holds ``locks/<producer_epoch>.lock`` for its whole lifetime and releases it only after
a clean close has renamed its active segment into ``closed/``. A reducer that can
acquire that lock while an ``active/`` segment still exists has proven the epoch ended
uncleanly, even when the visible sequence has no internal gap.
"""

from __future__ import annotations

import errno
import os
import re
import stat
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, BinaryIO, Final, Iterator

from aether_agents.observation.contracts import (
    MAX_EVENT_LINE_BYTES,
    CoverageClass,
    canonical_json_bytes,
    sha256_hex,
    validate_event,
)
from aether_agents.observation.identity import new_producer_epoch
from aether_agents.observation.privacy import ForbiddenPayload, assert_clean
from aether_agents.paths import (
    ObservationPaths,
    UnsafeObservationPath,
    _open_private_directory,
    ensure_private_dir,
    harden_file,
)

try:  # POSIX advisory locking; absent on Windows.
    import fcntl
except ImportError:  # pragma: no cover - exercised only on non-POSIX platforms
    fcntl = None  # type: ignore[assignment]

__all__ = [
    "AppendOutcome",
    "JournalWriter",
    "SegmentRef",
    "epoch_is_unclean",
    "iter_segment_lines",
    "list_segments",
    "parse_segment_name",
    "read_private_bytes",
    "read_segment",
]

#: Rotation thresholds. OBS-D-029/research section 7.2.6 leave these as measured
#: implementation parameters; only the archive format and no-pruning semantics are closed.
DEFAULT_MAX_SEGMENT_BYTES: Final = 64 * 1024 * 1024
DEFAULT_MAX_SEGMENT_EVENTS: Final = 50_000
# A semantic checkpoint may briefly contend with an ordinary local flush, but it never
# inherits unbounded kernel-fsync latency from the flusher.
DURABLE_SNAPSHOT_LOCK_TIMEOUT_S: Final = 0.005
APPEND_LOCK_TIMEOUT_S: Final = 0.005

_ACTIVE_RE: Final = re.compile(r"^(?P<epoch>prd_[a-f0-9]{32})\.(?P<first>\d+)\.active\.jsonl$")
_CLOSED_RE: Final = re.compile(
    r"^(?P<epoch>prd_[a-f0-9]{32})\.(?P<first>\d+)-(?P<last>\d+)\.jsonl$"
)


@dataclass(frozen=True, slots=True)
class SegmentRef:
    """One journal segment on disk."""

    path: Path
    producer_epoch: str
    first_seq: int
    last_seq: int | None  # None while the segment is still active
    state: str  # "active" | "closed" | "archive" | "quarantine"

    @property
    def is_active(self) -> bool:
        return self.state == "active"


@dataclass(frozen=True, slots=True)
class AppendOutcome:
    """Result of one synchronous append."""

    accepted: bool
    producer_seq: int | None
    byte_length: int
    reason_code: str | None = None
    coverage_class: str | None = None


@dataclass(frozen=True, slots=True)
class _CriticalSegmentDebt:
    """One content-free, identity-bound segment durability obligation."""

    active_path: Path
    closed_path: Path | None
    expected_dev: int | None
    expected_ino: int | None
    expected_size: int | None

    @property
    def key(self) -> str:
        if self.expected_dev is not None and self.expected_ino is not None:
            return f"inode:{self.expected_dev}:{self.expected_ino}"
        return f"path:{self.active_path}"

    @property
    def candidates(self) -> tuple[Path, ...]:
        if self.closed_path is None:
            return (self.active_path,)
        return (self.closed_path, self.active_path)

    @property
    def durability_directories(self) -> tuple[Path, ...]:
        if self.closed_path is None:
            return (self.active_path.parent,)
        # A rename crossing active/closed is durable only after both directory entries.
        return (self.closed_path.parent, self.active_path.parent)


def parse_segment_name(path: Path) -> SegmentRef | None:
    """Parse a segment filename into its producer epoch and sequence range."""
    name = path.name
    match = _ACTIVE_RE.match(name)
    if match:
        return SegmentRef(
            path=path,
            producer_epoch=match.group("epoch"),
            first_seq=int(match.group("first")),
            last_seq=None,
            state="active",
        )
    if name.endswith(".jsonl.gz"):
        name = name[: -len(".gz")]
    match = _CLOSED_RE.match(name)
    if match:
        state = (
            path.parent.name
            if path.parent.name in {"closed", "archive", "quarantine"}
            else "closed"
        )
        return SegmentRef(
            path=path,
            producer_epoch=match.group("epoch"),
            first_seq=int(match.group("first")),
            last_seq=int(match.group("last")),
            state=state,
        )
    return None


def list_segments(paths: ObservationPaths) -> list[SegmentRef]:
    """Every segment currently on disk, ordered by epoch then first sequence."""
    found: list[SegmentRef] = []
    for directory in (paths.active, paths.closed, paths.archive, paths.quarantine):
        for name in _private_directory_names(directory):
            candidate = directory / name
            reference = parse_segment_name(candidate)
            if reference is not None:
                found.append(reference)
    found.sort(key=lambda ref: (ref.producer_epoch, ref.first_seq))
    return found


def _private_directory_names(directory: Path) -> tuple[str, ...]:
    """List one journal directory without following its final path component."""
    if os.name != "posix":  # pragma: no cover - exercised by platform CI
        if directory.is_symlink():
            raise UnsafeObservationPath("journal directory is a symlink")
        if not directory.exists():
            return ()
        if not directory.is_dir():
            raise UnsafeObservationPath("journal directory is not a directory")
        return tuple(sorted(candidate.name for candidate in directory.iterdir()))

    try:
        descriptor = _open_private_directory(directory)
    except FileNotFoundError:
        return ()
    try:
        names = tuple(sorted(os.listdir(descriptor)))
        verification_descriptor = _open_private_directory(directory)
        try:
            verified = os.fstat(verification_descriptor)
            opened = os.fstat(descriptor)
            if (verified.st_dev, verified.st_ino) != (opened.st_dev, opened.st_ino):
                raise UnsafeObservationPath("journal directory changed while listing")
        finally:
            os.close(verification_descriptor)
        return names
    finally:
        os.close(descriptor)


def iter_segment_lines(path: Path) -> Iterator[tuple[int, bytes]]:
    """Yield ``(offset, line_without_lf)`` for every LF-terminated line.

    A trailing fragment without its LF is not yielded: it is an unfinished append and
    the caller records it as the segment's recoverable tail.
    """
    opener = _open_maybe_gzip(path)
    with opener as handle:
        offset = 0
        for raw in handle:
            if not raw.endswith(b"\n"):
                return
            yield offset, raw[:-1]
            offset += len(raw)


@contextmanager
def _open_private_regular(path: Path) -> Iterator[BinaryIO]:
    """Open one singly-linked regular file through a verified parent directory.

    ``O_NOFOLLOW`` prevents a symbolic-link target from ever becoming the opened
    descriptor.  The link-count and named-inode checks reject hard links and
    replacement races before bytes are returned to an observation reader.
    """
    path = Path(path)
    if path.name in {"", ".", ".."}:
        raise UnsafeObservationPath("private file has an unsafe name")

    if os.name != "posix":  # pragma: no cover - exercised by platform CI
        before = os.stat(path, follow_symlinks=False)
        if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
            raise UnsafeObservationPath("private file is a symlink or non-regular file")
        if before.st_nlink != 1:
            raise UnsafeObservationPath("private file has multiple hard links")
        handle = path.open("rb")
        try:
            opened = os.fstat(handle.fileno())
            if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
                raise UnsafeObservationPath("private file changed while opening")
            yield handle
            after = os.fstat(handle.fileno())
            if after.st_nlink != 1:
                raise UnsafeObservationPath("private file gained another hard link")
        finally:
            handle.close()
        return

    parent_descriptor = _open_private_directory(path.parent)

    descriptor = -1
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
                raise UnsafeObservationPath(
                    "private file is a symlink or non-regular file"
                ) from exc
            raise

        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise UnsafeObservationPath("private file is not a regular file")
        if opened.st_nlink != 1:
            raise UnsafeObservationPath("private file has multiple hard links")
        try:
            named = os.stat(path.name, dir_fd=parent_descriptor, follow_symlinks=False)
        except FileNotFoundError:
            # An active segment may be atomically renamed to ``closed`` after the
            # descriptor is opened.  The descriptor remains a safe, owned inode.
            named = None
        if named is not None and (
            stat.S_ISLNK(named.st_mode)
            or not stat.S_ISREG(named.st_mode)
            or (named.st_dev, named.st_ino) != (opened.st_dev, opened.st_ino)
        ):
            raise UnsafeObservationPath("private file changed while opening")

        handle = os.fdopen(descriptor, "rb", closefd=True)
        descriptor = -1
        try:
            yield handle
            after = os.fstat(handle.fileno())
            if not stat.S_ISREG(after.st_mode) or after.st_nlink != 1:
                raise UnsafeObservationPath("private file ownership changed while reading")
            verification_descriptor = _open_private_directory(path.parent)
            try:
                verified_parent = os.fstat(verification_descriptor)
                opened_parent = os.fstat(parent_descriptor)
                if (verified_parent.st_dev, verified_parent.st_ino) != (
                    opened_parent.st_dev,
                    opened_parent.st_ino,
                ):
                    raise UnsafeObservationPath("private file parent changed while reading")
            finally:
                os.close(verification_descriptor)
        finally:
            handle.close()
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        os.close(parent_descriptor)


@contextmanager
def _open_maybe_gzip(path: Path) -> Iterator[BinaryIO]:
    with _open_private_regular(path) as raw:
        if path.name.endswith(".gz"):
            import gzip

            with gzip.GzipFile(fileobj=raw, mode="rb") as handle:
                yield handle
        else:
            yield raw


def read_private_bytes(path: Path) -> bytes:
    """Read exact on-disk bytes from a real, singly-linked private file."""
    with _open_private_regular(path) as handle:
        return handle.read()


@dataclass(frozen=True, slots=True)
class SegmentRead:
    """Outcome of reading one segment's raw lines."""

    lines: list[bytes]
    trailing_fragment: bytes
    uncompressed_sha256: str
    byte_length: int


def read_segment(path: Path) -> SegmentRead:
    """Read a segment, preserving any unfinished trailing fragment verbatim.

    Ingestion stops at the last valid LF-terminated line; the exact original bytes and
    the exact tail are preserved for local diagnosis until an explicit owner purge.
    """
    with _open_maybe_gzip(path) as handle:
        data = handle.read()
    lines: list[bytes] = []
    fragment = b""
    if data:
        parts = data.split(b"\n")
        fragment = parts.pop()  # empty when the file ends with LF
        lines = parts
    return SegmentRead(
        lines=lines,
        trailing_fragment=fragment,
        uncompressed_sha256=sha256_hex(data),
        byte_length=len(data),
    )


def _open_epoch_lock(
    paths: ObservationPaths,
    producer_epoch: str,
    *,
    create: bool,
) -> tuple[int, int]:
    """Open one producer lock through a retained, fully verified directory chain."""
    lock_path = paths.lock_file(producer_epoch)
    parent_descriptor = _open_private_directory(lock_path.parent)
    descriptor: int | None = None
    try:
        flags = (
            os.O_RDWR
            | (os.O_CREAT if create else 0)
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_CLOEXEC", 0)
        )
        descriptor = os.open(lock_path.name, flags, 0o600, dir_fd=parent_descriptor)
        opened = os.fstat(descriptor)
        named = os.stat(lock_path.name, dir_fd=parent_descriptor, follow_symlinks=False)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_nlink != 1
            or not stat.S_ISREG(named.st_mode)
            or named.st_nlink != 1
            or (named.st_dev, named.st_ino) != (opened.st_dev, opened.st_ino)
        ):
            raise UnsafeObservationPath("producer epoch lock is aliased or changed")
        verification_descriptor = _open_private_directory(lock_path.parent)
        try:
            verified_parent = os.fstat(verification_descriptor)
            opened_parent = os.fstat(parent_descriptor)
            if (verified_parent.st_dev, verified_parent.st_ino) != (
                opened_parent.st_dev,
                opened_parent.st_ino,
            ):
                raise UnsafeObservationPath("producer epoch lock directory route changed")
        finally:
            os.close(verification_descriptor)
        return descriptor, parent_descriptor
    except BaseException:
        if descriptor is not None:
            os.close(descriptor)
        os.close(parent_descriptor)
        raise


def epoch_is_unclean(paths: ObservationPaths, producer_epoch: str) -> bool:
    """True when ``producer_epoch`` ended without a clean close.

    Ownership is the evidence. If the epoch lock can be acquired while an ``active/``
    segment still exists, the writer is gone and never renamed its segment. Contiguous
    visible sequence numbers never prove a clean tail (OBS-FR-086).
    """
    active_present = any(
        reference.producer_epoch == producer_epoch and reference.is_active
        for reference in list_segments(paths)
    )
    if not active_present:
        return False
    if fcntl is None:  # pragma: no cover - non-POSIX fallback
        return True
    parent_descriptor: int | None = None
    try:
        descriptor, parent_descriptor = _open_epoch_lock(
            paths,
            producer_epoch,
            create=False,
        )
    except FileNotFoundError:
        # No live writer ever held the lock, yet an active segment remains.
        return True
    except (OSError, UnsafeObservationPath):
        # An unavailable or unstable authority path cannot prove an unclean epoch.
        return False
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        # A live writer still owns it. A reducer never disturbs a held lock.
        return False
    else:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        return True
    finally:
        os.close(descriptor)
        if parent_descriptor is not None:
            os.close(parent_descriptor)


@dataclass
class JournalWriter:
    """One process's exclusive writer for one project's journal.

    The writer owns exactly one active segment at a time and never shares its file
    descriptor. Every failure mode is fail-open: an append that cannot be completed
    degrades coverage and is reported, and never escapes into the agent loop.
    """

    paths: ObservationPaths
    producer_epoch: str
    max_segment_bytes: int = DEFAULT_MAX_SEGMENT_BYTES
    max_segment_events: int = DEFAULT_MAX_SEGMENT_EVENTS
    max_line_bytes: int = MAX_EVENT_LINE_BYTES

    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    _lock_fd: int | None = field(default=None, init=False, repr=False)
    _segment_fd: int | None = field(default=None, init=False, repr=False)
    _segment_parent_fd: int | None = field(default=None, init=False, repr=False)
    _segment_path: Path | None = field(default=None, init=False, repr=False)
    _first_seq: int = field(default=0, init=False, repr=False)
    _next_seq: int = field(default=0, init=False, repr=False)
    _segment_bytes: int = field(default=0, init=False, repr=False)
    _durable_bytes: int = field(default=0, init=False, repr=False)
    _durable_snapshot_state: tuple[Path, int, int, int] | None = field(
        default=None,
        init=False,
        repr=False,
    )
    _segment_events: int = field(default=0, init=False, repr=False)
    _degraded: bool = field(default=False, init=False, repr=False)
    _critical_pending: bool = field(default=False, init=False, repr=False)
    _current_segment_critical: bool = field(default=False, init=False, repr=False)
    _rotation_pending: bool = field(default=False, init=False, repr=False)
    _undurable_critical_segments: dict[str, _CriticalSegmentDebt] = field(
        default_factory=dict,
        init=False,
        repr=False,
    )
    _flush_signal: threading.Event = field(default_factory=threading.Event, init=False, repr=False)
    _io_failures: int = field(default=0, init=False, repr=False)
    _rejected: int = field(default=0, init=False, repr=False)
    _closed_segments: list[Path] = field(default_factory=list, init=False, repr=False)

    # -- lifecycle ----------------------------------------------------------------
    def open(self) -> None:
        """Acquire the epoch lock and open a fresh active segment."""
        with self._lock:
            if self._segment_fd is not None:
                return
            self.paths.ensure()
            self._acquire_epoch_lock()
            self._open_segment(self._next_seq)

    def close(self) -> Path | None:
        """Clean close: flush, fsync, atomically rename into ``closed/``, then unlock.

        The lock is released last, and only after the rename is durable, so the
        ownership test in :func:`epoch_is_unclean` cannot produce a false positive.
        """
        with self._lock:
            closed = self._close_segment_locked()
            self._release_epoch_lock()
            return closed

    def close_bounded(self, timeout_s: float) -> Path | None:
        """Attempt a clean close without letting teardown wait indefinitely.

        Python cannot cancel a kernel ``fsync`` or a thread blocked on ``_lock``.  A
        daemon owns that best-effort attempt; the caller waits only ``timeout_s`` and
        reports an I/O failure if the kernel operation remains stuck.
        """
        completed = threading.Event()
        result: list[Path | None] = []

        def run() -> None:
            try:
                result.append(self.close())
            except Exception:  # noqa: BLE001 - teardown stays fail-open
                result.append(None)
            finally:
                completed.set()

        worker = threading.Thread(target=run, name="aether-observation-journal-close", daemon=True)
        worker.start()
        if not completed.wait(max(0.0, timeout_s)):
            self._io_failures += 1
            self._degraded = True
            return None
        return result[0] if result else None

    # -- synchronous collection path ----------------------------------------------
    def append(self, event: dict[str, Any], *, critical: bool = False) -> AppendOutcome:
        """Serialize and append one event. Never calls ``fsync``; never raises.

        ``critical`` marks a contract-critical fact (``contract.persisted``,
        ``handoff.completed``, ``work_unit.bound``, ``acceptance.evaluated``,
        ``contract.completion_verified``, terminal resolution, explicit coverage gaps).
        It only asks the supervised flusher to run sooner; it never makes the caller wait.
        """
        try:
            return self._append_guarded(event, critical=critical)
        except ForbiddenPayload as rejection:
            self._rejected += 1
            return AppendOutcome(
                accepted=False,
                producer_seq=None,
                byte_length=0,
                reason_code=rejection.reason_code,
                coverage_class=CoverageClass.FORBIDDEN_PAYLOAD_REJECTED,
            )
        except Exception:  # noqa: BLE001 - fail-open is the accepted contract
            self._io_failures += 1
            self._degraded = True
            return AppendOutcome(
                accepted=False,
                producer_seq=None,
                byte_length=0,
                reason_code="APPEND_FAILED",
                coverage_class=CoverageClass.OBSERVER_IO_FAILURE,
            )

    def append_nonblocking(
        self,
        event: dict[str, Any],
        *,
        critical: bool = False,
    ) -> AppendOutcome:
        """Best-effort diagnostic append that never waits for durability work.

        A checkpoint may discover unavailable authority while the flusher owns the
        writer lock for a potentially unbounded kernel ``fsync``. Its content-free
        diagnostic must not turn that observer failure into native workflow latency.
        """
        try:
            self._validate_append_event(event)
            if not self._lock.acquire(blocking=False):
                return AppendOutcome(
                    accepted=False,
                    producer_seq=None,
                    byte_length=0,
                    reason_code="JOURNAL_BUSY",
                    coverage_class=CoverageClass.OBSERVER_IO_FAILURE,
                )
            try:
                return self._append_locked(event, critical=critical)
            finally:
                self._lock.release()
        except ForbiddenPayload as rejection:
            self._rejected += 1
            return AppendOutcome(
                accepted=False,
                producer_seq=None,
                byte_length=0,
                reason_code=rejection.reason_code,
                coverage_class=CoverageClass.FORBIDDEN_PAYLOAD_REJECTED,
            )
        except Exception:  # noqa: BLE001 - fail-open is the accepted contract
            self._io_failures += 1
            self._degraded = True
            return AppendOutcome(
                accepted=False,
                producer_seq=None,
                byte_length=0,
                reason_code="APPEND_FAILED",
                coverage_class=CoverageClass.OBSERVER_IO_FAILURE,
            )

    def _append_guarded(self, event: dict[str, Any], *, critical: bool) -> AppendOutcome:
        self._validate_append_event(event)
        if not self._lock.acquire(timeout=APPEND_LOCK_TIMEOUT_S):
            self._io_failures += 1
            self._degraded = True
            return AppendOutcome(
                accepted=False,
                producer_seq=None,
                byte_length=0,
                reason_code="JOURNAL_BUSY",
                coverage_class=CoverageClass.OBSERVER_IO_FAILURE,
            )
        try:
            return self._append_locked(event, critical=critical)
        finally:
            self._lock.release()

    @staticmethod
    def _validate_append_event(event: dict[str, Any]) -> None:
        # Defence in depth after projection: a forbidden field must not reach the
        # serializer, the buffer, or a diagnostic message.
        assert_clean(event)
        try:
            validate_event(event)
        except Exception as error:
            # jsonschema error messages can echo payload values.  Convert the
            # failure to a bounded rejection before it reaches any log or retry
            # buffer and never retain the original exception text.
            raise ForbiddenPayload("EVENT_SCHEMA_INVALID", "$") from error

    def _append_locked(self, event: dict[str, Any], *, critical: bool) -> AppendOutcome:
        if self._segment_fd is None:
            self.paths.ensure()
            self._acquire_epoch_lock()
            self._open_segment(self._next_seq)

        producer_seq = self._next_seq
        payload = dict(event)
        payload["producer_epoch"] = self.producer_epoch
        payload["producer_seq"] = producer_seq
        line = canonical_json_bytes(payload) + b"\n"

        if len(line) > self.max_line_bytes:
            # Rejected before append, never split into a partial line.
            self._rejected += 1
            return AppendOutcome(
                accepted=False,
                producer_seq=None,
                byte_length=len(line),
                reason_code="LINE_TOO_LARGE",
                coverage_class=CoverageClass.FORBIDDEN_PAYLOAD_REJECTED,
            )

        written = self._write_all(line)
        if written != len(line):
            # A short write leaves a partial line. Stop using this segment so no
            # later append can be appended behind the fragment.
            self._degraded = True
            self._io_failures += 1
            self._roll_after_failure()
            return AppendOutcome(
                accepted=False,
                producer_seq=None,
                byte_length=written,
                reason_code="SHORT_WRITE",
                coverage_class=CoverageClass.OBSERVER_IO_FAILURE,
            )

        self._next_seq = producer_seq + 1
        self._segment_bytes += len(line)
        self._segment_events += 1
        if critical:
            self._current_segment_critical = True
            self._critical_pending = True
            self._flush_signal.set()
        if (
            self._segment_bytes >= self.max_segment_bytes
            or self._segment_events >= self.max_segment_events
        ):
            # Thresholds are soft until the supervised flusher crosses the durability
            # boundary. A callback only requests that work; it never closes/fsyncs.
            self._rotation_pending = True
            self._flush_signal.set()
        return AppendOutcome(accepted=True, producer_seq=producer_seq, byte_length=len(line))

    # -- supervised durability (called by the flusher, never from a callback) -------
    def flush(self) -> bool:
        """Durably flush the active segment and retry older critical segment debt."""
        with self._lock:
            # Retry only debt that existed when this supervised cycle began. If this
            # cycle itself encounters a failure, it reports that failure and leaves the
            # newly recorded obligation for the next supervised cycle.
            debt_snapshot = tuple(self._undurable_critical_segments.items())
            active_succeeded = True
            if self._segment_fd is not None:
                try:
                    durable_stat = self._sync_active_segment_locked()
                except (OSError, UnsafeObservationPath):
                    self._io_failures += 1
                    self._degraded = True
                    active_succeeded = False
                else:
                    self._durable_bytes = self._segment_bytes
                    self._durable_snapshot_state = (
                        self._segment_path,
                        self._durable_bytes,
                        durable_stat.st_dev,
                        durable_stat.st_ino,
                    )
                    if self._rotation_pending:
                        # Rotation's rename and both directory fsyncs remain part of
                        # this segment's durability boundary.
                        active_succeeded = self._rotate_locked(presynced=True)
                    else:
                        self._current_segment_critical = False

            debt_succeeded = self._retry_critical_debt_locked(debt_snapshot)
            self._critical_pending = self._current_segment_critical or bool(
                self._undurable_critical_segments
            )
            if not self._critical_pending:
                self._flush_signal.clear()
            return active_succeeded and debt_succeeded and not self._critical_pending

    def durable_snapshot(self) -> tuple[Path, bytes] | None:
        """Copy only this writer's file+directory-fsynced active prefix.

        The flusher atomically publishes an immutable path/length/inode tuple only after
        file and directory fsync. A bounded lock acquisition excludes an in-progress
        durability transition; timeout makes the evidence unavailable instead of
        inheriting unbounded kernel-fsync latency. A no-follow reader then proves that
        tuple still names the same inode. Bytes appended after the last successful
        boundary are deliberately excluded.
        """

        if not self._lock.acquire(timeout=DURABLE_SNAPSHOT_LOCK_TIMEOUT_S):
            return None
        reader: int | None = None
        try:
            state = self._durable_snapshot_state
            if state is None:
                return None
            path, durable_bytes, expected_dev, expected_ino = state
            flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
            try:
                if os.name == "posix":
                    parent_descriptor = self._segment_parent_fd
                    if parent_descriptor is None:
                        return None
                    reader = os.open(path.name, flags, dir_fd=parent_descriptor)
                    named = os.stat(
                        path.name,
                        dir_fd=parent_descriptor,
                        follow_symlinks=False,
                    )
                    self._assert_directory_route(path.parent, parent_descriptor)
                else:  # pragma: no cover - exercised by platform CI
                    reader = os.open(path, flags)
                    named = os.stat(path, follow_symlinks=False)
                reader_stat = os.fstat(reader)
            except (OSError, UnsafeObservationPath):
                if reader is not None:
                    os.close(reader)
                return None
            if (
                not stat.S_ISREG(reader_stat.st_mode)
                or reader_stat.st_nlink != 1
                or not stat.S_ISREG(named.st_mode)
                or named.st_nlink != 1
                or (reader_stat.st_dev, reader_stat.st_ino) != (expected_dev, expected_ino)
                or (named.st_dev, named.st_ino) != (expected_dev, expected_ino)
                or reader_stat.st_size < durable_bytes
                or named.st_size < durable_bytes
            ):
                os.close(reader)
                reader = None
                return None
        finally:
            self._lock.release()
        assert reader is not None
        try:
            data = os.pread(reader, durable_bytes, 0)
        except OSError:
            return None
        finally:
            os.close(reader)
        if len(data) != durable_bytes:
            return None
        return path, data

    def wait_for_flush_request(self, timeout_s: float) -> bool:
        """Wait for a critical append or until the ordinary interval expires."""
        requested = self._flush_signal.wait(max(0.0, timeout_s))
        if requested:
            # Pending durability is a separate state and survives a failed fsync.  The
            # signal only interrupts the current sleep; consuming it avoids a busy loop.
            self._flush_signal.clear()
        return requested

    def wake_flusher(self) -> None:
        """Interrupt flusher sleep during teardown without changing durability state."""
        self._flush_signal.set()

    @property
    def critical_pending(self) -> bool:
        return self._critical_pending

    @property
    def degraded(self) -> bool:
        return self._degraded

    @property
    def io_failure_count(self) -> int:
        return self._io_failures

    @property
    def rejected_count(self) -> int:
        return self._rejected

    @property
    def next_seq(self) -> int:
        return self._next_seq

    @property
    def active_segment(self) -> Path | None:
        return self._segment_path

    @property
    def closed_segments(self) -> tuple[Path, ...]:
        return tuple(self._closed_segments)

    # -- internals ----------------------------------------------------------------
    def _acquire_epoch_lock(self) -> None:
        if fcntl is None:  # pragma: no cover - non-POSIX fallback
            return
        ensure_private_dir(self.paths.locks)
        descriptor, parent_descriptor = _open_epoch_lock(
            self.paths,
            self.producer_epoch,
            create=True,
        )
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            os.fchmod(descriptor, 0o600)
            self._assert_directory_route(self.paths.locks, parent_descriptor)
        except UnsafeObservationPath:
            os.close(descriptor)
            raise
        except OSError:
            os.close(descriptor)
            raise RuntimeError(f"producer epoch already locked: {self.producer_epoch}")
        finally:
            os.close(parent_descriptor)
        self._lock_fd = descriptor

    def _release_epoch_lock(self) -> None:
        if self._lock_fd is None:
            return
        if fcntl is not None:
            try:
                fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
            except OSError:
                pass
        try:
            os.close(self._lock_fd)
        except OSError:
            pass
        self._lock_fd = None

    def _open_segment(self, first_seq: int) -> None:
        ensure_private_dir(self.paths.active)
        name = f"{self.producer_epoch}.{first_seq}.active.jsonl"
        path = self.paths.active / name
        parent_descriptor: int | None = None
        descriptor: int | None = None
        try:
            if os.name == "posix":
                parent_descriptor = _open_private_directory(path.parent)
                flags = (
                    os.O_WRONLY
                    | os.O_APPEND
                    | os.O_CREAT
                    | os.O_EXCL
                    | getattr(os, "O_NOFOLLOW", 0)
                    | getattr(os, "O_CLOEXEC", 0)
                )
                descriptor = os.open(name, flags, 0o600, dir_fd=parent_descriptor)
                opened = os.fstat(descriptor)
                named = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
                if (
                    not stat.S_ISREG(opened.st_mode)
                    or opened.st_nlink != 1
                    or not stat.S_ISREG(named.st_mode)
                    or named.st_nlink != 1
                    or (named.st_dev, named.st_ino) != (opened.st_dev, opened.st_ino)
                ):
                    raise UnsafeObservationPath("active journal segment is aliased or changed")
                os.fchmod(descriptor, 0o600)
                self._assert_directory_route(path.parent, parent_descriptor)
            else:  # pragma: no cover - exercised by platform CI
                descriptor = os.open(
                    path,
                    os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_EXCL,
                    0o600,
                )
                harden_file(path)
        except BaseException:
            if descriptor is not None:
                os.close(descriptor)
            if parent_descriptor is not None:
                os.close(parent_descriptor)
            raise
        assert descriptor is not None
        self._segment_fd = descriptor
        self._segment_parent_fd = parent_descriptor
        self._segment_path = path
        self._durable_bytes = 0
        self._durable_snapshot_state = None
        self._current_segment_critical = False
        self._rotation_pending = False
        self._first_seq = first_seq
        self._next_seq = max(self._next_seq, first_seq)
        try:
            self._segment_bytes = os.fstat(descriptor).st_size
        except OSError:
            self._segment_bytes = 0
        self._segment_events = 0

    def _sync_active_segment_locked(self) -> os.stat_result:
        """Fsync the exact active inode and its retained, still-routed parent."""
        descriptor = self._segment_fd
        path = self._segment_path
        if descriptor is None or path is None:
            raise UnsafeObservationPath("active journal segment is unavailable")

        before = os.fstat(descriptor)
        if os.name != "posix":  # pragma: no cover - exercised by platform CI
            os.fsync(descriptor)
            self._fsync_directory(path.parent)
            return os.fstat(descriptor)

        parent_descriptor = self._segment_parent_fd
        if parent_descriptor is None:
            raise UnsafeObservationPath("active journal parent descriptor is unavailable")
        self._assert_active_segment_binding(before)
        os.fsync(descriptor)
        after_file = os.fstat(descriptor)
        self._assert_active_segment_binding(after_file)

        # Keep the public seam used by durability-failure tests, then prove that the
        # retained directory (not merely whatever the route names now) crossed fsync.
        self._fsync_directory(path.parent)
        self._fsync_bound_directory(path.parent, parent_descriptor)
        durable = os.fstat(descriptor)
        self._assert_active_segment_binding(durable)
        return durable

    def _assert_active_segment_binding(self, expected: os.stat_result) -> None:
        descriptor = self._segment_fd
        parent_descriptor = self._segment_parent_fd
        path = self._segment_path
        if descriptor is None or parent_descriptor is None or path is None:
            raise UnsafeObservationPath("active journal binding is unavailable")
        opened = os.fstat(descriptor)
        named = os.stat(path.name, dir_fd=parent_descriptor, follow_symlinks=False)
        expected_identity = (expected.st_dev, expected.st_ino)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_nlink != 1
            or not stat.S_ISREG(named.st_mode)
            or named.st_nlink != 1
            or (opened.st_dev, opened.st_ino) != expected_identity
            or (named.st_dev, named.st_ino) != expected_identity
            or opened.st_size != expected.st_size
            or named.st_size != expected.st_size
        ):
            raise UnsafeObservationPath("active journal segment changed during durability")
        self._assert_directory_route(path.parent, parent_descriptor)

    @staticmethod
    def _assert_directory_route(directory: Path, expected_descriptor: int) -> None:
        verification_descriptor = _open_private_directory(directory)
        try:
            expected = os.fstat(expected_descriptor)
            verified = os.fstat(verification_descriptor)
            if (
                not stat.S_ISDIR(expected.st_mode)
                or not stat.S_ISDIR(verified.st_mode)
                or (verified.st_dev, verified.st_ino) != (expected.st_dev, expected.st_ino)
            ):
                raise UnsafeObservationPath("journal durability directory route changed")
        finally:
            os.close(verification_descriptor)

    @classmethod
    def _fsync_bound_directory(cls, directory: Path, descriptor: int) -> None:
        opened = os.fstat(descriptor)
        if not stat.S_ISDIR(opened.st_mode):
            raise UnsafeObservationPath("journal durability parent is not a real directory")
        os.fsync(descriptor)
        cls._assert_directory_route(directory, descriptor)

    def _write_all(self, line: bytes) -> int:
        """Perform exactly one append write (retrying only an interrupted syscall).

        A short write is evidence loss, not an invitation to append a second chunk
        behind a potentially torn line.  The caller abandons that segment intact.
        """
        assert self._segment_fd is not None
        while True:
            try:
                return os.write(self._segment_fd, line)
            except OSError as error:
                if error.errno == errno.EINTR:
                    continue
                # ENOSPC and friends: report what actually reached the file.
                return 0

    def _drop_active_handles(self) -> None:
        if self._segment_fd is not None:
            try:
                os.close(self._segment_fd)
            except OSError:
                pass
        if self._segment_parent_fd is not None:
            try:
                os.close(self._segment_parent_fd)
            except OSError:
                pass
        self._segment_fd = None
        self._segment_parent_fd = None
        self._segment_path = None
        self._durable_bytes = 0
        self._durable_snapshot_state = None
        self._rotation_pending = False

    def _close_segment_locked(self, *, presynced: bool = False) -> Path | None:
        if self._segment_fd is None:
            return None
        descriptor = self._segment_fd
        source = self._segment_path
        assert source is not None
        try:
            segment_stat = os.fstat(descriptor)
        except OSError:
            segment_stat = None
        last_seq = max(self._next_seq - 1, self._first_seq)
        target = self.paths.closed / f"{self.producer_epoch}.{self._first_seq}-{last_seq}.jsonl"

        try:
            if not presynced:
                segment_stat = self._sync_active_segment_locked()
            elif segment_stat is not None and os.name == "posix":
                self._assert_active_segment_binding(segment_stat)
        except (OSError, UnsafeObservationPath):
            self._io_failures += 1
            self._degraded = True
            self._drop_active_handles()
            self._record_durability_debt(
                source,
                closed_path=target,
                segment_stat=segment_stat,
            )
            return None

        ensure_private_dir(self.paths.closed)
        closed_parent_descriptor: int | None = None
        close_succeeded = False
        empty_segment = (
            self._segment_events == 0 and segment_stat is not None and segment_stat.st_size == 0
        )
        try:
            if segment_stat is None:
                raise UnsafeObservationPath("active journal identity is unavailable at close")
            if os.name == "posix":
                active_parent_descriptor = self._segment_parent_fd
                if active_parent_descriptor is None:
                    raise UnsafeObservationPath("active journal parent is unavailable at close")
                closed_parent_descriptor = _open_private_directory(target.parent)
                self._assert_active_segment_binding(segment_stat)
                self._assert_directory_route(target.parent, closed_parent_descriptor)

                if empty_segment:
                    os.unlink(source.name, dir_fd=active_parent_descriptor)
                    self._fsync_directory(source.parent)
                    self._fsync_bound_directory(source.parent, active_parent_descriptor)
                else:
                    os.replace(
                        source.name,
                        target.name,
                        src_dir_fd=active_parent_descriptor,
                        dst_dir_fd=closed_parent_descriptor,
                    )
                    os.fchmod(descriptor, 0o600)
                    named_target = os.stat(
                        target.name,
                        dir_fd=closed_parent_descriptor,
                        follow_symlinks=False,
                    )
                    if not self._same_private_file(named_target, segment_stat):
                        raise UnsafeObservationPath("closed journal inode changed during publish")
                    self._fsync_directory(target.parent)
                    self._fsync_bound_directory(target.parent, closed_parent_descriptor)
                    self._fsync_directory(source.parent)
                    self._fsync_bound_directory(source.parent, active_parent_descriptor)
                    named_after = os.stat(
                        target.name,
                        dir_fd=closed_parent_descriptor,
                        follow_symlinks=False,
                    )
                    if not self._same_private_file(named_after, segment_stat):
                        raise UnsafeObservationPath("closed journal inode changed after durability")
                close_succeeded = True
            else:  # pragma: no cover - exercised by platform CI
                routed_source = os.stat(source, follow_symlinks=False)
                if not self._same_private_file(routed_source, segment_stat):
                    raise UnsafeObservationPath("active journal route changed before close")
                if empty_segment:
                    source.unlink(missing_ok=True)
                    self._fsync_directory(source.parent)
                else:
                    os.replace(source, target)
                    harden_file(target)
                    self._fsync_directory(target.parent)
                    self._fsync_directory(source.parent)
                    routed_target = os.stat(target, follow_symlinks=False)
                    if not self._same_private_file(routed_target, segment_stat):
                        raise UnsafeObservationPath("closed journal route changed during publish")
                close_succeeded = True
        except (OSError, UnsafeObservationPath):
            self._io_failures += 1
            self._degraded = True
        finally:
            if closed_parent_descriptor is not None:
                os.close(closed_parent_descriptor)
            self._drop_active_handles()

        if not close_succeeded:
            self._record_durability_debt(
                source,
                closed_path=target,
                segment_stat=segment_stat,
            )
            return None
        self._current_segment_critical = False
        self._critical_pending = bool(self._undurable_critical_segments)
        self._flush_signal.clear()
        if empty_segment:
            return None
        self._closed_segments.append(target)
        return target

    def _rotate_locked(self, *, presynced: bool = False) -> bool:
        """Close the full segment and open the next one inside the same epoch."""
        next_first = self._next_seq
        closed = self._close_segment_locked(presynced=presynced)
        self._open_segment(next_first)
        return closed is not None

    def _roll_after_failure(self) -> None:
        """Abandon a possibly torn segment and continue under a fresh epoch."""
        if self._segment_fd is None:
            return
        damaged_path = self._segment_path
        try:
            segment_stat = os.fstat(self._segment_fd)
        except OSError:
            segment_stat = None
        if damaged_path is not None:
            self._record_durability_debt(damaged_path, segment_stat=segment_stat)
        try:
            os.close(self._segment_fd)
        except OSError:
            pass
        self._segment_fd = None
        if self._segment_parent_fd is not None:
            try:
                os.close(self._segment_parent_fd)
            except OSError:
                pass
        self._segment_parent_fd = None
        # The damaged segment stays exactly where it is, in ``active/``. The reducer
        # ingests its valid LF-terminated prefix and records the tail as a coverage gap;
        # nothing rewrites or truncates the original bytes.
        self._segment_path = None
        self._durable_bytes = 0
        self._durable_snapshot_state = None
        self._rotation_pending = False
        self._release_epoch_lock()
        self.producer_epoch = new_producer_epoch()
        self._first_seq = 0
        self._next_seq = 0
        self._segment_bytes = 0
        self._segment_events = 0

    def _record_durability_debt(
        self,
        segment_path: Path,
        *,
        closed_path: Path | None = None,
        segment_stat: os.stat_result | None = None,
    ) -> None:
        """Retain an identity-bound, content-free obligation for supervised retry."""
        if self._current_segment_critical:
            if segment_stat is None:
                try:
                    segment_stat = os.stat(segment_path, follow_symlinks=False)
                except OSError:
                    segment_stat = None
            regular = segment_stat is not None and stat.S_ISREG(segment_stat.st_mode)
            debt = _CriticalSegmentDebt(
                active_path=segment_path,
                closed_path=closed_path,
                expected_dev=segment_stat.st_dev if regular else None,
                expected_ino=segment_stat.st_ino if regular else None,
                expected_size=segment_stat.st_size if regular else None,
            )
            existing = self._undurable_critical_segments.get(debt.key)
            if existing is not None and existing.closed_path is not None:
                debt = existing
            self._undurable_critical_segments[debt.key] = debt
        self._current_segment_critical = False
        self._critical_pending = bool(self._undurable_critical_segments)

    def _retry_critical_debt_locked(
        self,
        debt_snapshot: tuple[tuple[str, _CriticalSegmentDebt], ...],
    ) -> bool:
        """Retry every pre-existing debt without acknowledging changed filesystem state."""
        succeeded = True
        for key, debt in sorted(debt_snapshot, key=lambda item: item[0]):
            if self._undurable_critical_segments.get(key) != debt:
                continue
            durable_path = self._retry_one_critical_debt(debt)
            if durable_path is None:
                self._io_failures += 1
                self._degraded = True
                succeeded = False
                continue
            # Remove only the exact obligation whose identity was just proven durable.
            if self._undurable_critical_segments.get(key) == debt:
                del self._undurable_critical_segments[key]
            if (
                durable_path.parent == self.paths.closed
                and durable_path not in self._closed_segments
            ):
                self._closed_segments.append(durable_path)
        return succeeded

    def _retry_one_critical_debt(self, debt: _CriticalSegmentDebt) -> Path | None:
        """Reopen one known segment without following links and cross its full boundary."""
        if debt.expected_dev is None or debt.expected_ino is None or debt.expected_size is None:
            return None
        for candidate in debt.candidates:
            if not self._debt_candidate_is_confined(debt, candidate):
                continue
            parent_fd: int | None = None
            descriptor: int | None = None
            try:
                parent_fd = _open_private_directory(candidate.parent)
                parent_stat = os.fstat(parent_fd)
                if not stat.S_ISDIR(parent_stat.st_mode):
                    continue
                file_flags = (
                    os.O_RDONLY
                    | getattr(os, "O_NOFOLLOW", 0)
                    | getattr(os, "O_CLOEXEC", 0)
                    | getattr(os, "O_NONBLOCK", 0)
                )
                descriptor = os.open(candidate.name, file_flags, dir_fd=parent_fd)
                if not self._debt_identity_matches(
                    os.fstat(descriptor),
                    debt,
                ):
                    continue
                named = os.stat(candidate.name, dir_fd=parent_fd, follow_symlinks=False)
                if not self._debt_identity_matches(named, debt):
                    continue
                os.fsync(descriptor)
                if not self._debt_identity_matches(os.fstat(descriptor), debt):
                    continue
                for directory in debt.durability_directories:
                    self._fsync_directory(directory)
                named_after = os.stat(candidate.name, dir_fd=parent_fd, follow_symlinks=False)
                absolute_after = os.stat(candidate, follow_symlinks=False)
                if not self._debt_identity_matches(named_after, debt):
                    continue
                if not self._debt_identity_matches(absolute_after, debt):
                    continue
                return candidate
            except (OSError, UnsafeObservationPath):
                continue
            finally:
                if descriptor is not None:
                    try:
                        os.close(descriptor)
                    except OSError:
                        pass
                if parent_fd is not None:
                    try:
                        os.close(parent_fd)
                    except OSError:
                        pass
        return None

    def _debt_candidate_is_confined(
        self,
        debt: _CriticalSegmentDebt,
        candidate: Path,
    ) -> bool:
        if candidate not in {debt.active_path, debt.closed_path}:
            return False
        if candidate.parent not in {self.paths.active, self.paths.closed}:
            return False
        reference = parse_segment_name(candidate)
        if reference is None:
            return False
        active_reference = parse_segment_name(debt.active_path)
        if active_reference is None or not active_reference.is_active:
            return False
        if (
            reference.producer_epoch != active_reference.producer_epoch
            or reference.first_seq != active_reference.first_seq
        ):
            return False
        if candidate == debt.active_path:
            return reference.is_active
        closed_reference = parse_segment_name(debt.closed_path) if debt.closed_path else None
        return closed_reference is not None and reference == closed_reference

    @staticmethod
    def _debt_identity_matches(
        observed: os.stat_result,
        debt: _CriticalSegmentDebt,
    ) -> bool:
        return (
            stat.S_ISREG(observed.st_mode)
            and observed.st_nlink == 1
            and observed.st_dev == debt.expected_dev
            and observed.st_ino == debt.expected_ino
            and observed.st_size == debt.expected_size
        )

    @staticmethod
    def _same_private_file(observed: os.stat_result, expected: os.stat_result) -> bool:
        return (
            stat.S_ISREG(observed.st_mode)
            and observed.st_nlink == 1
            and observed.st_dev == expected.st_dev
            and observed.st_ino == expected.st_ino
            and observed.st_size == expected.st_size
        )

    @staticmethod
    def _fsync_directory(directory: Path) -> None:
        if os.name != "posix":
            return
        descriptor = _open_private_directory(directory)
        try:
            opened = os.fstat(descriptor)
            if not stat.S_ISDIR(opened.st_mode):
                raise UnsafeObservationPath("journal durability parent is not a real directory")
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def __enter__(self) -> "JournalWriter":
        self.open()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()
