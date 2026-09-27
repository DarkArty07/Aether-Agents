"""Deterministic deduplication and derived-gap discovery.

Normative sources: OBS-D-024, OBS-D-025, OBS-D-031, OBS-FR-033, OBS-FR-035, OBS-FR-079,
OBS-FR-086.

Everything here produces *derived* facts. Reducer-discovered corruption, incompatibility,
unknown schema, unclean tails, and unpaired spans are reproducible read-model and summary
diagnostics; none of them is ever appended back into a source segment.

Two refusals matter most:

* an incomplete native identity is never fuzzy-matched — deduplication happens on the
  event ID or on a *complete* native tuple, and on nothing else;
* a missing ``turn_id`` or ``api_request_id`` stays null. It is never inferred from
  timestamps, and its absence becomes explicit coverage when it affects causality.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Iterable

from aether_agents.observation.capture.journal import SegmentRef
from aether_agents.observation.contracts import CoverageClass, canonical_digest

__all__ = [
    "ReconciliationReport",
    "dedupe",
    "derive_gaps",
    "native_disposition",
    "native_key",
]


_AUTHORITY_FACT_EVENTS = frozenset(
    {
        "contract.completion_verified",
        "trace.cancelled",
        "trace.abandoned",
        "trace.failed",
        "review.requested",
        "review.approved",
        "review.changes_requested",
        "acceptance.declared",
        "acceptance.evaluated",
        "invariant.passed",
        "invariant.failed",
    }
)


def native_key(event: dict[str, Any]) -> str | None:
    """Complete native identity tuple for one event, or ``None`` when incomplete.

    Only a tuple with every part present produces a key. A partial tuple returns ``None``
    so the caller falls back to the event ID and never guesses a match.
    """
    event_type = event.get("event_type")
    if not isinstance(event_type, str):
        return None

    parts: dict[str, Any] | None = None
    if event_type.startswith("tool."):
        tool = event.get("tool") or {}
        parts = {
            "kind": "tool",
            "phase": "started" if event_type == "tool.started" else "terminal",
            "session": event.get("session_id"),
            "call": tool.get("call_id"),
        }
    elif event_type.startswith("run."):
        parts = {
            "kind": "run",
            "phase": event_type,
            "task": (event.get("work_unit") or {}).get("task_ref"),
            "run": event.get("run_id"),
        }
    elif event_type == "work_unit.status":
        unit = event.get("work_unit") or {}
        parts = {
            "kind": "work_unit",
            "phase": "status",
            "task": unit.get("task_ref"),
            # A task can enter the same state again after a retry, so the run is
            # not sufficient by itself.  The authoritative transition/heartbeat
            # timestamp distinguishes repeated states without a fuzzy window.
            "run": event.get("run_id") or "not_available",
            "at": event.get("occurred_at"),
        }
    elif event_type in ("work_unit.bound", "work_unit.unbound"):
        unit = event.get("work_unit") or {}
        parts = {
            "kind": "binding",
            "lane": (
                "product_classification"
                if event.get("source_kind") == "aether_checkpoint"
                else "native_assignment"
            ),
            "phase": event_type,
            "task": unit.get("task_ref"),
            "binding": unit.get("binding_ref"),
        }
    elif event_type.startswith(("model.", "context.")):
        request = event.get("model_request") or {}
        parts = {
            "kind": "model",
            "phase": event_type,
            "session": event.get("session_id"),
            "request": request.get("request_ref"),
            "attempt": request.get("attempt_count"),
        }
    elif event_type == "dispatch.observed":
        parts = {"kind": "dispatch", "tick": (event.get("dispatch") or {}).get("tick_ref")}
    if parts is None:
        return None
    if any(value is None or value == "" for value in parts.values()):
        return None
    return canonical_digest(parts)


@dataclass
class ReconciliationReport:
    """What reconciliation found. All of it is derived, none of it is written back."""

    events: list[dict[str, Any]] = field(default_factory=list)
    duplicates_dropped: int = 0
    gaps: list[dict[str, str]] = field(default_factory=list)
    producer_epochs: set[str] = field(default_factory=set)
    ambiguous_binding_tasks: set[str] = field(default_factory=set)
    ambiguous_status_tasks: set[str] = field(default_factory=set)
    ambiguous_review_tasks: set[str] = field(default_factory=set)
    ambiguous_runs: set[tuple[str, int]] = field(default_factory=set)
    ambiguous_authority_event_ids: set[str] = field(default_factory=set)

    def add_gap(self, gap_class: str, reason_code: str, event_id: str) -> None:
        self.gaps.append({"class": gap_class, "reason_code": reason_code, "event_id": event_id})


def _retain_bounded_graph_ambiguity(
    report: ReconciliationReport, candidates: Iterable[dict[str, Any]]
) -> None:
    """Retain only the semantic coordinates needed to avoid choosing a graph fact.

    Conflicting payload bytes are never copied into a gap. Tool/model conflicts remain
    ordinary coverage ambiguity and cannot gate contract closure through this path.
    """

    for event in candidates:
        event_type = str(event.get("event_type") or "")
        event_id = event.get("event_id")
        if event_type in _AUTHORITY_FACT_EVENTS and isinstance(event_id, str):
            report.ambiguous_authority_event_ids.add(event_id)
        unit = event.get("work_unit") or {}
        task_ref = unit.get("task_ref")
        if not isinstance(task_ref, str):
            continue
        if event_type in ("work_unit.bound", "work_unit.unbound"):
            report.ambiguous_binding_tasks.add(task_ref)
        elif event_type == "work_unit.status":
            report.ambiguous_status_tasks.add(task_ref)
        elif event_type.startswith("review."):
            report.ambiguous_review_tasks.add(task_ref)
        elif event_type.startswith("run."):
            run_id = event.get("run_id")
            if isinstance(run_id, int):
                report.ambiguous_runs.add((task_ref, run_id))


def _retain_sequence_graph_ambiguity(report: ReconciliationReport) -> None:
    per_position: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for event in report.events:
        epoch = event.get("producer_epoch")
        sequence = event.get("producer_seq")
        if isinstance(epoch, str) and isinstance(sequence, int):
            per_position.setdefault((epoch, sequence), []).append(event)
    for candidates in per_position.values():
        if len(candidates) > 1:
            _retain_bounded_graph_ambiguity(report, candidates)


def dedupe(events: Iterable[dict[str, Any]]) -> ReconciliationReport:
    """Collapse a hook capture and a later native reconciliation of the same fact.

    A deterministic event ID already makes most duplicates identical. The native key
    catches the remaining case where the same fact was captured once by a hook and once by
    a store scan under different random IDs.
    """
    report = ReconciliationReport()
    grouped_by_id: dict[str, list[dict[str, Any]]] = {}
    id_order: list[str] = []
    for event in events:
        event_id = event.get("event_id")
        if not isinstance(event_id, str):
            continue
        if event_id not in grouped_by_id:
            grouped_by_id[event_id] = []
            id_order.append(event_id)
        grouped_by_id[event_id].append(event)
        epoch = event.get("producer_epoch")
        if isinstance(epoch, str):
            report.producer_epochs.add(epoch)

    unique_ids: list[dict[str, Any]] = []
    for event_id in id_order:
        candidates = grouped_by_id[event_id]
        by_digest = {canonical_digest(candidate): candidate for candidate in candidates}
        report.duplicates_dropped += len(candidates) - 1
        if len(by_digest) > 1:
            report.add_gap(
                CoverageClass.RECONCILIATION_AMBIGUOUS,
                "EVENT_ID_CONFLICT",
                _synthetic_ref(":".join(("event-id-conflict", event_id, *sorted(by_digest)))),
            )
            _retain_bounded_graph_ambiguity(report, by_digest.values())
        # A conflict cannot preserve two rows with the same primary identity. Retain a
        # stable canonical representative and expose the ambiguity; input order never
        # chooses which incompatible claim survives.
        unique_ids.append(by_digest[min(by_digest)])

    referenced_event_ids = {
        parent for event in unique_ids if isinstance((parent := event.get("parent_event_id")), str)
    }
    seen_native: dict[str, list[dict[str, Any]]] = {}

    for event in unique_ids:
        event_id = event.get("event_id")
        key = native_key(event)
        if key is not None:
            candidates = seen_native.setdefault(key, [])
            disposition = native_disposition(event)
            equivalents = [
                candidate
                for candidate in candidates
                if native_disposition(candidate) == disposition
            ]
            if equivalents:
                event_referenced = event_id in referenced_event_ids
                referenced_equivalents = [
                    candidate
                    for candidate in equivalents
                    if candidate.get("event_id") in referenced_event_ids
                ]
                if event_referenced and referenced_equivalents:
                    # Distinct children may explicitly name distinct envelopes of the
                    # same native fact. Both targets remain addressable; causal evidence
                    # cannot be erased merely because their native disposition matches.
                    candidates.append(event)
                    report.events.append(event)
                    continue

                existing = min(equivalents, key=_native_representative_rank)
                report.duplicates_dropped += 1
                if event_referenced or (
                    not referenced_equivalents
                    and _native_representative_rank(event) < _native_representative_rank(existing)
                ):
                    report.events[report.events.index(existing)] = event
                    candidates[candidates.index(existing)] = event
                continue
            if candidates:
                # One complete native identity cannot truthfully have two incompatible
                # descriptions. Preserve both facts and expose the conflict; dropping
                # either would turn ambiguity into an invented outcome.
                terminal_conflict = _terminal_disposition(event) is not None and any(
                    _terminal_disposition(candidate) is not None for candidate in candidates
                )
                report.add_gap(
                    CoverageClass.RECONCILIATION_AMBIGUOUS,
                    (
                        "NATIVE_TERMINAL_CONFLICT"
                        if terminal_conflict
                        else "NATIVE_IDENTITY_CONFLICT"
                    ),
                    _synthetic_ref(
                        ":".join(
                            [
                                "native-terminal-conflict",
                                key,
                                *sorted(str(item.get("event_id")) for item in (*candidates, event)),
                            ]
                        )
                    ),
                )
                status_candidates = [
                    candidate
                    for candidate in (*candidates, event)
                    if candidate.get("event_type") == "work_unit.status"
                ]
                if status_candidates:
                    _retain_bounded_graph_ambiguity(report, status_candidates)
            candidates.append(event)

        report.events.append(event)

    _add_cross_lane_binding_gaps(report)
    _retain_sequence_graph_ambiguity(report)
    return report


def _native_representative_rank(event: dict[str, Any]) -> tuple[int, str, str]:
    """Canonical rank for unreferenced duplicate native envelopes."""

    source_rank = {
        "hermes_hook": 0,
        "native_reconciliation": 1,
        "aether_checkpoint": 2,
    }.get(str(event.get("source_kind")), 3)
    return (
        source_rank,
        str(event.get("event_id") or ""),
        canonical_digest(event),
    )


def _compatible_binding_refinement(first: dict[str, Any], second: dict[str, Any]) -> bool:
    """True when one exact product classification only fills native unknowns."""

    if (
        first.get("event_type") != "work_unit.bound"
        or second.get("event_type") != "work_unit.bound"
    ):
        return False
    if first.get("source_kind") == "aether_checkpoint":
        product, native = first, second
    elif second.get("source_kind") == "aether_checkpoint":
        product, native = second, first
    else:
        return False
    if native.get("source_kind") not in {"hermes_hook", "native_reconciliation"}:
        return False
    product_unit = product.get("work_unit") or {}
    native_unit = native.get("work_unit") or {}
    product_relation = product_unit.get("relation")
    product_required = product_unit.get("required")
    native_relation = native_unit.get("relation")
    native_required = native_unit.get("required")
    if product_relation == "unknown" or not isinstance(product_required, bool):
        return False
    return (native_relation == "unknown" or native_relation == product_relation) and (
        native_required is None or native_required == product_required
    )


def _add_cross_lane_binding_gaps(report: ReconciliationReport) -> None:
    """Compare preserved native assignment and product classification lanes."""

    grouped: dict[tuple[Any, Any, Any], list[dict[str, Any]]] = {}
    for event in report.events:
        if event.get("event_type") != "work_unit.bound":
            continue
        unit = event.get("work_unit") or {}
        key = (event.get("trace_id"), unit.get("task_ref"), unit.get("binding_ref"))
        grouped.setdefault(key, []).append(event)
    for key, events in sorted(grouped.items(), key=lambda item: str(item[0])):
        native_events = [
            event
            for event in events
            if event.get("source_kind") in {"hermes_hook", "native_reconciliation"}
        ]
        product_events = [
            event for event in events if event.get("source_kind") == "aether_checkpoint"
        ]
        incompatible = next(
            (
                (native, product)
                for native in native_events
                for product in product_events
                if not _compatible_binding_refinement(native, product)
                and (product.get("work_unit") or {}).get("relation") != "unknown"
                and isinstance((product.get("work_unit") or {}).get("required"), bool)
            ),
            None,
        )
        if incompatible is None:
            continue
        native, product = incompatible
        report.add_gap(
            CoverageClass.RECONCILIATION_AMBIGUOUS,
            "NATIVE_IDENTITY_CONFLICT",
            _synthetic_ref(
                ":".join(
                    (
                        "binding-lane-conflict",
                        *(str(part) for part in key),
                        *sorted((str(native.get("event_id")), str(product.get("event_id")))),
                    )
                )
            ),
        )


def _terminal_disposition(event: dict[str, Any]) -> tuple[Any, ...] | None:
    """Lossless bounded disposition used to distinguish duplicates from conflicts."""
    event_type = str(event.get("event_type") or "")
    if event_type.startswith("tool.") and event_type != "tool.started":
        return ("tool", event_type, event.get("status"))
    if event_type == "run.finished":
        unit = event.get("work_unit") or {}
        return (
            "run",
            event.get("status"),
            unit.get("task_status"),
            unit.get("run_status"),
            unit.get("run_outcome"),
        )
    if event_type == "work_unit.status":
        unit = event.get("work_unit") or {}
        task_status = unit.get("task_status")
        run_status = unit.get("run_status")
        run_outcome = unit.get("run_outcome")
        terminal = (
            task_status in {"done", "archived"}
            or run_status not in {None, "running", "unknown"}
            or run_outcome not in {None, "unknown"}
        )
        if terminal:
            return (
                "work_unit_status",
                event.get("status"),
                task_status,
                run_status,
                run_outcome,
            )
    if event_type in ("model.request_completed", "model.request_failed"):
        request = event.get("model_request") or {}
        return ("model", event_type, request.get("state"), event.get("status"))
    return None


def native_disposition(event: dict[str, Any]) -> tuple[Any, ...]:
    """Bounded semantic identity used only after a complete native key matches."""
    terminal = _terminal_disposition(event)
    if terminal is not None:
        return terminal
    event_type = str(event.get("event_type") or "")
    if event_type in ("work_unit.bound", "work_unit.unbound"):
        unit = event.get("work_unit") or {}
        actor = event.get("actor") or {}
        product_owned = event.get("source_kind") == "aether_checkpoint"
        return (
            "binding",
            event_type,
            unit.get("relation"),
            unit.get("required"),
            tuple(sorted(unit.get("parent_task_refs") or ())),
            unit.get("task_status"),
            "product_owned" if product_owned else "native",
            actor.get("kind"),
            actor.get("id"),
            actor.get("profile"),
            actor.get("role") if product_owned else None,
            event.get("parent_event_id") if product_owned else None,
        )
    if event_type == "tool.started":
        tool = event.get("tool") or {}
        return ("tool", event_type, tool.get("name"), tool.get("category"))
    if event_type == "run.started":
        unit = event.get("work_unit") or {}
        return ("run", event_type, unit.get("task_status"), unit.get("run_status"))
    if event_type == "work_unit.status":
        unit = event.get("work_unit") or {}
        return (
            "work_unit_status",
            event.get("status"),
            unit.get("task_status"),
            unit.get("run_status"),
            unit.get("run_outcome"),
        )
    if event_type.startswith(("model.", "context.")):
        request = event.get("model_request") or {}
        return ("model", event_type, request.get("state"))
    if event_type == "dispatch.observed":
        dispatch = event.get("dispatch") or {}
        return (
            "dispatch",
            dispatch.get("outcome"),
            dispatch.get("eligible_count"),
            dispatch.get("running_count"),
            dispatch.get("global_limit"),
            dispatch.get("per_profile_limit"),
            dispatch.get("bottleneck_class"),
        )
    return (event_type, canonical_digest(event))


def derive_gaps(
    report: ReconciliationReport,
    *,
    segments: list[SegmentRef] | None = None,
    unclean_epochs: Iterable[str] = (),
    corrupt_segments: Iterable[tuple[str, str]] = (),
    quarantined: Iterable[tuple[str, str]] = (),
) -> list[dict[str, str]]:
    """Collect every derived coverage gap for one trace's event set."""
    gaps: list[dict[str, str]] = list(report.gaps)

    for epoch in sorted(set(unclean_epochs)):
        # Ownership proved the writer died before a clean close. Contiguous visible
        # sequence numbers do not disprove it (OBS-FR-086).
        gaps.append(
            {
                "class": CoverageClass.EVENT_DROP,
                "reason_code": "UNCLEAN_PRODUCER_TAIL",
                "event_id": _synthetic_ref(epoch),
            }
        )

    for segment_name, reason in sorted(set(corrupt_segments)):
        gaps.append(
            {
                "class": CoverageClass.CORRUPT_SEGMENT,
                "reason_code": reason,
                "event_id": _synthetic_ref(segment_name),
            }
        )

    for segment_name, reason in sorted(set(quarantined)):
        gaps.append(
            {
                "class": CoverageClass.UNKNOWN_SCHEMA,
                "reason_code": reason,
                "event_id": _synthetic_ref(segment_name),
            }
        )

    gaps.extend(_sequence_gaps(report))
    gaps.extend(_identifier_gaps(report))
    return gaps


def _sequence_gaps(report: ReconciliationReport) -> list[dict[str, str]]:
    """A hole in a producer's own sequence proves events were appended and then lost."""
    per_epoch: dict[str, list[dict[str, Any]]] = {}
    for event in report.events:
        epoch = event.get("producer_epoch")
        if isinstance(epoch, str):
            per_epoch.setdefault(epoch, []).append(event)

    gaps: list[dict[str, str]] = []
    for epoch in sorted(per_epoch):
        sequences = sorted(
            e.get("producer_seq")
            for e in per_epoch[epoch]
            if isinstance(e.get("producer_seq"), int)
        )
        sequence_counts = Counter(sequences)
        for sequence in sorted(value for value, count in sequence_counts.items() if count > 1):
            gaps.append(
                {
                    "class": CoverageClass.RECONCILIATION_AMBIGUOUS,
                    "reason_code": "PRODUCER_SEQUENCE_CONFLICT",
                    "event_id": _synthetic_ref(f"{epoch}:duplicate:{sequence}"),
                }
            )
        for previous, following in zip(sequences, sequences[1:]):
            if following > previous + 1:
                gaps.append(
                    {
                        "class": CoverageClass.EVENT_DROP,
                        "reason_code": "PRODUCER_SEQUENCE_GAP",
                        "event_id": _synthetic_ref(f"{epoch}:{previous}:{following}"),
                    }
                )
    return gaps


def _identifier_gaps(report: ReconciliationReport) -> list[dict[str, str]]:
    """A missing turn or API identifier is reported, never inferred (OBS-FR-033)."""
    gaps: list[dict[str, str]] = []
    for event in report.events:
        if not str(event.get("event_type") or "").startswith(("tool.", "model.")):
            continue
        if event.get("turn_id") is None:
            gaps.append(
                {
                    "class": CoverageClass.NATIVE_SOURCE_UNAVAILABLE,
                    "reason_code": "TURN_ID_MISSING",
                    "event_id": str(event.get("event_id")),
                }
            )
        if event.get("api_request_id") is None:
            gaps.append(
                {
                    "class": CoverageClass.NATIVE_SOURCE_UNAVAILABLE,
                    "reason_code": "API_REQUEST_ID_MISSING",
                    "event_id": str(event.get("event_id")),
                }
            )
    return gaps


def _synthetic_ref(seed: str) -> str:
    """A derived diagnostic still needs a stable, schema-shaped reference."""
    return "evt_" + canonical_digest({"derived": seed})
