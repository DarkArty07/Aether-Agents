"""Read-side query library shared by ``aether observe`` (OBS-D-010, section 13.1).

Must work with the Hermes service stopped, and must never import Hermes: every module
imported here is either stdlib or another Hermes-independent Aether module. Reduction
is owned by :mod:`aether_agents.observation.reduce.ingest` and the derived SQLite
projection by :mod:`aether_agents.observation.storage`.  Both are imported lazily
inside the functions that need them, preserving the manager/Hermes import boundary.
"""

from __future__ import annotations

import json
import re
import time
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator

from aether_agents.observation.privacy import safe_error_class
from aether_agents.paths import ObservationPaths, UnsafeObservationPath, read_private_bytes

__all__ = [
    "ObservationQueryError",
    "ProjectResolution",
    "ProjectResolutionError",
    "NoOpenTraceError",
    "TraceAmbiguousError",
    "TraceNotFoundError",
    "StateUnreadableError",
    "SummaryNotFoundError",
    "load_previous_summary",
    "load_summary",
    "resolve_project",
    "resolve_trace",
    "watch",
]


# ------------------------------------------------------------------------------------
# Bounded errors. Messages never echo captured observation content or a raw filesystem
# path back to the caller (section 8.3 / OBS_BRIEF invariant 1); they describe the
# bounded reason only.
# ------------------------------------------------------------------------------------


class ObservationQueryError(Exception):
    """Base for every bounded query error `aether observe` can present to a caller."""


class ProjectResolutionError(ObservationQueryError):
    """The canonical project UUID could not be resolved exactly (OBS-FR-077)."""


class NoOpenTraceError(ObservationQueryError):
    """Zero (open) traces: an empty-state report, not a failure (section 13.1)."""


class TraceNotFoundError(ObservationQueryError):
    """REF was supplied but resolves to no trace."""


class TraceAmbiguousError(ObservationQueryError):
    """REF (or its absence) resolves to more than one trace; never guessed."""

    def __init__(self, message: str, *, candidates: tuple[str, ...] = ()) -> None:
        super().__init__(message)
        self.candidates = candidates


class StateUnreadableError(ObservationQueryError):
    """Local observation state exists but could not be read (I/O failure, missing
    reduction modules, or an unexpected internal error)."""


class SummaryNotFoundError(ObservationQueryError):
    """``--since SUMMARY_ID`` does not name a retained summary."""


# ------------------------------------------------------------------------------------
# Project resolution (OBS-FR-077 / OBS-D-022)
# ------------------------------------------------------------------------------------

_PROJECT_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


@dataclass(frozen=True, slots=True)
class ProjectResolution:
    """The canonical lower-case project UUID plus the directory it was read from."""

    project_id: str
    project_root: Path


def _read_project_toml(candidate: Path) -> ProjectResolution | None:
    marker = candidate / ".aether" / "project.toml"
    if not marker.is_file():
        return None
    try:
        with marker.open("rb") as handle:
            data = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return None
    project_id = data.get("project_id")
    if not isinstance(project_id, str) or not _PROJECT_UUID_RE.fullmatch(project_id):
        return None
    return ProjectResolution(project_id=project_id, project_root=candidate)


def resolve_project(
    explicit: str | Path | None = None, *, start: str | Path | None = None
) -> ProjectResolution:
    """Resolve the canonical lower-case project UUID.

    ``explicit`` (``--project PATH``) is checked exactly; otherwise ``start`` (default:
    the current directory) and its ancestors are checked in turn, matching how
    ``.aether/project.toml`` was written by ``aether init``. Never falls back to a
    guessed identity: an unreadable, missing, or schema-invalid marker is a bounded
    error (OBS-FR-077's "no project event and never writes into a guessed project").
    """
    if explicit is not None:
        root = Path(explicit).expanduser().resolve()
        resolution = _read_project_toml(root)
        if resolution is None:
            raise ProjectResolutionError(
                "no valid Aether project found at the provided --project path"
            )
        return resolution

    cursor = Path(start).expanduser().resolve() if start is not None else Path.cwd()
    for candidate in (cursor, *cursor.parents):
        resolution = _read_project_toml(candidate)
        if resolution is not None:
            return resolution
    raise ProjectResolutionError(
        "no Aether project found in the current directory or its ancestors"
    )


# ------------------------------------------------------------------------------------
# Trace resolution (section 13.1 / cli.md)
# ------------------------------------------------------------------------------------

_TRACE_ID_RE = re.compile(r"^ctr_[a-f0-9]{32}$")


@dataclass(frozen=True, slots=True)
class _TraceRow:
    trace_id: str
    contract_id: str | None
    task_ids: tuple[str, ...]
    termination: str


def _read_model(paths: ObservationPaths) -> Any:
    from aether_agents.observation.storage import ReadModel  # narrow seam; lazy import

    return ReadModel.open(paths)


def _list_traces(paths: ObservationPaths) -> list[_TraceRow]:
    try:
        model = _read_model(paths)
        try:
            rows = model.list_traces()
        finally:
            model.close()
    except ImportError as exc:
        raise StateUnreadableError(
            "the observation read model is not available in this build"
        ) from exc
    except Exception as exc:  # defensive: never leak raw driver/internal detail
        raise StateUnreadableError(
            f"observation state could not be read ({safe_error_class(type(exc)) or 'error'})"
        ) from exc

    result: list[_TraceRow] = []
    for row in rows:
        get: Callable[[str, Any], Any]
        if isinstance(row, dict):
            get = row.get
        else:
            get = lambda key, default=None, _row=row: getattr(_row, key, default)  # noqa: E731
        result.append(
            _TraceRow(
                trace_id=get("trace_id", None),
                contract_id=get("contract_id", None),
                task_ids=tuple(get("task_ids", None) or ()),
                termination=get("termination", "unknown"),
            )
        )
    return result


def resolve_trace(paths: ObservationPaths, ref: str | None) -> str:
    """Resolve ``REF`` to exactly one ``trace_id`` (section 13.1).

    ``REF`` may be an exact ``trace_id``, a canonical ``contract_id``, or a bound Kanban
    ``task_id``, tried in that order. Without ``REF``, the single open trace is
    selected. Zero (open) traces raises :class:`NoOpenTraceError` (an empty-state
    report, not a failure); more than one candidate raises
    :class:`TraceAmbiguousError` rather than guessing.
    """
    if not paths.project.is_dir():
        raise NoOpenTraceError("no observation state recorded for this project yet")

    try:
        from aether_agents.observation.reduce.ingest import ingest_pending

        ingest_pending(paths)
    except Exception as exc:
        raise StateUnreadableError(
            f"observation state could not be ingested ({safe_error_class(type(exc)) or 'error'})"
        ) from exc

    rows = _list_traces(paths)

    if ref is None:
        open_rows = [row for row in rows if row.termination == "open"]
        if not open_rows:
            raise NoOpenTraceError("no open contract trace observed for this project")
        if len(open_rows) > 1:
            raise TraceAmbiguousError(
                f"{len(open_rows)} open traces observed; specify REF",
                candidates=tuple(sorted(row.trace_id for row in open_rows)),
            )
        return open_rows[0].trace_id

    if _TRACE_ID_RE.fullmatch(ref):
        matches = [row for row in rows if row.trace_id == ref]
    else:
        matches = [row for row in rows if row.contract_id == ref]
        if not matches:
            matches = [row for row in rows if ref in row.task_ids]

    if not matches:
        raise TraceNotFoundError("no trace matches the given REF")
    if len(matches) > 1:
        raise TraceAmbiguousError(
            f"{len(matches)} traces match the given REF; specify the exact trace_id",
            candidates=tuple(sorted(row.trace_id for row in matches)),
        )
    return matches[0].trace_id


# ------------------------------------------------------------------------------------
# Summary loading
# ------------------------------------------------------------------------------------

_SUMMARY_ID_RE = re.compile(r"^sum_[a-f0-9]{64}$")


def load_summary(paths: ObservationPaths, trace_id: str) -> dict[str, Any]:
    """Produce the current deterministic summary for ``trace_id``.

    Performs local incremental ingest then pure reduction — the same local
    ingest/reduction path :func:`watch` uses per check (OBS-FR-070) — and writes only
    Aether-owned observation state, never a Kanban/SessionDB/artifact record, so
    ``aether observe`` remains read-only with respect to every authoritative system
    (OBS-FR-025).
    """
    try:
        from aether_agents.observation.reduce.ingest import ingest_pending, reduce_trace
    except ImportError as exc:
        raise StateUnreadableError(
            "observation reduction modules are not available in this build"
        ) from exc

    try:
        ingest_pending(paths)
        return reduce_trace(paths, trace_id)
    except Exception as exc:
        raise StateUnreadableError(
            f"observation state could not be reduced ({safe_error_class(type(exc)) or 'error'})"
        ) from exc


def load_previous_summary(paths: ObservationPaths, summary_id: str) -> dict[str, Any]:
    """Load a previously retained, immutable summary by ID (OBS-D-002) for ``--since``."""
    if not _SUMMARY_ID_RE.fullmatch(summary_id):
        raise SummaryNotFoundError("summary id is not well-formed")
    try:
        candidate = paths.summary_file(summary_id)
        text = read_private_bytes(candidate).decode("utf-8")
    except FileNotFoundError:
        raise SummaryNotFoundError("the requested prior summary was not found") from None
    except (OSError, UnicodeError, UnsafeObservationPath):
        raise StateUnreadableError("the requested prior summary could not be read safely") from None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise StateUnreadableError("the requested prior summary is not valid JSON") from exc
    try:
        from aether_agents.observation.contracts import validate_summary
        from aether_agents.observation.identity import summary_id as make_summary_id
        from aether_agents.observation.privacy import assert_clean

        if not isinstance(payload, dict):
            raise ValueError("summary is not an object")
        validate_summary(payload)
        assert_clean(payload)
        if payload.get("summary_id") != summary_id or make_summary_id(payload) != summary_id:
            raise ValueError("summary identity mismatch")
        if payload.get("project_id") != paths.project_id:
            raise ValueError("summary project mismatch")
    except Exception as exc:
        raise StateUnreadableError(
            "the requested prior summary failed integrity validation"
        ) from exc
    return payload


# ------------------------------------------------------------------------------------
# Watch (OBS-FR-070)
# ------------------------------------------------------------------------------------

_WATCH_MIN_INTERVAL_S = 1.0
_WATCH_MAX_INTERVAL_S = 5.0


def _fs_signature(paths: ObservationPaths) -> tuple:
    """A cheap directory/segment metadata signature.

    Never opens or parses journal content: only names, mtimes, and sizes, so a poll
    tick that finds nothing changed costs a few stat calls, never a reduction.
    """
    signature: list[tuple] = []
    for directory in (paths.active, paths.closed, paths.projections):
        try:
            entries = sorted(directory.iterdir())
        except OSError:
            signature.append((str(directory), None, None))
            continue
        for entry in entries:
            try:
                info = entry.stat()
            except OSError:
                continue
            signature.append((entry.name, info.st_mtime_ns, info.st_size))
    return tuple(signature)


def _priority_fingerprint(summary: dict[str, Any]) -> tuple:
    """Owner-visible semantic facets that gate watch output.

    A canonical summary ID also changes for source-count and tool/request economics.
    Using that raw ID as a separate trigger would violate OBS-FR-070's explicit
    requirement to suppress unchanged heartbeat/request/tool activity.  Emitted
    summaries still carry their current canonical ID.
    """
    brief = summary.get("review_brief", {})
    coverage = summary.get("coverage", {})
    gate = brief.get("next_gate", {})
    findings = tuple(sorted((f["severity"], f["code"]) for f in brief.get("findings", [])))
    gaps = tuple(sorted(g["class"] for g in coverage.get("gaps", [])))
    return (
        brief.get("verdict"),
        findings,
        coverage.get("complete"),
        gaps,
        gate.get("kind"),
        gate.get("target_ref"),
    )


def watch(
    paths: ObservationPaths,
    trace_id: str,
    *,
    stop: Callable[[], bool] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> Iterator[dict[str, Any]]:
    """Yield a fresh summary only when an OBS-FR-070-watched facet changes.

    Never tails raw journal events and never full-replays the journal on every check: a
    cheap filesystem signature (:func:`_fs_signature`) gates whether a real
    ingest/reduction runs at all. Polling starts at once per second, backs off to at
    most once per five seconds while the signature is unchanged, and resets to once per
    second immediately after a detected filesystem change. The very first computable
    summary is always yielded (it establishes the caller's baseline); afterwards only a
    change in summary ID, verdict, priority findings, coverage state, or next gate is
    emitted. A transient unreadable tick is swallowed rather than raised, since a watch
    loop must survive a moment of collector-writer churn.
    """
    interval = _WATCH_MIN_INTERVAL_S
    last_signature: tuple | None = None
    last_priority: tuple | None = None
    first = True

    while True:
        if stop is not None and stop():
            return
        if not first:
            sleep(interval)
            if stop is not None and stop():
                return
        first = False

        signature = _fs_signature(paths)
        if signature == last_signature:
            interval = min(_WATCH_MAX_INTERVAL_S, interval * 2)
            continue
        last_signature = signature
        interval = _WATCH_MIN_INTERVAL_S

        try:
            summary = load_summary(paths, trace_id)
        except ObservationQueryError:
            continue

        priority = _priority_fingerprint(summary)
        if priority != last_priority:
            last_priority = priority
            yield summary
