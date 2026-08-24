"""Versioned, rebuildable SQLite read model.

Normative sources: ``specs/002-aether-contract-observation/spec.md`` section 6.3,
section 12; OBS-D-001, OBS-D-002, OBS-D-026, OBS-FR-081.

The database is derived and rebuildable from retained journal data. It is never
consulted to decide task lifecycle or effect authority (section 6.3), and nothing
here ever writes to a journal segment: ingestion only reads already-materialized,
already-clean canonical events and canonical summaries and mirrors them into
indexed tables. Every stored column is an opaque identifier, a timestamp, a status,
a count, or a hash — never prompt/response/diff/terminal/web content (section 8.3).

Rollback safety (OBS-D-026, spec section 6.3): a release only ever opens or
rewrites the projection file named after its OWN ``read_model_schema`` constant
(``paths.projection_db(schema)``). It never enumerates or touches a projection file
belonging to a different schema, so an older rollback release can never open or
rewrite a newer incompatible projection; newer projection files are simply never
looked at, which is exactly how they are preserved for later cleanup.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import sqlite3
import stat
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from aether_agents.observation.checkpoint import (
    AuthorityContext,
    authority_context_from_state_root,
)
from aether_agents.observation.contracts import (
    READ_MODEL_SCHEMA,
    CoverageClass,
    canonical_digest,
    canonical_json_str,
    validate_event,
    validate_summary,
)
from aether_agents.observation.locking import project_lock
from aether_agents.observation.privacy import assert_clean
from aether_agents.observation.reduce.process import causal_order
from aether_agents.observation.reduce.reconciliation import native_disposition, native_key
from aether_agents.paths import (
    FILE_MODE,
    ObservationPaths,
    UnsafeObservationPath,
    _open_private_directory,
    atomic_private_write,
    ensure_private_dir,
    harden_file,
    read_private_bytes,
)

try:  # Projection publication is POSIX-lock coordinated on supported platforms.
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX fallback has no process peers
    fcntl = None  # type: ignore[assignment]

__all__ = [
    "EventDerivationFailed",
    "EventIdentityCollision",
    "EventValidationFailed",
    "IngestCursor",
    "OpenTrace",
    "ProjectionPointerConflict",
    "ProjectionRebuildRequired",
    "ReadModel",
    "StorageReport",
    "publish_projection_pointer",
]


class EventIdentityCollision(ValueError):
    """A retained identity names different canonical bytes."""


class EventDerivationFailed(RuntimeError):
    """Raw plus derived projection failed atomically; source bytes remain replayable."""


class EventValidationFailed(ValueError):
    """One bulk event was rejected without retaining validation or payload detail."""


class ProjectionRebuildRequired(RuntimeError):
    """A legacy raw row has no proof that all of its derivations committed."""


class ProjectionPointerConflict(RuntimeError):
    """The active projection changed since its lifecycle owner last observed it."""


#: Tool lifecycle event types (mirrors contracts.TOOL_EVENT_TYPES; kept as a local
#: literal so this module does not depend on a non-exported contracts.py constant).
_TOOL_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "tool.started",
        "tool.completed",
        "tool.failed",
        "tool.blocked",
        "tool.cancelled",
        "tool.timed_out",
        "tool.interrupted",
    }
)

_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_EVENT_REF_RE = re.compile(r"^evt_(?:[a-f0-9]{32}|[a-f0-9]{64})$")
_TRACE_REF_RE = re.compile(r"^ctr_[a-f0-9]{32}$")
_PROJECTION_POINTER_RE = re.compile(
    rb"^aether\.observation\.projection\.v([1-9][0-9]*)\.sqlite3\n$"
)


def _fsync_projection_directory(directory: Path) -> None:
    if os.name != "posix":
        return
    descriptor = _open_private_directory(directory)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _assert_projection_path_identity(db_path: Path, expected: tuple[int, int]) -> None:
    """Prove one schema name still resolves to the prepared regular-file inode."""

    parent_descriptor = _open_private_directory(db_path.parent)
    descriptor: int | None = None
    try:
        flags = (
            os.O_RDONLY
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NONBLOCK", 0)
        )
        descriptor = os.open(db_path.name, flags, dir_fd=parent_descriptor)
        opened = os.fstat(descriptor)
        named = os.stat(
            db_path.name,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_nlink != 1
            or (opened.st_dev, opened.st_ino) != expected
            or (named.st_dev, named.st_ino) != expected
        ):
            raise ProjectionPointerConflict("prepared projection changed at pointer publish")
    except OSError as error:
        raise ProjectionPointerConflict(
            "prepared projection is unavailable at pointer publish"
        ) from error
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(parent_descriptor)


def publish_projection_pointer(
    paths: ObservationPaths,
    *,
    schema: str,
    expected_active: str | None,
    expected_projection_identity: tuple[int, int] | None = None,
    _fsync_directory: Any = _fsync_projection_directory,
) -> None:
    """Publish a prepared schema by inode without opening its SQLite contents."""

    ensure_private_dir(paths.projections)
    db_path = paths.projection_db(schema)
    pointer = paths.projection_pointer
    data = (db_path.name + "\n").encode("utf-8")
    if _PROJECTION_POINTER_RE.fullmatch(data) is None:
        raise RuntimeError("projection pointer schema is invalid")
    if expected_active is None:
        expected_data = None
    else:
        expected_data = (expected_active + "\n").encode("utf-8")
        if _PROJECTION_POINTER_RE.fullmatch(expected_data) is None:
            raise ValueError("expected active projection identity is invalid")

    with project_lock(paths, "projection-pointer"):
        if expected_projection_identity is not None:
            _assert_projection_path_identity(db_path, expected_projection_identity)
        try:
            harden_file(pointer)
            existing_data = read_private_bytes(pointer)
        except FileNotFoundError:
            existing_data = None
        if existing_data is not None and _PROJECTION_POINTER_RE.fullmatch(existing_data) is None:
            raise RuntimeError("projection pointer identity is invalid")
        if existing_data == data:
            _fsync_directory(pointer.parent)
            if read_private_bytes(pointer) != data:
                raise ProjectionPointerConflict("active projection changed during retry")
            if expected_projection_identity is not None:
                _assert_projection_path_identity(db_path, expected_projection_identity)
            return
        if existing_data != expected_data:
            raise ProjectionPointerConflict("active projection compare-and-swap failed")

        atomic_private_write(pointer, data)
        _fsync_directory(pointer.parent)
        if read_private_bytes(pointer) != data:
            raise ProjectionPointerConflict("active projection changed during publish")
        if expected_projection_identity is not None:
            _assert_projection_path_identity(db_path, expected_projection_identity)


class _ProjectionReaderLease:
    """Shared reader lease that upgrades exclusively around projection replacement."""

    def __init__(self, paths: ObservationPaths) -> None:
        ensure_private_dir(paths.locks)
        parent_descriptor = _open_private_directory(paths.locks)
        descriptor: int | None = None
        try:
            flags = (
                os.O_RDWR | os.O_CREAT | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
            )
            descriptor = os.open(
                "projection-readers.lock", flags, FILE_MODE, dir_fd=parent_descriptor
            )
            opened = os.fstat(descriptor)
            named = os.stat(
                "projection-readers.lock",
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
            if (
                not stat.S_ISREG(opened.st_mode)
                or opened.st_nlink != 1
                or (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino)
            ):
                raise UnsafeObservationPath("projection reader lock is not private")
            os.fchmod(descriptor, FILE_MODE)
            if fcntl is not None:
                fcntl.flock(descriptor, fcntl.LOCK_SH)
        except Exception:
            if descriptor is not None:
                os.close(descriptor)
            raise
        finally:
            os.close(parent_descriptor)
        self._descriptor = descriptor
        self._closed = False

    def upgrade(self) -> None:
        if self._closed:
            raise RuntimeError("projection reader lease is closed")
        if fcntl is not None:
            fcntl.flock(self._descriptor, fcntl.LOCK_EX)

    def downgrade(self) -> None:
        if not self._closed and fcntl is not None:
            fcntl.flock(self._descriptor, fcntl.LOCK_SH)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if fcntl is not None:
            fcntl.flock(self._descriptor, fcntl.LOCK_UN)
        os.close(self._descriptor)


def _now_iso() -> str:
    """Wall-clock storage bookkeeping timestamp.

    This is never read during reduction and never influences a summary's
    deterministic content (invariant 4); it only timestamps local DB housekeeping
    rows (ingest cursors, quarantine records, when a summary was written to disk).
    """
    return datetime.now(timezone.utc).isoformat()


def _bool_to_int(value: Any) -> int | None:
    if value is None:
        return None
    return 1 if value else 0


def _projection_native_key(event: Mapping[str, Any]) -> str | None:
    """Native dedupe key, excluding product-owned binding classifications.

    ``work_unit_classified`` reuses the canonical ``work_unit.bound`` event type but is
    a second semantic fact: native evidence owns binding/assignment, while the product
    checkpoint owns exact relation/required classification. Both raw rows must survive.
    """

    if (
        event.get("event_type") == "work_unit.bound"
        and event.get("source_kind") == "aether_checkpoint"
    ):
        return None
    return native_key(dict(event))


def _open_projection_descriptor(db_path: Path) -> tuple[int, int]:
    """Open/create the projection through a component-verified parent descriptor."""
    flags = os.O_RDWR | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    parent_descriptor = _open_private_directory(db_path.parent)
    try:
        try:
            descriptor = os.open(db_path.name, flags, dir_fd=parent_descriptor)
        except FileNotFoundError:
            try:
                descriptor = os.open(
                    db_path.name,
                    flags | os.O_CREAT | os.O_EXCL,
                    FILE_MODE,
                    dir_fd=parent_descriptor,
                )
            except FileExistsError:
                # A competing creator won between the two opens; validate that inode.
                descriptor = os.open(db_path.name, flags, dir_fd=parent_descriptor)
    except OSError as error:
        os.close(parent_descriptor)
        raise UnsafeObservationPath("projection database is not a safe regular file") from error

    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
            raise UnsafeObservationPath("projection database is not singly linked")
        named = os.stat(db_path.name, dir_fd=parent_descriptor, follow_symlinks=False)
        if (named.st_dev, named.st_ino) != (opened.st_dev, opened.st_ino):
            raise UnsafeObservationPath("projection database changed during secure open")
        os.fchmod(descriptor, FILE_MODE)
    except Exception:
        os.close(descriptor)
        os.close(parent_descriptor)
        raise
    return descriptor, parent_descriptor


def _connect_projection(
    db_path: Path,
    *,
    held_descriptor: int | None = None,
    held_parent_descriptor: int | None = None,
) -> sqlite3.Connection:
    """Connect SQLite through a held inode, then revalidate the product-owned name.

    SQLite's Python API has no ``O_NOFOLLOW`` opener.  On supported POSIX Linux/WSL,
    opening ``/proc/self/fd/<n>`` makes SQLite duplicate the already validated inode;
    a same-user rename/symlink swap at the pathname can therefore be rejected before
    the external target receives a byte.
    """
    if os.name != "posix":  # pragma: no cover - supported release platforms are POSIX
        return sqlite3.connect(str(db_path), check_same_thread=False)

    if (held_descriptor is None) != (held_parent_descriptor is None):
        raise ValueError("projection descriptor and parent must be supplied together")
    owns_descriptors = held_descriptor is None
    if owns_descriptors:
        descriptor, parent_descriptor = _open_projection_descriptor(db_path)
    else:
        descriptor = held_descriptor
        parent_descriptor = held_parent_descriptor
        assert descriptor is not None and parent_descriptor is not None
    connection: sqlite3.Connection | None = None
    try:
        proc_path = Path("/proc/self/fd") / str(descriptor)
        if not proc_path.exists():
            raise UnsafeObservationPath("secure projection descriptor path is unavailable")
        connection = sqlite3.connect(
            f"file:{proc_path}?mode=rw",
            uri=True,
            check_same_thread=False,
        )
        opened = os.fstat(descriptor)
        named = os.stat(db_path.name, dir_fd=parent_descriptor, follow_symlinks=False)
        if not stat.S_ISREG(named.st_mode) or (named.st_dev, named.st_ino) != (
            opened.st_dev,
            opened.st_ino,
        ):
            raise UnsafeObservationPath("projection database changed before SQLite connect")
        verification_descriptor = _open_private_directory(db_path.parent)
        try:
            verified_parent = os.fstat(verification_descriptor)
            opened_parent = os.fstat(parent_descriptor)
            if (verified_parent.st_dev, verified_parent.st_ino) != (
                opened_parent.st_dev,
                opened_parent.st_ino,
            ):
                raise UnsafeObservationPath("projection database parent changed before connect")
        finally:
            os.close(verification_descriptor)
        return connection
    except Exception:
        if connection is not None:
            connection.close()
        raise
    finally:
        if owns_descriptors:
            os.close(descriptor)
            os.close(parent_descriptor)


# --------------------------------------------------------------------------------------
# Schema DDL
# --------------------------------------------------------------------------------------

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS observation_trace (
    trace_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    contract_id TEXT,
    opened_at TEXT,
    last_event_at TEXT,
    last_event_id TEXT,
    closed_at TEXT,
    termination TEXT NOT NULL DEFAULT 'open',
    event_count INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_trace_project ON observation_trace(project_id);
CREATE INDEX IF NOT EXISTS idx_trace_contract ON observation_trace(contract_id);
CREATE INDEX IF NOT EXISTS idx_trace_termination ON observation_trace(termination);

CREATE TABLE IF NOT EXISTS observation_event (
    event_id TEXT PRIMARY KEY,
    native_identity_key TEXT,
    trace_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    producer_epoch TEXT NOT NULL,
    producer_seq INTEGER NOT NULL,
    collector_version TEXT NOT NULL,
    runtime_fingerprint TEXT NOT NULL,
    normalizer_ref TEXT,
    source_kind TEXT NOT NULL,
    source_hook TEXT,
    contract_id TEXT,
    task_id TEXT,
    run_id INTEGER,
    session_id TEXT,
    turn_id TEXT,
    api_request_id TEXT,
    parent_event_id TEXT,
    occurred_at TEXT NOT NULL,
    source_utc_offset_minutes INTEGER,
    monotonic_ns INTEGER,
    actor_kind TEXT,
    actor_id TEXT,
    actor_profile TEXT,
    actor_role TEXT,
    event_type TEXT NOT NULL,
    status TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    timestamp_source TEXT,
    tool_call_id TEXT,
    tool_name TEXT,
    tool_category TEXT,
    coverage_class TEXT,
    payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_event_project ON observation_event(project_id);
CREATE INDEX IF NOT EXISTS idx_event_trace ON observation_event(trace_id);
CREATE INDEX IF NOT EXISTS idx_event_contract ON observation_event(contract_id);
CREATE INDEX IF NOT EXISTS idx_event_time ON observation_event(occurred_at);
CREATE INDEX IF NOT EXISTS idx_event_participant ON observation_event(actor_id);
CREATE INDEX IF NOT EXISTS idx_event_type ON observation_event(event_type);
CREATE UNIQUE INDEX IF NOT EXISTS idx_event_producer_sequence
    ON observation_event(producer_epoch, producer_seq);
DROP INDEX IF EXISTS idx_event_native_identity;
CREATE INDEX IF NOT EXISTS idx_event_native_identity
    ON observation_event(trace_id, native_identity_key)
    WHERE native_identity_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS event_derivation (
    event_id TEXT PRIMARY KEY,
    derived_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS contract_decision (
    event_id TEXT PRIMARY KEY,
    trace_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    contract_id TEXT,
    decision_kind TEXT NOT NULL,
    status TEXT,
    occurred_at TEXT NOT NULL,
    revision INTEGER,
    artifact_ref TEXT,
    before_sha256 TEXT,
    after_sha256 TEXT,
    decision_refs_json TEXT,
    supersedes_decision_ref TEXT,
    evidence_refs_json TEXT,
    ambiguity_ref TEXT,
    invariant_key TEXT,
    semantic_delta TEXT
);
CREATE INDEX IF NOT EXISTS idx_decision_trace ON contract_decision(trace_id);
CREATE INDEX IF NOT EXISTS idx_decision_contract ON contract_decision(contract_id);
CREATE INDEX IF NOT EXISTS idx_decision_project ON contract_decision(project_id);

CREATE TABLE IF NOT EXISTS contract_revision (
    event_id TEXT PRIMARY KEY,
    trace_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    contract_id TEXT,
    revision INTEGER,
    occurred_at TEXT NOT NULL,
    artifact_ref TEXT,
    before_sha256 TEXT,
    after_sha256 TEXT,
    decision_refs_json TEXT,
    evidence_refs_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_revision_trace ON contract_revision(trace_id);
CREATE INDEX IF NOT EXISTS idx_revision_contract ON contract_revision(contract_id);

CREATE TABLE IF NOT EXISTS tool_span (
    trace_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    call_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    name TEXT,
    category TEXT,
    target_kind TEXT,
    target_ref TEXT,
    actor_kind TEXT,
    actor_id TEXT,
    started_at TEXT,
    started_event_id TEXT,
    terminal_status TEXT,
    terminal_event_id TEXT,
    ended_at TEXT,
    duration_ms INTEGER,
    exit_code INTEGER,
    error_class TEXT,
    approval_outcome TEXT,
    retry_count INTEGER,
    retry_of_call_id TEXT,
    PRIMARY KEY (trace_id, session_id, call_id)
);
CREATE INDEX IF NOT EXISTS idx_tool_span_project ON tool_span(project_id);
CREATE INDEX IF NOT EXISTS idx_tool_span_actor ON tool_span(actor_id);
CREATE INDEX IF NOT EXISTS idx_tool_span_name ON tool_span(name);

CREATE TABLE IF NOT EXISTS participant_contribution (
    trace_id TEXT NOT NULL,
    actor_kind TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    profile TEXT,
    role TEXT,
    action_total INTEGER NOT NULL DEFAULT 0,
    actions_json TEXT,
    last_event_id TEXT,
    last_event_at TEXT,
    PRIMARY KEY (trace_id, actor_kind, actor_id)
);
CREATE INDEX IF NOT EXISTS idx_participant_project ON participant_contribution(project_id);
CREATE INDEX IF NOT EXISTS idx_participant_actor ON participant_contribution(actor_id);

CREATE TABLE IF NOT EXISTS bound_work_unit (
    binding_ref TEXT PRIMARY KEY,
    trace_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    task_ref TEXT,
    relation TEXT,
    required INTEGER,
    parent_task_refs_json TEXT,
    task_status TEXT,
    run_status TEXT,
    run_outcome TEXT,
    bound_at TEXT,
    unbound_at TEXT,
    last_event_id TEXT,
    last_event_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_bound_unit_trace ON bound_work_unit(trace_id);
CREATE INDEX IF NOT EXISTS idx_bound_unit_task ON bound_work_unit(task_ref);
CREATE INDEX IF NOT EXISTS idx_bound_unit_project ON bound_work_unit(project_id);

CREATE TABLE IF NOT EXISTS work_unit_run (
    trace_id TEXT NOT NULL,
    run_id INTEGER NOT NULL,
    project_id TEXT NOT NULL,
    binding_ref TEXT,
    task_ref TEXT,
    started_at TEXT,
    finished_at TEXT,
    run_status TEXT,
    run_outcome TEXT,
    last_event_id TEXT,
    PRIMARY KEY (trace_id, run_id)
);
CREATE INDEX IF NOT EXISTS idx_run_task ON work_unit_run(task_ref);
CREATE INDEX IF NOT EXISTS idx_run_project ON work_unit_run(project_id);

CREATE TABLE IF NOT EXISTS process_step (
    trace_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    step_index INTEGER,
    kind TEXT,
    participant_ref TEXT,
    task_refs_json TEXT,
    run_refs_json TEXT,
    predecessor_step_ids_json TEXT,
    round_id TEXT,
    wave_id TEXT,
    started_at TEXT,
    ended_at TEXT,
    duration_ms INTEGER,
    outcome TEXT,
    semantic_delta INTEGER,
    evidence_event_ids_json TEXT,
    coverage TEXT,
    source_summary_id TEXT,
    PRIMARY KEY (trace_id, step_id)
);
CREATE INDEX IF NOT EXISTS idx_step_project ON process_step(project_id);
CREATE INDEX IF NOT EXISTS idx_step_round ON process_step(round_id);
CREATE INDEX IF NOT EXISTS idx_step_wave ON process_step(wave_id);

CREATE TABLE IF NOT EXISTS process_wave (
    trace_id TEXT NOT NULL,
    wave_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    round_id TEXT,
    step_ids_json TEXT,
    work_unit_refs_json TEXT,
    participant_refs_json TEXT,
    deployed_unit_count INTEGER,
    peak_parallelism INTEGER,
    eligible_unit_count_observed INTEGER,
    ready_but_not_running_count_observed INTEGER,
    ready_but_not_running_ms_observed INTEGER,
    global_limit INTEGER,
    per_profile_limit INTEGER,
    barrier TEXT,
    sampling_precision_ms INTEGER,
    started_at TEXT,
    ended_at TEXT,
    duration_ms INTEGER,
    evidence_event_ids_json TEXT,
    source_summary_id TEXT,
    PRIMARY KEY (trace_id, wave_id)
);
CREATE INDEX IF NOT EXISTS idx_wave_project ON process_wave(project_id);
CREATE INDEX IF NOT EXISTS idx_wave_round ON process_wave(round_id);

CREATE TABLE IF NOT EXISTS execution_round (
    trace_id TEXT NOT NULL,
    round_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    round_index INTEGER,
    trigger TEXT,
    previous_round_id TEXT,
    step_ids_json TEXT,
    wave_ids_json TEXT,
    participant_refs_json TEXT,
    deployed_unit_count INTEGER,
    started_at TEXT,
    ended_at TEXT,
    duration_ms INTEGER,
    outcome TEXT,
    evidence_event_ids_json TEXT,
    source_summary_id TEXT,
    PRIMARY KEY (trace_id, round_id)
);
CREATE INDEX IF NOT EXISTS idx_round_project ON execution_round(project_id);

CREATE TABLE IF NOT EXISTS configuration_fingerprint (
    trace_id TEXT NOT NULL,
    fingerprint_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    scope TEXT,
    participant_ref TEXT,
    model TEXT,
    provider TEXT,
    system_prompt_fingerprint TEXT,
    observed_skill_set_fingerprint TEXT,
    declared_toolset_fingerprint TEXT,
    effective_tool_surface_fingerprint TEXT,
    global_concurrency_limit INTEGER,
    per_profile_concurrency_limit INTEGER,
    observer_version TEXT,
    fingerprint_key_id TEXT,
    runtime_fingerprint TEXT,
    field_coverage_json TEXT,
    first_event_id TEXT,
    first_seen_at TEXT,
    PRIMARY KEY (trace_id, fingerprint_id)
);
CREATE INDEX IF NOT EXISTS idx_config_fp ON configuration_fingerprint(fingerprint_id);
CREATE INDEX IF NOT EXISTS idx_config_project ON configuration_fingerprint(project_id);

CREATE TABLE IF NOT EXISTS model_request_economics (
    trace_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    request_ref TEXT NOT NULL,
    project_id TEXT NOT NULL,
    state TEXT,
    model TEXT,
    provider TEXT,
    response_model TEXT,
    started_at TEXT,
    ended_at TEXT,
    duration_ms INTEGER,
    finish_reason TEXT,
    message_count INTEGER,
    tool_count INTEGER,
    attempt_count INTEGER NOT NULL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cache_read_tokens INTEGER,
    cache_write_tokens INTEGER,
    reasoning_tokens INTEGER,
    total_tokens INTEGER,
    usage_coverage TEXT,
    structured_reason_code TEXT,
    context_compressed INTEGER NOT NULL DEFAULT 0,
    context_overflow INTEGER NOT NULL DEFAULT 0,
    last_event_id TEXT,
    PRIMARY KEY (trace_id, session_id, request_ref, attempt_count)
);
CREATE INDEX IF NOT EXISTS idx_model_request_project ON model_request_economics(project_id);

CREATE TABLE IF NOT EXISTS tool_surface_snapshot (
    trace_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    request_ref TEXT NOT NULL,
    project_id TEXT NOT NULL,
    completeness TEXT,
    declared_toolset_fingerprint TEXT,
    effective_direct_surface_fingerprint TEXT,
    effective_deferred_surface_fingerprint TEXT,
    observed_tool_count INTEGER,
    granted_tool_refs_json TEXT,
    never_used_tool_refs_json TEXT,
    schema_serialized_bytes INTEGER,
    schema_estimated_tokens INTEGER,
    estimator_ref TEXT,
    fingerprint_key_id TEXT,
    occurred_at TEXT,
    event_id TEXT,
    PRIMARY KEY (trace_id, session_id, request_ref)
);
CREATE INDEX IF NOT EXISTS idx_tool_surface_project ON tool_surface_snapshot(project_id);

CREATE TABLE IF NOT EXISTS dispatch_observation (
    trace_id TEXT NOT NULL,
    tick_ref TEXT NOT NULL,
    project_id TEXT NOT NULL,
    outcome TEXT,
    eligible_count INTEGER,
    running_count INTEGER,
    global_limit INTEGER,
    per_profile_limit INTEGER,
    bottleneck_class TEXT,
    precision_ms INTEGER,
    evidence_refs_json TEXT,
    occurred_at TEXT,
    event_id TEXT,
    PRIMARY KEY (trace_id, tick_ref)
);
CREATE INDEX IF NOT EXISTS idx_dispatch_project ON dispatch_observation(project_id);
CREATE INDEX IF NOT EXISTS idx_dispatch_class ON dispatch_observation(bottleneck_class);

CREATE TABLE IF NOT EXISTS bottleneck_interval (
    event_id TEXT PRIMARY KEY,
    trace_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    attribution_class TEXT,
    provenance TEXT,
    started_at TEXT,
    ended_at TEXT,
    precision_ms INTEGER,
    evidence_refs_json TEXT,
    occurred_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_bottleneck_class ON bottleneck_interval(attribution_class);
CREATE INDEX IF NOT EXISTS idx_bottleneck_trace ON bottleneck_interval(trace_id);
CREATE INDEX IF NOT EXISTS idx_bottleneck_project ON bottleneck_interval(project_id);

CREATE TABLE IF NOT EXISTS defect_attribution (
    event_id TEXT PRIMARY KEY,
    trace_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    attribution_class TEXT,
    provenance TEXT,
    started_at TEXT,
    ended_at TEXT,
    precision_ms INTEGER,
    evidence_refs_json TEXT,
    occurred_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_defect_class ON defect_attribution(attribution_class);
CREATE INDEX IF NOT EXISTS idx_defect_trace ON defect_attribution(trace_id);
CREATE INDEX IF NOT EXISTS idx_defect_project ON defect_attribution(project_id);

CREATE TABLE IF NOT EXISTS review_transition (
    event_id TEXT PRIMARY KEY,
    trace_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    binding_ref TEXT,
    task_ref TEXT,
    transition TEXT NOT NULL,
    run_id INTEGER,
    actor_kind TEXT,
    actor_id TEXT,
    occurred_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_review_trace ON review_transition(trace_id);
CREATE INDEX IF NOT EXISTS idx_review_task ON review_transition(task_ref);

CREATE TABLE IF NOT EXISTS acceptance_criterion (
    trace_id TEXT NOT NULL,
    criterion_ref TEXT NOT NULL,
    project_id TEXT NOT NULL,
    state TEXT,
    evidence_refs_json TEXT,
    assigned_task_ref TEXT,
    review_task_ref TEXT,
    last_event_id TEXT,
    last_event_at TEXT,
    PRIMARY KEY (trace_id, criterion_ref)
);
CREATE INDEX IF NOT EXISTS idx_acceptance_project ON acceptance_criterion(project_id);
CREATE INDEX IF NOT EXISTS idx_acceptance_state ON acceptance_criterion(state);

CREATE TABLE IF NOT EXISTS invariant_transition (
    trace_id TEXT NOT NULL,
    invariant_key TEXT NOT NULL,
    project_id TEXT NOT NULL,
    state TEXT,
    last_event_id TEXT,
    last_event_at TEXT,
    PRIMARY KEY (trace_id, invariant_key)
);
CREATE INDEX IF NOT EXISTS idx_invariant_project ON invariant_transition(project_id);

CREATE TABLE IF NOT EXISTS coverage_gap (
    event_id TEXT PRIMARY KEY,
    trace_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    coverage_class TEXT,
    reason_code TEXT,
    started_at TEXT,
    ended_at TEXT,
    restored INTEGER NOT NULL DEFAULT 0,
    occurred_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_coverage_class ON coverage_gap(coverage_class);
CREATE INDEX IF NOT EXISTS idx_coverage_trace ON coverage_gap(trace_id);
CREATE INDEX IF NOT EXISTS idx_coverage_project ON coverage_gap(project_id);

CREATE TABLE IF NOT EXISTS observation_summary (
    summary_id TEXT PRIMARY KEY,
    trace_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    contract_id TEXT,
    reducer_version TEXT NOT NULL,
    as_of TEXT NOT NULL,
    completion_state TEXT NOT NULL,
    source_event_count INTEGER NOT NULL,
    recorded_at TEXT NOT NULL,
    canonical_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_summary_trace ON observation_summary(trace_id);
CREATE INDEX IF NOT EXISTS idx_summary_project ON observation_summary(project_id);
CREATE INDEX IF NOT EXISTS idx_summary_contract ON observation_summary(contract_id);
CREATE INDEX IF NOT EXISTS idx_summary_as_of ON observation_summary(as_of);

CREATE TABLE IF NOT EXISTS ingest_cursor (
    segment_path TEXT PRIMARY KEY,
    producer_epoch TEXT NOT NULL,
    first_seq INTEGER NOT NULL,
    last_seq INTEGER NOT NULL,
    byte_length INTEGER NOT NULL,
    uncompressed_sha256 TEXT NOT NULL,
    ingested_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS quarantine_event (
    segment_name TEXT NOT NULL,
    byte_offset INTEGER NOT NULL,
    byte_length INTEGER NOT NULL,
    sha256 TEXT NOT NULL,
    event_schema_version TEXT NOT NULL,
    project_id TEXT,
    quarantined_at TEXT NOT NULL,
    PRIMARY KEY (segment_name, byte_offset)
);

CREATE TABLE IF NOT EXISTS derived_diagnostic (
    diagnostic_id TEXT PRIMARY KEY,
    trace_id TEXT,
    project_id TEXT NOT NULL,
    coverage_class TEXT NOT NULL,
    reason_code TEXT NOT NULL,
    event_ref TEXT NOT NULL,
    segment_name TEXT,
    recorded_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_derived_diagnostic_trace
    ON derived_diagnostic(trace_id);
CREATE INDEX IF NOT EXISTS idx_derived_diagnostic_class
    ON derived_diagnostic(coverage_class);
"""


@dataclass(frozen=True, slots=True)
class OpenTrace:
    """One row of :meth:`ReadModel.list_open_traces`."""

    trace_id: str
    project_id: str
    contract_id: str | None
    opened_at: str | None
    last_event_at: str | None


@dataclass(frozen=True, slots=True)
class IngestCursor:
    """Per-segment ingestion progress, so a closed segment is never re-read and a
    growing active segment resumes from its last known offset."""

    segment_path: str
    producer_epoch: str
    first_seq: int
    last_seq: int
    byte_length: int
    uncompressed_sha256: str
    ingested_at: str


@dataclass(frozen=True, slots=True)
class StorageReport:
    """The subset of ``aether doctor``'s observation-storage facts (section 12)
    that this module alone can answer."""

    project_id: str
    projection_schema: str
    projection_db_bytes: int
    journal_bytes: int
    event_count: int
    observation_summary_count: int
    active_segment_count: int
    closed_segment_count: int
    archive_segment_count: int
    quarantine_segment_count: int
    quarantine_event_count: int
    projection_versions: tuple[str, ...]


class ReadModel:
    """The derived, rebuildable SQLite projection for one project (section 6.3).

    Nothing on this class ever opens, renames, or writes journal segment bytes;
    it only ingests already-canonical event/summary dictionaries produced by the
    reducer and mirrors them into indexed tables for ``aether observe``/``aether
    doctor``. Re-ingesting the same event or summary twice is a no-op: every
    write path is gated by ``INSERT OR IGNORE``/``ON CONFLICT`` on a natural key.
    """

    def __init__(
        self,
        *,
        connection: sqlite3.Connection,
        db_path: Path,
        paths: ObservationPaths,
        schema: str,
        authority_context: AuthorityContext,
        reader_lease: _ProjectionReaderLease,
    ) -> None:
        self._conn = connection
        self._db_path = db_path
        self._paths = paths
        self._schema = schema
        self._authority_context = authority_context
        self._reader_lease = reader_lease
        self._closed = False

    # -- lifecycle ------------------------------------------------------------
    @classmethod
    def open(
        cls,
        paths: ObservationPaths,
        *,
        schema: str = READ_MODEL_SCHEMA,
        authority_context: AuthorityContext | None = None,
    ) -> "ReadModel":
        """Open (creating if absent) the projection for ``schema`` only.

        This never inspects or touches a projection file for any other schema
        (OBS-D-026): a rollback release simply never looks at a newer file.
        """
        ensure_private_dir(paths.projections)
        db_path = paths.projection_db(schema)
        reader_lease = _ProjectionReaderLease(paths)
        # Validate every pre-existing SQLite path before SQLite can follow a link,
        # create sidecars, execute DDL, or otherwise mutate the referenced inode.
        connection: sqlite3.Connection | None = None
        try:
            paths.harden_projection_files(schema)
            connection = _connect_projection(db_path)
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=NORMAL")
        except Exception:
            if connection is not None:
                connection.close()
            reader_lease.close()
            raise
        context = (
            authority_context
            if authority_context is not None
            else authority_context_from_state_root(paths.root)
        )
        model = cls(
            connection=connection,
            db_path=db_path,
            paths=paths,
            schema=schema,
            authority_context=context,
            reader_lease=reader_lease,
        )
        try:
            model._create_schema()
            model._refresh_authority_dependent_work_units()
            paths.harden_projection_files(schema)
        except Exception:
            connection.close()
            reader_lease.close()
            raise
        return model

    def _create_schema(self) -> None:
        self._conn.executescript(_SCHEMA_SQL)
        self._conn.commit()

    def _refresh_authority_dependent_work_units(self) -> None:
        """Reproject retained classifications against the current release authority.

        SQLite is rebuildable state, while product authority belongs to the verified
        active release and may legitimately change between opens. Retained journal
        events are therefore re-evaluated instead of leaving a previously authorized
        positive classification sticky after authority becomes unavailable (or vice
        versa).
        """

        rows = self._conn.execute(
            "SELECT payload_json FROM observation_event "
            "WHERE event_type IN ('work_unit.bound', 'work_unit.unbound', 'work_unit.status')"
        ).fetchall()
        candidates: dict[tuple[str, str, str], dict[str, Any]] = {}
        for (payload_json,) in rows:
            event = json.loads(payload_json)
            work_unit = event.get("work_unit") or {}
            trace_id = event.get("trace_id")
            task_ref = work_unit.get("task_ref")
            binding_ref = work_unit.get("binding_ref")
            if not all(isinstance(value, str) for value in (trace_id, task_ref, binding_ref)):
                continue
            candidates.setdefault((trace_id, task_ref, binding_ref), event)
        for key in sorted(candidates):
            self._derive_bound_work_unit(candidates[key])
        self._conn.commit()

    def publish_projection(
        self,
        *,
        expected_active: str | None,
        expected_projection_identity: tuple[int, int] | None = None,
    ) -> None:
        """Explicitly select this compatible projection using lock-guarded CAS.

        Ordinary readers never call this operation.  A lifecycle/rebuild owner must
        name the exact pointer identity it observed (or ``None`` for first publish),
        so update, rollback, and re-update cannot silently overwrite one another.
        """
        publish_projection_pointer(
            self._paths,
            schema=self._schema,
            expected_active=expected_active,
            expected_projection_identity=expected_projection_identity,
            _fsync_directory=self._fsync_directory,
        )

    def unpublish_projection(self, *, expected_active: str) -> None:
        """CAS-select absence when rolling back an interrupted first publication."""
        expected_data = (expected_active + "\n").encode("utf-8")
        if _PROJECTION_POINTER_RE.fullmatch(expected_data) is None:
            raise ValueError("expected active projection identity is invalid")
        pointer = self._paths.projection_pointer
        with project_lock(self._paths, "projection-pointer"):
            try:
                existing_data = read_private_bytes(pointer)
            except FileNotFoundError:
                # Unlink may have become visible before its directory fsync failed.
                # Re-prove that boundary on every idempotent rollback retry.
                self._fsync_directory(pointer.parent)
                try:
                    read_private_bytes(pointer)
                except FileNotFoundError:
                    return
                raise ProjectionPointerConflict(
                    "active projection changed during unpublish retry"
                ) from None
            if existing_data != expected_data:
                raise ProjectionPointerConflict("active projection compare-and-swap failed")

            parent_descriptor = _open_private_directory(pointer.parent)
            descriptor: int | None = None
            try:
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
                if (
                    not stat.S_ISREG(opened.st_mode)
                    or opened.st_nlink != 1
                    or (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino)
                ):
                    raise UnsafeObservationPath("projection pointer changed before unpublish")
                chunks: list[bytes] = []
                while True:
                    chunk = os.read(descriptor, 256)
                    if not chunk:
                        break
                    chunks.append(chunk)
                if b"".join(chunks) != expected_data:
                    raise ProjectionPointerConflict("active projection changed before unpublish")
                named_after = os.stat(
                    pointer.name,
                    dir_fd=parent_descriptor,
                    follow_symlinks=False,
                )
                if (named_after.st_dev, named_after.st_ino) != (
                    opened.st_dev,
                    opened.st_ino,
                ):
                    raise ProjectionPointerConflict("active projection changed before unpublish")
                os.unlink(pointer.name, dir_fd=parent_descriptor)
                os.fsync(parent_descriptor)
            finally:
                if descriptor is not None:
                    os.close(descriptor)
                os.close(parent_descriptor)
            try:
                read_private_bytes(pointer)
            except FileNotFoundError:
                return
            raise ProjectionPointerConflict("active projection changed during unpublish")

    @staticmethod
    def _fsync_directory(directory: Path) -> None:
        if os.name != "posix":
            return
        descriptor = _open_private_directory(directory)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self._paths.harden_projection_files(self._schema)
        finally:
            try:
                self._conn.close()
            finally:
                self._reader_lease.close()

    def __enter__(self) -> "ReadModel":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    @property
    def path(self) -> Path:
        return self._db_path

    def rebuild(self) -> None:
        """Atomically replace the derived projection only. Never touches the journal."""
        with project_lock(self._paths, "storage-transition"):
            self._rebuild_locked()

    def _rebuild_locked(self) -> None:
        """Build, verify, and fsync a candidate before replacing the live DB.

        The current connection and its WAL/SHM remain untouched until the complete
        candidate is durable.  Publication upgrades this model's shared reader lease,
        closes/checkpoints the old connection, atomically renames within the verified
        projection directory, and fsyncs that directory before reopening the winner.
        """
        token = secrets.token_hex(16)
        candidate_name = f".{self._db_path.name}.rebuild-{token}.tmp"
        candidate_path = self._db_path.with_name(candidate_name)
        candidate_sidecars = tuple(
            candidate_path.with_name(candidate_name + suffix)
            for suffix in ("", "-journal", "-wal", "-shm")
        )
        parent_descriptor = _open_private_directory(self._db_path.parent)
        self._remove_stale_rebuild_candidates_locked(parent_descriptor)
        candidate_descriptor: int | None = None
        candidate_connection: sqlite3.Connection | None = None
        replacement_connection: sqlite3.Connection | None = None
        old_connection = self._conn
        old_connection_closed = False
        try:
            flags = (
                os.O_RDWR
                | os.O_CREAT
                | os.O_EXCL
                | getattr(os, "O_CLOEXEC", 0)
                | getattr(os, "O_NOFOLLOW", 0)
            )
            candidate_descriptor = os.open(
                candidate_name, flags, FILE_MODE, dir_fd=parent_descriptor
            )
            opened = os.fstat(candidate_descriptor)
            named = os.stat(
                candidate_name,
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
            if (
                not stat.S_ISREG(opened.st_mode)
                or opened.st_nlink != 1
                or (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino)
            ):
                raise UnsafeObservationPath("projection candidate is not private")
            os.fchmod(candidate_descriptor, FILE_MODE)

            candidate_connection = _connect_projection(
                candidate_path,
                held_descriptor=candidate_descriptor,
                held_parent_descriptor=parent_descriptor,
            )
            candidate_connection.execute("PRAGMA journal_mode=DELETE")
            candidate_connection.execute("PRAGMA synchronous=FULL")
            self._conn = candidate_connection
            self._create_schema()
            integrity = candidate_connection.execute("PRAGMA integrity_check").fetchone()
            if integrity != ("ok",):
                raise sqlite3.DatabaseError("candidate projection integrity check failed")
            candidate_connection.commit()
            candidate_connection.close()
            candidate_connection = None
            self._conn = old_connection

            os.fsync(candidate_descriptor)
            opened = os.fstat(candidate_descriptor)
            named = os.stat(
                candidate_name,
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
            if (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino):
                raise UnsafeObservationPath("projection candidate changed before publish")

            self._reader_lease.upgrade()
            try:
                # All cooperating readers are now drained. Closing checkpoints the
                # current WAL before any live name or sidecar is replaced.
                old_connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                old_connection.close()
                old_connection_closed = True
                self._remove_projection_sidecars_locked(parent_descriptor)
                os.replace(
                    candidate_name,
                    self._db_path.name,
                    src_dir_fd=parent_descriptor,
                    dst_dir_fd=parent_descriptor,
                )
                os.fsync(parent_descriptor)
                replacement_connection = _connect_projection(self._db_path)
                replacement_connection.execute("PRAGMA journal_mode=WAL")
                replacement_connection.execute("PRAGMA synchronous=NORMAL")
                self._paths.harden_projection_files(self._schema)
                self._conn = replacement_connection
                replacement_connection = None
            finally:
                self._reader_lease.downgrade()
        except Exception:
            if replacement_connection is not None:
                replacement_connection.close()
                replacement_connection = None
            self._conn = old_connection
            if old_connection_closed:
                try:
                    self._conn = _connect_projection(self._db_path)
                    self._conn.execute("PRAGMA journal_mode=WAL")
                    self._conn.execute("PRAGMA synchronous=NORMAL")
                except Exception:
                    self._conn = old_connection
            raise
        finally:
            if candidate_connection is not None:
                candidate_connection.close()
            if replacement_connection is not None:
                replacement_connection.close()
            if candidate_descriptor is not None:
                os.close(candidate_descriptor)
            for candidate in candidate_sidecars:
                try:
                    os.unlink(candidate.name, dir_fd=parent_descriptor)
                except FileNotFoundError:
                    pass
            os.close(parent_descriptor)

    def _remove_projection_sidecars_locked(self, parent_descriptor: int) -> None:
        """Remove only checkpointed sidecars while holding the exclusive reader lease."""
        for suffix in ("-wal", "-shm"):
            name = self._db_path.name + suffix
            try:
                os.unlink(name, dir_fd=parent_descriptor)
            except FileNotFoundError:
                pass

    def _remove_stale_rebuild_candidates_locked(self, parent_descriptor: int) -> None:
        """Idempotently remove only closed-grammar temps from interrupted rebuilds."""
        pattern = re.compile(
            rf"^\.{re.escape(self._db_path.name)}\.rebuild-[a-f0-9]{{32}}"
            r"\.tmp(?:-journal|-wal|-shm)?$"
        )
        removed = False
        for name in os.listdir(parent_descriptor):
            if pattern.fullmatch(name) is None:
                continue
            try:
                metadata = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
                if stat.S_ISDIR(metadata.st_mode):
                    raise UnsafeObservationPath("projection rebuild candidate is a directory")
                os.unlink(name, dir_fd=parent_descriptor)
                removed = True
            except FileNotFoundError:
                continue
        if removed:
            os.fsync(parent_descriptor)

    # -- generic upsert ---------------------------------------------------------
    def _upsert(self, table: str, row: dict[str, Any], key_columns: tuple[str, ...]) -> None:
        if not _IDENTIFIER_RE.match(table):
            raise ValueError("unsafe table name")
        for column in row:
            if not _IDENTIFIER_RE.match(column):
                raise ValueError("unsafe column name")
        columns = list(row.keys())
        placeholders = ", ".join("?" for _ in columns)
        non_key = [c for c in columns if c not in key_columns]
        sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
        if non_key:
            updates = ", ".join(f"{c}=excluded.{c}" for c in non_key)
            sql += f" ON CONFLICT({', '.join(key_columns)}) DO UPDATE SET {updates}"
        else:
            sql += f" ON CONFLICT({', '.join(key_columns)}) DO NOTHING"
        self._conn.execute(sql, tuple(row[c] for c in columns))

    # -- event ingestion ----------------------------------------------------------
    def upsert_event(self, event: Mapping[str, Any]) -> bool:
        """Ingest one canonical event. Returns ``True`` only for a new event_id."""
        try:
            inserted = self._upsert_event_savepoint(event)
            self._clear_event_failure(event)
            self._conn.commit()
            return inserted
        except Exception:
            self._conn.rollback()
            raise

    def upsert_events(self, events: Iterable[Mapping[str, Any]]) -> int:
        """Bulk-ingest while isolating one event-level projection failure.

        Each raw+derived event remains atomic under its savepoint.  A derivation or
        identity failure records only a stable, content-free diagnostic and permits
        later valid events to commit; replay removes that diagnostic when the event
        projects successfully.  Database/transaction failures still abort the batch.
        """
        count = 0
        for event in events:
            reason_code: str | None = None
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                inserted = self._upsert_event_savepoint(event)
                self._clear_event_failure(event)
            except EventDerivationFailed:
                reason_code = "EVENT_DERIVATION_FAILED"
                self._conn.rollback()
            except EventIdentityCollision:
                reason_code = "EVENT_IDENTITY_COLLISION"
                self._conn.rollback()
            except EventValidationFailed:
                reason_code = "EVENT_VALIDATION_FAILED"
                self._conn.rollback()
            except Exception:
                self._conn.rollback()
                raise
            else:
                self._conn.commit()
                if inserted:
                    count += 1

            if reason_code is not None:
                # The raw/derived event transaction is already gone.  The bounded
                # diagnostic has its own commit and can never make partial rows durable.
                try:
                    self._record_bulk_event_failure(event, reason_code)
                    self._conn.commit()
                except Exception:
                    self._conn.rollback()
                    raise
        return count

    @staticmethod
    def _bulk_diagnostic_id(event: Mapping[str, Any]) -> str:
        return "dia_" + canonical_digest(
            {"kind": "bulk-event-projection", "event_id": event["event_id"]}
        )

    def _record_bulk_event_failure(self, event: Mapping[str, Any], reason_code: str) -> None:
        """Record a bounded failure classification in its own transaction."""
        event_ref = event.get("event_id")
        trace_id = event.get("trace_id")
        if not isinstance(event_ref, str) or _EVENT_REF_RE.fullmatch(event_ref) is None:
            return
        if not isinstance(trace_id, str) or _TRACE_REF_RE.fullmatch(trace_id) is None:
            return
        self._conn.execute(
            "INSERT INTO derived_diagnostic ("
            "diagnostic_id, trace_id, project_id, coverage_class, reason_code, "
            "event_ref, segment_name, recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(diagnostic_id) DO UPDATE SET "
            "coverage_class=excluded.coverage_class, reason_code=excluded.reason_code, "
            "recorded_at=excluded.recorded_at",
            (
                self._bulk_diagnostic_id(event),
                trace_id,
                self._paths.project_id,
                CoverageClass.CORRUPT_SEGMENT,
                reason_code,
                event_ref,
                None,
                _now_iso(),
            ),
        )

    def _clear_event_failure(self, event: Mapping[str, Any]) -> None:
        """Clear only transient diagnostics proven repaired by this exact replay."""
        event_ref = event.get("event_id")
        if not isinstance(event_ref, str) or _EVENT_REF_RE.fullmatch(event_ref) is None:
            return
        self._conn.execute(
            "DELETE FROM derived_diagnostic "
            "WHERE diagnostic_id=? OR (event_ref=? AND reason_code=?)",
            (
                self._bulk_diagnostic_id(event),
                event_ref,
                "EVENT_DERIVATION_FAILED",
            ),
        )

    def _upsert_event_savepoint(self, event: Mapping[str, Any]) -> bool:
        """Atomically project one source event and every row derived from it."""
        savepoint = "aether_event_projection"
        self._conn.execute(f"SAVEPOINT {savepoint}")
        try:
            inserted = self._insert_event_row(event)
            if inserted:
                try:
                    if self._is_native_semantic_duplicate(event):
                        self._derive_native_semantic_duplicate(event)
                    else:
                        self._derive(event)
                except Exception:
                    raise EventDerivationFailed("event derivation failed") from None
                self._conn.execute(
                    "INSERT INTO event_derivation (event_id, derived_at) VALUES (?, ?)",
                    (event["event_id"], _now_iso()),
                )
            elif not self._has_derivation_proof(event):
                raise ProjectionRebuildRequired("projection derivation proof is missing")
        except Exception:
            self._conn.execute(f"ROLLBACK TO {savepoint}")
            self._conn.execute(f"RELEASE {savepoint}")
            raise
        else:
            self._conn.execute(f"RELEASE {savepoint}")
            return inserted

    def _is_native_semantic_duplicate(self, event: Mapping[str, Any]) -> bool:
        """Whether another retained envelope already owns this native semantic fact."""

        reconciliation_key = _projection_native_key(event)
        if reconciliation_key is None:
            return False
        rows = self._conn.execute(
            "SELECT payload_json FROM observation_event "
            "WHERE trace_id=? AND native_identity_key=? AND event_id<>?",
            (event["trace_id"], reconciliation_key, event["event_id"]),
        ).fetchall()
        disposition = native_disposition(dict(event))
        return any(
            native_disposition(json.loads(payload_json)) == disposition for (payload_json,) in rows
        )

    def _derive_native_semantic_duplicate(self, event: Mapping[str, Any]) -> None:
        """Keep raw/proof rows without incrementing semantic aggregate counters.

        Bound-unit projection is recomputed because a later explicit product parent may
        name this particular envelope. Other native derived rows already have an
        equivalent semantic owner and are intentionally left unchanged.
        """

        if event["event_type"] in ("work_unit.bound", "work_unit.unbound", "work_unit.status"):
            self._derive_bound_work_unit(event)

    def _has_derivation_proof(self, event: Mapping[str, Any]) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM event_derivation WHERE event_id=?", (event["event_id"],)
        ).fetchone()
        if row is not None:
            return True
        row = self._conn.execute(
            "SELECT 1 FROM event_derivation d "
            "JOIN observation_event e ON e.event_id=d.event_id "
            "WHERE e.producer_epoch=? AND e.producer_seq=?",
            (event["producer_epoch"], event["producer_seq"]),
        ).fetchone()
        return row is not None

    def _insert_event_row(self, event: Mapping[str, Any]) -> bool:
        try:
            validate_event(dict(event))
            assert_clean(event)  # defence in depth: never persist a forbidden field.
        except Exception:
            raise EventValidationFailed("event validation failed") from None
        actor = event.get("actor") or {}
        tool = event.get("tool") or {}
        coverage = event.get("coverage") or {}
        payload_json = canonical_json_str(event)
        reconciliation_key = _projection_native_key(event)
        row = (
            event["event_id"],
            reconciliation_key,
            event["trace_id"],
            event["project_id"],
            event["producer_epoch"],
            event["producer_seq"],
            event["collector_version"],
            event["runtime_fingerprint"],
            event.get("normalizer_ref"),
            event["source_kind"],
            event.get("source_hook"),
            event.get("contract_id"),
            event.get("task_id"),
            event.get("run_id"),
            event.get("session_id"),
            event.get("turn_id"),
            event.get("api_request_id"),
            event.get("parent_event_id"),
            event["occurred_at"],
            event.get("source_utc_offset_minutes"),
            event.get("monotonic_ns"),
            actor.get("kind"),
            actor.get("id"),
            actor.get("profile"),
            actor.get("role"),
            event["event_type"],
            event["status"],
            event["recorded_at"],
            event.get("timestamp_source"),
            tool.get("call_id"),
            tool.get("name"),
            tool.get("category"),
            coverage.get("class"),
            payload_json,
        )
        cur = self._conn.execute(
            """
            INSERT OR IGNORE INTO observation_event (
                event_id, native_identity_key, trace_id, project_id, producer_epoch, producer_seq,
                collector_version, runtime_fingerprint, normalizer_ref, source_kind,
                source_hook, contract_id, task_id, run_id, session_id, turn_id,
                api_request_id, parent_event_id, occurred_at,
                source_utc_offset_minutes, monotonic_ns, actor_kind, actor_id,
                actor_profile, actor_role, event_type, status, recorded_at,
                timestamp_source, tool_call_id, tool_name, tool_category,
                coverage_class, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                      ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            row,
        )
        if cur.rowcount > 0:
            return True

        # INSERT OR IGNORE may mean an exact replay, or it may mean evidence bytes
        # attempted to reuse an event/producer-sequence identity. Native identity is a
        # non-unique lookup key: distinct envelopes remain raw rows because an explicit
        # causal parent may name any one of them. Reducer reconciliation chooses only
        # unreferenced representatives.
        existing = self._conn.execute(
            "SELECT payload_json, native_identity_key FROM observation_event WHERE event_id=?",
            (event["event_id"],),
        ).fetchone()
        if existing is None:
            existing = self._conn.execute(
                "SELECT payload_json, native_identity_key FROM observation_event "
                "WHERE producer_epoch=? AND producer_seq=?",
                (event["producer_epoch"], event["producer_seq"]),
            ).fetchone()
        if existing is None or existing[0] != payload_json:
            raise EventIdentityCollision("observation event identity collision")
        return False

    def _derive(self, event: Mapping[str, Any]) -> None:
        self._touch_trace(event)
        self._touch_participant(event)
        event_type = event["event_type"]
        if event_type in _TOOL_EVENT_TYPES:
            self._derive_tool_span(event)
        elif event_type in ("decision.recorded", "decision.superseded", "decision.rejected"):
            self._derive_contract_decision(event)
        elif event_type == "contract.revision":
            self._derive_contract_revision(event)
        elif event_type in ("work_unit.bound", "work_unit.unbound", "work_unit.status"):
            self._derive_bound_work_unit(event)
        elif event_type in ("run.started", "run.finished"):
            self._derive_work_unit_run(event)
        elif event_type in ("review.requested", "review.approved", "review.changes_requested"):
            self._derive_review_transition(event)
        elif event_type in ("acceptance.declared", "acceptance.evaluated"):
            self._derive_acceptance_criterion(event)
        elif event_type in ("invariant.passed", "invariant.failed"):
            self._derive_invariant_transition(event)
        elif event_type in ("coverage.gap", "coverage.restored"):
            self._derive_coverage_gap(event)
        elif event_type == "configuration.observed":
            self._derive_configuration_fingerprint(event)
        elif event_type in (
            "model.request_started",
            "model.request_completed",
            "model.request_failed",
            "context.compression_observed",
            "context.overflow_observed",
        ):
            self._derive_model_request_economics(event)
        elif event_type == "tool_surface.observed":
            self._derive_tool_surface_snapshot(event)
        elif event_type == "dispatch.observed":
            self._derive_dispatch_observation(event)
        elif event_type == "bottleneck.attributed":
            self._derive_attribution(event, "bottleneck_interval")
        elif event_type == "defect.attributed":
            self._derive_attribution(event, "defect_attribution")

    def _touch_trace(self, event: Mapping[str, Any]) -> None:
        trace_id = event["trace_id"]
        occurred_at = event["occurred_at"]
        event_type = event["event_type"]
        contract_id = event.get("contract_id")
        existing = self._conn.execute(
            "SELECT opened_at, last_event_at, event_count, termination "
            "FROM observation_trace WHERE trace_id=?",
            (trace_id,),
        ).fetchone()
        if existing is None:
            opened_at, last_event_at, event_count, termination = (
                occurred_at,
                occurred_at,
                0,
                "open",
            )
        else:
            opened_at, last_event_at, event_count, termination = existing
            if opened_at is None or occurred_at < opened_at:
                opened_at = occurred_at
            if last_event_at is None or occurred_at > last_event_at:
                last_event_at = occurred_at

        row: dict[str, Any] = {
            "trace_id": trace_id,
            "project_id": event["project_id"],
            "opened_at": opened_at,
            "last_event_at": last_event_at,
            "last_event_id": event["event_id"],
            "event_count": event_count + 1,
        }
        if contract_id is not None:
            row["contract_id"] = contract_id
        # A raw terminal-shaped envelope is evidence, not authority.  In particular,
        # actor/profile/role strings inside that envelope cannot prove that the product
        # assigned the actor to terminate this trace.  Keep the read-side trace open
        # until ``record_summary`` mirrors the pure reducer's authority-checked result;
        # otherwise a forged or authority-unavailable event disappears from a no-REF
        # query before the reducer can surface its coverage gap.
        if event_type in ("trace.opened", "trace.resumed") and termination == "open":
            row["termination"] = "open"
            row["closed_at"] = None
        self._upsert("observation_trace", row, ("trace_id",))

    def _touch_participant(self, event: Mapping[str, Any]) -> None:
        actor = event.get("actor") or {}
        actor_kind = actor.get("kind")
        actor_id = actor.get("id")
        if not actor_kind or not actor_id:
            return
        trace_id = event["trace_id"]
        existing = self._conn.execute(
            "SELECT action_total, actions_json FROM participant_contribution "
            "WHERE trace_id=? AND actor_kind=? AND actor_id=?",
            (trace_id, actor_kind, actor_id),
        ).fetchone()
        if existing is None:
            action_total, actions = 0, {}
        else:
            action_total, actions_json = existing
            actions = json.loads(actions_json) if actions_json else {}
        event_type = event["event_type"]
        actions[event_type] = actions.get(event_type, 0) + 1
        row = {
            "trace_id": trace_id,
            "actor_kind": actor_kind,
            "actor_id": actor_id,
            "project_id": event["project_id"],
            "profile": actor.get("profile"),
            "role": actor.get("role"),
            "action_total": action_total + 1,
            "actions_json": canonical_json_str(actions),
            "last_event_id": event["event_id"],
            "last_event_at": event["occurred_at"],
        }
        self._upsert("participant_contribution", row, ("trace_id", "actor_kind", "actor_id"))

    def _derive_tool_span(self, event: Mapping[str, Any]) -> None:
        tool = event.get("tool") or {}
        call_id = tool.get("call_id")
        if not call_id:
            return
        actor = event.get("actor") or {}
        row: dict[str, Any] = {
            "trace_id": event["trace_id"],
            "session_id": event.get("session_id") or "",
            "call_id": call_id,
            "project_id": event["project_id"],
            "name": tool.get("name"),
            "category": tool.get("category"),
            "target_kind": tool.get("target_kind"),
            "target_ref": tool.get("target_ref"),
            "actor_kind": actor.get("kind"),
            "actor_id": actor.get("id"),
        }
        if event["event_type"] == "tool.started":
            row["started_at"] = event["occurred_at"]
            row["started_event_id"] = event["event_id"]
        else:
            row["terminal_status"] = event["status"]
            row["terminal_event_id"] = event["event_id"]
            row["ended_at"] = event["occurred_at"]
            row["duration_ms"] = tool.get("duration_ms")
            row["exit_code"] = tool.get("exit_code")
            row["error_class"] = tool.get("error_class")
            row["approval_outcome"] = tool.get("approval_outcome")
            row["retry_count"] = tool.get("retry_count")
            row["retry_of_call_id"] = tool.get("retry_of_call_id")
        self._upsert("tool_span", row, ("trace_id", "session_id", "call_id"))

    def _derive_contract_decision(self, event: Mapping[str, Any]) -> None:
        contract = event.get("contract") or {}
        row = {
            "event_id": event["event_id"],
            "trace_id": event["trace_id"],
            "project_id": event["project_id"],
            "contract_id": event.get("contract_id"),
            "decision_kind": event["event_type"],
            "status": event["status"],
            "occurred_at": event["occurred_at"],
            "revision": contract.get("revision"),
            "artifact_ref": contract.get("artifact_ref"),
            "before_sha256": contract.get("before_sha256"),
            "after_sha256": contract.get("after_sha256"),
            "decision_refs_json": canonical_json_str(contract.get("decision_refs") or []),
            "supersedes_decision_ref": contract.get("supersedes_decision_ref"),
            "evidence_refs_json": canonical_json_str(contract.get("evidence_refs") or []),
            "ambiguity_ref": contract.get("ambiguity_ref"),
            "invariant_key": contract.get("invariant_key"),
            "semantic_delta": contract.get("semantic_delta"),
        }
        self._upsert("contract_decision", row, ("event_id",))

    def _derive_contract_revision(self, event: Mapping[str, Any]) -> None:
        contract = event.get("contract") or {}
        row = {
            "event_id": event["event_id"],
            "trace_id": event["trace_id"],
            "project_id": event["project_id"],
            "contract_id": event.get("contract_id"),
            "revision": contract.get("revision"),
            "occurred_at": event["occurred_at"],
            "artifact_ref": contract.get("artifact_ref"),
            "before_sha256": contract.get("before_sha256"),
            "after_sha256": contract.get("after_sha256"),
            "decision_refs_json": canonical_json_str(contract.get("decision_refs") or []),
            "evidence_refs_json": canonical_json_str(contract.get("evidence_refs") or []),
        }
        self._upsert("contract_revision", row, ("event_id",))

    def _exact_work_unit_classification(
        self,
        *,
        trace_id: str,
        task_ref: Any,
        binding_ref: str,
    ) -> tuple[str, int | None] | None:
        """Return the deterministic product classification already retained raw.

        One exact value refines native ``unknown``/``null``. Multiple incompatible
        product values have no winner and deliberately project as ``unknown``/``null``;
        reconciliation exposes the conflict from the preserved source rows.
        """

        product_values: set[tuple[str, int]] = set()
        native_relations: set[str] = set()
        native_requirements: set[int] = set()
        rows = self._conn.execute(
            "SELECT payload_json FROM observation_event WHERE trace_id=? "
            "AND event_type IN ('work_unit.bound', 'work_unit.unbound')",
            (trace_id,),
        ).fetchall()
        candidates = [json.loads(payload_json) for (payload_json,) in rows]
        relevant = [
            candidate
            for candidate in candidates
            if (candidate.get("work_unit") or {}).get("task_ref") == task_ref
            and (candidate.get("work_unit") or {}).get("binding_ref") == binding_ref
        ]
        native_parent_ids = {
            candidate["event_id"]
            for candidate in relevant
            if candidate.get("source_kind") in {"hermes_hook", "native_reconciliation"}
            and candidate.get("event_type") in {"work_unit.bound", "work_unit.unbound"}
        }
        for candidate in relevant:
            unit = candidate.get("work_unit") or {}
            relation = unit.get("relation")
            required = unit.get("required")
            if candidate.get("source_kind") == "aether_checkpoint":
                if candidate.get("event_type") != "work_unit.bound":
                    continue
                actor = candidate.get("actor") or {}
                routed = self._authority_context.checkpoint_principal(
                    "work_unit.bound",
                    task_ref=task_ref if isinstance(task_ref, str) else None,
                )
                principal = self._authority_context.resolve_principal(
                    actor_id=actor.get("id"),
                    profile=actor.get("profile"),
                    role=actor.get("role"),
                )
                if routed is None or principal != routed:
                    self._record_classification_gap(
                        candidate,
                        "WORK_UNIT_CLASSIFICATION_AUTHORITY_UNVERIFIED",
                    )
                    continue
                if candidate.get("parent_event_id") not in native_parent_ids:
                    self._record_classification_gap(
                        candidate,
                        "WORK_UNIT_CLASSIFICATION_BINDING_UNVERIFIED",
                    )
                    continue
                self._clear_classification_gap(candidate)
                if (
                    relation != "unknown"
                    and isinstance(relation, str)
                    and isinstance(required, bool)
                ):
                    product_values.add((relation, _bool_to_int(required) or 0))
            elif candidate.get("event_type") == "work_unit.bound" and candidate.get(
                "source_kind"
            ) in {"hermes_hook", "native_reconciliation"}:
                if isinstance(relation, str) and relation != "unknown":
                    native_relations.add(relation)
                if isinstance(required, bool):
                    native_requirements.add(_bool_to_int(required) or 0)
        if not product_values:
            return None
        if len(product_values) != 1:
            return ("unknown", None)
        relation, required = next(iter(product_values))
        if any(value != relation for value in native_relations) or any(
            value != required for value in native_requirements
        ):
            return ("unknown", None)
        return relation, required

    @staticmethod
    def _classification_diagnostic_id(event: Mapping[str, Any]) -> str:
        return "dia_" + canonical_digest(
            {
                "kind": "work-unit-classification-authority",
                "event_id": event["event_id"],
            }
        )

    def _record_classification_gap(
        self,
        event: Mapping[str, Any],
        reason_code: str,
    ) -> None:
        self._conn.execute(
            "INSERT INTO derived_diagnostic ("
            "diagnostic_id, trace_id, project_id, coverage_class, reason_code, "
            "event_ref, segment_name, recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(diagnostic_id) DO UPDATE SET "
            "coverage_class=excluded.coverage_class, reason_code=excluded.reason_code, "
            "recorded_at=excluded.recorded_at",
            (
                self._classification_diagnostic_id(event),
                event["trace_id"],
                event["project_id"],
                CoverageClass.RECONCILIATION_AMBIGUOUS,
                reason_code,
                event["event_id"],
                None,
                _now_iso(),
            ),
        )

    def _clear_classification_gap(self, event: Mapping[str, Any]) -> None:
        self._conn.execute(
            "DELETE FROM derived_diagnostic WHERE diagnostic_id=?",
            (self._classification_diagnostic_id(event),),
        )

    def _native_work_unit_events(
        self,
        *,
        trace_id: str,
        task_ref: Any,
        binding_ref: str,
    ) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT payload_json FROM observation_event WHERE trace_id=? "
            "AND event_type IN ('work_unit.bound', 'work_unit.unbound', 'work_unit.status') "
            "AND source_kind IN ('hermes_hook', 'native_reconciliation')",
            (trace_id,),
        ).fetchall()
        events = []
        for (payload_json,) in rows:
            candidate = json.loads(payload_json)
            unit = candidate.get("work_unit") or {}
            if unit.get("task_ref") == task_ref and unit.get("binding_ref") == binding_ref:
                events.append(candidate)
        return causal_order(events)

    def _derive_bound_work_unit(self, event: Mapping[str, Any]) -> None:
        work_unit = event.get("work_unit") or {}
        binding_ref = work_unit.get("binding_ref")
        if not binding_ref:
            return
        trace_id = event["trace_id"]
        task_ref = work_unit.get("task_ref")
        classification = self._exact_work_unit_classification(
            trace_id=trace_id,
            task_ref=task_ref,
            binding_ref=binding_ref,
        )
        native_events = self._native_work_unit_events(
            trace_id=trace_id,
            task_ref=task_ref,
            binding_ref=binding_ref,
        )
        # Product classification owns only relation/required. Without a retained
        # native fact it cannot create or resurrect a binding projection.
        if not native_events:
            return

        native_relations: set[str] = set()
        native_requirements: set[int] = set()
        bound_at: str | None = None
        unbound_at: str | None = None
        latest = native_events[-1]
        latest_unit = latest.get("work_unit") or {}
        for candidate in native_events:
            candidate_unit = candidate.get("work_unit") or {}
            relation = candidate_unit.get("relation")
            required = candidate_unit.get("required")
            if isinstance(relation, str) and relation != "unknown":
                native_relations.add(relation)
            if isinstance(required, bool):
                native_requirements.add(_bool_to_int(required) or 0)
            if candidate.get("event_type") == "work_unit.bound":
                bound_at = candidate["occurred_at"]
                unbound_at = None
            elif candidate.get("event_type") == "work_unit.unbound":
                unbound_at = candidate["occurred_at"]

        native_relation = next(iter(native_relations)) if len(native_relations) == 1 else "unknown"
        native_required = next(iter(native_requirements)) if len(native_requirements) == 1 else None
        row: dict[str, Any] = {
            "binding_ref": binding_ref,
            "trace_id": trace_id,
            "project_id": latest["project_id"],
            "task_ref": task_ref,
            "relation": native_relation,
            "required": native_required,
            "parent_task_refs_json": canonical_json_str(latest_unit.get("parent_task_refs") or []),
            "task_status": latest_unit.get("task_status"),
            "run_status": latest_unit.get("run_status"),
            "run_outcome": latest_unit.get("run_outcome"),
            "bound_at": bound_at,
            "unbound_at": unbound_at,
            "last_event_id": latest["event_id"],
            "last_event_at": latest["occurred_at"],
        }
        if classification is not None:
            row["relation"], row["required"] = classification
        self._upsert("bound_work_unit", row, ("binding_ref",))

    def _derive_work_unit_run(self, event: Mapping[str, Any]) -> None:
        work_unit = event.get("work_unit") or {}
        run_id = event.get("run_id")
        if run_id is None:
            return
        row: dict[str, Any] = {
            "trace_id": event["trace_id"],
            "run_id": run_id,
            "project_id": event["project_id"],
            "binding_ref": work_unit.get("binding_ref"),
            "task_ref": work_unit.get("task_ref"),
            "run_status": work_unit.get("run_status"),
            "run_outcome": work_unit.get("run_outcome"),
            "last_event_id": event["event_id"],
        }
        if event["event_type"] == "run.started":
            row["started_at"] = event["occurred_at"]
        else:
            row["finished_at"] = event["occurred_at"]
        self._upsert("work_unit_run", row, ("trace_id", "run_id"))

    def _derive_review_transition(self, event: Mapping[str, Any]) -> None:
        work_unit = event.get("work_unit") or {}
        actor = event.get("actor") or {}
        row = {
            "event_id": event["event_id"],
            "trace_id": event["trace_id"],
            "project_id": event["project_id"],
            "binding_ref": work_unit.get("binding_ref"),
            "task_ref": work_unit.get("task_ref"),
            "transition": event["event_type"],
            "run_id": event.get("run_id"),
            "actor_kind": actor.get("kind"),
            "actor_id": actor.get("id"),
            "occurred_at": event["occurred_at"],
        }
        self._upsert("review_transition", row, ("event_id",))

    def _derive_acceptance_criterion(self, event: Mapping[str, Any]) -> None:
        acceptance = event.get("acceptance") or {}
        criterion_ref = acceptance.get("criterion_ref")
        if not criterion_ref:
            return
        row = {
            "trace_id": event["trace_id"],
            "criterion_ref": criterion_ref,
            "project_id": event["project_id"],
            "state": acceptance.get("state"),
            "evidence_refs_json": canonical_json_str(acceptance.get("evidence_refs") or []),
            "assigned_task_ref": acceptance.get("assigned_task_ref"),
            "review_task_ref": acceptance.get("review_task_ref"),
            "last_event_id": event["event_id"],
            "last_event_at": event["occurred_at"],
        }
        self._upsert("acceptance_criterion", row, ("trace_id", "criterion_ref"))

    def _derive_invariant_transition(self, event: Mapping[str, Any]) -> None:
        contract = event.get("contract") or {}
        invariant_key = contract.get("invariant_key")
        if not invariant_key:
            return
        row = {
            "trace_id": event["trace_id"],
            "invariant_key": invariant_key,
            "project_id": event["project_id"],
            "state": event["status"],
            "last_event_id": event["event_id"],
            "last_event_at": event["occurred_at"],
        }
        self._upsert("invariant_transition", row, ("trace_id", "invariant_key"))

    def _derive_coverage_gap(self, event: Mapping[str, Any]) -> None:
        coverage = event.get("coverage") or {}
        row = {
            "event_id": event["event_id"],
            "trace_id": event["trace_id"],
            "project_id": event["project_id"],
            "coverage_class": coverage.get("class"),
            "reason_code": coverage.get("reason_code"),
            "started_at": coverage.get("started_at"),
            "ended_at": coverage.get("ended_at"),
            "restored": 1 if event["event_type"] == "coverage.restored" else 0,
            "occurred_at": event["occurred_at"],
        }
        self._upsert("coverage_gap", row, ("event_id",))

    def _derive_configuration_fingerprint(self, event: Mapping[str, Any]) -> None:
        configuration = event.get("configuration") or {}
        fingerprint_id = configuration.get("fingerprint_id")
        if not fingerprint_id:
            return
        trace_id = event["trace_id"]
        existing = self._conn.execute(
            "SELECT 1 FROM configuration_fingerprint WHERE trace_id=? AND fingerprint_id=?",
            (trace_id, fingerprint_id),
        ).fetchone()
        row: dict[str, Any] = {
            "trace_id": trace_id,
            "fingerprint_id": fingerprint_id,
            "project_id": event["project_id"],
            "scope": configuration.get("scope"),
            "participant_ref": configuration.get("participant_ref"),
            "model": configuration.get("model"),
            "provider": configuration.get("provider"),
            "system_prompt_fingerprint": configuration.get("system_prompt_fingerprint"),
            "observed_skill_set_fingerprint": configuration.get("observed_skill_set_fingerprint"),
            "declared_toolset_fingerprint": configuration.get("declared_toolset_fingerprint"),
            "effective_tool_surface_fingerprint": configuration.get(
                "effective_tool_surface_fingerprint"
            ),
            "global_concurrency_limit": configuration.get("global_concurrency_limit"),
            "per_profile_concurrency_limit": configuration.get("per_profile_concurrency_limit"),
            "observer_version": configuration.get("observer_version"),
            "fingerprint_key_id": configuration.get("fingerprint_key_id"),
            "runtime_fingerprint": configuration.get("runtime_fingerprint"),
            "field_coverage_json": canonical_json_str(configuration.get("field_coverage") or {}),
        }
        if existing is None:
            row["first_event_id"] = event["event_id"]
            row["first_seen_at"] = event["occurred_at"]
        self._upsert("configuration_fingerprint", row, ("trace_id", "fingerprint_id"))

    def _derive_model_request_economics(self, event: Mapping[str, Any]) -> None:
        model_request = event.get("model_request") or {}
        request_ref = model_request.get("request_ref")
        if not request_ref:
            return
        attempt = model_request.get("attempt_count")
        if not isinstance(attempt, int) or isinstance(attempt, bool) or attempt < 1:
            return
        row: dict[str, Any] = {
            "trace_id": event["trace_id"],
            "session_id": event.get("session_id") or "",
            "request_ref": request_ref,
            "attempt_count": attempt,
            "project_id": event["project_id"],
            "last_event_id": event["event_id"],
        }
        event_type = event["event_type"]
        if event_type not in ("context.compression_observed", "context.overflow_observed"):
            row["state"] = model_request.get("state")
            for field in (
                "model",
                "provider",
                "response_model",
                "duration_ms",
                "finish_reason",
                "message_count",
                "tool_count",
                "input_tokens",
                "output_tokens",
                "cache_read_tokens",
                "cache_write_tokens",
                "reasoning_tokens",
                "total_tokens",
                "usage_coverage",
                "structured_reason_code",
            ):
                value = model_request.get(field)
                if value is not None:
                    row[field] = value
        if event_type == "model.request_started":
            row["started_at"] = event["occurred_at"]
        elif event_type in ("model.request_completed", "model.request_failed"):
            row["ended_at"] = event["occurred_at"]
        elif event_type == "context.compression_observed":
            row["context_compressed"] = 1
        elif event_type == "context.overflow_observed":
            row["context_overflow"] = 1
        self._upsert(
            "model_request_economics",
            row,
            ("trace_id", "session_id", "request_ref", "attempt_count"),
        )

    def _derive_tool_surface_snapshot(self, event: Mapping[str, Any]) -> None:
        tool_surface = event.get("tool_surface") or {}
        request_ref = tool_surface.get("request_ref")
        if not request_ref:
            return
        row = {
            "trace_id": event["trace_id"],
            "session_id": event.get("session_id") or "",
            "request_ref": request_ref,
            "project_id": event["project_id"],
            "completeness": tool_surface.get("completeness"),
            "declared_toolset_fingerprint": tool_surface.get("declared_toolset_fingerprint"),
            "effective_direct_surface_fingerprint": tool_surface.get(
                "effective_direct_surface_fingerprint"
            ),
            "effective_deferred_surface_fingerprint": tool_surface.get(
                "effective_deferred_surface_fingerprint"
            ),
            "observed_tool_count": tool_surface.get("observed_tool_count"),
            "granted_tool_refs_json": canonical_json_str(
                tool_surface.get("granted_tool_refs") or []
            ),
            "never_used_tool_refs_json": canonical_json_str(
                tool_surface.get("never_used_tool_refs") or []
            ),
            "schema_serialized_bytes": tool_surface.get("schema_serialized_bytes"),
            "schema_estimated_tokens": tool_surface.get("schema_estimated_tokens"),
            "estimator_ref": tool_surface.get("estimator_ref"),
            "fingerprint_key_id": tool_surface.get("fingerprint_key_id"),
            "occurred_at": event["occurred_at"],
            "event_id": event["event_id"],
        }
        self._upsert(
            "tool_surface_snapshot",
            row,
            ("trace_id", "session_id", "request_ref"),
        )

    def _derive_dispatch_observation(self, event: Mapping[str, Any]) -> None:
        dispatch = event.get("dispatch") or {}
        tick_ref = dispatch.get("tick_ref")
        if not tick_ref:
            return
        row = {
            "trace_id": event["trace_id"],
            "tick_ref": tick_ref,
            "project_id": event["project_id"],
            "outcome": dispatch.get("outcome"),
            "eligible_count": dispatch.get("eligible_count"),
            "running_count": dispatch.get("running_count"),
            "global_limit": dispatch.get("global_limit"),
            "per_profile_limit": dispatch.get("per_profile_limit"),
            "bottleneck_class": dispatch.get("bottleneck_class"),
            "precision_ms": dispatch.get("precision_ms"),
            "evidence_refs_json": canonical_json_str(dispatch.get("evidence_refs") or []),
            "occurred_at": event["occurred_at"],
            "event_id": event["event_id"],
        }
        self._upsert("dispatch_observation", row, ("trace_id", "tick_ref"))

    def _derive_attribution(self, event: Mapping[str, Any], table: str) -> None:
        attribution = event.get("attribution") or {}
        row = {
            "event_id": event["event_id"],
            "trace_id": event["trace_id"],
            "project_id": event["project_id"],
            "attribution_class": attribution.get("class"),
            "provenance": attribution.get("provenance"),
            "started_at": attribution.get("started_at"),
            "ended_at": attribution.get("ended_at"),
            "precision_ms": attribution.get("precision_ms"),
            "evidence_refs_json": canonical_json_str(attribution.get("evidence_refs") or []),
            "occurred_at": event["occurred_at"],
        }
        self._upsert(table, row, ("event_id",))

    # -- summary storage ----------------------------------------------------------
    def record_summary(self, summary: Mapping[str, Any]) -> bool:
        """Store one immutable canonical summary. Returns ``True`` for a new summary_id.

        Also fans the reducer's already-synthesized process steps/waves/rounds out
        into indexed tables; every other logical table is populated incrementally
        from raw events (:meth:`upsert_event`), never duplicated here.
        """
        payload = dict(summary)
        validate_summary(payload)
        assert_clean(payload)
        cur = self._conn.execute(
            """
            INSERT OR IGNORE INTO observation_summary (
                summary_id, trace_id, project_id, contract_id, reducer_version,
                as_of, completion_state, source_event_count, recorded_at, canonical_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["summary_id"],
                payload["trace_id"],
                payload["project_id"],
                payload.get("contract_id"),
                payload["reducer_version"],
                payload["as_of"],
                payload["completion_state"],
                payload["source_event_count"],
                _now_iso(),
                canonical_json_str(payload),
            ),
        )
        inserted = cur.rowcount > 0
        if inserted:
            self._fan_out_summary(payload)

        # ``trace.closed`` is only a lifecycle boundary.  It is not proof that the
        # required work graph and acceptance criteria were settled; only the pure
        # reducer can make that determination.  Mirror its conclusion into the
        # trace index so a later no-REF query does not classify a merely closed
        # journal as successfully completed (OBS-FR-047/049).
        runtime_state = payload.get("runtime_state") or {}
        timestamps = payload.get("timestamps") or {}
        termination = runtime_state.get("termination")
        if isinstance(termination, str):
            self._conn.execute(
                "UPDATE observation_trace SET termination=?, closed_at=? "
                "WHERE trace_id=? AND project_id=?",
                (
                    termination,
                    timestamps.get("closed_at"),
                    payload["trace_id"],
                    payload["project_id"],
                ),
            )
        self._conn.commit()
        return inserted

    def _fan_out_summary(self, summary: Mapping[str, Any]) -> None:
        trace_id = summary["trace_id"]
        project_id = summary["project_id"]
        summary_id = summary["summary_id"]
        process = summary.get("process") or {}

        for step in process.get("steps") or []:
            self._upsert(
                "process_step",
                {
                    "trace_id": trace_id,
                    "step_id": step["step_id"],
                    "project_id": project_id,
                    "step_index": step.get("index"),
                    "kind": step.get("kind"),
                    "participant_ref": step.get("participant_ref"),
                    "task_refs_json": canonical_json_str(step.get("task_refs") or []),
                    "run_refs_json": canonical_json_str(step.get("run_refs") or []),
                    "predecessor_step_ids_json": canonical_json_str(
                        step.get("predecessor_step_ids") or []
                    ),
                    "round_id": step.get("round_id"),
                    "wave_id": step.get("wave_id"),
                    "started_at": step.get("started_at"),
                    "ended_at": step.get("ended_at"),
                    "duration_ms": step.get("duration_ms"),
                    "outcome": step.get("outcome"),
                    "semantic_delta": _bool_to_int(step.get("semantic_delta")),
                    "evidence_event_ids_json": canonical_json_str(
                        step.get("evidence_event_ids") or []
                    ),
                    "coverage": step.get("coverage"),
                    "source_summary_id": summary_id,
                },
                ("trace_id", "step_id"),
            )

        for wave in process.get("waves") or []:
            self._upsert(
                "process_wave",
                {
                    "trace_id": trace_id,
                    "wave_id": wave["wave_id"],
                    "project_id": project_id,
                    "round_id": wave.get("round_id"),
                    "step_ids_json": canonical_json_str(wave.get("step_ids") or []),
                    "work_unit_refs_json": canonical_json_str(wave.get("work_unit_refs") or []),
                    "participant_refs_json": canonical_json_str(wave.get("participant_refs") or []),
                    "deployed_unit_count": wave.get("deployed_unit_count"),
                    "peak_parallelism": wave.get("peak_parallelism"),
                    "eligible_unit_count_observed": wave.get("eligible_unit_count_observed"),
                    "ready_but_not_running_count_observed": wave.get(
                        "ready_but_not_running_count_observed"
                    ),
                    "ready_but_not_running_ms_observed": wave.get(
                        "ready_but_not_running_ms_observed"
                    ),
                    "global_limit": wave.get("global_limit"),
                    "per_profile_limit": wave.get("per_profile_limit"),
                    "barrier": wave.get("barrier"),
                    "sampling_precision_ms": wave.get("sampling_precision_ms"),
                    "started_at": wave.get("started_at"),
                    "ended_at": wave.get("ended_at"),
                    "duration_ms": wave.get("duration_ms"),
                    "evidence_event_ids_json": canonical_json_str(
                        wave.get("evidence_event_ids") or []
                    ),
                    "source_summary_id": summary_id,
                },
                ("trace_id", "wave_id"),
            )

        for round_ in process.get("rounds") or []:
            self._upsert(
                "execution_round",
                {
                    "trace_id": trace_id,
                    "round_id": round_["round_id"],
                    "project_id": project_id,
                    "round_index": round_.get("index"),
                    "trigger": round_.get("trigger"),
                    "previous_round_id": round_.get("previous_round_id"),
                    "step_ids_json": canonical_json_str(round_.get("step_ids") or []),
                    "wave_ids_json": canonical_json_str(round_.get("wave_ids") or []),
                    "participant_refs_json": canonical_json_str(
                        round_.get("participant_refs") or []
                    ),
                    "deployed_unit_count": round_.get("deployed_unit_count"),
                    "started_at": round_.get("started_at"),
                    "ended_at": round_.get("ended_at"),
                    "duration_ms": round_.get("duration_ms"),
                    "outcome": round_.get("outcome"),
                    "evidence_event_ids_json": canonical_json_str(
                        round_.get("evidence_event_ids") or []
                    ),
                    "source_summary_id": summary_id,
                },
                ("trace_id", "round_id"),
            )

    def get_summary(self, summary_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT canonical_json FROM observation_summary WHERE summary_id=?",
            (summary_id,),
        ).fetchone()
        return json.loads(row[0]) if row is not None else None

    def latest_summary(self, trace_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT canonical_json FROM observation_summary WHERE trace_id=? "
            "ORDER BY as_of DESC, recorded_at DESC, summary_id ASC LIMIT 1",
            (trace_id,),
        ).fetchone()
        return json.loads(row[0]) if row is not None else None

    # -- query surfaces -------------------------------------------------------
    def list_traces(self) -> list[dict[str, Any]]:
        """Return every trace plus its exact bound task references.

        This is deliberately a small read-side shape rather than a mirror of the
        internal SQL row.  It is the one surface used by ``aether observe`` to
        resolve an exact trace/contract/task reference without guessing.
        """
        rows = self._conn.execute(
            "SELECT trace_id, contract_id, termination FROM observation_trace "
            "ORDER BY opened_at, trace_id"
        ).fetchall()
        result: list[dict[str, Any]] = []
        for trace_id, contract_id, termination in rows:
            task_ids = tuple(
                row[0]
                for row in self._conn.execute(
                    "SELECT task_ref FROM bound_work_unit WHERE trace_id=? "
                    "AND unbound_at IS NULL AND task_ref IS NOT NULL ORDER BY task_ref",
                    (trace_id,),
                ).fetchall()
            )
            result.append(
                {
                    "trace_id": trace_id,
                    "contract_id": contract_id,
                    "task_ids": task_ids,
                    "termination": termination,
                }
            )
        return result

    def events_for_trace(self, trace_id: str) -> list[dict[str, Any]]:
        """Load canonical projected events for deterministic reduction.

        Ordering here is only a stable storage order.  The reducer still applies
        explicit causal/native edges before producer sequence and UTC tie-breaks.
        """
        rows = self._conn.execute(
            "SELECT payload_json FROM observation_event WHERE trace_id=? "
            "ORDER BY occurred_at, producer_epoch, producer_seq, event_id",
            (trace_id,),
        ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def trace_ids_for_epoch(self, producer_epoch: str) -> tuple[str, ...]:
        rows = self._conn.execute(
            "SELECT DISTINCT trace_id FROM observation_event WHERE producer_epoch=? "
            "ORDER BY trace_id",
            (producer_epoch,),
        ).fetchall()
        return tuple(row[0] for row in rows)

    def list_open_traces(self) -> list[OpenTrace]:
        rows = self._conn.execute(
            "SELECT trace_id, project_id, contract_id, opened_at, last_event_at "
            "FROM observation_trace WHERE closed_at IS NULL ORDER BY opened_at"
        ).fetchall()
        return [OpenTrace(*row) for row in rows]

    def resolve_ref(self, ref: str) -> str | None:
        """Resolve an exact ``trace_id`` / ``contract_id`` / bound ``task_id``."""
        row = self._conn.execute(
            "SELECT trace_id FROM observation_trace WHERE trace_id = ?", (ref,)
        ).fetchone()
        if row is not None:
            return row[0]
        row = self._conn.execute(
            "SELECT trace_id FROM observation_trace WHERE contract_id = ? "
            "ORDER BY opened_at DESC, trace_id ASC LIMIT 1",
            (ref,),
        ).fetchone()
        if row is not None:
            return row[0]
        row = self._conn.execute(
            "SELECT trace_id FROM bound_work_unit WHERE task_ref = ? "
            "ORDER BY bound_at DESC, trace_id ASC LIMIT 1",
            (ref,),
        ).fetchone()
        return row[0] if row is not None else None

    def resolve_ref_candidates(self, ref: str) -> list[str]:
        """Every distinct trace_id ``ref`` could mean, for bounded-ambiguity errors."""
        seen: dict[str, None] = {}
        for row in self._conn.execute(
            "SELECT trace_id FROM observation_trace WHERE trace_id = ? OR contract_id = ? "
            "ORDER BY opened_at",
            (ref, ref),
        ):
            seen.setdefault(row[0], None)
        for row in self._conn.execute(
            "SELECT DISTINCT trace_id FROM bound_work_unit WHERE task_ref = ?", (ref,)
        ):
            seen.setdefault(row[0], None)
        return list(seen.keys())

    # -- ingest cursor --------------------------------------------------------
    def read_cursor(self, segment_path: str) -> IngestCursor | None:
        row = self._conn.execute(
            "SELECT segment_path, producer_epoch, first_seq, last_seq, byte_length, "
            "uncompressed_sha256, ingested_at FROM ingest_cursor WHERE segment_path = ?",
            (segment_path,),
        ).fetchone()
        return IngestCursor(*row) if row is not None else None

    def write_cursor(
        self,
        *,
        segment_path: str,
        producer_epoch: str,
        first_seq: int,
        last_seq: int,
        byte_length: int,
        uncompressed_sha256: str,
    ) -> None:
        self._upsert(
            "ingest_cursor",
            {
                "segment_path": segment_path,
                "producer_epoch": producer_epoch,
                "first_seq": first_seq,
                "last_seq": last_seq,
                "byte_length": byte_length,
                "uncompressed_sha256": uncompressed_sha256,
                "ingested_at": _now_iso(),
            },
            ("segment_path",),
        )
        self._conn.commit()

    # -- quarantine indexing --------------------------------------------------
    def quarantine(
        self,
        *,
        segment_name: str,
        byte_offset: int,
        byte_length: int,
        sha256: str,
        event_schema_version: str,
        project_id: str | None = None,
    ) -> bool:
        """Index an unknown-newer event by location only; source bytes are untouched."""
        cur = self._conn.execute(
            "INSERT OR IGNORE INTO quarantine_event ("
            "segment_name, byte_offset, byte_length, sha256, event_schema_version, "
            "project_id, quarantined_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                segment_name,
                byte_offset,
                byte_length,
                sha256,
                event_schema_version,
                project_id or self._paths.project_id,
                _now_iso(),
            ),
        )
        self._conn.commit()
        return cur.rowcount > 0

    def list_quarantine(self) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT segment_name, byte_offset, byte_length, sha256, event_schema_version, "
            "project_id, quarantined_at FROM quarantine_event ORDER BY segment_name, byte_offset"
        ).fetchall()
        columns = (
            "segment_name",
            "byte_offset",
            "byte_length",
            "sha256",
            "event_schema_version",
            "project_id",
            "quarantined_at",
        )
        return [dict(zip(columns, row)) for row in rows]

    # -- reducer-owned diagnostics -------------------------------------------
    def record_derived_gap(
        self,
        *,
        diagnostic_id: str,
        trace_id: str | None,
        coverage_class: str,
        reason_code: str,
        event_ref: str,
        segment_name: str | None = None,
    ) -> bool:
        """Persist a reproducible read-model diagnostic, never a source event."""
        cur = self._conn.execute(
            "INSERT OR IGNORE INTO derived_diagnostic ("
            "diagnostic_id, trace_id, project_id, coverage_class, reason_code, "
            "event_ref, segment_name, recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                diagnostic_id,
                trace_id,
                self._paths.project_id,
                coverage_class,
                reason_code,
                event_ref,
                segment_name,
                _now_iso(),
            ),
        )
        self._conn.commit()
        return cur.rowcount > 0

    def derived_gaps(self, trace_id: str) -> list[dict[str, str]]:
        rows = self._conn.execute(
            "SELECT coverage_class, reason_code, event_ref "
            "FROM derived_diagnostic WHERE trace_id=? "
            "ORDER BY coverage_class, reason_code, event_ref",
            (trace_id,),
        ).fetchall()
        return [{"class": row[0], "reason_code": row[1], "event_id": row[2]} for row in rows]

    # -- health/storage report -------------------------------------------------
    def storage_report(self) -> StorageReport:
        from aether_agents.observation.capture.journal import list_segments

        segments = list_segments(self._paths)
        active = sum(1 for s in segments if s.state == "active")
        closed = sum(1 for s in segments if s.state == "closed")
        archive = sum(1 for s in segments if s.state == "archive")
        quarantine_segments = sum(1 for s in segments if s.state == "quarantine")

        journal_bytes = 0
        for directory in (
            self._paths.active,
            self._paths.closed,
            self._paths.archive,
            self._paths.quarantine,
        ):
            if directory.is_dir():
                for child in directory.iterdir():
                    if child.is_file():
                        journal_bytes += child.stat().st_size

        db_bytes = 0
        for suffix in ("", "-wal", "-shm"):
            candidate = self._db_path.with_name(self._db_path.name + suffix)
            if candidate.exists():
                db_bytes += candidate.stat().st_size

        event_count = self._conn.execute("SELECT COUNT(*) FROM observation_event").fetchone()[0]
        summary_count = self._conn.execute("SELECT COUNT(*) FROM observation_summary").fetchone()[0]
        quarantine_event_count = self._conn.execute(
            "SELECT COUNT(*) FROM quarantine_event"
        ).fetchone()[0]
        versions: tuple[str, ...] = ()
        if self._paths.projections.is_dir():
            versions = tuple(sorted(p.name for p in self._paths.projections.glob("*.sqlite3")))

        return StorageReport(
            project_id=self._paths.project_id,
            projection_schema=self._schema,
            projection_db_bytes=db_bytes,
            journal_bytes=journal_bytes,
            event_count=event_count,
            observation_summary_count=summary_count,
            active_segment_count=active,
            closed_segment_count=closed,
            archive_segment_count=archive,
            quarantine_segment_count=quarantine_segments,
            quarantine_event_count=quarantine_event_count,
            projection_versions=versions,
        )
