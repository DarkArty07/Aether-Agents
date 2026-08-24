"""Incremental journal ingestion and deterministic trace reduction.

The JSONL journal remains the immutable evidence source.  This module reads only
new LF-terminated bytes from each representation, upcasts supported historical
events in memory, indexes unknown-newer bytes without moving them, and mirrors
valid events into the disposable SQLite projection.  Reducer diagnostics are
projection rows; they are never appended to a journal segment.

Normative sources: OBS-D-001, OBS-D-025..027, OBS-D-031 and OBS-FR-080..086.
"""

from __future__ import annotations

import json
import re
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
from aether_agents.observation.locking import project_lock
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


@dataclass(frozen=True, slots=True)
class IngestReport:
    segments_seen: int = 0
    lines_seen: int = 0
    events_inserted: int = 0
    duplicate_events: int = 0
    quarantined_events: int = 0
    corrupt_segments: int = 0
    unclean_epochs: int = 0


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


def _ingest_segment(
    model: ReadModel,
    paths: ObservationPaths,
    segment: SegmentRef,
) -> tuple[int, int, int, int, int]:
    """Return ``lines, inserted, duplicates, quarantined, corrupt``."""
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
        return 0, 0, 0, 0, 1

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
        return 0, 0, 0, 0, 1

    valid_prefix = b"".join(line + b"\n" for line in snapshot.lines)
    prefix_length = len(valid_prefix)
    prefix_digest = sha256_hex(valid_prefix)
    cursor = model.read_cursor(key)
    start_offset = 0
    if cursor is not None:
        if cursor.byte_length == prefix_length and cursor.uncompressed_sha256 == prefix_digest:
            # Nothing new in this representation.  Tail ownership is checked by
            # the caller because a live active file may legitimately end mid-write.
            return 0, 0, 0, 0, 0
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
            return 0, 0, 0, 0, 1

    lines_seen = inserted = duplicates = quarantined = corrupt = 0
    offset = 0
    last_seq = cursor.last_seq if cursor is not None else segment.first_seq - 1
    stopped_at: int | None = None

    for line_index, line in enumerate(snapshot.lines):
        line_start = offset
        line_length = len(line) + 1
        offset += line_length
        if line_start < start_offset:
            continue
        lines_seen += 1
        try:
            raw = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
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
                continue
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
            if model.upsert_event(event):
                inserted += 1
            else:
                duplicates += 1
        except ProjectionRebuildRequired:
            raise
        except EventIdentityCollision:
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

    cursor_length = stopped_at if stopped_at is not None else prefix_length
    cursor_bytes = valid_prefix[:cursor_length]
    model.write_cursor(
        segment_path=key,
        producer_epoch=segment.producer_epoch,
        first_seq=segment.first_seq,
        last_seq=max(last_seq, segment.first_seq - 1),
        byte_length=cursor_length,
        uncompressed_sha256=sha256_hex(cursor_bytes),
    )
    return lines_seen, inserted, duplicates, quarantined, corrupt


def ingest_pending(paths: ObservationPaths) -> IngestReport:
    """Incrementally ingest every visible source representation for one project."""
    paths.ensure()
    with project_lock(paths, "storage-transition"):
        rebuilt = False
        while True:
            try:
                return _ingest_pending_once(paths)
            except ProjectionRebuildRequired:
                if rebuilt:
                    raise RuntimeError(
                        "projection rebuild did not restore derivation proof"
                    ) from None
                with ReadModel.open(paths) as model:
                    model.rebuild()
                rebuilt = True


def _ingest_pending_once(paths: ObservationPaths) -> IngestReport:
    """One maintenance-locked ingestion pass, restartable after a rebuild."""
    segments = list_segments(paths)
    totals = {
        "segments_seen": len(segments),
        "lines_seen": 0,
        "events_inserted": 0,
        "duplicate_events": 0,
        "quarantined_events": 0,
        "corrupt_segments": 0,
        "unclean_epochs": 0,
    }

    with ReadModel.open(paths) as model:
        for segment in segments:
            lines, inserted, duplicates, quarantined, corrupt = _ingest_segment(
                model, paths, segment
            )
            totals["lines_seen"] += lines
            totals["events_inserted"] += inserted
            totals["duplicate_events"] += duplicates
            totals["quarantined_events"] += quarantined
            totals["corrupt_segments"] += corrupt

            try:
                trailing_fragment = read_segment(segment.path).trailing_fragment
            except (OSError, EOFError, UnsafeObservationPath):
                trailing_fragment = b""

            if trailing_fragment and not segment.is_active:
                totals["corrupt_segments"] += 1
                _record_gap(
                    model,
                    trace_ids=set(model.trace_ids_for_epoch(segment.producer_epoch)),
                    segment_name=_segment_key(paths, segment.path),
                    coverage_class=CoverageClass.CORRUPT_SEGMENT,
                    reason_code="CLOSED_TRAILING_FRAGMENT",
                    seed=f"{segment.producer_epoch}:{segment.first_seq}:closed-fragment",
                )

            if segment.is_active and epoch_is_unclean(paths, segment.producer_epoch):
                totals["unclean_epochs"] += 1
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

    return IngestReport(**totals)


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
