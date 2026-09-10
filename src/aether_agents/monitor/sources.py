"""Read-only source adapters for the Telegram monitor.

The monitor is an observer of native Aether/Hermes state.  This module deliberately
contains no native mutator imports: every SQLite source is opened with a ``mode=ro``
URI, ``query_only`` is asserted, and only an explicit allow-list of columns crosses the
adapter boundary.  Invalid identity is represented as a coverage gap rather than a
best-effort project/session guess.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import stat
import tomllib
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence

from aether_agents.observation.context import ProjectRegistry, canonical_project_id
from aether_agents.paths import read_private_bytes
from aether_agents.project_marker import ProjectMarkerValidationError, validate_project_marker

from .models import WorkItem

__all__ = [
    "BoardBinding",
    "CoverageGap",
    "ProjectBinding",
    "ReadOnlySourceError",
    "ReadOnlySources",
    "SessionRecord",
    "SourceCollection",
    "SourceItem",
    "SourceReadError",
    "enumerate_project_bindings",
    "open_read_only_sqlite",
]

SNAPSHOT_SCHEMA = "aether.telegram-monitor.snapshot.v1"
MAX_PROSE_CHARS = 600
MAX_SOURCE_EXCERPT_CHARS = 1_200
MAX_SNAPSHOT_CHARS = 24_000

_PROJECT_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.ASCII,
)
_CONTRACT_RE = re.compile(r"^oc_[0-9a-f]{16}$", re.ASCII)
_BOARD_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$", re.ASCII)
_VERSION_RE = re.compile(r"^v([1-9][0-9]*)$", re.ASCII)
_SAFE_REF_RE = re.compile(r"^[^\x00-\x1f\x7f]{1,256}$")
_EMAIL_RE = re.compile(r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d .()_-]{8,}\d)(?!\d)")
_ABSOLUTE_PATH_RE = re.compile(
    r"(?:^|[\s\"'=:])(?:/(?:home|Users|root|tmp|var|etc|opt)/|[A-Za-z]:[\\/])"
)
_URI_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://")
_TRANSCRIPT_RE = re.compile(r"(?:^|\[)(?:user|assistant|system|tool)(?:\]|:)", re.IGNORECASE)
_SECRET_RE = re.compile(
    r"(?:\b(?:sk|ghp|gho|ghs|ghu|ghr|xoxb|xoxp)-?[A-Za-z0-9_-]{12,}|"
    r"\bAKIA[0-9A-Z]{16}\b|-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})"
)

_TERMINAL_STATES = frozenset({"done", "completed", "failed", "crashed", "timed_out", "gave_up"})
_FAILURE_STATES = frozenset({"failed", "crashed", "timed_out", "gave_up", "spawn_failed"})
_PENDING_STATES = frozenset({"blocked", "triage", "review", "todo", "ready", "scheduled", "queued"})
_REPORT_SOURCES = frozenset({"cron", "report", "monitor", "gateway"})
_TASK_RE = re.compile(r"^t_[0-9a-f]{8}$", re.ASCII)


class ReadOnlySourceError(RuntimeError):
    """A source cannot be safely opened or does not expose its required schema."""


class SourceReadError(ReadOnlySourceError):
    """An individual source was unavailable or malformed."""


@dataclass(frozen=True, slots=True)
class CoverageGap:
    """A privacy-safe, deterministic source coverage diagnostic."""

    code: str
    detail: str = ""

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{1,63}", self.code, re.ASCII):
            raise ValueError("coverage code must be an uppercase diagnostic code")
        if self.detail and not _safe_text(self.detail, limit=180, allow_transcript=False):
            raise ValueError("coverage detail is not safe")

    @property
    def text(self) -> str:
        return self.code if not self.detail else f"{self.code}: {self.detail}"


@dataclass(frozen=True, slots=True)
class ProjectBinding:
    """A registry project whose marker and native Project path agree."""

    project_id: str
    name: str
    path: Path
    hermes_project_id: str
    hermes_project_name: str | None = None


@dataclass(frozen=True, slots=True)
class BoardBinding:
    """A finalized contract board bound to one verified project."""

    slug: str
    database_path: Path
    project: ProjectBinding
    contract_id: str
    contract_version: str
    contract_title: str
    created_in_session: str
    finalized_in_session: str
    observation_trace_id: str | None = None


@dataclass(frozen=True, slots=True)
class SessionRecord:
    """The bounded display and lifecycle fields of one exact native session."""

    session_id: str
    title: str
    source: str | None
    cwd: str | None
    git_repo_root: str | None
    started_at_utc: str | None
    ended_at_utc: str | None
    last_activity_at_utc: str | None
    database_path: Path

    @property
    def is_reporter(self) -> bool:
        source = (self.source or "").strip().lower()
        return source in _REPORT_SOURCES or source.startswith("cron") or "report" in source


@dataclass(frozen=True, slots=True)
class SourceItem:
    """One normalized pipeline or direct-work identity before store persistence."""

    work_key: str
    project_id: str
    project_name: str
    origin_session_id: str
    origin_session_title: str
    contract: Mapping[str, str] | None
    observed_state: str
    state_evidence_refs: tuple[str, ...] = ()
    started_at_utc: str | None = None
    ended_at_utc: str | None = None
    resolved: tuple[Mapping[str, Any], ...] = ()
    current: tuple[Mapping[str, Any], ...] = ()
    next: tuple[Mapping[str, Any], ...] = ()
    complications: tuple[Mapping[str, Any], ...] = ()
    pending: tuple[Mapping[str, Any], ...] = ()
    coverage_gaps: tuple[str, ...] = ()
    source_cursor: Mapping[str, Any] = field(default_factory=dict)
    active: bool = True

    def to_snapshot(self) -> dict[str, Any]:
        item: dict[str, Any] = {
            "work_key": self.work_key,
            "project": {"id": self.project_id, "name": self.project_name},
            "origin_session": {
                "id": self.origin_session_id,
                "title": self.origin_session_title,
            },
            "contract": dict(self.contract) if self.contract is not None else None,
            "observed_state": self.observed_state,
            "state_evidence_refs": list(self.state_evidence_refs),
            "resolved": [dict(value) for value in self.resolved],
            "current": [dict(value) for value in self.current],
            "next": [dict(value) for value in self.next],
            "complications": [dict(value) for value in self.complications],
            "pending": [dict(value) for value in self.pending],
            "coverage_gaps": list(self.coverage_gaps),
        }
        if self.started_at_utc is not None:
            item["started_at_utc"] = self.started_at_utc
        if self.ended_at_utc is not None:
            item["ended_at_utc"] = self.ended_at_utc
        return item

    @property
    def terminal(self) -> bool:
        return self.observed_state in {
            "completed",
            "failed",
            "crashed",
            "timed_out",
            "turn_ended_completed",
            "turn_ended_failed",
            "turn_ended_interrupted",
            "turn_ended_unknown",
        }


@dataclass(frozen=True, slots=True)
class SourceCollection:
    """Read-only source result consumed by the hourly collector."""

    items: tuple[SourceItem, ...]
    watermarks: Mapping[str, Any]
    coverage_gaps: tuple[str, ...] = ()

    @property
    def idle(self) -> bool:
        return not self.items and not self.coverage_gaps


@dataclass(frozen=True, slots=True)
class _TaskRow:
    values: Mapping[str, Any]
    board: BoardBinding
    parent_ids: tuple[str, ...]
    runs: tuple[Mapping[str, Any], ...]
    events: tuple[Mapping[str, Any], ...]
    worker_session_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class _ContractMetadata:
    contract_id: str
    version: str
    title: str
    created_in_session: str
    finalized_in_session: str
    observation_trace_id: str | None


def _safe_text(
    value: Any,
    *,
    limit: int,
    allow_transcript: bool = False,
    allow_path: bool = False,
) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.strip().split())
    if not text or len(text) > limit or any(ord(char) < 0x20 or ord(char) == 0x7F for char in text):
        return None
    if not allow_path and (_ABSOLUTE_PATH_RE.search(text) or _URI_RE.match(text)):
        return None
    if _EMAIL_RE.search(text) or _PHONE_RE.search(text) or _SECRET_RE.search(text):
        return None
    if not allow_transcript and _TRANSCRIPT_RE.search(text):
        return None
    return text


def _native_task_ref(value: Any) -> str | None:
    if not isinstance(value, str) or _TASK_RE.fullmatch(value) is None:
        return None
    return value


def _safe_ref(value: Any, *, limit: int = 256) -> str | None:
    if not isinstance(value, str) or len(value) > limit or not _SAFE_REF_RE.fullmatch(value):
        return None
    return value


def _canonical_timestamp(value: Any) -> str | None:
    """Normalize native epoch/ISO values to fixed UTC text without guessing."""
    try:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            parsed = datetime.fromtimestamp(float(value), tz=timezone.utc)
        elif isinstance(value, str) and value.strip():
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
            if parsed.tzinfo is None or parsed.utcoffset() is None:
                return None
            parsed = parsed.astimezone(timezone.utc)
        else:
            return None
    except (OverflowError, OSError, TypeError, ValueError):
        return None
    return parsed.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _parse_timestamp(value: Any) -> datetime | None:
    text = _canonical_timestamp(value)
    if text is None:
        return None
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def _version_text(value: Any) -> str | None:
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return f"v{value}"
    if isinstance(value, str):
        match = _VERSION_RE.fullmatch(value.strip())
        if match:
            return value.strip()
        if value.isdigit() and int(value) > 0:
            return f"v{int(value)}"
    return None


def _safe_path(path: Path) -> Path:
    """Reject links and aliases before a read-only SQLite open."""
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        raise ReadOnlySourceError("source path must be absolute")
    try:
        info = candidate.lstat()
    except OSError as exc:
        raise ReadOnlySourceError("source file is unavailable") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ReadOnlySourceError("source file is not a private singly-linked regular file")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise ReadOnlySourceError("source file cannot be resolved") from exc
    if resolved != candidate:
        raise ReadOnlySourceError("source file resolves through an alias")
    return candidate


@contextmanager
def open_read_only_sqlite(
    path: Path | str, *, timeout: float = 0.25
) -> Iterator[sqlite3.Connection]:
    """Open an existing SQLite file read-only and assert SQLite query-only mode."""
    source = _safe_path(Path(path))
    try:
        connection = sqlite3.connect(
            source.as_uri() + "?mode=ro",
            uri=True,
            timeout=timeout,
            check_same_thread=False,
        )
    except (OSError, sqlite3.Error) as exc:
        raise ReadOnlySourceError("source SQLite database cannot be opened read-only") from exc
    connection.row_factory = sqlite3.Row
    try:
        try:
            connection.execute("PRAGMA query_only=ON")
            row = connection.execute("PRAGMA query_only").fetchone()
        except sqlite3.Error as exc:
            raise ReadOnlySourceError(
                "source SQLite database did not enter query-only mode"
            ) from exc
        if row is None or int(row[0]) != 1:
            raise ReadOnlySourceError("source SQLite database did not enter query-only mode")
        yield connection
    finally:
        connection.close()


def _table_columns(connection: sqlite3.Connection, table: str) -> frozenset[str]:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table, re.ASCII):
        raise ValueError("unsafe source table name")
    try:
        rows = connection.execute(f'PRAGMA table_info("{table}")').fetchall()
    except sqlite3.Error as exc:
        raise SourceReadError("source schema could not be inspected") from exc
    return frozenset(str(row[1]) for row in rows)


def _select_rows(
    connection: sqlite3.Connection,
    table: str,
    columns: Sequence[str],
    *,
    required: Sequence[str] = (),
    order_by: Sequence[str] = (),
) -> tuple[dict[str, Any], ...]:
    available = _table_columns(connection, table)
    if not available:
        raise SourceReadError(f"source table {table} is missing")
    missing = [column for column in required if column not in available]
    if missing:
        raise SourceReadError(f"source table {table} lacks required columns")
    selected = tuple(column for column in columns if column in available)
    if not selected:
        return ()
    if any(column not in selected for column in order_by):
        order_by = ()
    sql = f'SELECT {", ".join(selected)} FROM "{table}"'
    if order_by:
        sql += " ORDER BY " + ", ".join(order_by)
    try:
        rows = connection.execute(sql).fetchall()
    except sqlite3.Error as exc:
        raise SourceReadError(f"source table {table} could not be read") from exc
    return tuple({column: row[column] for column in selected} for row in rows)


def _read_json_file(path: Path) -> Mapping[str, Any] | None:
    try:
        value = json.loads(read_private_bytes(path).decode("utf-8"))
    except (OSError, UnicodeError, ValueError):
        return None
    return value if isinstance(value, Mapping) else None


def _read_marker(path: Path) -> Mapping[str, Any] | None:
    marker_path = path / ".aether" / "project.toml"
    try:
        data = tomllib.loads(read_private_bytes(marker_path).decode("utf-8"))
        return validate_project_marker(data)
    except (OSError, UnicodeError, tomllib.TOMLDecodeError, ProjectMarkerValidationError):
        return None


def _registry_entries(registry: ProjectRegistry) -> tuple[Mapping[str, Any], ...]:
    value = _read_json_file(registry.path)
    if value is None or not isinstance(value.get("projects"), Mapping):
        raise SourceReadError("Aether project registry is unavailable or malformed")
    entries: list[Mapping[str, Any]] = []
    for raw_id, raw_entry in sorted(value["projects"].items(), key=lambda pair: str(pair[0])):
        project_id = canonical_project_id(raw_id)
        if project_id is None or not isinstance(raw_entry, Mapping):
            continue
        entry = dict(raw_entry)
        entry["project_id"] = project_id
        entries.append(entry)
    return tuple(entries)


def _resolve_native_projects_path(
    path: Path | str | None, hermes_home: Path | str | None
) -> Path | None:
    if path is not None:
        return Path(path).expanduser()
    if hermes_home is not None:
        return Path(hermes_home).expanduser() / "projects.db"
    configured = os.environ.get("HERMES_HOME", "").strip()
    if configured:
        return Path(configured).expanduser() / "projects.db"
    try:
        from hermes_constants import get_hermes_home  # type: ignore[import-not-found]

        return Path(get_hermes_home()) / "projects.db"
    except Exception:
        return None


def enumerate_project_bindings(
    registry: ProjectRegistry,
    *,
    native_projects_path: Path | str | None = None,
    hermes_home: Path | str | None = None,
) -> tuple[tuple[ProjectBinding, ...], tuple[str, ...]]:
    """Enumerate registry projects whose marker and exact native path agree."""
    gaps: list[str] = []
    try:
        entries = _registry_entries(registry)
    except SourceReadError:
        return (), ("PROJECT_REGISTRY_UNREADABLE",)
    native_path = _resolve_native_projects_path(native_projects_path, hermes_home)
    if native_path is None:
        return (), ("NATIVE_PROJECTS_UNAVAILABLE",)
    try:
        with open_read_only_sqlite(native_path) as connection:
            native_rows = _select_rows(
                connection,
                "projects",
                ("id", "name", "primary_path", "archived"),
                required=("id", "primary_path"),
                order_by=("id",),
            )
    except ReadOnlySourceError:
        return (), ("NATIVE_PROJECTS_UNREADABLE",)

    bindings: list[ProjectBinding] = []
    for entry in entries:
        project_id = str(entry["project_id"])
        raw_path = entry.get("path")
        if not isinstance(raw_path, str) or not raw_path:
            gaps.append("PROJECT_PATH_MISSING")
            continue
        project_path = Path(raw_path).expanduser()
        if project_path.is_symlink() or not project_path.is_dir():
            gaps.append("PROJECT_PATH_UNSAFE")
            continue
        try:
            project_root = project_path.resolve(strict=True)
        except OSError:
            gaps.append("PROJECT_PATH_UNREADABLE")
            continue
        marker = _read_marker(project_root)
        if marker is None or canonical_project_id(marker.get("project_id")) != project_id:
            gaps.append("PROJECT_MARKER_INVALID")
            continue
        name = _safe_text(marker.get("name"), limit=160)
        if name is None:
            gaps.append("PROJECT_NAME_UNSAFE")
            name = "[unavailable project name]"
        expected_native = entry.get("hermes_project_id")
        matches: list[Mapping[str, Any]] = []
        for row in native_rows:
            archived = row.get("archived")
            if archived not in (None, 0, False):
                continue
            primary = row.get("primary_path")
            if not isinstance(primary, str) or not primary:
                continue
            try:
                native_root = Path(primary).expanduser().resolve(strict=True)
            except OSError:
                continue
            if native_root == project_root:
                matches.append(row)
        if expected_native is not None:
            matches = [row for row in matches if str(row.get("id")) == str(expected_native)]
        if len(matches) != 1:
            gaps.append("NATIVE_PROJECT_PATH_CONFLICT" if matches else "NATIVE_PROJECT_MISSING")
            continue
        native_id = _safe_ref(matches[0].get("id"), limit=160)
        if native_id is None:
            gaps.append("NATIVE_PROJECT_ID_INVALID")
            continue
        native_name = _safe_text(matches[0].get("name"), limit=160)
        bindings.append(
            ProjectBinding(
                project_id=project_id,
                name=name,
                path=project_root,
                hermes_project_id=native_id,
                hermes_project_name=native_name,
            )
        )
    return tuple(sorted(bindings, key=lambda item: item.project_id)), tuple(sorted(set(gaps)))


def _contract_metadata(
    project: ProjectBinding,
    contract_id: str,
    version: str,
) -> _ContractMetadata | None:
    if not _CONTRACT_RE.fullmatch(contract_id):
        return None
    version_number = version[1:] if version.startswith("v") else version
    path = project.path / ".aether" / "objective-contracts" / contract_id / f"v{version_number}.md"
    try:
        text = read_private_bytes(path).decode("utf-8")
    except (OSError, UnicodeError):
        return None
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        return None
    front = text[4:].split("\n---\n", 1)[0]
    metadata: dict[str, Any] = {}
    try:
        for line in front.splitlines():
            key, raw = line.split(": ", 1)
            metadata[key] = json.loads(raw)
    except (ValueError, json.JSONDecodeError):
        return None
    if (
        metadata.get("artifact_type") != "aether.objective-contract.v1"
        or metadata.get("status") != "final"
        or canonical_project_id(metadata.get("project_id")) != project.project_id
        or metadata.get("contract_id") != contract_id
    ):
        return None
    actual_version = _version_text(metadata.get("version"))
    title = _safe_text(metadata.get("title"), limit=200)
    created = _safe_ref(metadata.get("created_in_session"))
    finalized = _safe_ref(metadata.get("finalized_in_session"))
    if actual_version != version or title is None or created is None or finalized is None:
        return None
    trace = metadata.get("observation_trace_id")
    if trace is not None and _safe_ref(trace) is None:
        trace = None
    return _ContractMetadata(contract_id, version, title, created, finalized, trace)


def _extract_contract_fields(metadata: Mapping[str, Any]) -> tuple[str | None, str | None]:
    nested = metadata.get("contract")
    if not isinstance(nested, Mapping):
        nested = metadata.get("objective_contract")
    if not isinstance(nested, Mapping):
        nested = {}
    contract_id = (
        metadata.get("aether_contract_id")
        or metadata.get("contract_id")
        or nested.get("id")
        or nested.get("contract_id")
    )
    version = (
        metadata.get("aether_contract_version")
        or metadata.get("contract_version")
        or metadata.get("version")
        or nested.get("version")
        or nested.get("contract_version")
    )
    return (
        contract_id if isinstance(contract_id, str) else None,
        _version_text(version),
    )


def _resolve_board_paths(
    *,
    board_paths: Sequence[Path | str | tuple[str, Path | str]] | None,
    hermes_home: Path | str | None,
) -> tuple[tuple[str, Path], ...]:
    if board_paths is not None:
        result: list[tuple[str, Path]] = []
        for raw in board_paths:
            if isinstance(raw, tuple):
                slug, path = raw
            else:
                path = raw
                slug = "default" if Path(path).name == "kanban.db" else Path(path).parent.name
            if isinstance(slug, str) and _BOARD_RE.fullmatch(slug):
                result.append((slug, Path(path).expanduser()))
        return tuple(sorted(result, key=lambda item: item[0]))
    root = Path(hermes_home).expanduser() if hermes_home is not None else None
    if root is None:
        configured = os.environ.get("HERMES_HOME", "").strip()
        root = Path(configured).expanduser() if configured else None
    if root is None:
        try:
            from hermes_constants import get_hermes_home  # type: ignore[import-not-found]

            root = Path(get_hermes_home())
        except Exception:
            return ()
    paths: list[tuple[str, Path]] = [("default", root / "kanban.db")]
    boards_root = root / "kanban" / "boards"
    if boards_root.is_dir() and not boards_root.is_symlink():
        for child in sorted(boards_root.iterdir(), key=lambda item: item.name):
            if _BOARD_RE.fullmatch(child.name):
                paths.append((child.name, child / "kanban.db"))
    return tuple(paths)


def _read_board_bindings(
    projects: Sequence[ProjectBinding],
    *,
    board_paths: Sequence[Path | str | tuple[str, Path | str]] | None,
    hermes_home: Path | str | None,
) -> tuple[tuple[BoardBinding, ...], tuple[str, ...]]:
    project_map = {project.project_id: project for project in projects}
    bindings: list[BoardBinding] = []
    gaps: list[str] = []
    for slug, database_path in _resolve_board_paths(
        board_paths=board_paths, hermes_home=hermes_home
    ):
        metadata_path = (
            database_path.parent / "board.json"
            if slug != "default"
            else database_path.parent / "kanban" / "boards" / "default" / "board.json"
        )
        metadata = _read_json_file(metadata_path) if metadata_path.is_file() else None
        if metadata is None:
            gaps.append("BOARD_METADATA_UNREADABLE")
            continue
        portable_id = canonical_project_id(
            metadata.get("aether_project_id")
            or metadata.get("portable_project_id")
            or metadata.get("project_id")
        )
        if portable_id is None or portable_id not in project_map:
            gaps.append("BOARD_PROJECT_UNBOUND")
            continue
        contract_id, version = _extract_contract_fields(metadata)
        if contract_id is None or version is None:
            gaps.append("BOARD_CONTRACT_UNBOUND")
            continue
        contract = _contract_metadata(project_map[portable_id], contract_id, version)
        if contract is None:
            gaps.append("FINAL_CONTRACT_UNREADABLE")
            continue
        expected_slug = f"oc-{portable_id.replace('-', '')}-{contract_id[3:]}-v{int(version[1:]):x}"
        if slug != expected_slug:
            gaps.append("BOARD_IDENTITY_CONFLICT")
            continue
        metadata_native = (
            metadata.get("project_id")
            or metadata.get("hermes_project_id")
            or metadata.get("native_project_id")
        )
        if (
            metadata_native is not None
            and str(metadata_native) != project_map[portable_id].hermes_project_id
        ):
            gaps.append("BOARD_NATIVE_PROJECT_CONFLICT")
            continue
        bindings.append(
            BoardBinding(
                slug=slug,
                database_path=Path(database_path).expanduser(),
                project=project_map[portable_id],
                contract_id=contract.contract_id,
                contract_version=contract.version,
                contract_title=contract.title,
                created_in_session=contract.created_in_session,
                finalized_in_session=contract.finalized_in_session,
                observation_trace_id=contract.observation_trace_id,
            )
        )
    return tuple(bindings), tuple(sorted(set(gaps)))


def _resolve_session_paths(
    *,
    session_db_paths: Sequence[Path | str] | None,
    hermes_home: Path | str | None,
) -> tuple[Path, ...]:
    if session_db_paths is not None:
        return tuple(sorted({Path(path).expanduser() for path in session_db_paths}))
    root = Path(hermes_home).expanduser() if hermes_home is not None else None
    if root is None:
        configured = os.environ.get("HERMES_HOME", "").strip()
        root = Path(configured).expanduser() if configured else None
    if root is None:
        try:
            from hermes_constants import get_hermes_home  # type: ignore[import-not-found]

            root = Path(get_hermes_home())
        except Exception:
            return ()
    candidates = [root / "state.db"]
    profiles = root / "profiles"
    if profiles.is_dir() and not profiles.is_symlink():
        candidates.extend(path for path in profiles.glob("*/state.db") if path.is_file())
    return tuple(sorted(set(candidates)))


def _session_catalog(
    paths: Sequence[Path],
) -> tuple[dict[str, SessionRecord], dict[str, int], tuple[str, ...]]:
    records: dict[str, SessionRecord] = {}
    watermarks: dict[str, int] = {}
    gaps: list[str] = []
    columns = (
        "id",
        "source",
        "title",
        "display_name",
        "cwd",
        "git_repo_root",
        "started_at",
        "ended_at",
        "last_activity_at",
    )
    for path in paths:
        try:
            with open_read_only_sqlite(path) as connection:
                rows = _select_rows(connection, "sessions", columns, required=("id",))
                message_columns = _table_columns(connection, "messages")
                if "id" not in message_columns:
                    gaps.append("SESSION_MESSAGES_SCHEMA_MISSING")
                if "id" in message_columns:
                    row = connection.execute(
                        'SELECT MAX("id") AS max_id FROM "messages"'
                    ).fetchone()
                    if row and row["max_id"] is not None:
                        watermarks[str(path)] = int(row["max_id"])
        except ReadOnlySourceError:
            gaps.append("SESSION_DB_UNREADABLE")
            continue
        for row in rows:
            session_id = _safe_ref(row.get("id"))
            if session_id is None:
                gaps.append("SESSION_ID_INVALID")
                continue
            title = _safe_text(row.get("title"), limit=240) or _safe_text(
                row.get("display_name"), limit=240
            )
            if title is None:
                title = "[untitled native session]"
                gaps.append("SESSION_TITLE_UNAVAILABLE")
            record = SessionRecord(
                session_id=session_id,
                title=title,
                source=_safe_text(row.get("source"), limit=80),
                cwd=_safe_text(row.get("cwd"), limit=1_000, allow_path=True),
                git_repo_root=_safe_text(row.get("git_repo_root"), limit=1_000, allow_path=True),
                started_at_utc=_canonical_timestamp(row.get("started_at")),
                ended_at_utc=_canonical_timestamp(row.get("ended_at")),
                last_activity_at_utc=_canonical_timestamp(row.get("last_activity_at")),
                database_path=Path(path),
            )
            existing = records.get(session_id)
            if existing is not None and existing != record:
                gaps.append("SESSION_ID_CONFLICT")
                continue
            records[session_id] = record
    return records, watermarks, tuple(sorted(set(gaps)))


def _path_belongs_to_project(value: str | None, project: ProjectBinding) -> bool:
    if not value:
        return False
    try:
        candidate = Path(value).expanduser().resolve(strict=True)
        return os.path.commonpath((str(project.path), str(candidate))) == str(project.path)
    except (OSError, ValueError):
        return False


def _path_is_project_root(value: str | None, project: ProjectBinding) -> bool:
    """Return whether a native path resolves to the registered project root."""
    if not isinstance(value, str) or not value:
        return False
    try:
        candidate = Path(value).expanduser().resolve(strict=True)
    except (OSError, ValueError):
        return False
    return candidate == project.path


def _session_belongs_to_project(session: SessionRecord, project: ProjectBinding) -> bool:
    """Validate every known native session path, not just its display title."""
    paths = [value for value in (session.cwd, session.git_repo_root) if value]
    return bool(paths) and all(_path_belongs_to_project(value, project) for value in paths)


def _cursor_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _row_changed_after(
    row: Mapping[str, Any],
    *,
    cursor: int | None,
    previous_cutoff: datetime | None,
) -> bool:
    """Select only new rows when a durable ID cursor or cutoff is available."""
    if cursor is not None:
        row_id = _cursor_int(row.get("id"))
        return row_id is None or row_id > cursor
    if previous_cutoff is None:
        return True
    timestamps = (
        _parse_timestamp(row.get("created_at")),
        _parse_timestamp(row.get("started_at")),
        _parse_timestamp(row.get("ended_at")),
        _parse_timestamp(row.get("last_heartbeat_at")),
    )
    known = tuple(value for value in timestamps if value is not None)
    # A row without a usable native timestamp is retained rather than silently
    # discarded; its bounded identity/facts still provide a visible source wake.
    return not known or any(value > previous_cutoff for value in known)


def _previous_work_items(
    values: Sequence[WorkItem] | Mapping[str, WorkItem] | None,
) -> dict[str, WorkItem]:
    if values is None:
        return {}
    iterable: Iterable[WorkItem]
    if isinstance(values, Mapping):
        iterable = values.values()
    else:
        iterable = values
    return {
        item.work_key: item
        for item in iterable
        if isinstance(item, WorkItem) and isinstance(item.work_key, str)
    }


def _retained_work_item(item: WorkItem, *, gap: str) -> SourceItem:
    contract = None
    if item.contract_id is not None:
        contract = {
            "id": item.contract_id,
            "version": item.contract_version or "",
            "title": item.contract_title or "",
        }
    ref = f"{item.work_key}:retained"
    return SourceItem(
        work_key=item.work_key,
        project_id=item.project_id,
        project_name=item.project_name or "[unavailable project name]",
        origin_session_id=item.origin_session_id,
        origin_session_title=item.origin_session_title,
        contract=contract,
        observed_state=item.observed_state,
        state_evidence_refs=(ref,),
        started_at_utc=item.started_at_utc,
        ended_at_utc=item.ended_at_utc,
        current=(_code_fact(ref, "SOURCE_ITEM_RETAINED", status="unknown"),),
        coverage_gaps=(gap,),
        source_cursor=item.source_cursor if isinstance(item.source_cursor, Mapping) else {},
        active=item.active,
    )


def _fact(
    ref: str, text: str, *, provenance: str = "observed", status: str = "verified"
) -> dict[str, Any] | None:
    clean = _safe_text(text, limit=MAX_SOURCE_EXCERPT_CHARS)
    safe_ref = _safe_ref(ref)
    if (
        clean is None
        or safe_ref is None
        or provenance not in {"observed", "reported"}
        or status
        not in {
            "verified",
            "unverified",
            "unknown",
        }
    ):
        return None
    return {
        "ref": safe_ref,
        "text": clean[:MAX_PROSE_CHARS],
        "provenance": provenance,
        "status": status,
    }


def _code_fact(ref: str, code: str, *, status: str = "verified") -> dict[str, Any]:
    return {
        "ref": ref,
        "text": code,
        "provenance": "observed",
        "status": status,
    }


def _event_texts(row: Mapping[str, Any], ref_prefix: str) -> tuple[dict[str, Any], ...]:
    """Select only bounded event diagnostics and summaries."""
    kind = _safe_text(row.get("kind"), limit=80)
    event_id = _safe_ref(str(row.get("id"))) if row.get("id") is not None else None
    if kind is None or event_id is None:
        return ()
    result: list[dict[str, Any]] = []
    if kind in {
        "protocol_violation",
        "stale",
        "failed",
        "blocked",
        "changes_requested",
        "review_requested",
    }:
        result.append(_code_fact(f"{ref_prefix}:event:{event_id}", f"NATIVE_EVENT_{kind.upper()}"))
    payload = row.get("payload")
    if isinstance(payload, str) and payload:
        try:
            decoded = json.loads(payload)
        except (TypeError, ValueError):
            decoded = None
        if isinstance(decoded, Mapping):
            for field_name in ("summary", "message", "diagnostic", "code", "error_class"):
                candidate = decoded.get(field_name)
                if field_name == "error_class":
                    safe_candidate = _safe_text(candidate, limit=100)
                    if safe_candidate is not None and re.fullmatch(
                        r"[A-Za-z][A-Za-z0-9_.-]{1,100}", safe_candidate
                    ):
                        result.append(
                            _code_fact(
                                f"{ref_prefix}:event:{event_id}:{field_name}",
                                safe_candidate,
                                status="unknown",
                            )
                        )
                elif isinstance(candidate, str):
                    fact = _fact(
                        f"{ref_prefix}:event:{event_id}:{field_name}",
                        candidate,
                        provenance="reported",
                        status="unverified",
                    )
                    if fact is not None:
                        result.append(fact)
    return tuple(result)


def _run_facts(row: Mapping[str, Any], ref_prefix: str) -> tuple[dict[str, Any], ...]:
    run_id = row.get("id")
    ref = _safe_ref(str(run_id)) if run_id is not None else None
    if ref is None:
        return ()
    result: list[dict[str, Any]] = []
    outcome = _safe_text(row.get("outcome"), limit=80)
    status = _safe_text(row.get("status"), limit=80)
    if outcome in {"completed", "success", "succeeded"}:
        result.append(_code_fact(f"{ref_prefix}:run:{ref}", "RUN_COMPLETED"))
    elif outcome in _FAILURE_STATES or status in _FAILURE_STATES:
        failure = outcome if outcome in _FAILURE_STATES else status
        if failure is not None:
            result.append(_code_fact(f"{ref_prefix}:run:{ref}", f"RUN_{failure.upper()}"))
    summary = row.get("summary")
    if isinstance(summary, str):
        fact = _fact(
            f"{ref_prefix}:run:{ref}:summary", summary, provenance="reported", status="unverified"
        )
        if fact is not None:
            result.append(fact)
    return tuple(result)


def _state_from_tasks(tasks: Sequence[Mapping[str, Any]]) -> str:
    statuses = [_safe_text(task.get("status"), limit=80) or "unknown" for task in tasks]
    terminal_tasks = [task for task in tasks if bool(task.get("terminal_affinity"))]
    if terminal_tasks and all(
        (_safe_text(task.get("status"), limit=80) or "unknown") in _TERMINAL_STATES
        for task in terminal_tasks
    ):
        if any(
            (_safe_text(task.get("status"), limit=80) or "unknown") in _FAILURE_STATES
            for task in terminal_tasks
        ):
            return "failed"
        if all(
            (_safe_text(task.get("status"), limit=80) or "unknown") in {"done", "completed"}
            for task in terminal_tasks
        ):
            if all(status in _TERMINAL_STATES for status in statuses):
                return "completed"
    if any(status in {"blocked", "triage"} for status in statuses):
        return "blocked" if "blocked" in statuses else "triage"
    if any(status in {"review", "changes_requested"} for status in statuses):
        return "review"
    if any(status in {"running"} for status in statuses):
        return "running"
    if any(status in {"todo", "ready", "scheduled", "queued"} for status in statuses):
        return "queued"
    if statuses and all(status in _TERMINAL_STATES for status in statuses):
        if not terminal_tasks:
            return "waiting"
        return (
            "completed" if not any(status in _FAILURE_STATES for status in statuses) else "failed"
        )
    return "unknown"


class ReadOnlySources:
    """Enumerate and normalize registered project work using only read handles."""

    def __init__(
        self,
        *,
        registry: ProjectRegistry | None = None,
        state_root: Path | str | None = None,
        native_projects_path: Path | str | None = None,
        board_paths: Sequence[Path | str | tuple[str, Path | str]] | None = None,
        session_db_paths: Sequence[Path | str] | None = None,
        hermes_home: Path | str | None = None,
        observation_summary_paths: Mapping[str, Path | str] | None = None,
        clock: Any | None = None,
    ) -> None:
        self.registry = registry or ProjectRegistry(state_root)
        self.native_projects_path = native_projects_path
        self.board_paths = board_paths
        self.session_db_paths = session_db_paths
        self.hermes_home = hermes_home
        self.observation_summary_paths = {
            str(key): Path(value).expanduser()
            for key, value in (observation_summary_paths or {}).items()
        }
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def _read_tasks(
        self,
        board: BoardBinding,
        *,
        previous_cutoff: datetime | None = None,
        previous_watermark: Mapping[str, Any] | None = None,
    ) -> tuple[tuple[_TaskRow, ...], tuple[str, ...], int, int]:
        gaps: list[str] = []
        previous_watermark = previous_watermark or {}
        previous_run_id = _cursor_int(previous_watermark.get("task_run_id"))
        previous_event_id = _cursor_int(previous_watermark.get("task_event_id"))
        try:
            with open_read_only_sqlite(board.database_path) as connection:
                task_columns = (
                    "id",
                    "title",
                    "status",
                    "project_id",
                    "session_id",
                    "created_at",
                    "started_at",
                    "completed_at",
                    "workspace_path",
                    "current_run_id",
                    "session_affinity",
                    "block_kind",
                    "last_heartbeat_at",
                    "max_runtime_seconds",
                    "result",
                    "consecutive_failures",
                )
                tasks = _select_rows(
                    connection,
                    "tasks",
                    task_columns,
                    required=("id", "title", "status", "project_id"),
                    order_by=("id",),
                )
                tasks = tuple(
                    row for row in tasks if _safe_text(row.get("status"), limit=80) != "archived"
                )
                task_ids = set()
                for row in tasks:
                    if _native_task_ref(row.get("id")) is None:
                        gaps.append("TASK_ID_INVALID")
                        continue
                    task_ids.add(str(row.get("id")))
                tasks = tuple(row for row in tasks if str(row.get("id")) in task_ids)
                links: dict[str, list[str]] = {task_id: [] for task_id in task_ids}
                link_columns = _table_columns(connection, "task_links")
                if not link_columns:
                    gaps.append("BOARD_LINKS_SCHEMA_MISSING")
                if link_columns:
                    for row in _select_rows(
                        connection,
                        "task_links",
                        ("parent_id", "child_id"),
                        required=("parent_id", "child_id"),
                        order_by=("parent_id", "child_id"),
                    ):
                        parent, child = str(row.get("parent_id")), str(row.get("child_id"))
                        if child in links and parent in task_ids:
                            links[child].append(parent)
                runs_by_task: dict[str, list[Mapping[str, Any]]] = {
                    task_id: [] for task_id in task_ids
                }
                worker_sessions_by_task: dict[str, set[str]] = {
                    task_id: set() for task_id in task_ids
                }
                max_run_id = 0
                run_columns = _table_columns(connection, "task_runs")
                if not run_columns:
                    gaps.append("BOARD_RUNS_SCHEMA_MISSING")
                if run_columns:
                    run_rows = _select_rows(
                        connection,
                        "task_runs",
                        (
                            "id",
                            "task_id",
                            "status",
                            "outcome",
                            "started_at",
                            "ended_at",
                            "last_heartbeat_at",
                            "summary",
                            "error",
                            "profile",
                            "session_id",
                            "worker_session_id",
                            "workspace_path",
                        ),
                        required=("id", "task_id"),
                        order_by=("task_id", "started_at", "id"),
                    )
                    for row in run_rows:
                        run_id = _cursor_int(row.get("id"))
                        if run_id is not None:
                            max_run_id = max(max_run_id, run_id)
                        task_id = str(row.get("task_id"))
                        if task_id in worker_sessions_by_task:
                            for field_name in ("session_id", "worker_session_id"):
                                worker_session = _safe_ref(row.get(field_name))
                                if worker_session is not None:
                                    worker_sessions_by_task[task_id].add(worker_session)
                        if not _row_changed_after(
                            row, cursor=previous_run_id, previous_cutoff=previous_cutoff
                        ):
                            continue
                        if task_id in runs_by_task:
                            runs_by_task[task_id].append(row)
                events_by_task: dict[str, list[Mapping[str, Any]]] = {
                    task_id: [] for task_id in task_ids
                }
                event_columns = _table_columns(connection, "task_events")
                if not event_columns:
                    gaps.append("BOARD_EVENTS_SCHEMA_MISSING")
                max_event_id = 0
                if event_columns:
                    event_rows = _select_rows(
                        connection,
                        "task_events",
                        ("id", "task_id", "run_id", "kind", "payload", "created_at"),
                        required=("id", "task_id", "kind"),
                        order_by=("id",),
                    )
                    for row in event_rows:
                        task_id = str(row.get("task_id"))
                        try:
                            event_id_value = row.get("id")
                            if event_id_value is not None:
                                max_event_id = max(max_event_id, int(event_id_value))
                        except (TypeError, ValueError):
                            pass
                        if not _row_changed_after(
                            row, cursor=previous_event_id, previous_cutoff=previous_cutoff
                        ):
                            continue
                        if task_id in events_by_task:
                            events_by_task[task_id].append(row)

                affinity_columns = _table_columns(connection, "kanban_session_affinity")
                affinity_task_column = (
                    "owner_task_id"
                    if "owner_task_id" in affinity_columns
                    else "task_id"
                    if "task_id" in affinity_columns
                    else None
                )
                if affinity_task_column is not None and "session_id" in affinity_columns:
                    for row in _select_rows(
                        connection,
                        "kanban_session_affinity",
                        (affinity_task_column, "session_id"),
                        required=(affinity_task_column, "session_id"),
                        order_by=(affinity_task_column, "session_id"),
                    ):
                        task_id = str(row.get(affinity_task_column))
                        worker_session = _safe_ref(row.get("session_id"))
                        if task_id in worker_sessions_by_task and worker_session is not None:
                            worker_sessions_by_task[task_id].add(worker_session)
        except ReadOnlySourceError:
            return (), ("BOARD_DB_UNREADABLE",), 0, 0
        if not tasks:
            return (), tuple(gaps), max_event_id, max_run_id
        result: list[_TaskRow] = []
        for row in tasks:
            project_id = str(row.get("project_id"))
            if project_id not in {board.project.hermes_project_id, board.project.project_id}:
                gaps.append("TASK_PROJECT_CONFLICT")
                continue
            candidate_id = _safe_ref(str(row.get("id")))
            if candidate_id is None:
                gaps.append("TASK_ID_INVALID")
                continue
            affinity = row.get("session_affinity")
            terminal = False
            worker_session_ids = set(worker_sessions_by_task.get(candidate_id, set()))
            if isinstance(affinity, str) and affinity:
                try:
                    parsed_affinity = json.loads(affinity)
                    if isinstance(parsed_affinity, Mapping):
                        terminal = parsed_affinity.get("terminal") is True
                        for field_name in ("session_id", "worker_session_id"):
                            worker_session = _safe_ref(parsed_affinity.get(field_name))
                            if worker_session is not None:
                                worker_session_ids.add(worker_session)
                        raw_sessions = parsed_affinity.get("session_ids")
                        if isinstance(raw_sessions, Sequence) and not isinstance(
                            raw_sessions, (str, bytes)
                        ):
                            for raw_session in raw_sessions:
                                worker_session = _safe_ref(raw_session)
                                if worker_session is not None:
                                    worker_session_ids.add(worker_session)
                except (TypeError, ValueError):
                    gaps.append("TASK_AFFINITY_INVALID")
            normalized = dict(row)
            normalized["terminal_affinity"] = terminal
            result.append(
                _TaskRow(
                    values=normalized,
                    board=board,
                    parent_ids=tuple(sorted(links.get(candidate_id, []))),
                    runs=tuple(runs_by_task.get(candidate_id, [])),
                    events=tuple(events_by_task.get(candidate_id, [])),
                    worker_session_ids=tuple(sorted(worker_session_ids)),
                )
            )
        return tuple(result), tuple(sorted(set(gaps))), max_event_id, max_run_id

    def _observation_facts(
        self, board: BoardBinding
    ) -> tuple[tuple[Mapping[str, Any], ...], tuple[str, ...]]:
        """Read one explicitly bound immutable observation summary, if supplied."""
        raw_root = self.observation_summary_paths.get(board.project.project_id)
        if raw_root is None:
            return (), ()
        if raw_root.is_symlink() or not raw_root.exists():
            return (), ("OBSERVATION_SUMMARY_UNREADABLE",)
        candidates = (
            (raw_root,)
            if raw_root.is_file()
            else tuple(
                sorted(
                    path
                    for path in raw_root.glob("*.json")
                    if path.is_file() and not path.is_symlink()
                )
            )
        )
        facts: list[Mapping[str, Any]] = []
        gaps: list[str] = []
        expected_trace = board.observation_trace_id
        for path in candidates:
            summary = _read_json_file(path)
            if summary is None:
                gaps.append("OBSERVATION_SUMMARY_UNREADABLE")
                continue
            trace_id = summary.get("trace_id")
            if expected_trace is not None and trace_id != expected_trace:
                continue
            if not isinstance(trace_id, str) or _safe_ref(trace_id) is None:
                gaps.append("OBSERVATION_TRACE_INVALID")
                continue
            prefix = f"observation:{board.slug}:{trace_id}"
            completion = summary.get("completion_state")
            if isinstance(completion, str) and re.fullmatch(r"[a-z][a-z0-9_]{1,63}", completion):
                facts.append(
                    _code_fact(f"{prefix}:completion", f"OBS_COMPLETION_{completion.upper()}")
                )
            brief = summary.get("review_brief")
            if isinstance(brief, Mapping):
                verdict = brief.get("verdict")
                if isinstance(verdict, str) and re.fullmatch(r"[a-z][a-z0-9_]{1,63}", verdict):
                    facts.append(_code_fact(f"{prefix}:verdict", f"OBS_VERDICT_{verdict.upper()}"))
            runtime = summary.get("runtime_state")
            if isinstance(runtime, Mapping):
                for field_name in ("activity", "progress", "termination", "waiting"):
                    value = runtime.get(field_name)
                    if isinstance(value, str) and re.fullmatch(r"[a-z][a-z0-9_]{1,63}", value):
                        facts.append(
                            _code_fact(
                                f"{prefix}:runtime:{field_name}",
                                f"OBS_{field_name.upper()}_{value.upper()}",
                            )
                        )
            coverage = summary.get("coverage")
            if isinstance(coverage, Mapping):
                raw_gaps = coverage.get("gaps")
                if isinstance(raw_gaps, Sequence) and not isinstance(raw_gaps, (str, bytes)):
                    for gap in raw_gaps:
                        if isinstance(gap, Mapping):
                            code = gap.get("class") or gap.get("code")
                        else:
                            code = gap
                        if isinstance(code, str) and re.fullmatch(
                            r"[A-Za-z][A-Za-z0-9_.-]{1,63}", code
                        ):
                            facts.append(
                                _code_fact(
                                    f"{prefix}:coverage:{code}",
                                    f"OBS_COVERAGE_{code.upper().replace('-', '_').replace('.', '_')}",
                                    status="unknown",
                                )
                            )
        unique: dict[tuple[str, str], Mapping[str, Any]] = {}
        for fact in facts:
            unique[(str(fact.get("ref")), str(fact.get("text")))] = fact
        return tuple(unique[key] for key in sorted(unique)), tuple(sorted(set(gaps)))

    def _task_items(
        self,
        board: BoardBinding,
        tasks: Sequence[_TaskRow],
        sessions: Mapping[str, SessionRecord],
        *,
        cutoff: datetime,
        first_enabled: datetime | None = None,
        board_cursor: Mapping[str, Any] | None = None,
        observation_facts: Sequence[Mapping[str, Any]] = (),
    ) -> tuple[tuple[SourceItem, ...], tuple[str, ...]]:
        gaps: list[str] = []
        groups: dict[str, list[_TaskRow]] = {}
        origin_session_id = _safe_ref(board.created_in_session)
        origin_session = sessions.get(origin_session_id or "")
        if origin_session_id is None or origin_session is None:
            return (), ("CONTRACT_ORIGIN_SESSION_MISSING",)
        if origin_session.is_reporter:
            return (), ("CONTRACT_ORIGIN_SESSION_CONFLICT",)
        if not _session_belongs_to_project(origin_session, board.project):
            return (), ("CONTRACT_ORIGIN_PROJECT_CONFLICT",)
        for task in tasks:
            raw_session = task.values.get("session_id")
            session_id = _safe_ref(raw_session)
            if session_id is None:
                gaps.append("TASK_CREATOR_UNRESOLVED")
                continue
            creator = sessions.get(session_id)
            if creator is None:
                gaps.append("TASK_CREATOR_SESSION_MISSING")
                continue
            if creator.is_reporter:
                continue
            if not _session_belongs_to_project(creator, board.project):
                gaps.append("TASK_CREATOR_PROJECT_CONFLICT")
                continue
            workspace_path = task.values.get("workspace_path")
            if workspace_path is not None and not _path_belongs_to_project(
                workspace_path if isinstance(workspace_path, str) else None,
                board.project,
            ):
                gaps.append("TASK_WORKSPACE_PROJECT_CONFLICT")
                continue
            invalid_worker = False
            for worker_session_id in task.worker_session_ids:
                worker = sessions.get(worker_session_id)
                if worker is None:
                    gaps.append("WORKER_SESSION_MISSING")
                    invalid_worker = True
                    continue
                if worker.is_reporter or not _session_belongs_to_project(worker, board.project):
                    gaps.append("WORKER_SESSION_PROJECT_CONFLICT")
                    invalid_worker = True
            if invalid_worker:
                continue
            # The board task's session is creator context.  The finalized contract's
            # authored session is the stable report identity; worker/affinity sessions
            # above are independently validated evidence only.
            groups.setdefault(origin_session_id, []).append(task)
        items: list[SourceItem] = []
        for session_id, group in sorted(groups.items()):
            session = origin_session
            work_key = f"pipeline:{board.project.project_id}:{board.contract_id}:{session_id}"
            state = _state_from_tasks([task.values for task in group])
            if first_enabled is not None and state in _TERMINAL_STATES:
                terminal_times: list[datetime] = []
                for task in group:
                    task_time = _parse_timestamp(task.values.get("completed_at"))
                    if task_time is None:
                        run_times = [
                            value
                            for value in (
                                _parse_timestamp(run.get("ended_at")) for run in task.runs
                            )
                            if value is not None
                        ]
                        task_time = max(run_times) if run_times else None
                    if task_time is not None:
                        terminal_times.append(task_time)
                if len(terminal_times) == len(group) and max(terminal_times) <= first_enabled:
                    continue
            evidence_refs: set[str] = set()
            started_values: list[datetime] = []
            ended_values: list[datetime] = []
            resolved: list[dict[str, Any]] = []
            current: list[dict[str, Any]] = []
            next_facts: list[dict[str, Any]] = []
            complications: list[dict[str, Any]] = []
            pending: list[dict[str, Any]] = []
            current.extend(dict(fact) for fact in observation_facts)
            item_gaps: list[str] = []
            cursor = dict(board_cursor or {})
            max_event = _cursor_int(cursor.get("task_event_id")) or 0
            for task in sorted(group, key=lambda value: str(value.values.get("id"))):
                task_id = _safe_ref(str(task.values.get("id")))
                if task_id is None:
                    continue
                prefix = f"board:{board.slug}:task:{task_id}"
                evidence_refs.add(prefix)
                title = _safe_text(task.values.get("title"), limit=MAX_PROSE_CHARS)
                if title is None:
                    item_gaps.append("TASK_TITLE_UNSAFE")
                else:
                    fact = _fact(f"{prefix}:title", title)
                    if fact is not None:
                        current.append(fact)
                task_started = _parse_timestamp(task.values.get("started_at")) or _parse_timestamp(
                    task.values.get("created_at")
                )
                task_ended = _parse_timestamp(task.values.get("completed_at"))
                if task_started is not None:
                    started_values.append(task_started)
                if task_ended is not None:
                    ended_values.append(task_ended)
                task_status = _safe_text(task.values.get("status"), limit=80) or "unknown"
                current.append(_code_fact(f"{prefix}:state", f"TASK_STATE_{task_status.upper()}"))
                task_result = task.values.get("result")
                if isinstance(task_result, str):
                    result_fact = _fact(
                        f"{prefix}:result",
                        task_result,
                        provenance="reported",
                        status="unverified",
                    )
                    if result_fact is not None:
                        (resolved if task_status in _TERMINAL_STATES else current).append(
                            result_fact
                        )
                    else:
                        item_gaps.append("TASK_RESULT_UNSAFE")
                if task_status in _PENDING_STATES:
                    pending.append(
                        _code_fact(f"{prefix}:pending", f"TASK_PENDING_{task_status.upper()}")
                    )
                if task_status in {"review", "changes_requested"}:
                    next_facts.append(_code_fact(f"{prefix}:next", "REVIEW_GATE"))
                if task_status in _FAILURE_STATES:
                    complications.append(
                        _code_fact(
                            f"{prefix}:failure",
                            f"TASK_FAILURE_{task_status.upper()}",
                            status="unknown",
                        )
                    )
                heartbeat = _parse_timestamp(task.values.get("last_heartbeat_at"))
                max_runtime = task.values.get("max_runtime_seconds")
                if (
                    task_status == "running"
                    and heartbeat is not None
                    and isinstance(max_runtime, (int, float))
                ):
                    if (cutoff - heartbeat).total_seconds() > max(float(max_runtime), 1.0):
                        complications.append(
                            _code_fact(f"{prefix}:stale", "TASK_STALE", status="unknown")
                        )
                        item_gaps.append("TASK_STALE")
                for run in task.runs:
                    run_id = _safe_ref(str(run.get("id")))
                    if run_id is not None:
                        evidence_refs.add(f"{prefix}:run:{run_id}")
                    run_started = _parse_timestamp(run.get("started_at"))
                    run_ended = _parse_timestamp(run.get("ended_at"))
                    if run_started is not None:
                        started_values.append(run_started)
                    if run_ended is not None:
                        ended_values.append(run_ended)
                    run_facts = _run_facts(run, prefix)
                    for fact in run_facts:
                        if fact["text"] == "RUN_COMPLETED":
                            resolved.append(fact)
                        elif (
                            str(fact["text"]).startswith("RUN_") and fact["text"] != "RUN_COMPLETED"
                        ):
                            complications.append(fact)
                        else:
                            current.append(fact)
                for event in task.events:
                    try:
                        event_id_value = event.get("id")
                        if event_id_value is not None:
                            max_event = max(max_event, int(event_id_value))
                    except (TypeError, ValueError):
                        pass
                    facts = _event_texts(event, prefix)
                    for fact in facts:
                        if str(fact["text"]).startswith("NATIVE_EVENT_"):
                            complications.append(fact)
                        else:
                            current.append(fact)
            if state == "completed":
                resolved.append(_code_fact(f"{work_key}:closure", "FLOW_TERMINAL_CONFIRMED"))
                current = [fact for fact in current if fact.get("text") != "TASK_STATE_DONE"]
            elif state in {"blocked", "triage", "review", "queued", "running"}:
                next_facts.append(
                    _code_fact(f"{work_key}:next", "AWAIT_SOURCE_CHANGE", status="unknown")
                )

            # All facts are deterministic and duplicate-free by reference/text.
            def unique(values: Iterable[Mapping[str, Any]]) -> tuple[Mapping[str, Any], ...]:
                seen: set[tuple[str, str]] = set()
                result: list[Mapping[str, Any]] = []
                for value in sorted(
                    values, key=lambda item: (str(item.get("ref")), str(item.get("text")))
                ):
                    key = (str(value.get("ref")), str(value.get("text")))
                    if key not in seen:
                        seen.add(key)
                        result.append(dict(value))
                return tuple(result)

            if state == "waiting":
                item_gaps.append("TERMINAL_CLOSURE_UNRESOLVED")
            item_gaps = sorted(set(item_gaps))
            gaps.extend(item_gaps)
            items.append(
                SourceItem(
                    work_key=work_key,
                    project_id=board.project.project_id,
                    project_name=board.project.name,
                    origin_session_id=session.session_id,
                    origin_session_title=session.title,
                    contract={
                        "id": board.contract_id,
                        "version": board.contract_version,
                        "title": board.contract_title,
                    },
                    observed_state=state,
                    state_evidence_refs=tuple(sorted(evidence_refs)),
                    started_at_utc=min(started_values).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                    if started_values
                    else session.started_at_utc,
                    ended_at_utc=max(ended_values).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                    if ended_values and state in _TERMINAL_STATES
                    else None,
                    resolved=unique(resolved),
                    current=unique(current),
                    next=unique(next_facts),
                    complications=unique(complications),
                    pending=unique(pending),
                    coverage_gaps=tuple(item_gaps),
                    source_cursor={
                        "board": board.slug,
                        "task_event_id": max_event,
                        "task_run_id": _cursor_int(cursor.get("task_run_id")) or 0,
                    },
                    active=state not in _TERMINAL_STATES,
                )
            )
        return tuple(sorted(items, key=lambda item: item.work_key)), tuple(sorted(set(gaps)))

    def _direct_items(
        self,
        records: Sequence[Mapping[str, Any]],
        projects: Mapping[str, ProjectBinding],
        sessions: Mapping[str, SessionRecord],
        *,
        previous_cutoff: datetime | None = None,
        first_enabled: datetime | None = None,
    ) -> tuple[tuple[SourceItem, ...], tuple[str, ...]]:
        items: list[SourceItem] = []
        gaps: list[str] = []
        for record in records:
            project_id = canonical_project_id(record.get("project_id"))
            session_id = _safe_ref(record.get("session_id"))
            interval_id = _safe_ref(record.get("interval_id") or record.get("turn_id"))
            if (
                project_id is None
                or project_id not in projects
                or session_id is None
                or interval_id is None
            ):
                gaps.append("DIRECT_BINDING_INVALID")
                continue
            session = sessions.get(session_id)
            if session is None or session.is_reporter:
                if session is None:
                    gaps.append("DIRECT_SESSION_MISSING")
                continue
            binding = projects[project_id]
            native_id = _safe_ref(record.get("native_project_id"))
            project_path = record.get("project_path")
            alternate_project_path = record.get("native_project_path")
            if (
                native_id is None
                or native_id != binding.hermes_project_id
                or (alternate_project_path is not None and alternate_project_path != project_path)
            ):
                gaps.append("DIRECT_NATIVE_PROJECT_CONFLICT")
                continue
            if not isinstance(project_path, str):
                gaps.append("DIRECT_PROJECT_PATH_MISSING")
                continue
            if not _path_is_project_root(project_path, binding):
                gaps.append("DIRECT_PROJECT_PATH_CONFLICT")
                continue
            if not _session_belongs_to_project(session, binding):
                gaps.append("DIRECT_SESSION_PROJECT_CONFLICT")
                continue
            started = _canonical_timestamp(record.get("started_at")) or session.started_at_utc
            ended = _canonical_timestamp(record.get("ended_at")) or session.ended_at_utc
            ended_dt = _parse_timestamp(ended) if ended is not None else None
            if ended_dt is not None and (
                (first_enabled is not None and ended_dt <= first_enabled)
                or (previous_cutoff is not None and ended_dt <= previous_cutoff)
            ):
                continue
            if project_path is not None and not _path_belongs_to_project(project_path, binding):
                gaps.append("DIRECT_NATIVE_PROJECT_CONFLICT")
                continue
            outcome = _safe_text(record.get("outcome"), limit=80) or "unknown"
            outcome = outcome.lower()
            if outcome not in {"completed", "failed", "interrupted", "unknown"}:
                outcome = "unknown"
                gaps.append("DIRECT_OUTCOME_UNKNOWN")
            state = f"turn_ended_{outcome}"
            work_key = f"direct:{project_id}:{session_id}:{interval_id}"
            ref = f"direct:{project_id}:{session_id}:{interval_id}"
            facts = [_code_fact(f"{ref}:turn", f"TURN_ENDED_{outcome.upper()}")]
            summary = record.get("summary") or record.get("reported_outcome")
            if isinstance(summary, str):
                fact = _fact(f"{ref}:outcome", summary, provenance="reported", status="unverified")
                if fact is not None:
                    facts.append(fact)
            item_gaps: list[str] = []
            if outcome == "unknown":
                item_gaps.append("DIRECT_OUTCOME_UNKNOWN")
            items.append(
                SourceItem(
                    work_key=work_key,
                    project_id=project_id,
                    project_name=binding.name,
                    origin_session_id=session_id,
                    origin_session_title=session.title,
                    contract=None,
                    observed_state=state,
                    state_evidence_refs=(ref,),
                    started_at_utc=started,
                    ended_at_utc=ended,
                    resolved=(),
                    current=tuple(facts),
                    next=(
                        _code_fact(
                            f"{ref}:next", "PROJECT_ACCEPTANCE_NOT_OBSERVED", status="unknown"
                        ),
                    ),
                    complications=(),
                    pending=(
                        _code_fact(
                            f"{ref}:pending", "TURN_ENDED_NOT_PROJECT_ACCEPTED", status="unknown"
                        ),
                    ),
                    coverage_gaps=tuple(item_gaps),
                    source_cursor={"direct_session": session_id, "interval": interval_id},
                    active=False,
                )
            )
        return tuple(sorted(items, key=lambda item: item.work_key)), tuple(sorted(set(gaps)))

    def collect(
        self,
        *,
        previous_cutoff_utc: str | None = None,
        cutoff_utc: str | None = None,
        direct_records: Sequence[Mapping[str, Any]] = (),
        first_enabled_at_utc: str | None = None,
        previous_watermarks: Mapping[str, Any] | None = None,
        previous_work_items: Sequence[WorkItem] | Mapping[str, WorkItem] | None = None,
    ) -> SourceCollection:
        """Read one bounded source cut.  No source database is ever written."""
        cutoff = _parse_timestamp(cutoff_utc) if cutoff_utc is not None else self.clock()
        if cutoff is None or cutoff.tzinfo is None:
            raise ValueError("cutoff_utc must be timezone-aware")
        previous_cutoff = (
            _parse_timestamp(previous_cutoff_utc) if previous_cutoff_utc is not None else None
        )
        if previous_cutoff is not None and previous_cutoff >= cutoff:
            raise ValueError("previous cutoff must precede the snapshot cutoff")
        first_enabled = (
            _parse_timestamp(first_enabled_at_utc) if first_enabled_at_utc is not None else None
        )
        prior_items = _previous_work_items(previous_work_items)
        prior_watermarks = previous_watermarks or {}
        projects, project_gaps = enumerate_project_bindings(
            self.registry,
            native_projects_path=self.native_projects_path,
            hermes_home=self.hermes_home,
        )
        boards, board_gaps = _read_board_bindings(
            projects,
            board_paths=self.board_paths,
            hermes_home=self.hermes_home,
        )
        sessions, session_watermarks, session_gaps = _session_catalog(
            _resolve_session_paths(
                session_db_paths=self.session_db_paths, hermes_home=self.hermes_home
            )
        )
        all_items: list[SourceItem] = []
        gaps: list[str] = [*project_gaps, *board_gaps, *session_gaps]
        watermarks: dict[str, Any] = {"sessions": dict(sorted(session_watermarks.items()))}
        for board in boards:
            observation_facts, observation_gaps = self._observation_facts(board)
            gaps.extend(observation_gaps)
            raw_board_watermark = prior_watermarks.get(f"board:{board.slug}")
            if raw_board_watermark is not None and not isinstance(raw_board_watermark, Mapping):
                gaps.append("BOARD_WATERMARK_INVALID")
                raw_board_watermark = None
            task_rows, task_gaps, max_event, max_run = self._read_tasks(
                board,
                previous_cutoff=previous_cutoff,
                previous_watermark=raw_board_watermark,
            )
            board_cursor = {
                "board": board.slug,
                "task_event_id": max_event,
                "task_run_id": max_run,
            }
            items, item_gaps = self._task_items(
                board,
                task_rows,
                sessions,
                cutoff=cutoff,
                first_enabled=first_enabled,
                board_cursor=board_cursor,
                observation_facts=observation_facts,
            )
            all_items.extend(items)
            gaps.extend(task_gaps)
            gaps.extend(item_gaps)
            watermarks[f"board:{board.slug}"] = {
                "task_event_id": max_event,
                "task_run_id": max_run,
                "project_id": board.project.project_id,
                "contract_id": board.contract_id,
                "contract_version": board.contract_version,
            }
        direct_items, direct_gaps = self._direct_items(
            direct_records,
            {p.project_id: p for p in projects},
            sessions,
            previous_cutoff=previous_cutoff,
            first_enabled=first_enabled,
        )
        all_items.extend(direct_items)
        gaps.extend(direct_gaps)
        direct_watermark = prior_watermarks.get("direct")
        if not isinstance(direct_watermark, Mapping):
            direct_watermark = {}
        observed_direct_times: list[datetime] = [
            value
            for value in (
                _parse_timestamp(item.ended_at_utc or item.started_at_utc)
                for item in direct_items
                if item.ended_at_utc is not None or item.started_at_utc is not None
            )
            if value is not None
        ]
        latest_direct = (
            max(observed_direct_times).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            if observed_direct_times
            else direct_watermark.get("last_observed_at_utc")
        )
        watermarks["direct"] = {
            "last_observed_at_utc": latest_direct if isinstance(latest_direct, str) else None
        }
        deduped: dict[str, SourceItem] = {}
        for item in all_items:
            previous = prior_items.get(item.work_key)
            if item.terminal and previous is not None:
                if previous.final_outcome_delivery_marker is not None:
                    continue
            existing = deduped.get(item.work_key)
            if existing is not None and existing != item:
                gaps.append("WORK_IDENTITY_CONFLICT")
                continue
            deduped[item.work_key] = item
        # A final or active identity must not disappear merely because a source
        # stopped exposing its row between cuts.  A confirmed final is the only
        # durable suppression point; otherwise retain the identity with a visible
        # gap until the next source read or delivery confirmation.
        for work_key, previous in sorted(prior_items.items()):
            if work_key in deduped or previous.final_outcome_delivery_marker is not None:
                continue
            retained = _retained_work_item(previous, gap="SOURCE_ITEM_NOT_OBSERVED")
            deduped[work_key] = retained
            gaps.append("SOURCE_ITEM_NOT_OBSERVED")
        return SourceCollection(
            items=tuple(sorted(deduped.values(), key=lambda item: item.work_key)),
            watermarks=watermarks,
            coverage_gaps=tuple(sorted(set(gaps))),
        )


# Local aliases make the boundary discoverable without adding another implementation.
MonitorSources = ReadOnlySources
SourceAdapter = ReadOnlySources
