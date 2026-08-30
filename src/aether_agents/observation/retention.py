"""Deterministic closed-segment compaction and retention policy.

Normative sources: OBS-D-029 (read literally, in full), OBS-FR-080, OBS-FR-084,
``specs/002-aether-contract-observation/spec.md`` section 12.

Only **closed** segments compact. Active, corrupt, unknown-schema, unverified, or
interrupted-temporary segments keep their source JSONL. There is no automatic
time-based pruning and no path that deletes a source event to reclaim space
(OBS-FR-080): reduction/compaction is side-effect-free with respect to source
segments except for this one, fully-verified, lossless representation change.

Exact transition order (OBS-D-029): write and verify a temporary archive plus a
temporary manifest, fsync both, atomically rename both, fsync the directory,
replay-check that decompressing the *final* renamed archive reproduces the exact
uncompressed bytes and the identical parsed event list, and only then remove the
original closed JSONL and fsync again. Source deletion never precedes
verification, and every interrupted stage is recoverable on the next run via
:func:`recover_interrupted`.
"""

from __future__ import annotations

import gzip
import io
import json
import os
import secrets
import stat
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from aether_agents.observation.capture.journal import (
    SegmentRead,
    SegmentRef,
    iter_segment_lines,
    read_private_bytes,
)
from aether_agents.observation.contracts import (
    MANIFEST_SCHEMA_VERSION,
    canonical_json_bytes,
    sha256_hex,
    validate_event,
    validate_manifest,
)
from aether_agents.observation.identity import segment_id as _segment_id
from aether_agents.observation.locking import project_lock
from aether_agents.observation.privacy import assert_clean
from aether_agents.paths import (
    ObservationPaths,
    UnsafeObservationPath,
    _open_private_directory,
    ensure_private_dir,
)

__all__ = [
    "ArchiveResult",
    "RecoveryReport",
    "RetentionError",
    "SegmentNotEligible",
    "VerificationFailed",
    "VerifyResult",
    "compact_segment",
    "gzip_header_fields",
    "iter_archive_events",
    "recover_interrupted",
    "verify_archive",
]


class RetentionError(Exception):
    """Base class for compaction/retention failures.

    Messages describe the failing stage only; they never quote event content
    (privacy invariant 1) and never quote a path outside the project's own
    observation directories.
    """


class SegmentNotEligible(RetentionError):
    """Raised when a segment is not eligible for compaction (OBS-D-029/section 12)."""


class VerificationFailed(RetentionError):
    """Raised when a deterministic/lossless invariant cannot be proven."""


@dataclass(frozen=True, slots=True)
class ArchiveResult:
    """The successful outcome of :func:`compact_segment`."""

    manifest_path: Path
    archive_path: Path
    manifest: dict[str, Any]


@dataclass(frozen=True, slots=True)
class VerifyResult:
    """Structured result of :func:`verify_archive`."""

    ok: bool
    errors: tuple[str, ...]
    manifest: dict[str, Any] | None


@dataclass(frozen=True, slots=True)
class RecoveryReport:
    """What :func:`recover_interrupted` found and fixed. Counts only, no content."""

    removed_temp_files: int
    removed_orphan_files: int
    completed_deletions: int
    left_for_manual_review: tuple[str, ...]


# --------------------------------------------------------------------------------------
# Deterministic gzip (OBS-D-029): one standard-library member, level 9, mtime=0, no
# filename, no comment, OS byte 255.
# --------------------------------------------------------------------------------------


def _deterministic_gzip(data: bytes) -> bytes:
    """Compress ``data`` with the exact deterministic parameters OBS-D-029 requires.

    CPython's ``gzip.GzipFile`` always writes OS byte 255 unconditionally (verified
    against the installed stdlib source; see the module test) and never writes a
    comment field. Passing ``filename=""`` suppresses the optional FNAME field so no
    filename is embedded. Byte 9 is defensively re-checked/normalised afterwards
    rather than trusting that behaviour blindly, in case a future or alternate
    runtime differs.
    """
    buffer = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buffer, mtime=0, compresslevel=9) as handle:
        handle.write(data)
    compressed = bytearray(buffer.getvalue())
    if len(compressed) > 9:
        compressed[9] = 255
    return bytes(compressed)


def gzip_header_fields(data: bytes) -> dict[str, int]:
    """Parse the fixed 10-byte gzip header. Raises :class:`VerificationFailed` if malformed."""
    if len(data) < 10 or data[0:2] != b"\x1f\x8b":
        raise VerificationFailed("not a gzip stream")
    return {
        "compression_method": data[2],
        "flags": data[3],
        "mtime": int.from_bytes(data[4:8], "little"),
        "extra_flags": data[8],
        "os_byte": data[9],
    }


@dataclass(eq=False, slots=True)
class _BoundDirectory:
    """A retained directory inode used for every destructive retention boundary."""

    path: Path
    descriptor: int | None
    identity: tuple[int, int]

    @classmethod
    def open(cls, path: Path) -> _BoundDirectory:
        path = Path(path)
        if os.name != "posix":  # pragma: no cover - exercised by platform CI
            if path.is_symlink() or not path.is_dir():
                raise UnsafeObservationPath("retention directory is not a real directory")
            info = path.stat()
            return cls(path=path, descriptor=None, identity=(info.st_dev, info.st_ino))
        descriptor = _open_private_directory(path)
        info = os.fstat(descriptor)
        return cls(path=path, descriptor=descriptor, identity=(info.st_dev, info.st_ino))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, _BoundDirectory):
            return self.identity == other.identity and self.path == other.path
        if isinstance(other, Path):
            return self.path == other
        return False

    def close(self) -> None:
        if self.descriptor is not None:
            os.close(self.descriptor)
            self.descriptor = None

    def assert_current(self) -> None:
        """Prove that the retained inode is still named by the canonical path."""
        if os.name != "posix":  # pragma: no cover - exercised by platform CI
            if self.path.is_symlink() or not self.path.is_dir():
                raise UnsafeObservationPath("retention directory changed during operation")
            info = self.path.stat()
            if (info.st_dev, info.st_ino) != self.identity:
                raise UnsafeObservationPath("retention directory changed during operation")
            return
        if self.descriptor is None:
            raise UnsafeObservationPath("retention directory descriptor is closed")
        verification = _open_private_directory(self.path)
        try:
            current = os.fstat(verification)
            retained = os.fstat(self.descriptor)
            if (current.st_dev, current.st_ino) != self.identity or (
                retained.st_dev,
                retained.st_ino,
            ) != self.identity:
                raise UnsafeObservationPath("retention directory changed during operation")
        finally:
            os.close(verification)


def _safe_entry_name(name: str) -> str:
    if not isinstance(name, str) or name in {"", ".", ".."} or Path(name).name != name:
        raise UnsafeObservationPath("retention entry name is outside its directory")
    return name


def _entry_info(directory: _BoundDirectory, name: str) -> os.stat_result:
    name = _safe_entry_name(name)
    if directory.descriptor is None:  # pragma: no cover - exercised by platform CI
        return os.stat(directory.path / name, follow_symlinks=False)
    return os.stat(name, dir_fd=directory.descriptor, follow_symlinks=False)


def _private_file_identity(directory: _BoundDirectory, name: str) -> tuple[int, int]:
    info = _entry_info(directory, name)
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise UnsafeObservationPath("retention entry is not a singly-linked regular file")
    directory.assert_current()
    return info.st_dev, info.st_ino


def _entry_exists(directory: _BoundDirectory, name: str) -> bool:
    try:
        _entry_info(directory, name)
    except FileNotFoundError:
        directory.assert_current()
        return False
    directory.assert_current()
    return True


def _read_bound_bytes(directory: _BoundDirectory, name: str) -> tuple[bytes, tuple[int, int]]:
    name = _safe_entry_name(name)
    if directory.descriptor is None:  # pragma: no cover - exercised by platform CI
        data = read_private_bytes(directory.path / name)
        identity = _private_file_identity(directory, name)
        directory.assert_current()
        return data, identity
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    try:
        descriptor = os.open(name, flags, dir_fd=directory.descriptor)
    except OSError as exc:
        try:
            named = _entry_info(directory, name)
        except OSError:
            raise exc
        if stat.S_ISLNK(named.st_mode) or not stat.S_ISREG(named.st_mode):
            raise UnsafeObservationPath(
                "retention entry is a symlink or non-regular file"
            ) from None
        raise
    try:
        opened = os.fstat(descriptor)
        named = _entry_info(directory, name)
        identity = (opened.st_dev, opened.st_ino)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_nlink != 1
            or not stat.S_ISREG(named.st_mode)
            or named.st_nlink != 1
            or (named.st_dev, named.st_ino) != identity
        ):
            raise UnsafeObservationPath("retention entry changed while opening")
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 65536):
            chunks.append(chunk)
        after = os.fstat(descriptor)
        named_after = _entry_info(directory, name)
        if (
            not stat.S_ISREG(after.st_mode)
            or after.st_nlink != 1
            or (after.st_dev, after.st_ino) != identity
            or (named_after.st_dev, named_after.st_ino) != identity
            or named_after.st_nlink != 1
        ):
            raise UnsafeObservationPath("retention entry changed while reading")
        directory.assert_current()
        return b"".join(chunks), identity
    finally:
        os.close(descriptor)


def _list_bound_entries(directory: _BoundDirectory) -> dict[str, os.stat_result]:
    if directory.descriptor is None:  # pragma: no cover - exercised by platform CI
        names = os.listdir(directory.path)
    else:
        names = os.listdir(directory.descriptor)
    entries: dict[str, os.stat_result] = {}
    for name in names:
        try:
            entries[_safe_entry_name(name)] = _entry_info(directory, name)
        except FileNotFoundError:
            continue
    directory.assert_current()
    return entries


def _fsync_directory(directory: Path | _BoundDirectory) -> None:
    if os.name != "posix":
        return
    owned = not isinstance(directory, _BoundDirectory)
    bound = _BoundDirectory.open(directory) if owned else directory
    try:
        bound.assert_current()
        if bound.descriptor is None:  # pragma: no cover - POSIX descriptor is always present
            raise UnsafeObservationPath("retention directory descriptor is unavailable")
        os.fsync(bound.descriptor)
        bound.assert_current()
    finally:
        if owned:
            bound.close()


def _write_bytes_durable(directory: _BoundDirectory, name: str, data: bytes) -> tuple[int, int]:
    name = _safe_entry_name(name)
    if directory.descriptor is None:  # pragma: no cover - exercised by platform CI
        path = directory.path / name
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    else:
        descriptor = os.open(
            name,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_CLOEXEC", 0),
            0o600,
            dir_fd=directory.descriptor,
        )
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
            raise UnsafeObservationPath("retention temporary is not a private regular file")
        identity = opened.st_dev, opened.st_ino
        os.fchmod(descriptor, 0o600)
        written = 0
        view = memoryview(data)
        while written < len(data):
            count = os.write(descriptor, view[written:])
            if count <= 0:
                raise OSError("durable write made no progress")
            written += count
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    if _private_file_identity(directory, name) != identity:
        raise UnsafeObservationPath("retention temporary changed after durable write")
    directory.assert_current()
    return identity


def _replace_bound(
    directory: _BoundDirectory,
    source_name: str,
    target_name: str,
    expected_identity: tuple[int, int],
) -> None:
    source_name = _safe_entry_name(source_name)
    target_name = _safe_entry_name(target_name)
    if _private_file_identity(directory, source_name) != expected_identity:
        raise UnsafeObservationPath("retention temporary changed before replace")
    directory.assert_current()
    if directory.descriptor is None:  # pragma: no cover - exercised by platform CI
        os.replace(directory.path / source_name, directory.path / target_name)
    else:
        os.replace(
            source_name,
            target_name,
            src_dir_fd=directory.descriptor,
            dst_dir_fd=directory.descriptor,
        )
    if _private_file_identity(directory, target_name) != expected_identity:
        raise UnsafeObservationPath("retention target changed during replace")
    directory.assert_current()


def _unlink_bound(
    directory: _BoundDirectory,
    name: str,
    expected_identity: tuple[int, int],
) -> None:
    name = _safe_entry_name(name)
    if _private_file_identity(directory, name) != expected_identity:
        raise UnsafeObservationPath("retention entry changed before unlink")
    directory.assert_current()
    if directory.descriptor is None:  # pragma: no cover - exercised by platform CI
        os.unlink(directory.path / name)
    else:
        os.unlink(name, dir_fd=directory.descriptor)


def _restore_source(directory: _BoundDirectory, name: str, data: bytes) -> None:
    """Restore exact source bytes after an uncertain durable-unlink boundary."""
    if _entry_exists(directory, name):
        existing, _identity = _read_bound_bytes(directory, name)
        if existing != data:
            raise VerificationFailed("source changed during durable cleanup")
        return
    temporary_name = f".{name}.restore-{secrets.token_hex(8)}.tmp"
    identity: tuple[int, int] | None = None
    try:
        identity = _write_bytes_durable(directory, temporary_name, data)
        _replace_bound(directory, temporary_name, name, identity)
        identity = None
        _fsync_directory(directory)
    finally:
        if identity is not None:
            try:
                _unlink_bound(directory, temporary_name, identity)
            except (FileNotFoundError, UnsafeObservationPath):
                pass


def _remove_source_durable(directory: _BoundDirectory, name: str, data: bytes) -> None:
    """Remove a verified source, restoring it if the directory barrier fails.

    POSIX cannot make unlink plus directory fsync transactional.  Keeping the
    already-verified bytes in memory lets a reported failure restore the canonical
    JSONL name before control returns.  A failure of the restoration barrier is
    attached to the original exception without copying path or event content; the
    restored file remains visible for retry/recovery.
    """
    on_disk, identity = _read_bound_bytes(directory, name)
    if on_disk != data:
        raise VerificationFailed("source changed before durable cleanup")
    try:
        _unlink_bound(directory, name, identity)
        _fsync_directory(directory)
    except Exception as removal_error:
        if not _entry_exists(directory, name):
            try:
                _restore_source(directory, name, data)
            except Exception as restoration_error:
                removal_error.add_note(
                    "source restoration durability also failed "
                    f"({type(restoration_error).__name__})"
                )
        raise


def _build_manifest(
    *,
    project_id: str,
    producer_epoch: str,
    first_seq: int,
    last_seq: int,
    event_count: int,
    line_count: int,
    source_name: str,
    archive_name: str,
    uncompressed_length: int,
    uncompressed_sha256: str,
    compressed_length: int,
    compressed_sha256: str,
    event_schema_versions: set[str],
    collector_versions: set[str],
    runtime_fingerprints: set[str],
) -> dict[str, Any]:
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "segment_id": _segment_id(uncompressed_sha256),
        "project_id": project_id,
        "producer_epoch": producer_epoch,
        "first_seq": first_seq,
        "last_seq": last_seq,
        "event_count": event_count,
        "line_count": line_count,
        "source_name": source_name,
        "archive_name": archive_name,
        "uncompressed_length": uncompressed_length,
        "uncompressed_sha256": uncompressed_sha256,
        "compressed_length": compressed_length,
        "compressed_sha256": compressed_sha256,
        "event_schema_versions": sorted(event_schema_versions),
        "collector_versions": sorted(collector_versions),
        "runtime_fingerprints": sorted(runtime_fingerprints),
        "compression": {
            "algorithm": "gzip",
            "level": 9,
            "mtime": 0,
            "header_filename": None,
            "header_comment": None,
            "os_byte": 255,
        },
    }


def _validate_manifest_invariants(manifest: dict[str, Any]) -> None:
    """OBS-D-029's extra reducer-side checks beyond plain schema validity."""
    validate_manifest(manifest)
    if manifest["first_seq"] > manifest["last_seq"]:
        raise VerificationFailed("first_seq exceeds last_seq")
    if manifest["event_count"] != manifest["line_count"]:
        raise VerificationFailed("event_count does not equal line_count")
    if manifest["segment_id"] != _segment_id(manifest["uncompressed_sha256"]):
        raise VerificationFailed("segment_id does not match the uncompressed digest")
    expected_source = (
        f"{manifest['producer_epoch']}.{manifest['first_seq']}-{manifest['last_seq']}.jsonl"
    )
    if manifest["source_name"] != expected_source:
        raise VerificationFailed("source name does not match the recorded sequence range")
    if manifest["archive_name"] != expected_source + ".gz":
        raise VerificationFailed("archive name does not match the source name")


# --------------------------------------------------------------------------------------
# Compaction
# --------------------------------------------------------------------------------------


def compact_segment(paths: ObservationPaths, segment: SegmentRef) -> ArchiveResult:
    """Serialize compaction with ingestion and interrupted-transition recovery."""
    paths.ensure()
    with project_lock(paths, "storage-transition"):
        archive_directory = _BoundDirectory.open(paths.archive)
        closed_directory = _BoundDirectory.open(paths.closed)
        try:
            return _compact_segment_locked(
                paths,
                segment,
                archive_directory=archive_directory,
                closed_directory=closed_directory,
            )
        finally:
            closed_directory.close()
            archive_directory.close()


def _compact_segment_locked(
    paths: ObservationPaths,
    segment: SegmentRef,
    *,
    archive_directory: _BoundDirectory,
    closed_directory: _BoundDirectory,
) -> ArchiveResult:
    """Compact one closed segment into a verified, lossless ``.jsonl.gz`` archive.

    Raises :class:`SegmentNotEligible` when ``segment`` is not a closed, complete,
    non-empty segment, and :class:`VerificationFailed` if any deterministic/lossless
    invariant cannot be proven. In both cases the source JSONL is left untouched.
    """
    if segment.state != "closed" or segment.last_seq is None:
        raise SegmentNotEligible("only closed segments may be compacted")
    if segment.path.parent != paths.closed:
        raise UnsafeObservationPath("closed segment is outside the project journal")

    source_name = segment.path.name
    archive_name = source_name + ".gz"
    manifest_name = archive_name + ".manifest.json"
    ensure_private_dir(paths.archive)
    archive_path = paths.archive / archive_name
    manifest_path = paths.archive / manifest_name

    # A caller may retain the original closed SegmentRef across a successful
    # compaction.  Recognize the already-durable final pair before touching the now
    # absent source, and re-prove its directory boundary on every idempotent retry.
    if not _entry_exists(closed_directory, source_name):
        if _entry_exists(archive_directory, archive_name) and _entry_exists(
            archive_directory, manifest_name
        ):
            existing = _verify_archive_bound(archive_directory, manifest_name)
            manifest = existing.manifest
            if (
                existing.ok
                and manifest is not None
                and manifest.get("project_id") == paths.project_id
                and manifest.get("producer_epoch") == segment.producer_epoch
                and manifest.get("first_seq") == segment.first_seq
                and manifest.get("last_seq") == segment.last_seq
                and manifest.get("source_name") == source_name
            ):
                _fsync_directory(archive_directory)
                return ArchiveResult(
                    manifest_path=manifest_path,
                    archive_path=archive_path,
                    manifest=manifest,
                )
        if _entry_exists(archive_directory, archive_name) or _entry_exists(
            archive_directory, manifest_name
        ):
            raise VerificationFailed("an existing final archive pair is incomplete or mismatched")
        raise SegmentNotEligible("closed segment source is no longer present")

    data, _source_identity = _read_bound_bytes(closed_directory, source_name)
    if not data or not data.endswith(b"\n"):
        raise SegmentNotEligible("segment is empty or has an unterminated tail")
    lines = data.split(b"\n")
    trailing = lines.pop()
    if trailing != b"" or not lines:
        raise SegmentNotEligible("segment is empty or has an unterminated tail")

    schema_versions: set[str] = set()
    collector_versions: set[str] = set()
    runtime_fingerprints: set[str] = set()
    expected_sequences = range(segment.first_seq, segment.first_seq + len(lines))
    for line, expected_seq in zip(lines, expected_sequences):
        try:
            record = json.loads(line.decode("utf-8"))
            validate_event(record)
            assert_clean(record)
            if record.get("project_id") != paths.project_id:
                raise ValueError("cross-project event")
            if record.get("producer_epoch") != segment.producer_epoch:
                raise ValueError("producer epoch mismatch")
            if record.get("producer_seq") != expected_seq:
                raise ValueError("producer sequence mismatch")
            schema_versions.add(record["schema_version"])
            collector_versions.add(record["collector_version"])
            runtime_fingerprints.add(record["runtime_fingerprint"])
        except Exception as error:
            raise SegmentNotEligible(
                f"segment contains an unparseable or unknown-schema line ({type(error).__name__})"
            ) from error

    if segment.last_seq != segment.first_seq + len(lines) - 1:
        raise SegmentNotEligible("segment filename sequence range does not match its events")

    uncompressed_sha256 = sha256_hex(data)
    compressed = _deterministic_gzip(data)
    header = gzip_header_fields(compressed)
    if header["mtime"] != 0 or header["os_byte"] != 255:
        raise VerificationFailed("deterministic gzip header invariant violated")
    compressed_sha256 = sha256_hex(compressed)

    manifest = _build_manifest(
        project_id=paths.project_id,
        producer_epoch=segment.producer_epoch,
        first_seq=segment.first_seq,
        last_seq=segment.last_seq,
        event_count=len(lines),
        line_count=len(lines),
        source_name=source_name,
        archive_name=archive_name,
        uncompressed_length=len(data),
        uncompressed_sha256=uncompressed_sha256,
        compressed_length=len(compressed),
        compressed_sha256=compressed_sha256,
        event_schema_versions=schema_versions,
        collector_versions=collector_versions,
        runtime_fingerprints=runtime_fingerprints,
    )
    _validate_manifest_invariants(manifest)

    if _entry_exists(archive_directory, archive_name) or _entry_exists(
        archive_directory, manifest_name
    ):
        if _entry_exists(archive_directory, archive_name) and _entry_exists(
            archive_directory, manifest_name
        ):
            existing = _verify_archive_bound(archive_directory, manifest_name)
            if (
                existing.ok
                and existing.manifest is not None
                and existing.manifest.get("uncompressed_sha256") == uncompressed_sha256
            ):
                # A previous process may have returned immediately after final rename
                # because the archive-directory fsync failed. Re-prove that boundary
                # before allowing its source to be removed on retry.
                _fsync_directory(archive_directory)
                _remove_source_durable(closed_directory, source_name, data)
                return ArchiveResult(
                    manifest_path=manifest_path,
                    archive_path=archive_path,
                    manifest=existing.manifest,
                )
        raise VerificationFailed("an existing final archive pair is incomplete or mismatched")
    temp_suffix = secrets.token_hex(8)
    # The temporary archive name must still end in ".gz" so the shared gzip-aware
    # reader (`_open_maybe_gzip`) recognises it as compressed during verification.
    temp_archive_name = f"{source_name}.tmp-{temp_suffix}.gz"
    temp_manifest_name = f"{manifest_name}.tmp-{temp_suffix}"

    temp_archive_identity = _write_bytes_durable(archive_directory, temp_archive_name, compressed)
    manifest_bytes = canonical_json_bytes(manifest)
    temp_manifest_identity = _write_bytes_durable(
        archive_directory, temp_manifest_name, manifest_bytes
    )

    # First verification: the temporaries, still at their ".tmp-" names.
    _verify_temp_pair(
        archive_directory,
        temp_archive_name,
        temp_manifest_name,
        expected_data=data,
        manifest=manifest,
    )

    _replace_bound(
        archive_directory,
        temp_archive_name,
        archive_name,
        temp_archive_identity,
    )
    _replace_bound(
        archive_directory,
        temp_manifest_name,
        manifest_name,
        temp_manifest_identity,
    )
    _fsync_directory(archive_directory)

    # Second, independent verification: read back from the FINAL renamed location
    # before the only pristine source is ever removed.
    result = _verify_archive_bound(archive_directory, manifest_name)
    if not result.ok:
        raise VerificationFailed("post-rename replay-check failed: " + "; ".join(result.errors))

    # Complete every archive/manifest boundary while the pristine JSONL still
    # exists.  In particular, no later archive fsync may fail after source unlink.
    _fsync_directory(archive_directory)
    _remove_source_durable(closed_directory, source_name, data)

    archive_directory.assert_current()
    closed_directory.assert_current()

    return ArchiveResult(manifest_path=manifest_path, archive_path=archive_path, manifest=manifest)


def _verify_temp_pair(
    directory: _BoundDirectory,
    temp_archive_name: str,
    temp_manifest_name: str,
    *,
    expected_data: bytes,
    manifest: dict[str, Any],
) -> None:
    manifest_bytes, _manifest_identity = _read_bound_bytes(directory, temp_manifest_name)
    manifest_on_disk = json.loads(manifest_bytes.decode("utf-8"))
    validate_manifest(manifest_on_disk)
    if manifest_on_disk != manifest:
        raise VerificationFailed("temporary manifest content mismatch")

    compressed, _archive_identity = _read_bound_bytes(directory, temp_archive_name)
    read = _read_gzip_segment(compressed)
    if read.trailing_fragment != b"":
        raise VerificationFailed("temporary archive did not decompress cleanly")
    if (
        read.uncompressed_sha256 != manifest["uncompressed_sha256"]
        or read.byte_length != manifest["uncompressed_length"]
    ):
        raise VerificationFailed("temporary archive does not reproduce the original bytes")
    original_lines = expected_data.split(b"\n")[:-1]
    if read.lines != original_lines:
        raise VerificationFailed("temporary archive parsed event list differs from the source")


def _read_gzip_segment(compressed: bytes) -> SegmentRead:
    data = gzip.decompress(compressed)
    lines: list[bytes] = []
    fragment = b""
    if data:
        parts = data.split(b"\n")
        fragment = parts.pop()
        lines = parts
    return SegmentRead(
        lines=lines,
        trailing_fragment=fragment,
        uncompressed_sha256=sha256_hex(data),
        byte_length=len(data),
    )


def verify_archive(manifest_path: Path) -> VerifyResult:
    """Independently verify one archive/manifest pair already at their final names."""
    try:
        directory = _BoundDirectory.open(manifest_path.parent)
    except (OSError, UnsafeObservationPath):
        return VerifyResult(ok=False, errors=("cannot read manifest",), manifest=None)
    try:
        return _verify_archive_bound(directory, manifest_path.name)
    finally:
        directory.close()


def _verify_archive_bound(directory: _BoundDirectory, manifest_name: str) -> VerifyResult:
    """Verify a final pair through one retained archive-directory inode."""
    errors: list[str] = []
    try:
        manifest_bytes, _manifest_identity = _read_bound_bytes(directory, manifest_name)
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (OSError, UnsafeObservationPath):
        return VerifyResult(ok=False, errors=("cannot read manifest",), manifest=None)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return VerifyResult(ok=False, errors=("manifest is not valid JSON",), manifest=None)

    try:
        _validate_manifest_invariants(manifest)
    except Exception as error:  # jsonschema.ValidationError or VerificationFailed
        errors.append(f"manifest invariant violated: {type(error).__name__}")
        return VerifyResult(ok=False, errors=tuple(errors), manifest=manifest)

    archive_name = manifest["archive_name"]
    if manifest_name != archive_name + ".manifest.json":
        return VerifyResult(
            ok=False,
            errors=("manifest filename does not match archive_name",),
            manifest=manifest,
        )
    if not _entry_exists(directory, archive_name):
        return VerifyResult(ok=False, errors=("archive file is missing",), manifest=manifest)

    try:
        on_disk, _archive_identity = _read_bound_bytes(directory, archive_name)
    except (OSError, UnsafeObservationPath):
        return VerifyResult(ok=False, errors=("cannot read archive",), manifest=manifest)
    if (
        len(on_disk) != manifest["compressed_length"]
        or sha256_hex(on_disk) != manifest["compressed_sha256"]
    ):
        errors.append("compressed bytes do not match the manifest")

    try:
        header = gzip_header_fields(on_disk)
    except VerificationFailed:
        errors.append("gzip header is malformed")
        return VerifyResult(ok=False, errors=tuple(errors), manifest=manifest)
    if (
        header["compression_method"] != 8
        or header["flags"] != 0
        or header["extra_flags"] != 2
        or header["mtime"] != manifest["compression"]["mtime"]
        or header["os_byte"] != manifest["compression"]["os_byte"]
    ):
        errors.append("gzip header does not match the recorded compression parameters")

    try:
        read = _read_gzip_segment(on_disk)
    except (OSError, EOFError, gzip.BadGzipFile, zlib.error):
        errors.append("archive cannot be decompressed")
        return VerifyResult(ok=False, errors=tuple(errors), manifest=manifest)
    if read.trailing_fragment != b"":
        errors.append("archive did not decompress to a clean LF-terminated stream")
    if (
        read.uncompressed_sha256 != manifest["uncompressed_sha256"]
        or read.byte_length != manifest["uncompressed_length"]
    ):
        errors.append("decompressed bytes do not match the manifest")
    if len(read.lines) != manifest["line_count"]:
        errors.append("decompressed line count does not match the manifest")

    schema_versions: set[str] = set()
    collector_versions: set[str] = set()
    runtime_fingerprints: set[str] = set()
    for index, line in enumerate(read.lines):
        try:
            event = json.loads(line.decode("utf-8"))
            validate_event(event)
            assert_clean(event)
            if event.get("project_id") != manifest["project_id"]:
                raise ValueError("project mismatch")
            if event.get("producer_epoch") != manifest["producer_epoch"]:
                raise ValueError("epoch mismatch")
            if event.get("producer_seq") != manifest["first_seq"] + index:
                raise ValueError("sequence mismatch")
            schema_versions.add(event["schema_version"])
            collector_versions.add(event["collector_version"])
            runtime_fingerprints.add(event["runtime_fingerprint"])
        except Exception:
            errors.append("decompressed event list failed schema or sequence validation")
            break
    if len(read.lines) != manifest["event_count"]:
        errors.append("decompressed event count does not match the manifest")
    if sorted(schema_versions) != manifest["event_schema_versions"]:
        errors.append("event schema versions do not match the manifest")
    if sorted(collector_versions) != manifest["collector_versions"]:
        errors.append("collector versions do not match the manifest")
    if sorted(runtime_fingerprints) != manifest["runtime_fingerprints"]:
        errors.append("runtime fingerprints do not match the manifest")

    return VerifyResult(ok=not errors, errors=tuple(errors), manifest=manifest)


def iter_archive_events(archive_path: Path) -> Iterator[dict[str, Any]]:
    """Yield each parsed event from a closed-segment archive, for ingestion."""
    for _offset, line in iter_segment_lines(archive_path):
        yield json.loads(line.decode("utf-8"))


# --------------------------------------------------------------------------------------
# Crash recovery
# --------------------------------------------------------------------------------------


def recover_interrupted(paths: ObservationPaths) -> RecoveryReport:
    """Serialize recovery with ingestion and compaction for this project."""
    paths.ensure()
    with project_lock(paths, "storage-transition"):
        archive_directory = _BoundDirectory.open(paths.archive)
        closed_directory = _BoundDirectory.open(paths.closed)
        try:
            return _recover_interrupted_locked(
                paths,
                archive_directory=archive_directory,
                closed_directory=closed_directory,
            )
        finally:
            closed_directory.close()
            archive_directory.close()


def _recover_interrupted_locked(
    paths: ObservationPaths,
    *,
    archive_directory: _BoundDirectory,
    closed_directory: _BoundDirectory,
) -> RecoveryReport:
    """Clean up any compaction left interrupted by a prior crash.

    The caller holds the common project storage-transition lock shared with
    ingestion and compaction; it is not a substitute for the epoch lock the
    journal writer holds. Every action here is safe precisely because a source
    JSONL is only ever removed *after* an independent, successful replay-check of
    its final archive.
    """
    removed_temp = 0
    removed_orphans = 0
    completed_deletions = 0
    manual: list[str] = []

    def report() -> RecoveryReport:
        return RecoveryReport(
            removed_temp_files=removed_temp,
            removed_orphan_files=removed_orphans,
            completed_deletions=completed_deletions,
            left_for_manual_review=tuple(sorted(set(manual))),
        )

    def directory_is_current(directory: _BoundDirectory, label: str) -> bool:
        try:
            directory.assert_current()
        except (OSError, UnsafeObservationPath):
            manual.append(label)
            return False
        return True

    def entry_identity(name: str, info: os.stat_result) -> tuple[int, int]:
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise UnsafeObservationPath("recovery entry is not a private regular file")
        return info.st_dev, info.st_ino

    # Stage 1: bare leftover temporaries never reached a final name. The source
    # JSONL was never touched while these existed, so deleting them is always safe.
    try:
        entries = _list_bound_entries(archive_directory)
    except (OSError, UnsafeObservationPath):
        manual.append("archive-directory")
        return report()
    for name, info in entries.items():
        if ".tmp-" in name:
            try:
                identity = entry_identity(name, info)
                _unlink_bound(archive_directory, name, identity)
                _fsync_directory(archive_directory)
                removed_temp += 1
            except (OSError, UnsafeObservationPath):
                manual.append(name)
                if not directory_is_current(archive_directory, name):
                    return report()

    # Stage 2: a final archive without its sibling manifest, or vice versa. Neither
    # half alone is verifiable compaction evidence, and the source JSONL is still
    # intact in `closed/` at this point, so the orphan is simply discarded; the
    # segment is recompacted (idempotently) on a later pass.
    try:
        entries = _list_bound_entries(archive_directory)
    except (OSError, UnsafeObservationPath):
        manual.append("archive-directory")
        return report()
    archives = {name for name in entries if name.endswith(".jsonl.gz")}
    manifests = {name for name in entries if name.endswith(".jsonl.gz.manifest.json")}
    for archive_name in sorted(archives):
        if archive_name + ".manifest.json" not in manifests:
            source_name = archive_name[: -len(".gz")]
            try:
                _private_file_identity(closed_directory, source_name)
            except (OSError, UnsafeObservationPath):
                manual.append(archive_name)
                continue
            try:
                identity = entry_identity(archive_name, entries[archive_name])
                _unlink_bound(archive_directory, archive_name, identity)
                _fsync_directory(archive_directory)
                removed_orphans += 1
            except (OSError, UnsafeObservationPath):
                manual.append(archive_name)
                if not directory_is_current(archive_directory, archive_name):
                    return report()
    for manifest_name in sorted(manifests):
        archive_name = manifest_name[: -len(".manifest.json")]
        if archive_name not in archives:
            try:
                manifest_bytes, _manifest_identity = _read_bound_bytes(
                    archive_directory, manifest_name
                )
                payload = json.loads(manifest_bytes.decode("utf-8"))
                _validate_manifest_invariants(payload)
                if payload.get("project_id") != paths.project_id:
                    raise VerificationFailed("manifest project does not match recovery scope")
                source_name = payload["source_name"]
            except Exception:
                manual.append(manifest_name)
                continue
            try:
                _private_file_identity(closed_directory, source_name)
            except (OSError, UnsafeObservationPath):
                manual.append(manifest_name)
                continue
            try:
                identity = entry_identity(manifest_name, entries[manifest_name])
                _unlink_bound(archive_directory, manifest_name, identity)
                _fsync_directory(archive_directory)
                removed_orphans += 1
            except (OSError, UnsafeObservationPath):
                manual.append(manifest_name)
                if not directory_is_current(archive_directory, manifest_name):
                    return report()

    # Stage 3: a verified pair whose source JSONL deletion never completed. This is
    # already a fully safe, lossless state; only the pending source cleanup and its
    # directory fsync remain.
    try:
        entries = _list_bound_entries(archive_directory)
    except (OSError, UnsafeObservationPath):
        manual.append("archive-directory")
        return report()
    archives = {name for name in entries if name.endswith(".jsonl.gz")}
    manifests = {name for name in entries if name.endswith(".jsonl.gz.manifest.json")}
    for archive_name in sorted(archives):
        manifest_name = archive_name + ".manifest.json"
        if manifest_name not in manifests:
            continue
        if not directory_is_current(archive_directory, archive_name):
            return report()
        result = _verify_archive_bound(archive_directory, manifest_name)
        if not result.ok or result.manifest is None:
            manual.append(archive_name)
            continue
        if result.manifest.get("project_id") != paths.project_id:
            manual.append(archive_name)
            continue
        source_name = result.manifest["source_name"]
        if _entry_exists(closed_directory, source_name):
            try:
                # The pair can be left at final names by a failed directory fsync.
                # Re-establish that durability boundary before source cleanup.
                _fsync_directory(archive_directory)
                source_data, _source_identity = _read_bound_bytes(closed_directory, source_name)
                if sha256_hex(source_data) != result.manifest["uncompressed_sha256"]:
                    raise VerificationFailed("source does not match verified archive")
                archive_directory.assert_current()
                _remove_source_durable(closed_directory, source_name, source_data)
                completed_deletions += 1
            except (OSError, VerificationFailed, UnsafeObservationPath):
                manual.append(archive_name)

    return report()
