"""Incremental journal ingestion and deterministic trace reduction.

The JSONL journal remains the immutable evidence source.  This module reads only
new LF-terminated bytes from each representation, upcasts supported historical
events in memory, indexes unknown-newer bytes without moving them, and mirrors
valid events into the disposable SQLite projection.  Reducer diagnostics are
projection rows; they are never appended to a journal segment.

Normative sources: OBS-D-001, OBS-D-025..027, OBS-D-031 and OBS-FR-080..086.

Issue #417: journal catch-up commits event batches (not one transaction per
event), checkpoints the segment cursor after each durable batch so an interrupted
observe resumes, and query callers may bound lock wait / event count / wall time
while reporting truthful incomplete coverage.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aether_agents.observation.capture.journal import (
    SegmentRef,
    epoch_is_unclean,
    list_segments,
    read_segment,
)
from aether_agents.observation.checkpoint import authority_context_from_state_root
from aether_agents.observation.contracts import (
    CoverageClass,
    canonical_digest,
    canonical_json_bytes,
    sha256_hex,
    validate_event,
    validate_summary,
)
from aether_agents.observation.locking import ProjectLockTimeout, project_lock
from aether_agents.observation.privacy import assert_clean
from aether_agents.observation.reduce.reconciliation import dedupe, derive_gaps
from aether_agents.observation.reduce.reducer import ReductionInput, reduce_events
from aether_agents.observation.reduce.upcast import upcast_event
from aether_agents.observation.retention import verify_archive
from aether_agents.observation.storage import (
    EventDerivationFailed,
    EventIdentityCollision,
    ProjectionRebuildRequired,
    ReadModel,
)
from aether_agents.paths import (
    ObservationPaths,
    UnsafeObservationPath,
    atomic_private_write,
    read_private_bytes,
)

__all__ = ["IngestReport", "ingest_pending", "reduce_trace"]

_TRACE_RE = re.compile(r"^ctr_[a-f0-9]{32}$")

#: Durable projection commits per journal segment (#417).
_INGEST_EVENT_BATCH = ReadModel.EVENT_UPSERT_BATCH_SIZE


@dataclass(frozen=True, slots=True)
class IngestReport:
    segments_seen: int = 0
    lines_seen: int = 0
    events_inserted: int = 0
    duplicate_events: int = 0
    quarantined_events: int = 0
    corrupt_segments: int = 0
    unclean_epochs: int = 0
    incomplete: bool = False
    lock_timed_out: bool = False


@dataclass(slots=True)
class _IngestBudget:
    """Mutable catch-up budget shared across segments for one ingest pass."""

    deadline_monotonic: float | None = None
    max_events: int | None = None
    events_processed: int = 0
    exhausted: bool = False

    def note_events(self, count: int) -> None:
        if count <= 0:
            return
        self.events_processed += count
        if self.max_events is not None and self.events_processed >= self.max_events:
            self.exhausted = True

    def check_deadline(self) -> None:
        if self.deadline_monotonic is not None and time.monotonic() >= self.deadline_monotonic:
            self.exhausted = True


def _event_ref(seed: str) -> str:
    return "evt_" + canonical_digest({"derived": seed})


def _diagnostic_id(*parts: Any) -> str:
    return "dia_" + canonical_digest({"parts": list(parts)})


def _segment_key(paths: ObservationPaths, path: Path) -> str:
    try:
        return path.relative_to(paths.journal).as_posix()
    except ValueError:
        # Segment discovery only walks the journal tree.  This fallback is a
        # bounded basename, never an absolute machine path.
        return path.name


def _record_gap(
    model: ReadModel,
    *,
    trace_ids: set[str] | tuple[str, ...],
    segment_name: str,
    coverage_class: str,
    reason_code: str,
    seed: str,
) -> None:
    reference = _event_ref(seed)
    for trace_id in sorted(set(trace_ids)):
        model.record_derived_gap(
            diagnostic_id=_diagnostic_id(trace_id, segment_name, coverage_class, reason_code, seed),
            trace_id=trace_id,
            coverage_class=coverage_class,
            reason_code=reason_code,
            event_ref=reference,
            segment_name=segment_name,
        )


def _archive_is_verified(segment: SegmentRef) -> bool:
    if segment.state != "archive":
        return True
    manifest = segment.path.with_name(segment.path.name + ".manifest.json")
    return verify_archive(manifest).ok


def _checkpoint_cursor(
    model: ReadModel,
    *,
    key: str,
    segment: SegmentRef,
    last_seq: int,
    cursor_length: int,
    valid_prefix: bytes,
    prefix_digest: str | None = None,
) -> None:
    model.write_cursor(
        segment_path=key,
        producer_epoch=segment.producer_epoch,
        first_seq=segment.first_seq,
        last_seq=max(last_seq, segment.first_seq - 1),
        byte_length=cursor_length,
        uncompressed_sha256=prefix_digest or sha256_hex(valid_prefix[:cursor_length]),
    )


def _ingest_segment(
    model: ReadModel,
    paths: ObservationPaths,
    segment: SegmentRef,
    budget: _IngestBudget,
) -> tuple[int, int, int, int, int, bytes, bool]:
    """Return ``lines, inserted, duplicates, quarantined, corrupt, trailing, stopped``.

    ``stopped`` is True when the catch-up budget was exhausted mid-segment after a
    durable cursor checkpoint (incomplete coverage, not corruption).
    """
    key = _segment_key(paths, segment.path)
    known_trace_ids = set(model.trace_ids_for_epoch(segment.producer_epoch))

    if not _archive_is_verified(segment):
        _record_gap(
            model,
            trace_ids=known_trace_ids,
            segment_name=key,
            coverage_class=CoverageClass.CORRUPT_SEGMENT,
            reason_code="ARCHIVE_VERIFICATION_FAILED",
            seed=f"{key}:archive-verification",
        )
        return 0, 0, 0, 0, 1, b"", False

    try:
        snapshot = read_segment(segment.path)
    except (OSError, EOFError, UnsafeObservationPath):
        _record_gap(
            model,
            trace_ids=known_trace_ids,
            segment_name=key,
            coverage_class=CoverageClass.CORRUPT_SEGMENT,
            reason_code="SEGMENT_UNREADABLE",
            seed=f"{key}:unreadable",
        )
        return 0, 0, 0, 0, 1, b"", False

    valid_prefix = b"".join(line + b"\n" for line in snapshot.lines)
    prefix_length = len(valid_prefix)
    prefix_digest = sha256_hex(valid_prefix)
    cursor = model.read_cursor(key)
    start_offset = 0
    if cursor is not None:
        if cursor.byte_length == prefix_length and cursor.uncompressed_sha256 == prefix_digest:
            # Nothing new in this representation.  Tail ownership is checked by
            # the caller because a live active file may legitimately end mid-write.
            return 0, 0, 0, 0, 0, snapshot.trailing_fragment, False
        if (
            cursor.byte_length <= prefix_length
            and sha256_hex(valid_prefix[: cursor.byte_length]) == cursor.uncompressed_sha256
        ):
            start_offset = cursor.byte_length
        else:
            _record_gap(
                model,
                trace_ids=known_trace_ids,
                segment_name=key,
                coverage_class=CoverageClass.CORRUPT_SEGMENT,
                reason_code="SEGMENT_PREFIX_CHANGED",
                seed=f"{key}:prefix-changed",
            )
            return 0, 0, 0, 0, 1, snapshot.trailing_fragment, False

    lines_seen = inserted = duplicates = quarantined = corrupt = 0
    offset = 0
    last_seq = cursor.last_seq if cursor is not None else segment.first_seq - 1
    stopped_at: int | None = None
    budget_stopped = False
    batch_open = False
    batch_count = 0
    checkpoint_offset = start_offset
    checkpoint_seq = last_seq
    checkpoint_hasher = hashlib.sha256()
    hashed_offset = 0

    def digest_at(length: int) -> str:
        nonlocal hashed_offset
        if not hashed_offset <= length <= prefix_length:
            raise ValueError("ingest checkpoint prefix must advance monotonically")
        checkpoint_hasher.update(memoryview(valid_prefix)[hashed_offset:length])
        hashed_offset = length
        return checkpoint_hasher.hexdigest()

    def flush_batch() -> None:
        nonlocal batch_open, batch_count
        if not batch_open:
            return
        model.commit_event_batch()
        batch_open = False
        batch_count = 0
        _checkpoint_cursor(
            model,
            key=key,
            segment=segment,
            last_seq=checkpoint_seq,
            cursor_length=checkpoint_offset,
            valid_prefix=valid_prefix,
            prefix_digest=digest_at(checkpoint_offset),
        )

    try:
        for line_index, line in enumerate(snapshot.lines):
            budget.check_deadline()
            line_start = offset
            line_length = len(line) + 1
            offset += line_length
            if line_start < start_offset:
                continue

            if budget.exhausted and batch_count == 0:
                budget_stopped = True
                break

            lines_seen += 1
            try:
                raw = json.loads(line.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                flush_batch()
                corrupt += 1
                stopped_at = line_start
                _record_gap(
                    model,
                    trace_ids=known_trace_ids,
                    segment_name=key,
                    coverage_class=CoverageClass.CORRUPT_SEGMENT,
                    reason_code="SEGMENT_LINE_MALFORMED",
                    seed=f"{key}:{line_start}:json",
                )
                break

            trace_id = raw.get("trace_id") if isinstance(raw, dict) else None
            project_id = raw.get("project_id") if isinstance(raw, dict) else None
            if (
                isinstance(trace_id, str)
                and _TRACE_RE.fullmatch(trace_id)
                and project_id == paths.project_id
            ):
                known_trace_ids.add(trace_id)

            try:
                upcast = upcast_event(raw)
            except Exception:  # content-free classification; never retain exception text
                flush_batch()
                corrupt += 1
                stopped_at = line_start
                _record_gap(
                    model,
                    trace_ids=known_trace_ids,
                    segment_name=key,
                    coverage_class=CoverageClass.CORRUPT_SEGMENT,
                    reason_code="EVENT_UPCAST_FAILED",
                    seed=f"{key}:{line_start}:upcast",
                )
                break
            if not upcast.ok:
                if upcast.status == "unknown_schema":
                    if (
                        not isinstance(raw, dict)
                        or raw.get("project_id") != paths.project_id
                        or raw.get("producer_epoch") != segment.producer_epoch
                        or raw.get("producer_seq") != segment.first_seq + line_index
                    ):
                        flush_batch()
                        corrupt += 1
                        stopped_at = line_start
                        _record_gap(
                            model,
                            trace_ids=known_trace_ids,
                            segment_name=key,
                            coverage_class=CoverageClass.CORRUPT_SEGMENT,
                            reason_code="UNKNOWN_EVENT_ENVELOPE_INVALID",
                            seed=f"{key}:{line_start}:unknown-envelope",
                        )
                        break
                    version = raw.get("schema_version") if isinstance(raw, dict) else None
                    version_text = version if isinstance(version, str) else "unknown"
                    flush_batch()
                    model.quarantine(
                        segment_name=key,
                        byte_offset=line_start,
                        byte_length=line_length,
                        sha256=sha256_hex(line + b"\n"),
                        event_schema_version=version_text[:128],
                        project_id=paths.project_id,
                    )
                    quarantined += 1
                    last_seq = max(last_seq, segment.first_seq + line_index)
                    checkpoint_offset = offset
                    checkpoint_seq = last_seq
                    _checkpoint_cursor(
                        model,
                        key=key,
                        segment=segment,
                        last_seq=checkpoint_seq,
                        cursor_length=checkpoint_offset,
                        valid_prefix=valid_prefix,
                        prefix_digest=digest_at(checkpoint_offset),
                    )
                    _record_gap(
                        model,
                        trace_ids={trace_id}
                        if isinstance(trace_id, str) and trace_id in known_trace_ids
                        else known_trace_ids,
                        segment_name=key,
                        coverage_class=CoverageClass.UNKNOWN_SCHEMA,
                        reason_code=upcast.reason_code or "UNKNOWN_EVENT_SCHEMA",
                        seed=f"{key}:{line_start}:schema",
                    )
                    budget.note_events(1)
                    continue
                flush_batch()
                corrupt += 1
                stopped_at = line_start
                _record_gap(
                    model,
                    trace_ids=known_trace_ids,
                    segment_name=key,
                    coverage_class=CoverageClass.CORRUPT_SEGMENT,
                    reason_code=upcast.reason_code or "EVENT_MALFORMED",
                    seed=f"{key}:{line_start}:event",
                )
                break

            assert upcast.event is not None
            event = upcast.event
            try:
                if event.get("project_id") != paths.project_id:
                    raise ValueError("cross-project event")
                if event.get("producer_epoch") != segment.producer_epoch:
                    raise ValueError("producer epoch mismatch")
                if event.get("producer_seq") != segment.first_seq + line_index:
                    raise ValueError("producer sequence mismatch")
                validate_event(event)
                assert_clean(event)
            except Exception:  # bounded diagnostic; never expose offending data
                flush_batch()
                corrupt += 1
                stopped_at = line_start
                _record_gap(
                    model,
                    trace_ids=known_trace_ids,
                    segment_name=key,
                    coverage_class=CoverageClass.CORRUPT_SEGMENT,
                    reason_code="EVENT_SCHEMA_OR_PRIVACY_INVALID",
                    seed=f"{key}:{line_start}:validation",
                )
                break

            try:
                if not batch_open:
                    model.begin_event_batch()
                    batch_open = True
                if model.project_event(event):
                    inserted += 1
                else:
                    duplicates += 1
            except ProjectionRebuildRequired:
                if batch_open:
                    model.rollback_event_batch()
                    batch_open = False
                raise
            except EventIdentityCollision:
                # Savepoint already dropped the bad event; keep prior batch rows.
                if batch_open and batch_count > 0:
                    flush_batch()
                elif batch_open:
                    model.rollback_event_batch()
                    batch_open = False
                corrupt += 1
                stopped_at = line_start
                _record_gap(
                    model,
                    trace_ids=known_trace_ids,
                    segment_name=key,
                    coverage_class=CoverageClass.CORRUPT_SEGMENT,
                    reason_code="EVENT_IDENTITY_COLLISION",
                    seed=f"{key}:{line_start}:identity",
                )
                break
            except EventDerivationFailed:
                if batch_open and batch_count > 0:
                    flush_batch()
                elif batch_open:
                    model.rollback_event_batch()
                    batch_open = False
                corrupt += 1
                stopped_at = line_start
                _record_gap(
                    model,
                    trace_ids=known_trace_ids,
                    segment_name=key,
                    coverage_class=CoverageClass.CORRUPT_SEGMENT,
                    reason_code="EVENT_DERIVATION_FAILED",
                    seed=f"{key}:{line_start}:derivation",
                )
                break
            except Exception:
                if batch_open and batch_count > 0:
                    flush_batch()
                elif batch_open:
                    model.rollback_event_batch()
                    batch_open = False
                corrupt += 1
                stopped_at = line_start
                _record_gap(
                    model,
                    trace_ids=known_trace_ids,
                    segment_name=key,
                    coverage_class=CoverageClass.CORRUPT_SEGMENT,
                    reason_code="EVENT_STORAGE_FAILED",
                    seed=f"{key}:{line_start}:storage",
                )
                break

            seq = event.get("producer_seq")
            if isinstance(seq, int):
                last_seq = max(last_seq, seq)
            checkpoint_offset = offset
            checkpoint_seq = last_seq
            batch_count += 1
            budget.note_events(1)
            budget.check_deadline()
            if batch_count >= _INGEST_EVENT_BATCH or budget.exhausted:
                flush_batch()
                if budget.exhausted:
                    budget_stopped = True
                    break
        else:
            flush_batch()
    except BaseException:
        # Persist any fully projected events already in the open batch so an
        # interrupted observe resumes instead of replaying the segment from zero.
        if batch_open and batch_count > 0:
            try:
                flush_batch()
            except Exception:
                try:
                    model.rollback_event_batch()
                except Exception:
                    pass
                raise
            raise
        if batch_open:
            model.rollback_event_batch()
        raise

    if stopped_at is not None:
        _checkpoint_cursor(
            model,
            key=key,
            segment=segment,
            last_seq=checkpoint_seq,
            cursor_length=stopped_at,
            valid_prefix=valid_prefix,
            prefix_digest=digest_at(stopped_at),
        )
    elif not budget_stopped:
        _checkpoint_cursor(
            model,
            key=key,
            segment=segment,
            last_seq=last_seq,
            cursor_length=prefix_length,
            valid_prefix=valid_prefix,
            prefix_digest=digest_at(prefix_length),
        )

    # A cooperative catch-up limit is a transient operation result, not a loss of
    # source evidence. Query entry points reject an incomplete IngestReport before
    # reduction, so no durable gap is inserted or subsequently deleted here.

    return (
        lines_seen,
        inserted,
        duplicates,
        quarantined,
        corrupt,
        snapshot.trailing_fragment,
        budget_stopped,
    )


def ingest_pending(
    paths: ObservationPaths,
    *,
    deadline_monotonic: float | None = None,
    max_events: int | None = None,
    lock_timeout_s: float | None = None,
) -> IngestReport:
    """Incrementally ingest every visible source representation for one project.

    Query callers may pass ``deadline_monotonic``, ``max_events``, and/or
    ``lock_timeout_s`` so ``aether observe`` returns with incomplete coverage
    before a host tool deadline instead of holding the project lock unbounded.
    """
    paths.ensure()
    try:
        with project_lock(paths, "storage-transition", timeout_s=lock_timeout_s):
            rebuilt = False
            while True:
                try:
                    return _ingest_pending_once(
                        paths,
                        deadline_monotonic=deadline_monotonic,
                        max_events=max_events,
                    )
                except ProjectionRebuildRequired:
                    if rebuilt:
                        raise RuntimeError(
                            "projection rebuild did not restore derivation proof"
                        ) from None
                    with ReadModel.open(paths) as model:
                        model.rebuild()
                    rebuilt = True
    except ProjectLockTimeout:
        return IngestReport(incomplete=True, lock_timed_out=True)


def _ingest_pending_once(
    paths: ObservationPaths,
    *,
    deadline_monotonic: float | None = None,
    max_events: int | None = None,
) -> IngestReport:
    """One maintenance-locked ingestion pass, restartable after a rebuild."""
    segments = list_segments(paths)
    budget = _IngestBudget(deadline_monotonic=deadline_monotonic, max_events=max_events)
    segments_seen = len(segments)
    lines_seen = 0
    events_inserted = 0
    duplicate_events = 0
    quarantined_events = 0
    corrupt_segments = 0
    unclean_epochs = 0
    incomplete = False

    with ReadModel.open(paths) as model:
        for segment in segments:
            budget.check_deadline()
            if budget.exhausted:
                incomplete = True
                break

            (
                lines,
                inserted,
                duplicates,
                quarantined,
                corrupt,
                trailing_fragment,
                budget_stopped,
            ) = _ingest_segment(model, paths, segment, budget)
            lines_seen += lines
            events_inserted += inserted
            duplicate_events += duplicates
            quarantined_events += quarantined
            corrupt_segments += corrupt
            if budget_stopped:
                incomplete = True

            if trailing_fragment and not segment.is_active:
                corrupt_segments += 1
                _record_gap(
                    model,
                    trace_ids=set(model.trace_ids_for_epoch(segment.producer_epoch)),
                    segment_name=_segment_key(paths, segment.path),
                    coverage_class=CoverageClass.CORRUPT_SEGMENT,
                    reason_code="CLOSED_TRAILING_FRAGMENT",
                    seed=f"{segment.producer_epoch}:{segment.first_seq}:closed-fragment",
                )

            if segment.is_active and epoch_is_unclean(paths, segment.producer_epoch):
                unclean_epochs += 1
                trace_ids = set(model.trace_ids_for_epoch(segment.producer_epoch))
                _record_gap(
                    model,
                    trace_ids=trace_ids,
                    segment_name=_segment_key(paths, segment.path),
                    coverage_class=CoverageClass.EVENT_DROP,
                    reason_code="UNCLEAN_PRODUCER_TAIL",
                    seed=f"{segment.producer_epoch}:unclean-tail",
                )
                if trailing_fragment:
                    _record_gap(
                        model,
                        trace_ids=trace_ids,
                        segment_name=_segment_key(paths, segment.path),
                        coverage_class=CoverageClass.CORRUPT_SEGMENT,
                        reason_code="UNCLEAN_TRAILING_FRAGMENT",
                        seed=f"{segment.producer_epoch}:trailing-fragment",
                    )

            if budget_stopped:
                break

    return IngestReport(
        segments_seen=segments_seen,
        lines_seen=lines_seen,
        events_inserted=events_inserted,
        duplicate_events=duplicate_events,
        quarantined_events=quarantined_events,
        corrupt_segments=corrupt_segments,
        unclean_epochs=unclean_epochs,
        incomplete=incomplete,
        lock_timed_out=False,
    )


def _write_summary(paths: ObservationPaths, summary: dict[str, Any]) -> None:
    target = paths.summary_file(summary["summary_id"])
    data = canonical_json_bytes(summary) + b"\n"
    try:
        existing = read_private_bytes(target)
    except FileNotFoundError:
        atomic_private_write(target, data)
        return
    if existing != data:
        raise UnsafeObservationPath("immutable observation summary identity collision")


def reduce_trace(paths: ObservationPaths, trace_id: str) -> dict[str, Any]:
    """Reduce one already-ingested trace and retain its immutable summary."""
    with ReadModel.open(paths) as model:
        stored = model.events_for_trace(trace_id)
        if not stored:
            raise KeyError("trace has no ingested events")
        reconciliation = dedupe(stored)
        gaps = model.derived_gaps(trace_id)
        gaps.extend(derive_gaps(reconciliation))
        summary = reduce_events(
            ReductionInput(
                trace_id=trace_id,
                project_id=paths.project_id,
                events=reconciliation.events,
                derived_gaps=gaps,
                producer_count=max(1, len(reconciliation.producer_epochs)),
                authority_context=authority_context_from_state_root(paths.root),
            )
        )
        validate_summary(summary)
        model.record_summary(summary)
    _write_summary(paths, summary)
    return summary
