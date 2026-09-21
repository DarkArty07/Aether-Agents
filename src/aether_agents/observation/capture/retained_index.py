"""One validated retained-evidence index per catch-up snapshot.

Builds and incrementally maintains an in-memory index of validated retained events,
traces, and work unit bindings for one project. Synchronous native hooks and
passive startup must not replay journal files or hold maintenance locks; this index
is refreshed asynchronously by the reconciliation worker or lazily on demand,
reusing validated segments across snapshots and invalidating on replacement or truncation.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from aether_agents.observation.capture.journal import (
    SegmentRef,
    list_segments,
    read_segment,
)
from aether_agents.observation.contracts import canonical_json_bytes, validate_event
from aether_agents.observation.privacy import (
    assert_clean,
    native_kanban_task_ref,
)
from aether_agents.paths import ObservationPaths, UnsafeObservationPath

_TRACE_RE = re.compile(r"^ctr_[a-f0-9]{32}$")


def _resolve_retained_binding(
    candidates: list[tuple[str, int, str, str, str, str]],
) -> tuple[str, str] | None:
    """Resolve durable binding candidates across producer epochs."""
    if not candidates:
        return None
    per_epoch: dict[str, list[tuple[str, int, str, str, str, str]]] = {}
    for candidate in candidates:
        per_epoch.setdefault(candidate[0], []).append(candidate)
    resolved: list[tuple[str, str] | None] = []
    for rows in per_epoch.values():
        highest_sequence = max(row[1] for row in rows)
        latest = [row for row in rows if row[1] == highest_sequence]
        values = {None if row[3] == "work_unit.unbound" else (row[5], row[4]) for row in latest}
        if len(values) != 1:
            return None
        resolved.append(values.pop())
    # Independent producers may corroborate the same durable fact, but neither a clock
    # nor an opaque producer/event ID may resolve contradictory bind/unbind claims.
    return resolved[0] if resolved and all(value == resolved[0] for value in resolved) else None


def _current_segment_stats(
    paths: ObservationPaths,
) -> tuple[list[tuple[SegmentRef, int, int, int]], bool]:
    """Stat every eligible retained segment without reading journal content.

    Quarantined segments are excluded.  An archive whose manifest cannot be verified,
    or a segment that cannot be stated, marks the view incomplete so no caller mistakes
    a partial enumeration for the authoritative retained set.  An enumeration failure
    raises, exactly as it does for a full validation.
    """
    segments = list_segments(paths)
    stats: list[tuple[SegmentRef, int, int, int]] = []
    complete = True
    for segment in segments:
        if segment.state == "quarantine":
            continue
        if segment.state == "archive":
            try:
                from aether_agents.observation.retention import verify_archive

                manifest = segment.path.with_name(segment.path.name + ".manifest.json")
                if not verify_archive(manifest).ok:
                    complete = False
                    continue
            except Exception:
                complete = False
                continue
        try:
            st = os.stat(segment.path)
        except (OSError, UnsafeObservationPath):
            complete = False
            continue
        stats.append((segment, st.st_size, st.st_mtime_ns, st.st_ino))
    return stats, complete


@dataclass(slots=True)
class _SegmentIndexState:
    path: Path
    state: str
    producer_epoch: str
    first_seq: int
    last_seq: int | None
    mtime_ns: int
    size: int
    inode: int
    line_count: int
    valid: bool
    traces: set[str]
    candidates: dict[str, list[tuple[str, int, str, str, str, str]]]


@dataclass(slots=True)
class _PendingBinding:
    """A native binding intent waiting for retained evidence validation."""

    trace_id: str
    relation: str
    event: dict[str, Any] | None = None
    emitted: bool = False


class RetainedIndex:
    """Validated index of traces and bindings derived from retained journal segments."""

    def __init__(self, project_id: str) -> None:
        self.project_id = project_id
        self.traces: set[str] = set()
        self.candidate_rows: dict[str, list[tuple[str, int, str, str, str, str]]] = {}
        self.resolved_bindings: dict[str, tuple[str, str]] = {}
        self.validation_count: int = 0
        self._segment_states: dict[Path, _SegmentIndexState] = {}
        self._snapshot_signature: tuple[tuple[str, str, int, int, int], ...] = ()
        self._snapshot_state: str = "unknown"
        self._pending_bindings: dict[str, _PendingBinding] = {}
        self._conflicted_bindings: set[str] = set()

    @property
    def snapshot_state(self) -> str:
        """Return whether the current retained snapshot is usable for attribution."""
        return self._snapshot_state

    def trace_exists(self, trace_id: str) -> bool:
        return self._snapshot_state == "validated" and trace_id in self.traces

    def get_binding(self, task_ref: str) -> tuple[str, str] | None:
        """Return only a binding verified by the current retained snapshot."""
        if self._snapshot_state != "validated":
            return None
        return self.resolved_bindings.get(task_ref)

    def binding_state(self, task_ref: str) -> str:
        """Classify one binding without treating an unvalidated absence as proof.

        ``pending`` is an in-process native intent and is deliberately not returned by
        ``get_binding``.  ``incomplete`` covers cold, unreadable, or valid-prefix-limited
        snapshots; callers must keep coverage unresolved in that state.
        """
        if self._snapshot_state != "validated":
            if task_ref in self._pending_bindings:
                return "pending"
            return "incomplete"
        if task_ref in self.resolved_bindings:
            return "verified"
        if task_ref in self._pending_bindings:
            return "pending"
        if task_ref in self._conflicted_bindings or task_ref in self.candidate_rows:
            return "conflict"
        return "absent"

    def get_bindings(self) -> dict[str, tuple[str, str]]:
        if self._snapshot_state != "validated":
            return {}
        return dict(self.resolved_bindings)

    def snapshot_covers_disk(
        self,
        paths: ObservationPaths,
        *,
        own_epoch: str | None = None,
    ) -> bool:
        """Return whether the validated snapshot still covers the live retained evidence.

        Stat-only: no journal content is read and no lock is taken, so a synchronous
        native hook may call it.  A segment that another producer added, appended to,
        replaced, truncated or removed after validation makes the snapshot's ``absent``
        verdict unusable as proof -- that producer may already have attributed the same
        task, and publishing a second claim would make the conflict destroy both.  The
        caller keeps such an intent pending for the asynchronous validated emission
        path instead.

        Segments owned by ``own_epoch`` are this process's own writer: its appends and
        rotations are tracked as pending intents here, so they do not invalidate the
        verdict and a healthy process still publishes its own claim promptly.
        """
        if self._snapshot_state != "validated":
            return False
        try:
            current_stats, complete = _current_segment_stats(paths)
        except Exception:
            return False
        if not complete:
            return False

        seen: set[str] = set()
        validated = {
            path: (epoch, size, mtime, inode)
            for path, epoch, size, mtime, inode in self._snapshot_signature
        }
        for segment, size, mtime_ns, inode in current_stats:
            path = str(segment.path)
            seen.add(path)
            previous = validated.get(path)
            if previous is None:
                # A segment that did not exist when the snapshot was validated.
                if own_epoch is not None and segment.producer_epoch == own_epoch:
                    continue
                return False
            if previous == (segment.producer_epoch, size, mtime_ns, inode):
                continue
            if own_epoch is not None and segment.producer_epoch == own_epoch:
                continue
            return False

        for path, epoch, _size, _mtime, _inode in self._snapshot_signature:
            if path in seen:
                continue
            if own_epoch is not None and epoch == own_epoch:
                continue
            # A validated foreign segment disappeared (quarantined or removed).
            return False
        return True

    def record_binding(
        self,
        task_ref: str,
        trace_id: str,
        relation: str,
        *,
        event: dict[str, Any] | None = None,
        emitted: bool = False,
    ) -> None:
        """Keep a native binding intent pending until retained evidence corroborates it."""
        candidate = (trace_id, relation)
        existing = self.resolved_bindings.get(task_ref)
        if existing is not None:
            if existing != candidate:
                self._conflicted_bindings.add(task_ref)
            return
        if task_ref in self.candidate_rows:
            self._conflicted_bindings.add(task_ref)
            return
        pending = self._pending_bindings.get(task_ref)
        if pending is not None:
            if (pending.trace_id, pending.relation) != candidate:
                self._conflicted_bindings.add(task_ref)
                self._pending_bindings.pop(task_ref, None)
                return
            if pending.event is None and event is not None:
                pending.event = event
            pending.emitted = pending.emitted or emitted
            return
        self._pending_bindings[task_ref] = _PendingBinding(
            trace_id=trace_id,
            relation=relation,
            event=event,
            emitted=emitted,
        )

    def pending_binding(self, task_ref: str) -> tuple[str, str] | None:
        pending = self._pending_bindings.get(task_ref)
        return None if pending is None else (pending.trace_id, pending.relation)

    def pending_binding_events(
        self,
    ) -> tuple[tuple[str, str, str, dict[str, Any]], ...]:
        """Return un-emitted intents only after a complete snapshot proves absence."""
        if self._snapshot_state != "validated":
            return ()
        ready: list[tuple[str, str, str, dict[str, Any]]] = []
        for task_ref, pending in self._pending_bindings.items():
            if pending.event is None or pending.emitted:
                continue
            if (
                task_ref not in self.resolved_bindings
                and task_ref not in self.candidate_rows
                and task_ref not in self._conflicted_bindings
            ):
                ready.append((task_ref, pending.trace_id, pending.relation, pending.event))
        return tuple(ready)

    def mark_pending_binding_emitted(self, task_ref: str) -> None:
        pending = self._pending_bindings.get(task_ref)
        if pending is not None:
            pending.emitted = True

    def refresh(
        self,
        paths: ObservationPaths,
        *,
        collector: Any = None,
        stop_check: Callable[[], bool] | None = None,
    ) -> None:
        """Update the index if the on-disk segment snapshot changed."""
        try:
            current_stats, stats_complete = _current_segment_stats(paths)
        except Exception:
            self._snapshot_state = "unavailable"
            if collector is not None and hasattr(collector, "health"):
                collector.health.increment("RETAINED_INDEX_UNAVAILABLE")
            return

        # Build the current file signature for all eligible non-quarantine segments.
        snapshot_complete = stats_complete
        current_sig = tuple(
            (str(seg.path), seg.producer_epoch, size, mtime, ino)
            for seg, size, mtime, ino in current_stats
        )
        if current_sig == self._snapshot_signature and self._snapshot_state in {
            "validated",
            "incomplete",
        }:
            return  # Snapshot is unchanged; skip all validation

        new_segment_states: dict[Path, _SegmentIndexState] = {}
        changed = False

        for segment, size, mtime_ns, inode in current_stats:
            if stop_check is not None and stop_check():
                return

            prev = self._segment_states.get(segment.path)
            if (
                prev is not None
                and prev.inode == inode
                and prev.size == size
                and prev.mtime_ns == mtime_ns
            ):
                # Completely unchanged segment; reuse cached evidence
                new_segment_states[segment.path] = prev
                if not prev.valid:
                    snapshot_complete = False
                continue

            # Need to read or incrementally update this segment
            changed = True
            seg_state = self._index_segment(
                segment=segment,
                size=size,
                mtime_ns=mtime_ns,
                inode=inode,
                paths=paths,
                prev=prev,
            )
            if seg_state is not None:
                new_segment_states[segment.path] = seg_state
                if not seg_state.valid:
                    snapshot_complete = False
            else:
                snapshot_complete = False

        if not changed and len(new_segment_states) == len(self._segment_states):
            self._snapshot_signature = current_sig
            self._snapshot_state = "validated" if snapshot_complete else "incomplete"
            self.validation_count += 1
            if collector is not None and hasattr(collector, "health"):
                collector.health.increment("RETAINED_INDEX_VALIDATED")
                if not snapshot_complete:
                    collector.health.increment("RETAINED_INDEX_INCOMPLETE")
            return

        # Re-aggregate across all valid segments
        all_traces: set[str] = set()
        all_candidates: dict[str, list[tuple[str, int, str, str, str, str]]] = {}
        for state in new_segment_states.values():
            all_traces.update(state.traces)
            for t_ref, rows in state.candidates.items():
                all_candidates.setdefault(t_ref, []).extend(rows)

        all_bindings: dict[str, tuple[str, str]] = {}
        conflicted: set[str] = set()
        for t_ref, cands in all_candidates.items():
            resolved = _resolve_retained_binding(cands)
            if resolved is not None:
                all_bindings[t_ref] = resolved
            else:
                conflicted.add(t_ref)

        # A pending native intent is not evidence. Keep it while its event is not
        # visible in the validated snapshot; once the task has retained candidates,
        # either corroborate the exact intent or reject it as contradictory.
        for task_ref, pending in list(self._pending_bindings.items()):
            candidate = (pending.trace_id, pending.relation)
            if task_ref not in all_candidates:
                continue
            if all_bindings.get(task_ref) == candidate:
                del self._pending_bindings[task_ref]
            else:
                del self._pending_bindings[task_ref]
                conflicted.add(task_ref)

        self.traces = all_traces
        self.candidate_rows = all_candidates
        self.resolved_bindings = all_bindings
        self._conflicted_bindings = conflicted
        self._snapshot_state = "validated" if snapshot_complete else "incomplete"
        self._segment_states = new_segment_states
        self._snapshot_signature = current_sig
        self.validation_count += 1

        if collector is not None and hasattr(collector, "health"):
            collector.health.increment("RETAINED_INDEX_VALIDATED")
            if not snapshot_complete:
                collector.health.increment("RETAINED_INDEX_INCOMPLETE")

    def _index_segment(
        self,
        *,
        segment: SegmentRef,
        size: int,
        mtime_ns: int,
        inode: int,
        paths: ObservationPaths,
        prev: _SegmentIndexState | None,
    ) -> _SegmentIndexState | None:
        try:
            snapshot = read_segment(segment.path)
        except (OSError, EOFError, UnsafeObservationPath):
            return None

        if segment.last_seq is not None and (
            snapshot.trailing_fragment
            or not snapshot.lines
            or segment.last_seq != segment.first_seq + len(snapshot.lines) - 1
        ):
            return None

        # Check if we can do an incremental append from prev.line_count
        can_append = (
            prev is not None
            and prev.valid
            and prev.inode == inode
            and size > prev.size
            and len(snapshot.lines) >= prev.line_count
        )

        if can_append and prev is not None:
            traces = set(prev.traces)
            candidates = {k: list(v) for k, v in prev.candidates.items()}
            start_index = prev.line_count
            lines_to_process = snapshot.lines[start_index:]
        else:
            traces = set()
            candidates = {}
            start_index = 0
            lines_to_process = snapshot.lines

        valid = True
        for offset, line in enumerate(lines_to_process):
            index = start_index + offset
            try:
                event = json.loads(line.decode("utf-8"))
                if not isinstance(event, dict) or canonical_json_bytes(event) != line:
                    raise ValueError("retained event is not canonical")
                validate_event(event)
                assert_clean(event)
                if event.get("project_id") != paths.project_id:
                    raise ValueError("retained event belongs to another project")
                if event.get("producer_epoch") != segment.producer_epoch:
                    raise ValueError("retained event producer does not match segment")
                if event.get("producer_seq") != segment.first_seq + index:
                    raise ValueError("retained event sequence does not match segment")
            except Exception:
                # Valid prefix rule: stop at first malformed line
                valid = False
                break

            t_id = event.get("trace_id")
            if isinstance(t_id, str) and _TRACE_RE.fullmatch(t_id):
                traces.add(t_id)

            unit = event.get("work_unit")
            if isinstance(unit, dict):
                event_type = event.get("event_type")
                if event_type in ("work_unit.bound", "work_unit.unbound") and event.get(
                    "source_kind"
                ) in {"hermes_hook", "native_reconciliation"}:
                    task_ref = native_kanban_task_ref(unit.get("task_ref"))
                    epoch = event.get("producer_epoch")
                    sequence = event.get("producer_seq")
                    if (
                        task_ref is not None
                        and isinstance(t_id, str)
                        and _TRACE_RE.fullmatch(t_id)
                        and isinstance(epoch, str)
                        and isinstance(sequence, int)
                    ):
                        candidates.setdefault(task_ref, []).append(
                            (
                                epoch,
                                sequence,
                                str(event.get("event_id") or ""),
                                event_type,
                                str(unit.get("relation") or "unknown"),
                                t_id,
                            )
                        )

        processed_lines = start_index + (
            len(lines_to_process) if valid else offset  # type: ignore[name-defined]
        )

        return _SegmentIndexState(
            path=segment.path,
            state=segment.state,
            producer_epoch=segment.producer_epoch,
            first_seq=segment.first_seq,
            last_seq=segment.last_seq,
            mtime_ns=mtime_ns,
            size=size,
            inode=inode,
            line_count=processed_lines,
            valid=valid,
            traces=traces,
            candidates=candidates,
        )


_PROJECT_INDEXES: dict[tuple[str, str], RetainedIndex] = {}


def get_retained_index(paths: ObservationPaths) -> RetainedIndex:
    """Return the cached RetainedIndex for a project."""
    key = (str(paths.root), paths.project_id)
    if key not in _PROJECT_INDEXES:
        _PROJECT_INDEXES[key] = RetainedIndex(paths.project_id)
    return _PROJECT_INDEXES[key]
