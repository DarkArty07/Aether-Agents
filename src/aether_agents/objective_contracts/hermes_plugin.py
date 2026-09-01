"""Hermes plugin exposing Morfeo-only Objective Contract authoring."""

from __future__ import annotations

import json
import os
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .execution_boards import ExecutionBoardError, execution_board_slug
from .store import REQUIRED_SECTIONS, ContractError, ObjectiveContractStore

_ACTIONS = (
    "begin",
    "set_section",
    "show",
    "list",
    "validate",
    "finalize",
    "supersede",
    "prepare_handoff",
)


def _required(args: dict[str, Any], name: str) -> Any:
    value = args.get(name)
    if value is None or value == "":
        raise ContractError("AETHER-OBJECTIVE-CONTRACT-ARGUMENT-MISSING", f"{name} is required")
    return value


def _primary_path(project: Any) -> Path | None:
    raw = getattr(project, "primary_path", None)
    return Path(raw).expanduser().resolve() if isinstance(raw, str) and raw else None


_THREAD_LOCKS: dict[str, threading.Lock] = {}
_THREAD_LOCKS_GUARD = threading.Lock()


def _safe_board_paths(kanban_db: Any, board_slug: str) -> tuple[Path, Path, Path]:
    """Return canonical paths after rejecting every board-local redirection."""
    home = kanban_db.kanban_home()
    boards = kanban_db.boards_root()
    directory = kanban_db.board_dir(board_slug)
    expected = boards / board_slug
    if directory != expected:
        raise ExecutionBoardError(
            "AETHER-EXECUTION-BOARD-PATH-CONFLICT",
            "Hermes resolved the execution board outside its canonical board root",
        )
    for path in (home, home / "kanban", boards, directory):
        if path.is_symlink():
            raise ExecutionBoardError(
                "AETHER-EXECUTION-BOARD-UNSAFE-PATH",
                "the execution-board directory chain contains a symbolic link",
            )
        if path.exists() and not path.is_dir():
            raise ExecutionBoardError(
                "AETHER-EXECUTION-BOARD-UNSAFE-PATH",
                "the execution-board directory chain contains a non-directory",
            )
    metadata = directory / "board.json"
    database = directory / "kanban.db"
    for path in (metadata, database):
        if path.is_symlink():
            raise ExecutionBoardError(
                "AETHER-EXECUTION-BOARD-UNSAFE-PATH",
                "execution-board metadata or database is a symbolic link",
            )
        if path.exists() and not path.is_file():
            raise ExecutionBoardError(
                "AETHER-EXECUTION-BOARD-UNSAFE-PATH",
                "execution-board metadata or database is not a regular file",
            )
    return directory, metadata, database


def _create_metadata_exclusive(
    metadata_path: Path,
    *,
    slug: str,
    project_root: Path,
    runtime_project_id: str,
    aether_project_id: str,
    contract_id: str,
    version: int,
) -> bool:
    """Create board metadata without ever overwriting a competing writer."""
    payload = {
        "slug": slug,
        "name": f"Objective {contract_id}@v{version}",
        "description": "Aether Objective Contract execution board",
        "icon": "",
        "color": "",
        "default_workdir": str(project_root),
        "project_id": runtime_project_id,
        "aether_project_id": aether_project_id,
        "aether_contract_id": contract_id,
        "aether_contract_version": version,
        "created_at": int(time.time()),
        "archived": False,
    }
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = -1
    try:
        descriptor = os.open(metadata_path, flags, 0o600)
    except FileExistsError:
        return False
    except OSError as exc:
        raise ExecutionBoardError(
            "AETHER-EXECUTION-BOARD-RUNTIME-FAILURE",
            "execution-board metadata could not be created exclusively",
        ) from exc
    try:
        encoded = (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            descriptor = -1
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        metadata_path.unlink(missing_ok=True)
        raise ExecutionBoardError(
            "AETHER-EXECUTION-BOARD-RUNTIME-FAILURE",
            "execution-board metadata could not be written completely",
        ) from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    return True


def _validate_execution_metadata(
    metadata: dict[str, Any],
    *,
    runtime_project_id: str,
    project_root: Path,
    aether_project_id: str,
    contract_id: str,
    version: int,
) -> None:
    if metadata.get("archived"):
        raise ExecutionBoardError(
            "AETHER-EXECUTION-BOARD-ARCHIVED",
            "the execution board for this contract version is archived",
        )
    if metadata.get("project_id") != runtime_project_id:
        raise ExecutionBoardError(
            "AETHER-EXECUTION-BOARD-IDENTITY-CONFLICT",
            "the execution board is bound to a different Hermes Project",
        )
    if metadata.get("default_workdir") != str(project_root):
        raise ExecutionBoardError(
            "AETHER-EXECUTION-BOARD-PATH-CONFLICT",
            "the execution board is bound to a different project root",
        )
    identity = (
        metadata.get("aether_project_id"),
        metadata.get("aether_contract_id"),
        metadata.get("aether_contract_version"),
    )
    if identity != (aether_project_id, contract_id, version):
        raise ExecutionBoardError(
            "AETHER-EXECUTION-BOARD-IDENTITY-CONFLICT",
            "the execution board carries a different Objective Contract identity",
        )


@contextmanager
def _runtime_project_lock(project_root: Path) -> Iterator[Any]:
    """Resolve one live exact Project while excluding concurrent registry writers."""
    from hermes_cli import projects_db  # type: ignore[import-untyped]

    root = project_root.expanduser().resolve()
    try:
        with projects_db.connect_closing() as connection:
            connection.execute("BEGIN IMMEDIATE")
            matches = [
                project
                for project in projects_db.list_projects(connection, include_archived=False)
                if _primary_path(project) == root
            ]
            if not matches:
                raise ExecutionBoardError(
                    "AETHER-EXECUTION-BOARD-PROJECT-MISSING",
                    "no live Hermes Project has the verified Aether project as its exact primary path",
                )
            if len(matches) != 1:
                raise ExecutionBoardError(
                    "AETHER-EXECUTION-BOARD-PROJECT-CONFLICT",
                    "more than one live Hermes Project has the verified Aether project as its exact primary path",
                )
            try:
                yield matches[0]
            finally:
                connection.rollback()
    except ExecutionBoardError:
        raise
    except Exception as exc:
        raise ExecutionBoardError(
            "AETHER-EXECUTION-BOARD-PROJECT-UNAVAILABLE",
            "the native Hermes Project registry could not be locked and read",
        ) from exc


@contextmanager
def _provision_lock(board_slug: str) -> Iterator[None]:
    """Serialize idempotent board creation across threads and local processes."""
    from hermes_cli import kanban_db  # type: ignore[import-untyped]

    with _THREAD_LOCKS_GUARD:
        thread_lock = _THREAD_LOCKS.setdefault(board_slug, threading.Lock())
    directory, _metadata, _database = _safe_board_paths(kanban_db, board_slug)
    lock_path = directory.parent / f".{board_slug}.provision.lock"
    descriptor = -1
    try:
        if lock_path.is_symlink() or (lock_path.exists() and not lock_path.is_file()):
            raise OSError("unsafe provision lock path")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        _safe_board_paths(kanban_db, board_slug)
        flags = os.O_RDWR | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(lock_path, flags, 0o600)
        handle = os.fdopen(descriptor, "r+b", closefd=True)
        descriptor = -1
    except OSError as exc:
        if descriptor >= 0:
            os.close(descriptor)
        raise ExecutionBoardError(
            "AETHER-EXECUTION-BOARD-RUNTIME-FAILURE",
            "the execution-board provision lock could not be opened",
        ) from exc

    with thread_lock, handle:
        locked = False
        try:
            if os.name == "nt":  # pragma: no cover - CI/runtime qualification is POSIX.
                import msvcrt

                handle.seek(0)
                if handle.read(1) == b"":
                    handle.write(b"0")
                    handle.flush()
                handle.seek(0)
                locking = getattr(msvcrt, "locking")
                lock = getattr(msvcrt, "LK_LOCK")
                locking(handle.fileno(), lock, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            locked = True
        except (OSError, AttributeError) as exc:
            raise ExecutionBoardError(
                "AETHER-EXECUTION-BOARD-RUNTIME-FAILURE",
                "the execution-board provision lock could not be acquired",
            ) from exc
        try:
            yield
        finally:
            if locked:
                try:
                    if os.name == "nt":  # pragma: no cover - see above.
                        import msvcrt

                        handle.seek(0)
                        locking = getattr(msvcrt, "locking")
                        unlock = getattr(msvcrt, "LK_UNLCK")
                        locking(handle.fileno(), unlock, 1)
                    else:
                        import fcntl

                        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                except (OSError, AttributeError):
                    # The protected mutation has already completed or failed; closing the
                    # descriptor releases the OS lock even when explicit unlock reports an
                    # error. Never replace the original result with cleanup noise.
                    pass


def _provision_execution_board(
    *, project_id: str, project_root: Path, contract_id: str, version: int
) -> dict[str, str]:
    """Create or verify the one Hermes board for an executable contract version."""
    from hermes_cli import kanban_db  # type: ignore[import-untyped]

    if os.environ.get("HERMES_KANBAN_DB", "").strip():
        raise ExecutionBoardError(
            "AETHER-EXECUTION-BOARD-RAW-DB-OVERRIDE",
            "HERMES_KANBAN_DB bypasses board isolation; unset it before preparing a handoff",
        )
    slug = execution_board_slug(project_id, contract_id, version)
    root = project_root.expanduser().resolve()

    with _runtime_project_lock(root) as runtime_project:
        runtime_project_id = str(runtime_project.id)
        with _provision_lock(slug):
            try:
                directory, metadata_path, db_path = _safe_board_paths(kanban_db, slug)
                exists = db_path.exists() or metadata_path.exists()
                if not exists:
                    directory.mkdir(parents=False, exist_ok=True)
                    directory, metadata_path, db_path = _safe_board_paths(kanban_db, slug)
                    _create_metadata_exclusive(
                        metadata_path,
                        slug=slug,
                        project_root=root,
                        runtime_project_id=runtime_project_id,
                        aether_project_id=project_id,
                        contract_id=contract_id,
                        version=version,
                    )
                    directory, metadata_path, db_path = _safe_board_paths(kanban_db, slug)

                metadata = kanban_db.read_board_metadata(slug)
                _validate_execution_metadata(
                    metadata,
                    runtime_project_id=runtime_project_id,
                    project_root=root,
                    aether_project_id=project_id,
                    contract_id=contract_id,
                    version=version,
                )

                # Use the canonical explicit path, never Hermes's raw DB override. Idempotent
                # on a healthy board and repairs an exclusively-created metadata-only state.
                kanban_db.init_db(db_path=db_path)
                _directory, metadata_path, db_path = _safe_board_paths(kanban_db, slug)
                metadata = kanban_db.read_board_metadata(slug)
                _validate_execution_metadata(
                    metadata,
                    runtime_project_id=runtime_project_id,
                    project_root=root,
                    aether_project_id=project_id,
                    contract_id=contract_id,
                    version=version,
                )
                if not db_path.is_file():
                    raise ExecutionBoardError(
                        "AETHER-EXECUTION-BOARD-VERIFY-FAILED",
                        "the execution board database is missing after initialization",
                    )
            except ExecutionBoardError:
                raise
            except Exception as exc:
                raise ExecutionBoardError(
                    "AETHER-EXECUTION-BOARD-RUNTIME-FAILURE",
                    "the Hermes execution board could not be created or verified",
                ) from exc

    return {"slug": slug, "hermes_project_id": runtime_project_id}


def _handle(
    args: dict[str, Any],
    *,
    session_id: str = "",
    author_profile: str = "",
    **_kwargs: Any,
) -> str:
    try:
        if author_profile != "morfeo":
            raise ContractError(
                "AETHER-OBJECTIVE-CONTRACT-ROLE-DENIED",
                "Objective Contract authoring is restricted to Morfeo",
            )
        action = _required(args, "action")
        project_id = _required(args, "project_id")
        store = ObjectiveContractStore(author_profile=author_profile)
        if action == "begin":
            result = store.begin(
                project_id=project_id,
                title=_required(args, "title"),
                session_id=session_id,
            )
        elif action == "set_section":
            result = store.set_section(
                project_id=project_id,
                contract_id=_required(args, "contract_id"),
                expected_revision=_required(args, "expected_revision"),
                section=_required(args, "section"),
                content=_required(args, "content"),
                session_id=session_id,
            )
        elif action == "show":
            result = store.show(
                project_id=project_id,
                contract_id=_required(args, "contract_id"),
            )
        elif action == "list":
            result = store.list(project_id=project_id)
        elif action == "validate":
            result = store.validate(
                project_id=project_id,
                contract_id=_required(args, "contract_id"),
            )
        elif action == "finalize":
            result = store.finalize(
                project_id=project_id,
                contract_id=_required(args, "contract_id"),
                expected_revision=_required(args, "expected_revision"),
                session_id=session_id,
            )
        elif action == "supersede":
            result = store.supersede(
                project_id=project_id,
                contract_id=_required(args, "contract_id"),
                version=_required(args, "version"),
                change_reason=_required(args, "change_reason"),
                session_id=session_id,
            )
        elif action == "prepare_handoff":

            def provision(prepared: dict[str, Any], project_root: Path) -> dict[str, str]:
                try:
                    binding = _provision_execution_board(
                        project_id=str(prepared["project_id"]),
                        project_root=project_root,
                        contract_id=str(prepared["contract_id"]),
                        version=int(prepared["version"]),
                    )
                except ExecutionBoardError as exc:
                    raise ContractError(exc.code, str(exc)) from exc
                if binding["slug"] != prepared["execution_board"]:
                    raise ContractError(
                        "AETHER-EXECUTION-BOARD-IDENTITY-CONFLICT",
                        "provisioned board identity does not match the prepared handoff",
                    )
                return {"hermes_project_id": binding["hermes_project_id"]}

            result = store.prepare_handoff(
                project_id=project_id,
                contract_id=_required(args, "contract_id"),
                version=_required(args, "version"),
                on_ready=provision,
            )
        else:
            raise ContractError(
                "AETHER-OBJECTIVE-CONTRACT-ACTION-INVALID", "action is not supported"
            )
        return json.dumps(result, ensure_ascii=False)
    except ContractError as exc:
        return json.dumps(
            {"success": False, "error": {"code": exc.code, "message": str(exc)}},
            ensure_ascii=False,
        )


def register(ctx: Any) -> None:
    """Register one transactional authoring tool only in the configured Morfeo profile."""
    get_config = getattr(ctx, "get_config", None)
    profile_name = getattr(ctx, "profile_name", "")
    if (
        profile_name != "morfeo"
        or not callable(get_config)
        or get_config("author_profile", "") != "morfeo"
    ):
        return

    def handler(args: dict[str, Any], **runtime_kwargs: Any) -> str:
        runtime_kwargs.pop("author_profile", None)
        return _handle(
            args,
            author_profile=getattr(ctx, "profile_name", ""),
            **runtime_kwargs,
        )

    ctx.register_tool(
        name="objective_contract",
        toolset="aether_contracts",
        description="Author project-bound Objective Contracts for Morfeo-to-Supervisor handoff.",
        schema={
            "name": "objective_contract",
            "description": (
                "Incrementally author, finalize, version and prepare a project-bound Objective "
                "Contract. Always pass the explicit portable project UUID. Hermes supplies the "
                "authoring session id; never put a complete contract in one call. A ready "
                "prepare_handoff provisions an isolated execution board and returns "
                "execution_board/hermes_project_id as root-card side data; pass them unchanged "
                "as kanban_create board/project and never copy them into the envelope or body."
            ),
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "required": ["action", "project_id"],
                "properties": {
                    "action": {"type": "string", "enum": list(_ACTIONS)},
                    "project_id": {
                        "type": "string",
                        "description": "Portable UUID from the verified .aether/project.toml marker.",
                    },
                    "title": {"type": "string", "maxLength": 200},
                    "contract_id": {"type": "string", "pattern": "^oc_[a-f0-9]{16}$"},
                    "expected_revision": {"type": "integer", "minimum": 1},
                    "section": {"type": "string", "enum": list(REQUIRED_SECTIONS)},
                    "content": {
                        "type": "string",
                        "description": "One accepted section only; do not resend the whole contract.",
                    },
                    "version": {"type": "integer", "minimum": 1},
                    "change_reason": {"type": "string"},
                },
            },
        },
        handler=handler,
        check_fn=lambda: getattr(ctx, "profile_name", "") == "morfeo",
    )
