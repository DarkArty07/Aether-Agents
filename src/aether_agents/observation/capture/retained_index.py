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


class RetainedIndex:
    """Validated index of traces and bindings derived from retained journal segments."""

    def __init__(self, project_id: str) -> None:
        self.project_id = project_id
        self.traces: set[str] = set()
        self.candidate_rows: dict[str, list[tuple[str, int, str, str, str, str]]] = {}
        self.resolved_bindings: dict[str, tuple[str, str]] = {}
        self.validation_count: int = 0
        self._segment_states: dict[Path, _SegmentIndexState] = {}
        self._snapshot_signature: tuple[tuple[str, int, int, int], ...] = ()

    def trace_exists(self, trace_id: str) -> bool:
        return trace_id in self.traces

    def get_binding(self, task_ref: str) -> tuple[str, str] | None:
        return self.resolved_bindings.get(task_ref)

    def get_bindings(self) -> dict[str, tuple[str, str]]:
        return dict(self.resolved_bindings)

    def record_binding(self, task_ref: str, trace_id: str, relation: str) -> None:
        """Record an in-memory binding immediately without waiting for disk sync."""
        self.traces.add(trace_id)
        self.resolved_bindings[task_ref] = (trace_id, relation)

    def refresh(
        self,
        paths: ObservationPaths,
        *,
        collector: Any = None,
        stop_check: Callable[[], bool] | None = None,
    ) -> None:
        """Update the index if the on-disk segment snapshot changed."""
        try:
            segments = list_segments(paths)
        except Exception:
            return

        # Build current file signature for all eligible non-quarantine segments.
        current_stats: list[tuple[SegmentRef, int, int, int]] = []
        for segment in segments:
            if segment.state == "quarantine":
                continue
            if segment.state == "archive":
                try:
                    from aether_agents.observation.retention import verify_archive

                    manifest = segment.path.with_name(segment.path.name + ".manifest.json")
                    if not verify_archive(manifest).ok:
                        continue
                except Exception:
                    continue
            try:
                st = os.stat(segment.path)
                current_stats.append((segment, st.st_size, st.st_mtime_ns, st.st_ino))
            except (OSError, UnsafeObservationPath):
                continue

        current_sig = tuple(
            (str(seg.path), size, mtime, ino) for seg, size, mtime, ino in current_stats
        )
        if current_sig == self._snapshot_signature:
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

        if not changed and len(new_segment_states) == len(self._segment_states):
            self._snapshot_signature = current_sig
            return

        # Re-aggregate across all valid segments
        all_traces: set[str] = set()
        all_candidates: dict[str, list[tuple[str, int, str, str, str, str]]] = {}
        for state in new_segment_states.values():
            all_traces.update(state.traces)
            for t_ref, rows in state.candidates.items():
                all_candidates.setdefault(t_ref, []).extend(rows)

        all_bindings: dict[str, tuple[str, str]] = {}
        for t_ref, cands in all_candidates.items():
            resolved = _resolve_retained_binding(cands)
            if resolved is not None:
                all_bindings[t_ref] = resolved

        self.traces = all_traces
        self.candidate_rows = all_candidates
        self.resolved_bindings = all_bindings
        self._segment_states = new_segment_states
        self._snapshot_signature = current_sig
        self.validation_count += 1

        if collector is not None and hasattr(collector, "health"):
            collector.health.increment("RETAINED_INDEX_VALIDATED")

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
