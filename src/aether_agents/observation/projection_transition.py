"""Release-local projection transition runner.

The lifecycle manager executes this module with the *target release's* manager
interpreter.  Consequently :data:`READ_MODEL_SCHEMA` and all reducer code imported
here belong to that target; a caller-provided schema is only an equality assertion
and is never used to construct a path.

Requests and responses intentionally contain only state-root routing, canonical
project IDs, projection pointer identities, and aggregate counts.  Errors crossing
the subprocess boundary are a single bounded code with no exception text or path.
"""

from __future__ import annotations

import json
import os
import re
import stat
import sys
import uuid
from pathlib import Path
from typing import Any, BinaryIO, Mapping, Sequence

from aether_agents.observation.contracts import READ_MODEL_SCHEMA
from aether_agents.observation.locking import project_lock
from aether_agents.observation.reduce.ingest import ingest_pending
from aether_agents.observation.storage import publish_projection_pointer
from aether_agents.paths import (
    FILE_MODE,
    ObservationPaths,
    _open_private_directory,
    atomic_private_write,
)

__all__ = [
    "ProjectionTransitionError",
    "main",
    "run_transition",
]


_MAX_REQUEST_BYTES = 64 * 1024
_PROJECT_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.ASCII,
)
_POINTER_RE = re.compile(
    r"^aether\.observation\.projection\.v[1-9][0-9]*\.sqlite3$",
    re.ASCII,
)
_FAILURE_RESPONSE = b'{"error":"PROJECTION_TRANSITION_FAILED"}\n'
_COMMON_REQUEST_KEYS = frozenset({"operation", "state_root", "expected_schema"})


class ProjectionTransitionError(RuntimeError):
    """A bounded transition failure safe to translate across the process seam."""

    def __init__(self) -> None:
        super().__init__("projection transition failed")


class _PrivateFileMissing(FileNotFoundError):
    """The final name was absent under an already verified parent descriptor."""


def _fail() -> ProjectionTransitionError:
    return ProjectionTransitionError()


def _is_canonical_project_id(value: Any) -> bool:
    if not isinstance(value, str) or _PROJECT_UUID_RE.fullmatch(value) is None:
        return False
    try:
        return str(uuid.UUID(value)) == value
    except (AttributeError, ValueError):
        return False


def _is_pointer(value: Any) -> bool:
    return isinstance(value, str) and _POINTER_RE.fullmatch(value) is not None


def _validate_state_root(value: Any) -> Path:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise _fail()
    root = Path(value)
    if not root.is_absolute() or any(part == ".." for part in root.parts):
        raise _fail()
    descriptor: int | None = None
    try:
        descriptor = _open_private_directory(root)
    except (OSError, ValueError):
        raise _fail() from None
    finally:
        if descriptor is not None:
            os.close(descriptor)
    return root


def _open_child_directory(
    parent_descriptor: int,
    name: str,
    *,
    missing_ok: bool,
) -> int | None:
    """Open one fixed child without following it and bind name to opened inode."""

    flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    try:
        descriptor = os.open(name, flags, dir_fd=parent_descriptor)
    except FileNotFoundError:
        if missing_ok:
            return None
        raise _fail() from None
    except OSError:
        raise _fail() from None
    try:
        opened = os.fstat(descriptor)
        named = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
        if (
            not stat.S_ISDIR(opened.st_mode)
            or not stat.S_ISDIR(named.st_mode)
            or (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino)
        ):
            raise _fail()
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def _enumerate_project_ids(root: Path) -> tuple[str, ...]:
    """List only canonical UUID directories below the held observation root."""

    if os.name != "posix":  # pragma: no cover - supported release runners are POSIX
        projects = root / "observations" / "projects"
        if not projects.exists():
            return ()
        if projects.is_symlink() or not projects.is_dir():
            raise _fail()
        result: list[str] = []
        for candidate in projects.iterdir():
            if not _is_canonical_project_id(candidate.name):
                continue
            if candidate.is_symlink() or not candidate.is_dir():
                raise _fail()
            result.append(candidate.name)
        return tuple(sorted(result))

    root_descriptor: int | None = None
    observations_descriptor: int | None = None
    projects_descriptor: int | None = None
    try:
        root_descriptor = _open_private_directory(root)
        observations_descriptor = _open_child_directory(
            root_descriptor, "observations", missing_ok=True
        )
        if observations_descriptor is None:
            return ()
        projects_descriptor = _open_child_directory(
            observations_descriptor, "projects", missing_ok=True
        )
        if projects_descriptor is None:
            return ()
        project_ids: list[str] = []
        try:
            names = os.listdir(projects_descriptor)
        except OSError:
            raise _fail() from None
        for name in names:
            # Foreign names remain opaque: do not stat, open, or inspect them.
            if not _is_canonical_project_id(name):
                continue
            project_descriptor = _open_child_directory(projects_descriptor, name, missing_ok=False)
            assert project_descriptor is not None
            os.close(project_descriptor)
            project_ids.append(name)
        return tuple(sorted(project_ids))
    except ProjectionTransitionError:
        raise
    except (OSError, ValueError):
        raise _fail() from None
    finally:
        for descriptor in (
            projects_descriptor,
            observations_descriptor,
            root_descriptor,
        ):
            if descriptor is not None:
                os.close(descriptor)


def _assert_project_still_confined(root: Path, project_id: str) -> None:
    """Re-open the exact project path at each mutation boundary."""

    try:
        descriptor = _open_private_directory(root / "observations" / "projects" / project_id)
    except (OSError, ValueError):
        raise _fail() from None
    else:
        os.close(descriptor)


def _read_bounded_private_file(
    path: Path,
    *,
    max_bytes: int,
    require_private_mode: bool,
) -> bytes:
    """Read a stable, singly-linked regular file through a verified parent fd."""

    if not path.is_absolute() or path.name in ("", ".", ".."):
        raise _fail()
    parent_descriptor: int | None = None
    descriptor: int | None = None
    try:
        parent_descriptor = _open_private_directory(path.parent)
        flags = (
            os.O_RDONLY
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NONBLOCK", 0)
        )
        try:
            descriptor = os.open(path.name, flags, dir_fd=parent_descriptor)
        except FileNotFoundError:
            raise _PrivateFileMissing() from None
        opened = os.fstat(descriptor)
        named = os.stat(path.name, dir_fd=parent_descriptor, follow_symlinks=False)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_nlink != 1
            or not stat.S_ISREG(named.st_mode)
            or named.st_nlink != 1
            or (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino)
            or opened.st_size > max_bytes
        ):
            raise _fail()
        if os.name == "posix" and (
            opened.st_uid != os.getuid()
            or (require_private_mode and stat.S_IMODE(opened.st_mode) != FILE_MODE)
        ):
            raise _fail()
        remaining = opened.st_size
        chunks: list[bytes] = []
        while remaining:
            block = os.read(descriptor, min(remaining, 8192))
            if not block:
                raise _fail()
            chunks.append(block)
            remaining -= len(block)
        if os.read(descriptor, 1):
            raise _fail()
        after = os.fstat(descriptor)
        named_after = os.stat(path.name, dir_fd=parent_descriptor, follow_symlinks=False)
        if (
            (after.st_dev, after.st_ino) != (opened.st_dev, opened.st_ino)
            or after.st_size != opened.st_size
            or (named_after.st_dev, named_after.st_ino) != (opened.st_dev, opened.st_ino)
        ):
            raise _fail()
        return b"".join(chunks)
    except _PrivateFileMissing:
        raise
    except ProjectionTransitionError:
        raise
    except (OSError, ValueError):
        raise _fail() from None
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if parent_descriptor is not None:
            os.close(parent_descriptor)


def _read_pointer(paths: ObservationPaths) -> str | None:
    try:
        data = _read_bounded_private_file(
            paths.projection_pointer,
            max_bytes=128,
            require_private_mode=True,
        )
    except _PrivateFileMissing:
        return None
    try:
        value = data.decode("ascii")
    except UnicodeError:
        raise _fail() from None
    if not value.endswith("\n") or not _is_pointer(value[:-1]):
        raise _fail()
    return value[:-1]


def _own_projection_identity(paths: ObservationPaths) -> tuple[int, int]:
    """Prove the prepared target DB exists without opening any other schema."""

    target = paths.projection_db(READ_MODEL_SCHEMA)
    parent_descriptor: int | None = None
    descriptor: int | None = None
    try:
        parent_descriptor = _open_private_directory(target.parent)
        flags = (
            os.O_RDONLY
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NONBLOCK", 0)
        )
        descriptor = os.open(target.name, flags, dir_fd=parent_descriptor)
        opened = os.fstat(descriptor)
        named = os.stat(target.name, dir_fd=parent_descriptor, follow_symlinks=False)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_nlink != 1
            or (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino)
        ):
            raise _fail()
        return opened.st_dev, opened.st_ino
    except ProjectionTransitionError:
        raise
    except (OSError, ValueError):
        raise _fail() from None
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if parent_descriptor is not None:
            os.close(parent_descriptor)


def _require_own_projection(paths: ObservationPaths) -> tuple[int, int]:
    """Capture the exact prepared target inode before opening its SQLite model."""

    return _own_projection_identity(paths)


def _validate_expected_pointers(value: Any) -> dict[str, str | None]:
    if not isinstance(value, dict):
        raise _fail()
    result: dict[str, str | None] = {}
    for project_id, pointer in value.items():
        if not _is_canonical_project_id(project_id):
            raise _fail()
        if pointer is not None and not _is_pointer(pointer):
            raise _fail()
        result[project_id] = pointer
    return result


def _validate_request(
    request: Mapping[str, Any],
) -> tuple[str, Path, dict[str, str | None] | None]:
    if not isinstance(request, dict):
        raise _fail()
    operation = request.get("operation")
    if operation not in {"prepare", "select", "unselect"}:
        raise _fail()
    expected_keys = (
        _COMMON_REQUEST_KEYS
        if operation == "prepare"
        else _COMMON_REQUEST_KEYS | {"expected_pointers"}
    )
    if set(request) != expected_keys:
        raise _fail()
    if request.get("expected_schema") != READ_MODEL_SCHEMA:
        raise _fail()
    root = _validate_state_root(request.get("state_root"))
    if operation == "prepare":
        expected_pointers: dict[str, str | None] | None = {}
    elif operation == "unselect" and request.get("expected_pointers") is None:
        # Explicit total deactivation: the runner, not LifecycleManager, owns the
        # exact confined UUID enumeration and desired-absence expansion.
        expected_pointers = None
    else:
        expected_pointers = _validate_expected_pointers(request.get("expected_pointers"))
    return operation, root, expected_pointers


def _prepare(root: Path, project_ids: tuple[str, ...]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for project_id in project_ids:
        _assert_project_still_confined(root, project_id)
        paths = ObservationPaths.for_project(project_id, root=root)
        report = ingest_pending(paths)
        _assert_project_still_confined(root, project_id)
        rows.append(
            {
                "project_id": project_id,
                "expected_pointer": _read_pointer(paths),
                "segments_seen": report.segments_seen,
                "lines_seen": report.lines_seen,
                "events_inserted": report.events_inserted,
                "duplicate_events": report.duplicate_events,
                "quarantined_events": report.quarantined_events,
                "corrupt_segments": report.corrupt_segments,
                "unclean_epochs": report.unclean_epochs,
            }
        )
    return {
        "operation": "prepare",
        "target_schema": READ_MODEL_SCHEMA,
        "project_count": len(rows),
        "projects": rows,
    }


def _select(
    root: Path,
    project_ids: tuple[str, ...],
    expected_pointers: Mapping[str, str | None],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    own_pointer = f"{READ_MODEL_SCHEMA}.sqlite3"
    for project_id in project_ids:
        _assert_project_still_confined(root, project_id)
        paths = ObservationPaths.for_project(project_id, root=root)
        prepared_identity = _require_own_projection(paths)
        expected = expected_pointers[project_id]
        observed = _read_pointer(paths)
        if observed != expected and observed != own_pointer:
            raise _fail()
        publish_projection_pointer(
            paths,
            schema=READ_MODEL_SCHEMA,
            expected_active=expected,
            expected_projection_identity=prepared_identity,
        )
        _assert_project_still_confined(root, project_id)
        if _read_pointer(paths) != own_pointer:
            raise _fail()
        rows.append(
            {
                "project_id": project_id,
                "previous_pointer": observed,
                "selected_pointer": own_pointer,
            }
        )
    return {
        "operation": "select",
        "target_schema": READ_MODEL_SCHEMA,
        "project_count": len(rows),
        "selected_count": len(rows),
        "projects": rows,
    }


def _fsync_private_directory(path: Path) -> None:
    if os.name != "posix":  # pragma: no cover - release transition targets are POSIX
        return
    try:
        descriptor = _open_private_directory(path)
    except (OSError, ValueError):
        raise _fail() from None
    try:
        os.fsync(descriptor)
    except OSError:
        raise _fail() from None
    finally:
        os.close(descriptor)


def _restore_projection_pointer(
    paths: ObservationPaths,
    *,
    own_pointer: str,
    expected_pointer: str | None,
) -> tuple[str | None, bool]:
    """CAS-restore one pre-select pointer without opening either projection DB."""

    with project_lock(paths, "projection-pointer"):
        observed = _read_pointer(paths)
        if observed == expected_pointer:
            _fsync_private_directory(paths.projections)
            return observed, False
        if observed != own_pointer:
            raise _fail()

        pointer = paths.projection_pointer
        parent_descriptor: int | None = None
        descriptor: int | None = None
        try:
            parent_descriptor = _open_private_directory(pointer.parent)
            flags = (
                os.O_RDONLY
                | getattr(os, "O_NOFOLLOW", 0)
                | getattr(os, "O_CLOEXEC", 0)
                | getattr(os, "O_NONBLOCK", 0)
            )
            descriptor = os.open(pointer.name, flags, dir_fd=parent_descriptor)
            opened = os.fstat(descriptor)
            named = os.stat(
                pointer.name,
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = os.read(descriptor, 128)
                if not chunk:
                    break
                total += len(chunk)
                if total > 128:
                    raise _fail()
                chunks.append(chunk)
            named_after = os.stat(
                pointer.name,
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
            if (
                not stat.S_ISREG(opened.st_mode)
                or opened.st_nlink != 1
                or (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino)
                or (opened.st_dev, opened.st_ino) != (named_after.st_dev, named_after.st_ino)
                or b"".join(chunks) != (own_pointer + "\n").encode("ascii")
            ):
                raise _fail()

            if expected_pointer is None:
                os.unlink(pointer.name, dir_fd=parent_descriptor)
                os.fsync(parent_descriptor)
            else:
                atomic_private_write(
                    pointer,
                    (expected_pointer + "\n").encode("ascii"),
                )
        except ProjectionTransitionError:
            raise
        except (OSError, ValueError):
            raise _fail() from None
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if parent_descriptor is not None:
                os.close(parent_descriptor)

        if _read_pointer(paths) != expected_pointer:
            raise _fail()
        return observed, True


def _unselect(
    root: Path,
    project_ids: tuple[str, ...],
    expected_pointers: Mapping[str, str | None],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    own_pointer = f"{READ_MODEL_SCHEMA}.sqlite3"
    restored_count = 0
    for project_id in project_ids:
        _assert_project_still_confined(root, project_id)
        paths = ObservationPaths.for_project(project_id, root=root)
        expected = expected_pointers[project_id]
        observed, restored = _restore_projection_pointer(
            paths,
            own_pointer=own_pointer,
            expected_pointer=expected,
        )
        restored_count += int(restored)
        _assert_project_still_confined(root, project_id)
        if _read_pointer(paths) != expected:
            raise _fail()
        rows.append(
            {
                "project_id": project_id,
                "previous_pointer": observed,
                "selected_pointer": expected,
            }
        )
    return {
        "operation": "unselect",
        "target_schema": READ_MODEL_SCHEMA,
        "project_count": len(rows),
        "unselected_count": restored_count,
        "projects": rows,
    }


def run_transition(request: Mapping[str, Any]) -> dict[str, Any]:
    """Execute one target-local transition request.

    The public exception is deliberately generic.  Callers needing diagnostics use
    lifecycle transition state and content-free pointer snapshots, never raw paths or
    reducer/SQLite exception messages.
    """

    try:
        operation, root, expected_pointers = _validate_request(request)
        project_ids = _enumerate_project_ids(root)
        if operation == "select":
            if expected_pointers is None or set(project_ids) != set(expected_pointers):
                raise _fail()
        elif operation == "unselect":
            if expected_pointers is None:
                expected_pointers = dict.fromkeys(project_ids)
            elif set(project_ids) != set(expected_pointers):
                raise _fail()
        if operation == "prepare":
            result = _prepare(root, project_ids)
        elif operation == "select":
            assert expected_pointers is not None
            result = _select(root, project_ids, expected_pointers)
        else:
            assert expected_pointers is not None
            result = _unselect(root, project_ids, expected_pointers)
        if _enumerate_project_ids(root) != project_ids:
            raise _fail()
        return result
    except ProjectionTransitionError:
        raise
    except Exception:
        raise _fail() from None


def _read_stdin(stream: BinaryIO) -> bytes:
    try:
        data = stream.read(_MAX_REQUEST_BYTES + 1)
    except OSError:
        raise _fail() from None
    if len(data) > _MAX_REQUEST_BYTES:
        raise _fail()
    return data


def _load_request(argv: Sequence[str], stdin: BinaryIO) -> dict[str, Any]:
    if not argv:
        data = _read_stdin(stdin)
    elif len(argv) == 2 and argv[0] == "--request-file":
        request_path = Path(argv[1])
        data = _read_bounded_private_file(
            request_path,
            max_bytes=_MAX_REQUEST_BYTES,
            require_private_mode=True,
        )
    else:
        raise _fail()

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise _fail()
            result[key] = value
        return result

    try:
        value = json.loads(data, object_pairs_hook=unique_object)
    except (UnicodeError, json.JSONDecodeError):
        raise _fail() from None
    if not isinstance(value, dict):
        raise _fail()
    return value


def main(argv: Sequence[str] | None = None) -> int:
    """Content-free subprocess entry point used by :class:`LifecycleManager`."""

    arguments = tuple(sys.argv[1:] if argv is None else argv)
    try:
        request = _load_request(arguments, sys.stdin.buffer)
        result = run_transition(request)
        encoded = json.dumps(
            result,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("ascii")
        sys.stdout.buffer.write(encoded + b"\n")
        sys.stdout.buffer.flush()
        return 0
    except Exception:
        try:
            sys.stderr.buffer.write(_FAILURE_RESPONSE)
            sys.stderr.buffer.flush()
        except Exception:
            pass
        return 2


if __name__ == "__main__":  # pragma: no branch - module subprocess entry point
    raise SystemExit(main())
