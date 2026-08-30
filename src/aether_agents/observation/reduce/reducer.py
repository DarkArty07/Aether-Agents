"""The deterministic full-lifecycle reducer.

Normative sources: spec sections 7, 9, 10, 11; the summary schema is
``specs/002-aether-contract-observation/contracts/observation-summary.schema.json``.

Determinism is a hard property, not an aspiration: the same ordered event set and the
same reducer version MUST produce byte-equivalent canonical JSON. So this module reads no
wall clock (``as_of`` is the maximum included ``occurred_at``), sorts every collection it
emits, performs no model call, and never repairs an impossible timestamp — an anomaly
becomes a coverage gap instead.

It also refuses to over-claim. Settled mechanical state produces ``completion_candidate``;
``completed`` additionally requires authoritative verification evidence. A heartbeat can
change liveness and can never change progress. A telemetry gap never becomes a control gate.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from aether_agents.observation.checkpoint import AuthorityContext
from aether_agents.observation.contracts import (
    ANOMALOUS_RUN_OUTCOMES,
    OPEN_TASK_STATUSES,
    SUMMARY_SCHEMA_VERSION,
    WORK_UNIT_RELATIONS,
    CoverageClass,
    canonical_digest,
)
from aether_agents.observation.identity import summary_id as make_summary_id
from aether_agents.observation.reduce.process import build_process, causal_order, parse_timestamp
from aether_agents.observation.reduce.reconciliation import dedupe, derive_gaps
from aether_agents.observation.reduce.review import build_review_brief
from aether_agents.observation.reduce.upcast import declared_versions

__all__ = [
    "HEARTBEAT_POLICY_VERSION",
    "HEARTBEAT_STALE_AFTER_MS",
    "ReductionInput",
    "reduce_events",
]


HEARTBEAT_POLICY_VERSION = "aether.heartbeat-recency.v1"
HEARTBEAT_STALE_AFTER_MS = 120_000
_AUTHORITY_PROTECTED_EVENTS = frozenset(
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
_TRACE_TERMINAL_STATUSES = {
    "trace.cancelled": "cancelled",
    "trace.abandoned": "unknown",
    "trace.failed": "failed",
}
REQUIRED_EXECUTABLE_INVARIANTS = frozenset(f"OBS-INV-{number:03d}" for number in range(1, 11))


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.strftime("%Y-%m-%dT%H:%M:%S.") + f"{value.microsecond // 1000:03d}Z"


def _ms(start: datetime | None, end: datetime | None) -> int | None:
    if start is None or end is None:
        return None
    delta = int((end - start).total_seconds() * 1000)
    return delta if delta >= 0 else None


# ---------------------------------------------------------------------------------------
# Interval arithmetic (spec section 10)
# ---------------------------------------------------------------------------------------


def _union_ms(intervals: list[tuple[datetime, datetime]]) -> int:
    """Total covered milliseconds. Parallel spans raise call counts, never wall duration."""
    if not intervals:
        return 0
    ordered = sorted(intervals, key=lambda item: (item[0], item[1]))
    total = timedelta()
    current_start, current_end = ordered[0]
    for start, end in ordered[1:]:
        if start > current_end:
            total += current_end - current_start
            current_start, current_end = start, end
        elif end > current_end:
            current_end = end
    total += current_end - current_start
    return int(total.total_seconds() * 1000)


def _subtract(
    intervals: list[tuple[datetime, datetime]],
    higher: list[tuple[datetime, datetime]],
) -> list[tuple[datetime, datetime]]:
    """Remove higher-precedence intervals so reporting categories never double-count."""
    if not higher:
        return intervals
    result: list[tuple[datetime, datetime]] = []
    blockers = sorted(higher, key=lambda item: item[0])
    for start, end in intervals:
        cursor = start
        for block_start, block_end in blockers:
            if block_end <= cursor or block_start >= end:
                continue
            if block_start > cursor:
                result.append((cursor, min(block_start, end)))
            cursor = max(cursor, block_end)
            if cursor >= end:
                break
        if cursor < end:
            result.append((cursor, end))
    return result


def _overlap_ms(
    left: list[tuple[datetime, datetime]], right: list[tuple[datetime, datetime]]
) -> int:
    total = timedelta()
    for a_start, a_end in left:
        for b_start, b_end in right:
            start, end = max(a_start, b_start), min(a_end, b_end)
            if end > start:
                total += end - start
    return int(total.total_seconds() * 1000)


# ---------------------------------------------------------------------------------------
# Reduction
# ---------------------------------------------------------------------------------------


@dataclass
class ReductionInput:
    """Everything the reducer is allowed to see."""

    trace_id: str
    project_id: str
    events: list[dict[str, Any]]
    #: Reducer-discovered problems. They stay derived and are never written back into a
    #: source segment (OBS-D-025).
    derived_gaps: list[dict[str, str]] = field(default_factory=list)
    producer_count: int = 1
    supporting_trace_count: int = 1
    # Trusted product/lifecycle input. It is never reconstructed from event actor strings.
    authority_context: AuthorityContext = field(default_factory=AuthorityContext.unavailable)


def reduce_events(data: ReductionInput) -> dict[str, Any]:
    """Reduce one trace's events into one deterministic summary object."""
    reconciliation = dedupe(data.events)
    events = causal_order(reconciliation.events)
    state = _TraceState(
        events,
        data.authority_context,
        ambiguous_binding_tasks=frozenset(reconciliation.ambiguous_binding_tasks),
        ambiguous_status_tasks=frozenset(reconciliation.ambiguous_status_tasks),
        ambiguous_review_tasks=frozenset(reconciliation.ambiguous_review_tasks),
        ambiguous_runs=frozenset(reconciliation.ambiguous_runs),
        ambiguous_authority_event_ids=frozenset(reconciliation.ambiguous_authority_event_ids),
    )

    as_of = state.as_of
    work_graph = state.work_graph()
    acceptance = state.acceptance()
    completion = state.completion_state(work_graph, acceptance)
    # Successful closure is a derived agreement between authoritative graph,
    # acceptance, and Morfeo verification. Compute that agreement before exposing
    # timestamps/durations so premature verification cannot fabricate completed_at.
    timestamps = state.timestamps()
    duration = state.duration(as_of)
    flow, flow_gaps = state.flow()
    process = build_process(
        events,
        verified_review_event_ids=frozenset(state.verified_review_event_ids),
        verified_completion_event_ids=frozenset(state.verified_completion_event_ids),
    )
    _enrich_waves_with_dispatch(process, state)

    coverage = state.coverage(list(data.derived_gaps) + derive_gaps(reconciliation) + flow_gaps)
    bottlenecks = state.bottlenecks()
    defects = state.defects()

    summary: dict[str, Any] = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "summary_id": "",  # replaced below, over the canonical form without it
        "reducer_version": declared_versions()["reducer_version"],
        "trace_id": data.trace_id,
        "project_id": data.project_id,
        "contract_id": state.contract_id,
        "as_of": _iso(as_of) or _iso(state.first_moment) or "1970-01-01T00:00:00.000Z",
        "completion_state": completion,
        "timestamps": timestamps,
        "duration": duration,
        "runtime_state": state.runtime_state(work_graph, flow, coverage, completion),
        "work_graph": work_graph,
        "acceptance": acceptance,
        "participants": state.participants(),
        "tools": state.tools(),
        "flow": flow,
        "invariants": state.invariants(),
        "coverage": coverage,
        "provenance": state.provenance(data.producer_count),
        "source_event_count": len(events),
        "process": process,
        "configuration_fingerprints": state.configuration_fingerprints(),
        "capability_evidence": state.capability_evidence(),
        "model_context_economics": state.model_context_economics(flow),
        "bottlenecks": bottlenecks,
        "defect_attributions": defects,
        "improvement_evidence": _improvement_evidence(data.supporting_trace_count),
        "review_brief": {},  # replaced below
    }
    summary["review_brief"] = build_review_brief(summary)
    summary["summary_id"] = make_summary_id(summary)
    return summary


def _improvement_evidence(supporting_trace_count: int) -> dict[str, Any]:
    """A signal from one trace is anecdotal and must say so (OBS-FR-065)."""
    if supporting_trace_count <= 0:
        strength = "insufficient_evidence"
    elif supporting_trace_count == 1:
        strength = "anecdotal"
    else:
        strength = "multi_trace_observation"
    return {
        "supporting_trace_count": max(0, supporting_trace_count),
        "strength": strength,
        # OBS-FR-066: the observer supplies evidence and never a recommendation.
        "automated_recommendation": None,
    }


def _enrich_waves_with_dispatch(process: dict[str, Any], state: "_TraceState") -> None:
    """Attach dispatch-tick samples to the wave whose interval contains the tick.

    Sampled values always carry their precision, and an interval with no tick keeps
    ``null`` rather than an interpolated number (OBS-FR-054, OBS-FR-056).
    """
    for wave in process["waves"]:
        started = parse_timestamp(wave.get("started_at"))
        ended = parse_timestamp(wave.get("ended_at"))
        if started is None:
            continue
        samples = [
            tick
            for tick in state.dispatch_ticks
            if tick["at"] >= started and (ended is None or tick["at"] <= ended)
        ]
        if not samples:
            continue
        eligible = [s["eligible"] for s in samples if s["eligible"] is not None]
        running = [s["running"] for s in samples if s["running"] is not None]
        limits = [s["global_limit"] for s in samples if s["global_limit"] is not None]
        per_profile = [
            s["per_profile_limit"] for s in samples if s["per_profile_limit"] is not None
        ]
        wave["eligible_unit_count_observed"] = max(eligible) if eligible else None
        if eligible and running:
            wave["ready_but_not_running_count_observed"] = max(0, max(eligible) - max(running))
        wave["global_limit"] = max(limits) if limits else None
        wave["per_profile_limit"] = max(per_profile) if per_profile else None
        precisions = [s["precision_ms"] for s in samples if s["precision_ms"] is not None]
        wave["sampling_precision_ms"] = max(precisions) if precisions else None
        if len(samples) > 1:
            span = _ms(samples[0]["at"], samples[-1]["at"])
            if span is not None and wave["ready_but_not_running_count_observed"]:
                wave["ready_but_not_running_ms_observed"] = span


class _TraceState:
    """Single pass over the ordered events, then pure projections of what it found."""

    def __init__(
        self,
        events: list[dict[str, Any]],
        authority_context: AuthorityContext,
        *,
        ambiguous_binding_tasks: frozenset[str] = frozenset(),
        ambiguous_status_tasks: frozenset[str] = frozenset(),
        ambiguous_review_tasks: frozenset[str] = frozenset(),
        ambiguous_runs: frozenset[tuple[str, int]] = frozenset(),
        ambiguous_authority_event_ids: frozenset[str] = frozenset(),
    ) -> None:
        self.events = events
        self.authority_context = authority_context
        self._ambiguous_binding_tasks = ambiguous_binding_tasks
        self._ambiguous_status_tasks = ambiguous_status_tasks
        self._ambiguous_review_tasks = ambiguous_review_tasks
        self._ambiguous_runs = ambiguous_runs
        self._ambiguous_authority_event_ids = ambiguous_authority_event_ids
        self.contract_id: str | None = None
        self.first_moment: datetime | None = None
        self.as_of: datetime | None = None

        self._started_at: datetime | None = None
        self._first_action_at: datetime | None = None
        self._executable_at: datetime | None = None
        self._persisted_at: datetime | None = None
        self._handed_off_at: datetime | None = None
        self._execution_started_at: datetime | None = None
        self._last_progress_at: datetime | None = None
        self._completed_at: datetime | None = None
        self._verification_at: datetime | None = None
        self._terminated_at: datetime | None = None
        self._terminal_kind: str | None = None
        self._verification_evidence = False
        self._verification_order: int | None = None
        self._post_verification_delta = False
        self._verification_freshness_unknown = False
        self._verification_events: list[dict[str, Any]] = []
        self._semantic_delta_events: dict[str, dict[str, Any]] = {}
        self._executable_evidence = False
        self._graph_integrity_ok = not any(
            (
                ambiguous_binding_tasks,
                ambiguous_status_tasks,
                ambiguous_review_tasks,
                ambiguous_runs,
            )
        )

        self.units: dict[str, dict[str, Any]] = {}
        self.criteria: dict[str, dict[str, Any]] = {}
        self.invariant_states: dict[str, dict[str, Any]] = {}
        self.participants_seen: dict[tuple[str, str], dict[str, Any]] = {}
        self.tool_spans: list[dict[str, Any]] = []
        self.open_tool_spans: dict[tuple[str, str], dict[str, Any]] = {}
        self.open_model_requests: dict[tuple[str, str, int], dict[str, Any]] = {}
        self.open_run_spans: dict[tuple[str, int], dict[str, Any]] = {}
        self._open_handoff: dict[str, Any] | None = None
        self._pairing_gaps: list[dict[str, str]] = []
        self.model_requests: list[dict[str, Any]] = []
        self.configurations: list[dict[str, Any]] = []
        self.tool_surfaces: list[dict[str, Any]] = []
        self.loaded_skills: set[str] = set()
        self.dispatch_ticks: list[dict[str, Any]] = []
        self.attributions: list[dict[str, Any]] = []
        self.source_gaps: list[dict[str, str]] = []
        if authority_context.source == "unavailable":
            evidence = next(
                (
                    str(event.get("event_id"))
                    for event in events
                    if isinstance(event.get("event_id"), str)
                ),
                "evt_" + "0" * 32,
            )
            self.source_gaps.append(
                {
                    "class": CoverageClass.NATIVE_SOURCE_UNAVAILABLE,
                    "reason_code": "AUTHORITY_CONTEXT_UNAVAILABLE",
                    "event_id": evidence,
                }
            )
        self.compat_pairs: set[tuple[str, str, str | None]] = set()
        self.owner_waits: list[tuple[datetime, datetime]] = []
        self.other_waits: list[tuple[datetime, datetime]] = []
        self.review_waits: list[tuple[datetime, datetime]] = []
        self.active_intervals: list[tuple[datetime, datetime]] = []
        self.clock_anomalies = 0
        self.protocol_violations = 0
        self.turns: set[str] = set()
        self.turns_with_delta: set[str] = set()
        self._last_wall_by_epoch: dict[str, datetime] = {}
        self._event_order = -1

        self._open_waits: dict[str, tuple[str, datetime]] = {}
        self._open_reviews: dict[str, datetime] = {}
        self.verified_review_event_ids: set[str] = set()
        self.verified_completion_event_ids: set[str] = set()
        self._open_clarifications: dict[str, datetime] = {}
        self._blocked_since: dict[str, datetime] = {}
        self._scan()
        self._finalize_review_authority()
        self._finalize_verification_freshness()

    # -- single pass ---------------------------------------------------------------
    def _add_gap(
        self,
        reason_code: str,
        event: dict[str, Any],
        *,
        gap_class: str = CoverageClass.RECONCILIATION_AMBIGUOUS,
    ) -> None:
        event_id = event.get("event_id")
        if not isinstance(event_id, str):
            event_id = "evt_" + canonical_digest(
                {"reason_code": reason_code, "event": str(event.get("event_type"))}
            )
        self.source_gaps.append(
            {"class": gap_class, "reason_code": reason_code, "event_id": event_id}
        )

    def _authorized(
        self,
        event: dict[str, Any],
        *,
        task_ref: str | None = None,
    ) -> bool:
        event_type = str(event.get("event_type") or "")
        if event.get("event_id") in self._ambiguous_authority_event_ids:
            return False
        if (
            event_type in _AUTHORITY_PROTECTED_EVENTS
            and event.get("source_kind") != "aether_checkpoint"
        ):
            return False
        actor = event.get("actor") or {}
        return self.authority_context.permits(
            event_type,
            actor_id=actor.get("id") if isinstance(actor.get("id"), str) else None,
            profile=actor.get("profile") if isinstance(actor.get("profile"), str) else None,
            role=actor.get("role") if isinstance(actor.get("role"), str) else None,
            task_ref=task_ref,
        )

    def _precedes(self, before: dict[str, Any], after: dict[str, Any]) -> bool:
        """Whether explicit producer/parent evidence orders ``before`` before ``after``."""
        before_id = before.get("event_id")
        after_id = after.get("event_id")
        if not isinstance(before_id, str) or not isinstance(after_id, str):
            return False
        if before.get("producer_epoch") == after.get("producer_epoch"):
            before_seq = before.get("producer_seq")
            after_seq = after.get("producer_seq")
            if isinstance(before_seq, int) and isinstance(after_seq, int):
                return before_seq < after_seq
        by_id = {
            event.get("event_id"): event
            for event in self.events
            if isinstance(event.get("event_id"), str)
        }
        cursor = after.get("parent_event_id")
        visited: set[str] = set()
        while isinstance(cursor, str) and cursor not in visited:
            if cursor == before_id:
                return True
            visited.add(cursor)
            cursor = (by_id.get(cursor) or {}).get("parent_event_id")
        return False

    def _finalize_verification_freshness(self) -> None:
        if not self._verification_events:
            return
        deltas = list(self._semantic_delta_events.values())
        fresh: list[dict[str, Any]] = []
        any_after = False
        any_independent = False
        for verification in self._verification_events:
            after = [delta for delta in deltas if self._precedes(verification, delta)]
            independent = [
                delta
                for delta in deltas
                if not self._precedes(delta, verification)
                and not self._precedes(verification, delta)
            ]
            any_after = any_after or bool(after)
            any_independent = any_independent or bool(independent)
            if not after and not independent:
                fresh.append(verification)
        if fresh:
            positions = {event.get("event_id"): index for index, event in enumerate(self.events)}
            selected = max(
                fresh,
                key=lambda event: positions.get(event.get("event_id"), -1),
            )
            self._verification_order = positions.get(selected.get("event_id"))
            self._verification_at = parse_timestamp(selected.get("occurred_at"))
            return
        self._post_verification_delta = any_after
        self._verification_freshness_unknown = any_independent

    def _finalize_review_authority(self) -> None:
        """Invalidate process approval claims when later graph facts revoke assignment."""

        invalid_tasks = {
            task_ref
            for task_ref, record in self.units.items()
            if (
                not record.get("bound")
                or record.get("relation") != "review"
                or not isinstance(record.get("required"), bool)
                or record.get("assigned_profile") is None
                or len(record.get("assigned_profiles", ())) != 1
                or record.get("assignment_conflict_emitted")
                or record.get("binding_conflicted")
                or record.get("classification_conflicted")
                or task_ref in self._ambiguous_binding_tasks
                or task_ref in self._ambiguous_review_tasks
            )
        }
        if not invalid_tasks:
            return
        for event in self.events:
            if not str(event.get("event_type") or "").startswith("review."):
                continue
            task_ref = (event.get("work_unit") or {}).get("task_ref")
            event_id = event.get("event_id")
            if task_ref in invalid_tasks and isinstance(event_id, str):
                self.verified_review_event_ids.discard(event_id)

    def _scan(self) -> None:
        for event_order, event in enumerate(self.events):
            self._event_order = event_order
            moment = parse_timestamp(event.get("occurred_at"))
            if moment is not None:
                self.first_moment = (
                    moment if self.first_moment is None else min(self.first_moment, moment)
                )
                self.as_of = moment if self.as_of is None else max(self.as_of, moment)
                epoch = event.get("producer_epoch")
                if isinstance(epoch, str):
                    previous_wall = self._last_wall_by_epoch.get(epoch)
                    if previous_wall is not None and moment < previous_wall:
                        self.clock_anomalies += 1
                    self._last_wall_by_epoch[epoch] = moment
            if isinstance(event.get("contract_id"), str) and self.contract_id is None:
                self.contract_id = event["contract_id"]
            self.compat_pairs.add(
                (
                    str(event.get("collector_version") or ""),
                    str(event.get("runtime_fingerprint") or ""),
                    event.get("normalizer_ref"),
                )
            )
            turn = event.get("turn_id")
            if isinstance(turn, str):
                self.turns.add(turn)

            work_unit = event.get("work_unit")
            if isinstance(work_unit, dict):
                envelope_task = event.get("task_id")
                unit_task = work_unit.get("task_ref")
                if (
                    isinstance(envelope_task, str)
                    and isinstance(unit_task, str)
                    and envelope_task != unit_task
                ):
                    self._add_gap("TASK_WORK_UNIT_MISMATCH", event)
                    continue

            actor = event.get("actor") or {}
            key = (str(actor.get("kind") or "system"), str(actor.get("id") or "unknown"))
            record = self.participants_seen.setdefault(
                key,
                {
                    "actor_kind": key[0],
                    "actor_id": key[1],
                    "profile": actor.get("profile"),
                    "role": actor.get("role"),
                    "actions": Counter(),
                    "evidence": [],
                },
            )
            record["actions"][str(event.get("event_type"))] += 1
            if len(record["evidence"]) < 32:
                record["evidence"].append(str(event.get("event_id")))

            self._dispatch(event, moment)

    def _dispatch(self, event: dict[str, Any], moment: datetime | None) -> None:
        event_type = str(event.get("event_type") or "")
        handler = _HANDLERS.get(event_type)
        if handler is not None:
            handler(self, event, moment)
        elif event_type.startswith("tool."):
            self._on_tool(event, moment)
        elif event_type.startswith("work_unit."):
            self._on_work_unit(event, moment)
        elif event_type.startswith("run."):
            self._on_run(event, moment)
        elif event_type.startswith("review."):
            self._on_review(event, moment)
        elif event_type.startswith("handoff."):
            self._on_handoff(event, moment)
        elif event_type.startswith("model.") or event_type.startswith("context."):
            self._on_model(event, moment)

    # -- individual event families --------------------------------------------------
    def _note_action(self, moment: datetime | None) -> None:
        if moment is None:
            return
        if self._first_action_at is None or moment < self._first_action_at:
            self._first_action_at = moment

    def _note_progress(self, moment: datetime | None, event: dict[str, Any]) -> None:
        """Only a normalized lifecycle delta advances verified progress (OBS-FR-045)."""
        event_id = event.get("event_id")
        if event.get("event_type") != "contract.completion_verified" and isinstance(event_id, str):
            self._semantic_delta_events[event_id] = event
        if moment is None:
            return
        if self._last_progress_at is None or moment > self._last_progress_at:
            self._last_progress_at = moment
        turn = event.get("turn_id")
        if isinstance(turn, str):
            self.turns_with_delta.add(turn)

    def _on_trace(self, event: dict[str, Any], moment: datetime | None) -> None:
        event_type = str(event.get("event_type"))
        if event_type in ("trace.opened", "trace.resumed"):
            contract = event.get("contract") or {}
            origin = contract.get("origin_message_id")
            if (
                self._started_at is None
                and origin is not None
                and moment is not None
                and event.get("timestamp_source") in ("native", "reconciled")
            ):
                self._started_at = moment
        elif event_type == "trace.closed":
            # Closure is not verification authority. contract.completion_verified
            # supplies completed_at; a bare trace.closed must never manufacture it.
            return
        elif event_type in ("trace.cancelled", "trace.abandoned", "trace.failed"):
            if event.get("status") != _TRACE_TERMINAL_STATUSES[event_type]:
                self._add_gap("TERMINAL_EVENT_CONTRADICTION", event)
                return
            if not self._authorized(event):
                self._add_gap("TERMINAL_AUTHORITY_UNVERIFIED", event)
                return
            self._terminated_at = moment
            self._terminal_kind = event_type.split(".", 1)[1]

    def _on_contract(self, event: dict[str, Any], moment: datetime | None) -> None:
        event_type = str(event.get("event_type"))
        self._note_action(moment)
        if event_type == "contract.executable":
            self._executable_at = moment
            self._executable_evidence = True
        elif event_type == "contract.persisted":
            self._persisted_at = moment
            self._note_progress(moment, event)
        elif event_type == "contract.execution_started":
            if self._execution_started_at is None:
                self._execution_started_at = moment
        elif event_type == "contract.completion_verified":
            # Morfeo's reconciliation against authoritative state. The observer records
            # this evidence; it never supplies it (OBS-D-013).
            if event.get("status") != "verified":
                self._add_gap("COMPLETION_EVENT_CONTRADICTION", event)
                return
            if self._authorized(event):
                self._verification_evidence = True
                self._verification_order = self._event_order
                self._verification_events.append(event)
                event_id = event.get("event_id")
                if isinstance(event_id, str):
                    self.verified_completion_event_ids.add(event_id)
                self._note_progress(moment, event)
            else:
                self._add_gap("COMPLETION_AUTHORITY_UNVERIFIED", event)
        elif (event.get("contract") or {}).get("semantic_delta") not in (None, "none"):
            self._note_progress(moment, event)
        if moment is not None:
            self.active_intervals.append((moment, moment))

    def _on_clarification(self, event: dict[str, Any], moment: datetime | None) -> None:
        contract = event.get("contract") or {}
        key = str(contract.get("ambiguity_ref") or event.get("event_id"))
        if str(event.get("event_type")) == "clarification.requested":
            if moment is not None:
                self._open_clarifications[key] = moment
        else:
            started = self._open_clarifications.pop(key, None)
            if started is not None and moment is not None and moment >= started:
                self.owner_waits.append((started, moment))
            self._note_progress(moment, event)

    def _on_tool(self, event: dict[str, Any], moment: datetime | None) -> None:
        tool = event.get("tool") or {}
        call_id = tool.get("call_id")
        if not isinstance(call_id, str):
            return
        span_key = (str(event.get("session_id") or ""), call_id)
        self._note_action(moment)
        if str(event.get("event_type")) == "tool.started":
            self.open_tool_spans[span_key] = {"started_at": moment, "event": event}
            return
        opened = self.open_tool_spans.pop(span_key, None)
        started = opened["started_at"] if opened else None
        duration = tool.get("duration_ms")
        if started is not None and moment is not None and moment >= started:
            self.active_intervals.append((started, moment))
        elif moment is not None and isinstance(duration, int):
            self.active_intervals.append((moment - timedelta(milliseconds=duration), moment))
        actor = event.get("actor") or {}
        self.tool_spans.append(
            {
                "call_id": call_id,
                "name": str(tool.get("name") or "unknown"),
                "status": str(event.get("status") or "unknown"),
                "duration_ms": duration if isinstance(duration, int) else 0,
                "actor_kind": str(actor.get("kind") or "system"),
                "actor_id": str(actor.get("id") or "unknown"),
                "retry_of": tool.get("retry_of_call_id"),
                "error_class": tool.get("error_class"),
                "approval_outcome": tool.get("approval_outcome"),
                "paired": opened is not None,
                "event_id": str(event.get("event_id") or ""),
            }
        )

    def _on_work_unit(self, event: dict[str, Any], moment: datetime | None) -> None:
        unit = event.get("work_unit") or {}
        task_ref = unit.get("task_ref")
        if not isinstance(task_ref, str):
            return
        event_type = str(event.get("event_type"))
        relation = unit.get("relation")
        required = unit.get("required")
        classification_unknown = (
            relation not in WORK_UNIT_RELATIONS
            or relation == "unknown"
            or not isinstance(required, bool)
        )
        if classification_unknown:
            relation = relation if relation in WORK_UNIT_RELATIONS else "unknown"
            required = required if isinstance(required, bool) else None
        parent_refs = tuple(
            sorted(
                {
                    parent
                    for parent in (unit.get("parent_task_refs") or ())
                    if isinstance(parent, str)
                }
            )
        )
        binding = unit.get("binding_ref")
        record = self.units.setdefault(
            task_ref,
            {
                "task_ref": task_ref,
                "relation": "unknown",
                "required": None,
                "parent_task_refs": [],
                "task_status": "unknown",
                "latest_run_id": None,
                "latest_run_status": None,
                "latest_run_outcome": None,
                "review_state": "not_required",
                "run_totals": Counter(),
                "run_outcome_history": [],
                "evidence": [],
                "bound": False,
                "binding_refs": set(),
                "binding_conflicted": False,
                "binding_conflict_emitted": False,
                "parentage_conflicted": False,
                "parentage_conflict_emitted": False,
                "last_heartbeat_at": None,
                "assigned_profile": None,
                "assigned_profiles": set(),
                "assignment_conflict_emitted": False,
                "review_assignment_conflict_emitted": False,
                "native_relations": set(),
                "native_requirements": set(),
                "native_binding_events": [],
                "classification_events": [],
                "review_request_events": [],
                "product_classifications": set(),
                "classification_exact": False,
                "classification_conflicted": False,
                "classification_unknown_event_id": None,
                "classification_gap_emitted": False,
                "run_terminal_dispositions": {},
                "run_terminal_conflicted": False,
            },
        )
        native_classification = event_type == "work_unit.bound" and event.get("source_kind") in {
            "hermes_hook",
            "native_reconciliation",
        }
        product_classification = (
            event_type == "work_unit.bound" and event.get("source_kind") == "aether_checkpoint"
        )
        native_binding_transition = event_type in {
            "work_unit.bound",
            "work_unit.unbound",
        } and event.get("source_kind") in {"hermes_hook", "native_reconciliation"}
        if native_binding_transition:
            record["native_binding_events"].append(event)
        if native_classification:
            if relation != "unknown":
                record["native_relations"].add(relation)
            if isinstance(required, bool):
                record["native_requirements"].add(required)
            if classification_unknown:
                record["classification_unknown_event_id"] = record[
                    "classification_unknown_event_id"
                ] or event.get("event_id")
            elif isinstance(required, bool):
                record["classification_events"].append(event)
        elif product_classification:
            if not self._authorized(event, task_ref=task_ref):
                self._add_gap("WORK_UNIT_CLASSIFICATION_AUTHORITY_UNVERIFIED", event)
            elif not any(
                (candidate.get("work_unit") or {}).get("binding_ref") == binding
                and self._precedes(candidate, event)
                for candidate in record["native_binding_events"]
            ):
                self._add_gap("WORK_UNIT_CLASSIFICATION_BINDING_UNVERIFIED", event)
            elif classification_unknown:
                record["classification_unknown_event_id"] = record[
                    "classification_unknown_event_id"
                ] or event.get("event_id")
            else:
                record["product_classifications"].add((relation, required))
                record["classification_events"].append(event)

        product_values = record["product_classifications"]
        native_relations = record["native_relations"]
        native_requirements = record["native_requirements"]
        classification_conflict = len(product_values) > 1
        if len(product_values) == 1:
            product_relation, product_required = next(iter(product_values))
            classification_conflict = (
                classification_conflict
                or any(value != product_relation for value in native_relations)
                or any(value != product_required for value in native_requirements)
            )
        classification_conflict = (
            classification_conflict or len(native_relations) > 1 or len(native_requirements) > 1
        )
        if classification_conflict:
            record["relation"] = "unknown"
            record["required"] = None
            record["classification_exact"] = False
            record["classification_conflicted"] = True
            record["classification_unknown_event_id"] = None
            self._graph_integrity_ok = False
        elif len(product_values) == 1:
            record["relation"], record["required"] = next(iter(product_values))
            record["classification_exact"] = True
            record["classification_conflicted"] = False
            record["classification_unknown_event_id"] = None
        else:
            record["relation"] = (
                next(iter(native_relations)) if len(native_relations) == 1 else "unknown"
            )
            record["required"] = (
                next(iter(native_requirements)) if len(native_requirements) == 1 else None
            )
            record["classification_exact"] = False
            record["classification_conflicted"] = False

        contributes_parentage = native_classification or (
            product_classification
            and self._authorized(event, task_ref=task_ref)
            and any(
                (candidate.get("work_unit") or {}).get("binding_ref") == binding
                and self._precedes(candidate, event)
                for candidate in record["native_binding_events"]
            )
            and not classification_unknown
        )
        if contributes_parentage and parent_refs:
            if record["parent_task_refs"] and list(parent_refs) != record["parent_task_refs"]:
                record["parentage_conflicted"] = True
                self._graph_integrity_ok = False
                if not record["parentage_conflict_emitted"]:
                    record["parentage_conflict_emitted"] = True
                    self._add_gap("WORK_UNIT_PARENTAGE_CONFLICT", event)
                record["parent_task_refs"] = []
            elif not record["parent_task_refs"] and not record["parentage_conflicted"]:
                record["parent_task_refs"] = list(parent_refs)
        if isinstance(binding, str):
            record["binding_refs"].add(binding)
            if len(record["binding_refs"]) > 1:
                record["binding_conflicted"] = True
                self._graph_integrity_ok = False
                if not record["binding_conflict_emitted"]:
                    record["binding_conflict_emitted"] = True
                    self._add_gap("WORK_UNIT_BINDING_CONFLICT", event)
        native_binding_source = event.get("source_kind") in {
            "hermes_hook",
            "native_reconciliation",
        }
        if event_type == "work_unit.bound" and native_binding_source:
            record["bound"] = True
            actor = event.get("actor") or {}
            assigned_profile = actor.get("profile")
            if isinstance(assigned_profile, str):
                record["assigned_profiles"].add(assigned_profile)
                if len(record["assigned_profiles"]) > 1:
                    if not record["assignment_conflict_emitted"]:
                        record["assignment_conflict_emitted"] = True
                        self._add_gap("WORK_UNIT_ASSIGNMENT_CONFLICT", event)
                    record["assigned_profile"] = None
                    if record["review_state"] == "approved":
                        record["review_state"] = "pending"
                        if not record["review_assignment_conflict_emitted"]:
                            record["review_assignment_conflict_emitted"] = True
                            self._add_gap("REVIEW_ASSIGNMENT_UNVERIFIED", event)
                else:
                    record["assigned_profile"] = assigned_profile
        elif event_type == "work_unit.unbound" and native_binding_source:
            record["bound"] = False
            # A same-project task observed next to an active trace but lacking a durable
            # binding is material coverage, not a project-global counter the summary
            # cannot localize (#214). It remains outside the contract graph.
            self._add_gap("UNBOUND_WORK_UNIT_OBSERVED", event)
        if (
            record["classification_conflicted"]
            or record["parentage_conflicted"]
            or record["binding_conflicted"]
            or task_ref in self._ambiguous_binding_tasks
        ):
            # Conflicting descriptions of one durable assignment are not a choice
            # between first and last. Neutralize every graph-authority dimension while
            # retaining the raw evidence and its reproducible gap.
            record["relation"] = "unknown"
            record["required"] = None
            record["classification_exact"] = False
            record["parent_task_refs"] = []
        if record["relation"] == "review" and record["review_state"] == "not_required":
            record["review_state"] = "pending"
        previous_status = record["task_status"]
        if unit.get("task_status"):
            record["task_status"] = unit["task_status"]
        if unit.get("run_status"):
            record["latest_run_status"] = unit["run_status"]
        if unit.get("run_outcome"):
            record["latest_run_outcome"] = unit["run_outcome"]
        run_id = event.get("run_id")
        collapsed_run_conflict = (
            isinstance(run_id, int) and (task_ref, run_id) in self._ambiguous_runs
        )
        if (
            record["run_terminal_conflicted"]
            or collapsed_run_conflict
            or task_ref in self._ambiguous_status_tasks
        ):
            record["task_status"] = "unknown"
            record["latest_run_status"] = "unknown"
            record["latest_run_outcome"] = "unknown"
        if len(record["evidence"]) < 32:
            record["evidence"].append(str(event.get("event_id")))
        is_native_heartbeat = (
            event_type == "work_unit.status"
            and event.get("source_kind") == "native_reconciliation"
            and event.get("timestamp_source") in ("native", "reconciled")
            and record["task_status"] == "running"
            and moment is not None
        )
        if is_native_heartbeat:
            # Locked Hermes materializes a running task status at its durable
            # last_heartbeat_at. Other starts are activity evidence, not a heartbeat.
            record["last_heartbeat_at"] = moment

        # Execution begins when the first required *bound* unit enters the
        # authoritative running state; a separate semantic checkpoint is optional.
        if (
            self._execution_started_at is None
            and record["bound"]
            and record["required"]
            and record["task_status"] == "running"
            and not is_native_heartbeat
        ):
            self._execution_started_at = moment

        # `blocked` is an open state, and its interval is dependency wait, not idle time.
        if record["task_status"] == "blocked" and moment is not None:
            self._blocked_since.setdefault(task_ref, moment)
        elif task_ref in self._blocked_since and moment is not None:
            started = self._blocked_since.pop(task_ref)
            if moment >= started:
                self.other_waits.append((started, moment))
        if record["task_status"] != previous_status and not is_native_heartbeat:
            self._note_progress(moment, event)

    def _on_run(self, event: dict[str, Any], moment: datetime | None) -> None:
        self._on_work_unit(event, moment)
        unit = event.get("work_unit") or {}
        task_ref = unit.get("task_ref")
        if not isinstance(task_ref, str):
            return
        record = self.units.get(task_ref)
        if record is None:
            return
        run_id = event.get("run_id")
        if isinstance(run_id, int):
            record["latest_run_id"] = run_id
        if str(event.get("event_type")) == "run.started":
            record["run_totals"]["running"] += 1
            if isinstance(run_id, int):
                self.open_run_spans[(task_ref, run_id)] = event
            if moment is not None and self._execution_started_at is None and record["required"]:
                self._execution_started_at = moment
        else:
            if (
                isinstance(run_id, int)
                and self.open_run_spans.pop((task_ref, run_id), None) is None
            ):
                self._add_gap("RUN_TERMINAL_WITHOUT_START", event, gap_class="unpaired_span")
            raw_outcome = unit.get("run_outcome")
            if raw_outcome == "protocol_violation":
                self.protocol_violations += 1
                self._add_gap("RUN_PROTOCOL_VIOLATION", event, gap_class=CoverageClass.OTHER)
                outcome = "protocol_violation"
            elif raw_outcome in {
                "completed",
                "blocked",
                "crashed",
                "timed_out",
                "failed",
                "spawn_failed",
                "gave_up",
                "reclaimed",
                "rate_limited",
                "stale",
                "review_requested",
                "changes_requested",
                "scheduled",
            }:
                outcome = raw_outcome
            elif unit.get("run_status") == "failed" or event.get("status") == "failed":
                outcome = "failed"
            else:
                outcome = "unknown"
                if raw_outcome not in (None, "unknown"):
                    self._add_gap("RUN_OUTCOME_UNSUPPORTED", event, gap_class=CoverageClass.OTHER)
            record["run_totals"]["running"] = max(0, record["run_totals"]["running"] - 1)
            collapsed_run_conflict = (
                isinstance(run_id, int) and (task_ref, run_id) in self._ambiguous_runs
            )
            counted_outcome = "unknown" if collapsed_run_conflict else outcome
            record["run_totals"][counted_outcome] += 1
            # Every attempt is retained: a crash that a later retry recovered from is
            # still a runtime failure that happened, and OBS-FR-043 counts it separately.
            record["run_outcome_history"].append(counted_outcome)
            if isinstance(run_id, int):
                disposition = (
                    event.get("status"),
                    unit.get("task_status"),
                    unit.get("run_status"),
                    outcome,
                )
                claims = record["run_terminal_dispositions"].setdefault(run_id, set())
                claims.add(disposition)
                if len(claims) > 1:
                    record["run_terminal_conflicted"] = True
                    self._graph_integrity_ok = False
            if record["run_terminal_conflicted"] or collapsed_run_conflict:
                record["task_status"] = "unknown"
                record["latest_run_status"] = "unknown"
                record["latest_run_outcome"] = "unknown"
            else:
                record["latest_run_outcome"] = outcome

    def _on_review(self, event: dict[str, Any], moment: datetime | None) -> None:
        unit = event.get("work_unit") or {}
        task_ref = unit.get("task_ref")
        if not isinstance(task_ref, str):
            return
        event_type = str(event.get("event_type"))
        expected_status = {
            "review.requested": "started",
            "review.approved": "passed",
            "review.changes_requested": "rejected",
        }.get(event_type)
        if event.get("status") != expected_status:
            self._add_gap("REVIEW_EVENT_CONTRADICTION", event)
            return
        if not self._authorized(event, task_ref=task_ref):
            self._add_gap("REVIEW_AUTHORITY_UNVERIFIED", event)
            return
        existing = self.units.get(task_ref)
        binding_ref = unit.get("binding_ref")
        actor = event.get("actor") or {}
        actor_profile = actor.get("profile")
        assignment_verified = (
            existing is not None
            and existing.get("bound")
            and existing.get("assigned_profile") is not None
            and actor_profile == existing.get("assigned_profile")
            and any(
                (candidate.get("actor") or {}).get("profile") == actor_profile
                and (candidate.get("work_unit") or {}).get("binding_ref") == binding_ref
                and self._precedes(candidate, event)
                for candidate in existing.get("native_binding_events", ())
                if candidate.get("event_type") == "work_unit.bound"
            )
        )
        classification_verified = (
            existing is not None
            and existing.get("relation") == "review"
            and isinstance(existing.get("required"), bool)
            and any(
                self._precedes(candidate, event)
                and (candidate.get("work_unit") or {}).get("binding_ref") == binding_ref
                for candidate in existing.get("classification_events", ())
            )
        )
        request_verified = event_type == "review.requested" or (
            existing is not None
            and any(
                self._precedes(candidate, event)
                and (candidate.get("work_unit") or {}).get("binding_ref") == binding_ref
                for candidate in existing.get("review_request_events", ())
            )
        )
        if not assignment_verified or not classification_verified or not request_verified:
            self._add_gap("REVIEW_ASSIGNMENT_UNVERIFIED", event)
            return
        event_id = event.get("event_id")
        if isinstance(event_id, str):
            self.verified_review_event_ids.add(event_id)
        self._on_work_unit(event, moment)
        record = self.units.get(task_ref)
        if record is None:
            return
        if event_type == "review.requested":
            record["review_state"] = "pending"
            record["review_request_events"].append(event)
            if moment is not None:
                self._open_reviews[task_ref] = moment
        else:
            record["review_state"] = (
                "approved" if event_type == "review.approved" else "changes_requested"
            )
            started = self._open_reviews.pop(task_ref, None)
            if started is None:
                self._add_gap("REVIEW_TERMINAL_WITHOUT_START", event, gap_class="unpaired_span")
            if started is not None and moment is not None and moment >= started:
                self.review_waits.append((started, moment))
            self._note_progress(moment, event)
        if task_ref in self._ambiguous_review_tasks:
            record["review_state"] = "pending"

    def _on_handoff(self, event: dict[str, Any], moment: datetime | None) -> None:
        event_type = str(event.get("event_type"))
        if event_type == "handoff.started":
            self._open_handoff = event
            return
        # The locked checkpoint may expose a successful handoff as one atomic fact with
        # no stable span identifier, so only an observed open start can become unpaired.
        self._open_handoff = None
        if event_type == "handoff.completed":
            self._handed_off_at = moment
            self._note_progress(moment, event)

    def _on_wait(self, event: dict[str, Any], moment: datetime | None) -> None:
        wait = event.get("wait") or {}
        wait_id = wait.get("wait_id")
        if not isinstance(wait_id, str) or moment is None:
            return
        if str(event.get("event_type")) == "wait.started":
            self._open_waits[wait_id] = (str(wait.get("kind") or "unknown"), moment)
            return
        opened = self._open_waits.pop(wait_id, None)
        if opened is None:
            self._add_gap("WAIT_TERMINAL_WITHOUT_START", event, gap_class="unpaired_span")
            return
        kind, started = opened
        if moment < started:
            self.clock_anomalies += 1
            return
        if kind == "owner":
            self.owner_waits.append((started, moment))
        elif kind == "review":
            self.review_waits.append((started, moment))
        else:
            self.other_waits.append((started, moment))

    def _on_acceptance(self, event: dict[str, Any], moment: datetime | None) -> None:
        acceptance = event.get("acceptance") or {}
        criterion = acceptance.get("criterion_ref")
        if not isinstance(criterion, str):
            return
        assigned = acceptance.get("review_task_ref") or acceptance.get("assigned_task_ref")
        task_ref = assigned if isinstance(assigned, str) else None
        if not self._authorized(event, task_ref=task_ref):
            self._add_gap("ACCEPTANCE_AUTHORITY_UNVERIFIED", event)
            return
        record = self.criteria.setdefault(
            criterion,
            {
                "criterion_ref": criterion,
                "state": "pending",
                "evidence_refs": [],
                "last_event_id": str(event.get("event_id")),
                "history": [],
            },
        )
        previous = (
            record["state"],
            tuple(sorted(record["evidence_refs"])),
        )
        record["state"] = acceptance.get("state") or "unknown"
        record["evidence_refs"] = list(acceptance.get("evidence_refs") or [])
        record["last_event_id"] = str(event.get("event_id"))
        record["history"].append(record["state"])
        current = (
            record["state"],
            tuple(sorted(record["evidence_refs"])),
        )
        if current != previous:
            self._note_progress(moment, event)

    def _on_invariant(self, event: dict[str, Any], moment: datetime | None) -> None:
        contract = event.get("contract") or {}
        key = contract.get("invariant_key")
        if not isinstance(key, str):
            return
        if not self._authorized(event):
            self._add_gap("INVARIANT_AUTHORITY_UNVERIFIED", event)
            return
        status = event.get("status")
        expected_status = "passed" if event.get("event_type") == "invariant.passed" else "failed"
        if status == "unknown":
            state = "unknown"
        elif status != expected_status:
            state = "unknown"
            self._add_gap("INVARIANT_EVENT_CONTRADICTION", event)
        else:
            state = expected_status
        record = self.invariant_states.setdefault(
            key, {"key": key, "state": "unknown", "history": []}
        )
        record["history"].append(record["state"])
        record["state"] = state
        record["last_event_id"] = str(event.get("event_id"))
        self._note_progress(moment, event)

    def _on_coverage(self, event: dict[str, Any], _moment: datetime | None) -> None:
        coverage = event.get("coverage") or {}
        if str(event.get("event_type")) != "coverage.gap":
            return
        if "PROTOCOL_VIOLATION" in str(coverage.get("reason_code") or ""):
            self.protocol_violations += 1
        self.source_gaps.append(
            {
                "class": str(coverage.get("class") or "other"),
                "reason_code": str(coverage.get("reason_code") or "UNCLASSIFIED"),
                "event_id": str(event.get("event_id")),
            }
        )

    def _on_configuration(self, event: dict[str, Any], _moment: datetime | None) -> None:
        configuration = event.get("configuration")
        if isinstance(configuration, dict):
            self.configurations.append(dict(configuration))

    def _on_tool_surface(self, event: dict[str, Any], _moment: datetime | None) -> None:
        surface = event.get("tool_surface")
        if isinstance(surface, dict):
            self.tool_surfaces.append(dict(surface))

    def _on_skill(self, event: dict[str, Any], _moment: datetime | None) -> None:
        tool = event.get("tool") or {}
        identifier = tool.get("target_ref")
        if isinstance(identifier, str):
            self.loaded_skills.add(identifier)

    def _on_model(self, event: dict[str, Any], moment: datetime | None) -> None:
        request = event.get("model_request")
        if not isinstance(request, dict):
            return
        state = str(request.get("state") or "unknown")
        request_ref = request.get("request_ref")
        attempt = request.get("attempt_count")
        key = (
            str(event.get("session_id") or ""),
            str(request_ref or ""),
            attempt if isinstance(attempt, int) and attempt > 0 else 1,
        )
        if state == "started":
            self.open_model_requests[key] = event
        else:
            if state in ("completed", "failed") and self.open_model_requests.pop(key, None) is None:
                self._add_gap("MODEL_TERMINAL_WITHOUT_START", event, gap_class="unpaired_span")
            # A start and its terminal event describe one API attempt. Totals retain
            # terminals (and explicit context lifecycle facts) only.
            recorded = dict(request)
            # request_ref is native only within a session.  Keep this private reducer
            # key out of the summary while preventing unrelated sessions from merging.
            recorded["_session_id"] = str(event.get("session_id") or "")
            self.model_requests.append(recorded)
        if moment is not None:
            duration = (request or {}).get("duration_ms")
            if isinstance(duration, int) and duration > 0:
                self.active_intervals.append((moment - timedelta(milliseconds=duration), moment))

    def _on_dispatch(self, event: dict[str, Any], moment: datetime | None) -> None:
        dispatch = event.get("dispatch") or {}
        if moment is None:
            return
        if dispatch.get("global_limit") is None and dispatch.get("per_profile_limit") is None:
            self._add_gap(
                "DISPATCH_LIMITS_UNAVAILABLE",
                event,
                gap_class=CoverageClass.NATIVE_SOURCE_UNAVAILABLE,
            )
        self.dispatch_ticks.append(
            {
                "at": moment,
                "eligible": dispatch.get("eligible_count"),
                "running": dispatch.get("running_count"),
                "global_limit": dispatch.get("global_limit"),
                "per_profile_limit": dispatch.get("per_profile_limit"),
                "bottleneck_class": dispatch.get("bottleneck_class") or "unknown",
                "precision_ms": dispatch.get("precision_ms"),
                "evidence": [str(event.get("event_id"))],
            }
        )

    def _on_attribution(self, event: dict[str, Any], moment: datetime | None) -> None:
        attribution = event.get("attribution")
        if not isinstance(attribution, dict):
            return
        self.attributions.append(
            {
                **attribution,
                "event_id": str(event.get("event_id")),
                "at": moment,
            }
        )

    def _on_participant(self, event: dict[str, Any], moment: datetime | None) -> None:
        self._note_action(moment)

    # -- projections ----------------------------------------------------------------
    def timestamps(self) -> dict[str, Any]:
        closed = self._completed_at or self._terminated_at
        return {
            # A later materialization timestamp never substitutes for an unknown origin.
            "started_at": _iso(self._started_at),
            "first_action_at": _iso(self._first_action_at),
            "executable_at": _iso(self._executable_at),
            "persisted_at": _iso(self._persisted_at),
            "handed_off_at": _iso(self._handed_off_at),
            "execution_started_at": _iso(self._execution_started_at),
            "last_verified_progress_at": _iso(self._last_progress_at),
            "completed_at": _iso(self._completed_at),
            "terminated_at": _iso(self._terminated_at),
            "closed_at": _iso(closed),
        }

    def duration(self, as_of: datetime | None) -> dict[str, Any]:
        origin = self._started_at
        closed = self._completed_at or self._terminated_at
        horizon = closed or as_of

        owner_raw = list(self.owner_waits)
        dependency_raw = list(self.other_waits)
        review_raw = list(self.review_waits)
        active_raw = list(self.active_intervals)

        def add_open(target: list[tuple[datetime, datetime]], started: datetime) -> None:
            if horizon is None:
                return
            if horizon < started:
                self.clock_anomalies += 1
                return
            target.append((started, horizon))

        for started in self._open_clarifications.values():
            add_open(owner_raw, started)
        for started in self._blocked_since.values():
            add_open(dependency_raw, started)
        for started in self._open_reviews.values():
            add_open(review_raw, started)
        for kind, started in self._open_waits.values():
            add_open(owner_raw if kind == "owner" else dependency_raw, started)
        for opened in self.open_tool_spans.values():
            started = opened.get("started_at")
            if isinstance(started, datetime):
                add_open(active_raw, started)

        def clip(
            intervals: list[tuple[datetime, datetime]],
        ) -> list[tuple[datetime, datetime]]:
            result: list[tuple[datetime, datetime]] = []
            for start, end in intervals:
                if end < start:
                    self.clock_anomalies += 1
                    continue
                clipped_start = max(start, origin) if origin is not None else start
                clipped_end = min(end, horizon) if horizon is not None else end
                if clipped_end < clipped_start:
                    self.clock_anomalies += 1
                    continue
                result.append((clipped_start, clipped_end))
            return result

        owner_raw = clip(owner_raw)
        dependency_raw = clip(dependency_raw)
        review_raw = clip(review_raw)
        active_raw = clip(active_raw)

        # Reporting precedence is normative and prevents double-counting.
        owner = owner_raw
        dependency = _subtract(dependency_raw, owner)
        review = _subtract(review_raw, owner + dependency)
        active = _subtract(active_raw, owner + dependency + review)

        owner_ms = _union_ms(owner)
        dependency_ms = _union_ms(dependency)
        review_ms = _union_ms(review)
        active_ms = _union_ms(active)
        # Preserve overlap multiplicity before precedence/union.  Parallel active
        # spans and simultaneous wait/activity classifications increase this counter
        # while the partitioned duration remains double-count-free.
        raw_sum = sum(
            max(0, int((end - start).total_seconds() * 1000))
            for intervals in (owner_raw, dependency_raw, review_raw, active_raw)
            for start, end in intervals
        )
        overlap_ms = max(
            0,
            raw_sum - _union_ms(owner_raw + dependency_raw + review_raw + active_raw),
        )

        wall = _ms(origin, horizon)
        if origin is not None and horizon is not None and wall is None:
            self.clock_anomalies += 1
        classified = _union_ms(owner + dependency + review + active)
        unclassified = None if wall is None else max(0, wall - classified)

        def phase(start: datetime | None, end: datetime | None) -> int | None:
            value = _ms(start, end)
            if start is not None and end is not None and value is None:
                self.clock_anomalies += 1
            return value

        return {
            "wall_ms": wall,
            "contract_creation_ms": phase(origin, self._persisted_at),
            "handoff_latency_ms": phase(self._persisted_at, self._handed_off_at),
            "dispatch_latency_ms": phase(self._handed_off_at, self._execution_started_at),
            "execution_ms": phase(self._execution_started_at, horizon),
            "time_to_completion_ms": phase(origin, self._completed_at),
            "time_to_termination_ms": phase(origin, self._terminated_at),
            "time_to_first_action_ms": phase(origin, self._first_action_at),
            "time_to_executable_ms": phase(origin, self._executable_at),
            "active_ms": active_ms,
            "owner_wait_ms": owner_ms,
            "external_wait_ms": dependency_ms,
            "review_wait_ms": review_ms,
            # Unclassified time stays visible; it is never relabelled productive or waiting.
            "unclassified_ms": unclassified,
            "overlap_ms": overlap_ms,
        }

    def work_graph(self) -> dict[str, Any]:
        units = []
        totals = Counter()
        root_refs: list[str] = []
        for task_ref in sorted(self.units):
            record = self.units[task_ref]
            unknown_event_id = record.get("classification_unknown_event_id")
            if (
                not record["classification_exact"]
                and isinstance(unknown_event_id, str)
                and not record["classification_gap_emitted"]
            ):
                self.source_gaps.append(
                    {
                        "class": CoverageClass.RECONCILIATION_AMBIGUOUS,
                        "reason_code": "WORK_UNIT_CLASSIFICATION_UNKNOWN",
                        "event_id": unknown_event_id,
                    }
                )
                record["classification_gap_emitted"] = True
            if not record["bound"]:
                continue
            if record["relation"] == "root":
                root_refs.append(task_ref)
            for outcome, count in record["run_totals"].items():
                totals[outcome] += count
            units.append(
                {
                    "task_ref": task_ref,
                    "relation": record["relation"],
                    "required": record["required"],
                    "parent_task_refs": sorted(record["parent_task_refs"]),
                    "task_status": record["task_status"],
                    "latest_run_id": record["latest_run_id"],
                    "latest_run_status": record["latest_run_status"],
                    "latest_run_outcome": record["latest_run_outcome"],
                    "review_state": record["review_state"],
                    "runtime_state": _unit_runtime_state(record, self.as_of),
                    "evidence_event_ids": sorted(set(record["evidence"])),
                }
            )
        root_ref = root_refs[0] if len(root_refs) == 1 else None
        unit_refs = {unit["task_ref"] for unit in units}

        def graph_gap(reason: str, evidence: str) -> None:
            self._graph_integrity_ok = False
            self.source_gaps.append(
                {
                    "class": CoverageClass.RECONCILIATION_AMBIGUOUS,
                    "reason_code": reason,
                    "event_id": evidence,
                }
            )

        if units and not root_refs:
            graph_gap("ROOT_TASK_MISSING", units[0]["evidence_event_ids"][0])
        elif len(root_refs) > 1:
            graph_gap(
                "MULTIPLE_ROOT_TASKS",
                next(
                    unit["evidence_event_ids"][0]
                    for unit in units
                    if unit["task_ref"] == root_refs[1]
                ),
            )

        for unit in units:
            missing_parents = [
                parent for parent in unit["parent_task_refs"] if parent not in unit_refs
            ]
            if missing_parents or (
                unit["relation"] != "root" and not unit["parent_task_refs"] and root_refs
            ):
                graph_gap("WORK_GRAPH_ORPHAN", unit["evidence_event_ids"][0])

        parents_by_task = {unit["task_ref"]: set(unit["parent_task_refs"]) for unit in units}
        visiting: set[str] = set()
        visited: set[str] = set()

        def has_cycle(task_ref: str) -> bool:
            if task_ref in visiting:
                return True
            if task_ref in visited:
                return False
            visiting.add(task_ref)
            cycle = any(
                parent in parents_by_task and has_cycle(parent)
                for parent in parents_by_task.get(task_ref, ())
            )
            visiting.remove(task_ref)
            visited.add(task_ref)
            return cycle

        for unit in units:
            if has_cycle(unit["task_ref"]):
                graph_gap("WORK_GRAPH_CYCLE", unit["evidence_event_ids"][0])
                break
        required = [u for u in units if u["required"] is True]
        unknown_requirements = [u for u in units if u["required"] is None]
        done = [u for u in required if u["task_status"] == "done"]
        open_units = [u for u in required if u["task_status"] in OPEN_TASK_STATUSES]
        run_totals = {
            "total": sum(totals.values()),
            "running": totals.get("running", 0),
            "completed": totals.get("completed", 0),
            "blocked": totals.get("blocked", 0),
            "crashed": totals.get("crashed", 0),
            "timed_out": totals.get("timed_out", 0),
            "failed": totals.get("failed", 0),
            "spawn_failed": totals.get("spawn_failed", 0),
            "gave_up": totals.get("gave_up", 0),
            "reclaimed": totals.get("reclaimed", 0),
            "protocol_violation": totals.get("protocol_violation", 0),
            "rate_limited": totals.get("rate_limited", 0),
            "stale": totals.get("stale", 0),
            "review_requested": totals.get("review_requested", 0),
            "changes_requested": totals.get("changes_requested", 0),
            "scheduled": totals.get("scheduled", 0),
            "unknown": totals.get("unknown", 0),
        }
        return {
            "root_task_ref": root_ref,
            "total_units": len(units),
            "required_units": len(required),
            "done_required_units": len(done),
            "open_required_units": len(open_units),
            "blocked_required_units": len([u for u in required if u["task_status"] == "blocked"]),
            "review_required_units": len([u for u in required if u["task_status"] == "review"]),
            "all_required_done": (
                bool(required) and not unknown_requirements and len(done) == len(required)
            ),
            "run_totals": run_totals,
            "units": units,
        }

    def acceptance(self) -> dict[str, Any]:
        criteria = []
        for criterion_ref in sorted(self.criteria):
            record = self.criteria[criterion_ref]
            criteria.append(
                {
                    "criterion_ref": criterion_ref,
                    "state": record["state"],
                    "evidence_refs": sorted(set(record["evidence_refs"])),
                    "last_event_id": record["last_event_id"],
                }
            )
        counts = Counter(c["state"] for c in criteria)
        # A criterion is satisfied only when it passed AND carries at least one evidence
        # reference; a bare `passed` with no evidence never completes a contract.
        evidenced = [c for c in criteria if c["state"] == "passed" and c["evidence_refs"]]
        return {
            "complete": bool(criteria) and len(evidenced) == len(criteria),
            "criterion_count": len(criteria),
            "passed": counts.get("passed", 0),
            "failed": counts.get("failed", 0),
            "pending": counts.get("pending", 0),
            "unknown": counts.get("unknown", 0),
            "criteria": criteria,
        }

    def completion_state(self, work_graph: dict[str, Any], acceptance: dict[str, Any]) -> str:
        if self._terminal_kind:
            return self._terminal_kind
        invariant_values = {key: record["state"] for key, record in self.invariant_states.items()}
        failed_invariants = sorted(
            key for key, state in invariant_values.items() if state == "failed"
        )
        unknown_invariants = sorted(
            key for key, state in invariant_values.items() if state in ("pending", "unknown")
        )
        closure_attempted = self._verification_evidence or bool(
            self.criteria and any(record["bound"] for record in self.units.values())
        )
        if closure_attempted and failed_invariants:
            record = self.invariant_states[failed_invariants[0]]
            self.source_gaps.append(
                {
                    "class": CoverageClass.OTHER,
                    "reason_code": "CLOSURE_INVARIANT_FAILED",
                    "event_id": record["last_event_id"],
                }
            )
        if closure_attempted and unknown_invariants:
            record = self.invariant_states[unknown_invariants[0]]
            self.source_gaps.append(
                {
                    "class": CoverageClass.OTHER,
                    "reason_code": "CLOSURE_INVARIANT_UNKNOWN",
                    "event_id": record["last_event_id"],
                }
            )
        explicit_invariants_complete = REQUIRED_EXECUTABLE_INVARIANTS.issubset(
            invariant_values
        ) and all(invariant_values[key] == "passed" for key in REQUIRED_EXECUTABLE_INVARIANTS)
        invariants_settled = (
            self._executable_evidence
            and explicit_invariants_complete
            and not failed_invariants
            and not unknown_invariants
        )
        if closure_attempted and (
            not self._executable_evidence or not explicit_invariants_complete
        ):
            evidence = (
                next(iter(self.invariant_states.values()))["last_event_id"]
                if self.invariant_states
                else self.events[0].get("event_id")
                if self.events
                else "evt_" + "0" * 32
            )
            self.source_gaps.append(
                {
                    "class": CoverageClass.NATIVE_SOURCE_UNAVAILABLE,
                    "reason_code": "EXECUTABLE_INVARIANTS_MISSING",
                    "event_id": str(evidence),
                }
            )
        graph_settled = (
            work_graph["root_task_ref"] is not None
            and self._graph_integrity_ok
            and work_graph["required_units"] > 0
            and work_graph["all_required_done"]
            and work_graph["open_required_units"] == 0
            and all(
                unit["review_state"] in ("approved", "not_required")
                for unit in work_graph["units"]
                if unit["required"]
            )
        )
        acceptance_settled = acceptance["complete"] and acceptance["failed"] == 0
        if graph_settled and acceptance_settled and invariants_settled:
            # OBS-D-013: mechanical settlement alone is a candidate, never `completed`.
            if (
                self._verification_evidence
                and not self._post_verification_delta
                and not self._verification_freshness_unknown
            ):
                self._completed_at = self._verification_at
                return "completed"
            return "completion_candidate"
        if work_graph["blocked_required_units"]:
            return "blocked"
        if work_graph["review_required_units"] or any(
            unit["review_state"] == "pending" for unit in work_graph["units"]
        ):
            return "in_review"
        if graph_settled and not acceptance_settled:
            return "awaiting_final_verification"
        if self._execution_started_at is not None:
            return "executing"
        if self._handed_off_at is not None:
            return "handed_off"
        if self._persisted_at is not None:
            return "persisted"
        return "open"

    def runtime_state(
        self,
        work_graph: dict[str, Any],
        flow: dict[str, Any],
        coverage: dict[str, Any],
        completion: str,
    ) -> dict[str, Any]:
        """Six dimensions, never collapsed into one progress label (spec section 7.5)."""
        running = work_graph["run_totals"]["running"]
        # Precedence: any active required run prevents `not_applicable`; a closed trace has
        # no liveness question left to answer; only *unresolved* stale/dead evidence makes
        # a clean aggregate impossible. A historical crash that was later retried
        # successfully is an anomaly in the record, not a dead worker now.
        unresolved_dead = any(
            unit["latest_run_outcome"] in ANOMALOUS_RUN_OUTCOMES and unit["task_status"] != "done"
            for unit in work_graph["units"]
        )
        running_units = [
            unit
            for unit in work_graph["units"]
            if unit["required"]
            and (unit["task_status"] == "running" or unit["latest_run_status"] == "running")
        ]
        running_liveness = {unit["runtime_state"]["liveness"] for unit in running_units}
        if "stale" in running_liveness:
            liveness = "stale"
        elif "alive" in running_liveness:
            liveness = "alive"
        elif running_units or running:
            # A start/outcome counter has no recency semantics. Without the durable
            # native heartbeat instant the honest state is unknown, never alive.
            liveness = "unknown"
        elif completion in ("completed", "cancelled", "abandoned", "failed"):
            liveness = "not_applicable"
        elif unresolved_dead:
            liveness = "dead"
        else:
            liveness = "unknown"
        if self.open_tool_spans:
            activity = "tool_running"
        elif running:
            activity = "working"
        elif self._open_reviews:
            activity = "reviewing"
        elif self._open_waits or self._open_clarifications or self._blocked_since:
            activity = "waiting"
        elif completion in ("completed", "cancelled", "abandoned", "failed"):
            activity = "idle"
        else:
            activity = "unknown"

        if completion == "completed":
            progress = "complete"
        elif flow["semantic_loops"]:
            progress = "suspected_loop"
        elif self._last_progress_at is not None:
            progress = "verified"
        elif self.events:
            progress = "no_verified_progress"
        else:
            progress = "unknown"

        if self._open_clarifications:
            waiting = "owner"
        elif self._blocked_since:
            waiting = "dependency"
        elif self._open_reviews:
            waiting = "review"
        elif self._open_waits:
            waiting = next(iter(sorted(kind for kind, _ in self._open_waits.values())), "unknown")
            waiting = {
                "owner": "owner",
                "dependency": "dependency",
                "approval": "approval",
                "provider_backoff": "provider_backoff",
                "process": "process",
                "external": "dependency",
            }.get(waiting, "unknown")
        elif completion in ("completed", "cancelled", "abandoned", "failed"):
            waiting = "none"
        else:
            waiting = "none"

        # OBS-FR-044 asks whether *unresolved* anomaly evidence exists. A crash that was
        # retried to success and a review return that was later approved are history, not
        # an open problem, so they must not permanently pin this dimension to `present`.
        unresolved = (
            unresolved_dead
            or any(unit["review_state"] == "changes_requested" for unit in work_graph["units"])
            or any(inv["state"] == "failed" for inv in self.invariants())
            or flow["unexplained_reversions"]
            or (flow["semantic_loops"] and completion not in ("completed",))
            or self.clock_anomalies
            or not coverage["complete"]
        )
        anomalies = "present" if unresolved else ("clear" if self.events else "unknown")
        termination = self._terminal_kind or ("completed" if completion == "completed" else "open")
        return {
            "liveness": liveness,
            "activity": activity,
            "progress": progress,
            "waiting": waiting,
            "anomalies": anomalies,
            "termination": termination,
        }

    def participants(self) -> list[dict[str, Any]]:
        records = []
        for key in sorted(self.participants_seen):
            record = self.participants_seen[key]
            actions = record["actions"]
            if record["actor_kind"] == "subagent":
                linked_start = bool(actions.get("participant.joined") or actions.get("run.started"))
                returned_or_terminal = any(
                    actions.get(event_type)
                    for event_type in (
                        "participant.left",
                        "run.finished",
                        "tool.completed",
                        "tool.failed",
                        "tool.blocked",
                        "tool.cancelled",
                        "tool.timed_out",
                        "tool.interrupted",
                    )
                )
                # A spawn observation alone does not establish participation.  The
                # child must both join a linked run and produce a returned/terminal
                # observation (OBS-FR-009).
                if not (linked_start and returned_or_terminal):
                    continue
            records.append(
                {
                    "actor_kind": record["actor_kind"],
                    "actor_id": record["actor_id"],
                    "profile": record["profile"],
                    "role": record["role"],
                    "action_total": sum(actions.values()),
                    "actions": dict(sorted(actions.items())),
                    "evidence_event_ids": sorted(set(record["evidence"])),
                }
            )
        return records

    def tools(self) -> dict[str, Any]:
        """Every terminal state keeps its own total; none is folded into success."""
        buckets: dict[str, Counter] = defaultdict(Counter)
        durations: dict[str, int] = defaultdict(int)
        actor_buckets: dict[tuple[str, str], dict[str, Any]] = {}
        totals = Counter()
        total_duration = 0
        retries = 0

        for span in self.tool_spans:
            status = span["status"] if span["status"] in _TOOL_STATUSES else "unknown"
            name = span["name"]
            buckets[name][status] += 1
            buckets[name]["calls"] += 1
            durations[name] += span["duration_ms"]
            totals[status] += 1
            totals["calls"] += 1
            total_duration += span["duration_ms"]
            if span["retry_of"]:
                retries += 1
            actor_key = (span["actor_kind"], span["actor_id"])
            actor = actor_buckets.setdefault(
                actor_key,
                {
                    "actor_kind": actor_key[0],
                    "actor_id": actor_key[1],
                    "counts": Counter(),
                    "duration": 0,
                    "by_name": defaultdict(Counter),
                    "by_name_duration": defaultdict(int),
                },
            )
            actor["counts"][status] += 1
            actor["counts"]["calls"] += 1
            actor["duration"] += span["duration_ms"]
            actor["by_name"][name][status] += 1
            actor["by_name"][name]["calls"] += 1
            actor["by_name_duration"][name] += span["duration_ms"]

        by_name = [_tool_bucket(name, buckets[name], durations[name]) for name in sorted(buckets)]
        by_actor = []
        for key in sorted(actor_buckets):
            record = actor_buckets[key]
            by_actor.append(
                {
                    "actor_kind": record["actor_kind"],
                    "actor_id": record["actor_id"],
                    "calls": record["counts"]["calls"],
                    "total_duration_ms": record["duration"],
                    **{s: record["counts"].get(s, 0) for s in _TOOL_STATUSES},
                    "by_name": [
                        _tool_bucket(n, record["by_name"][n], record["by_name_duration"][n])
                        for n in sorted(record["by_name"])
                    ],
                }
            )
        return {
            "total_calls": totals["calls"],
            "total_duration_ms": total_duration,
            **{s: totals.get(s, 0) for s in _TOOL_STATUSES},
            "technical_retries": retries,
            "by_name": by_name,
            "by_actor": by_actor,
        }

    def flow(self) -> tuple[dict[str, Any], list[dict[str, str]]]:
        from aether_agents.observation.reduce.flow import classify_flow

        return classify_flow(self)

    def invariants(self) -> list[dict[str, Any]]:
        return [
            {
                "key": key,
                "state": self.invariant_states[key]["state"],
                "last_event_id": self.invariant_states[key]["last_event_id"],
            }
            for key in sorted(self.invariant_states)
        ]

    def coverage(self, derived: list[dict[str, str]]) -> dict[str, Any]:
        gaps = list(self.source_gaps)
        # A pre-tool span with no terminal is one abandoned span, not a call plus a gap.
        for call_id, span in sorted(self.open_tool_spans.items()):
            gaps.append(
                {
                    "class": "unpaired_span",
                    "reason_code": "TOOL_SPAN_UNPAIRED",
                    "event_id": str(span["event"].get("event_id")),
                }
            )
        for span in self.tool_spans:
            if not span["paired"]:
                gaps.append(
                    {
                        "class": "unpaired_span",
                        "reason_code": "TOOL_TERMINAL_WITHOUT_START",
                        "event_id": span["event_id"],
                    }
                )
        for _, event in sorted(self.open_model_requests.items()):
            gaps.append(
                {
                    "class": "unpaired_span",
                    "reason_code": "MODEL_SPAN_UNPAIRED",
                    "event_id": str(event.get("event_id")),
                }
            )
        for _, event in sorted(self.open_run_spans.items()):
            gaps.append(
                {
                    "class": "unpaired_span",
                    "reason_code": "RUN_SPAN_UNPAIRED",
                    "event_id": str(event.get("event_id")),
                }
            )
        for wait_id, (_, _started) in sorted(self._open_waits.items()):
            event = next(
                (
                    item
                    for item in self.events
                    if item.get("event_type") == "wait.started"
                    and (item.get("wait") or {}).get("wait_id") == wait_id
                ),
                None,
            )
            if event is not None:
                gaps.append(
                    {
                        "class": "unpaired_span",
                        "reason_code": "WAIT_SPAN_UNPAIRED",
                        "event_id": str(event.get("event_id")),
                    }
                )
        for task_ref in sorted(self._open_reviews):
            event = next(
                (
                    item
                    for item in self.events
                    if item.get("event_type") == "review.requested"
                    and (item.get("work_unit") or {}).get("task_ref") == task_ref
                ),
                None,
            )
            if event is not None:
                gaps.append(
                    {
                        "class": "unpaired_span",
                        "reason_code": "REVIEW_SPAN_UNPAIRED",
                        "event_id": str(event.get("event_id")),
                    }
                )
        if self._open_handoff is not None:
            gaps.append(
                {
                    "class": "unpaired_span",
                    "reason_code": "HANDOFF_SPAN_UNPAIRED",
                    "event_id": str(self._open_handoff.get("event_id")),
                }
            )
        for event in self.events:
            event_type = str(event.get("event_type") or "")
            if not event_type.startswith(("tool.", "model.")):
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
        if self.clock_anomalies:
            gaps.append(
                {
                    "class": CoverageClass.CLOCK_ANOMALY,
                    "reason_code": "NEGATIVE_OR_REVERSED_INTERVAL",
                    "event_id": "evt_"
                    + canonical_digest(
                        {"clock_anomaly": [event.get("event_id") for event in self.events]}
                    ),
                }
            )
        if self._post_verification_delta:
            gaps.append(
                {
                    "class": CoverageClass.RECONCILIATION_AMBIGUOUS,
                    "reason_code": "VERIFICATION_PRECEDED_LIFECYCLE_DELTA",
                    "event_id": "evt_"
                    + canonical_digest(
                        {
                            "verification_order": self._verification_order,
                            "event_count": len(self.events),
                        }
                    ),
                }
            )
        if self._verification_freshness_unknown:
            gaps.append(
                {
                    "class": CoverageClass.RECONCILIATION_AMBIGUOUS,
                    "reason_code": "VERIFICATION_FRESHNESS_UNPROVEN",
                    "event_id": "evt_"
                    + canonical_digest(
                        {
                            "verification_ids": sorted(
                                str(event.get("event_id")) for event in self._verification_events
                            ),
                            "delta_ids": sorted(self._semantic_delta_events),
                        }
                    ),
                }
            )
        fingerprint_key_ids = sorted(
            {
                configuration.get("fingerprint_key_id")
                for configuration in self.configurations
                if configuration.get("fingerprint_key_id")
            }
        )
        if len(fingerprint_key_ids) > 1:
            # The key bytes and the reason for an out-of-process rotation are not
            # reducer inputs. Multiple observed epochs are nevertheless an exact
            # comparison boundary and must never look like a configuration delta.
            gaps.append(
                {
                    "class": CoverageClass.OTHER,
                    "reason_code": "FINGERPRINT_KEY_EPOCH_BOUNDARY",
                    "event_id": "evt_"
                    + canonical_digest({"fingerprint_key_epochs": fingerprint_key_ids}),
                }
            )
        gaps.extend(derived)
        seen: set[tuple[str, str, str]] = set()
        unique = []
        for gap in gaps:
            key = (gap["class"], gap["reason_code"], gap["event_id"])
            if key in seen:
                continue
            seen.add(key)
            unique.append(gap)
        unique.sort(key=lambda g: (g["class"], g["reason_code"], g["event_id"]))
        return {"complete": not unique, "gap_count": len(unique), "gaps": unique}

    def provenance(self, producer_count: int) -> dict[str, Any]:
        pairs = [
            {
                "collector_version": collector,
                "runtime_fingerprint": fingerprint,
                "normalizer_ref": normalizer,
            }
            for collector, fingerprint, normalizer in sorted(
                self.compat_pairs, key=lambda p: (p[0], p[1], p[2] or "")
            )
            if collector and fingerprint
        ]
        return {
            "producer_count": max(1, producer_count),
            "compatibility_pairs": pairs,
        }

    def configuration_fingerprints(self) -> list[dict[str, Any]]:
        seen: dict[str, dict[str, Any]] = {}
        for configuration in self.configurations:
            seen[str(configuration.get("fingerprint_id"))] = {
                "fingerprint_id": configuration.get("fingerprint_id"),
                "scope": configuration.get("scope"),
                "participant_ref": configuration.get("participant_ref"),
                "model": configuration.get("model"),
                "provider": configuration.get("provider"),
                "system_prompt_fingerprint": configuration.get("system_prompt_fingerprint"),
                "observed_skill_set_fingerprint": configuration.get(
                    "observed_skill_set_fingerprint"
                ),
                "declared_toolset_fingerprint": configuration.get("declared_toolset_fingerprint"),
                "effective_tool_surface_fingerprint": configuration.get(
                    "effective_tool_surface_fingerprint"
                ),
                "global_concurrency_limit": configuration.get("global_concurrency_limit"),
                "per_profile_concurrency_limit": configuration.get("per_profile_concurrency_limit"),
                "observer_version": configuration.get("observer_version"),
                "fingerprint_key_id": configuration.get("fingerprint_key_id"),
                "runtime_fingerprint": configuration.get("runtime_fingerprint"),
                "field_coverage": dict(configuration.get("field_coverage") or {}),
            }
        return [seen[key] for key in sorted(seen)]

    def capability_evidence(self) -> dict[str, Any]:
        """`never_used` is claimed only from a demonstrably complete snapshot."""
        missing_hooks = sorted(
            {
                gap["reason_code"][len("HOOK_MISSING_") :].lower()
                for gap in self.source_gaps
                if gap.get("reason_code", "").startswith("HOOK_MISSING_")
            }
        )
        used = sorted({span["name"] for span in self.tool_spans})
        failed = sorted({span["name"] for span in self.tool_spans if span["status"] == "failed"})
        denied = sorted(
            {
                span["name"]
                for span in self.tool_spans
                if span["status"] == "blocked" or span["approval_outcome"] == "denied"
            }
        )
        latest = self.tool_surfaces[-1] if self.tool_surfaces else {}
        if latest.get("completeness") == "exact":
            coverage = "exact"
            granted = sorted(set(latest.get("granted_tool_refs") or []))
            never_used = sorted(set(latest.get("never_used_tool_refs") or []))
        else:
            coverage = latest.get("completeness", "unavailable") if latest else "unavailable"
            granted = sorted(set(latest.get("granted_tool_refs") or []))
            # No negative claim may be derived from a partial surface.
            never_used = []
        return {
            "surface_coverage": coverage,
            "declared_toolset_fingerprint": latest.get("declared_toolset_fingerprint"),
            "effective_surface_fingerprint": latest.get("effective_direct_surface_fingerprint"),
            "observed_tool_count": latest.get("observed_tool_count"),
            "granted_tool_refs": granted,
            "used_tool_refs": [t for t in used if _REF_OK(t)],
            "never_used_tool_refs": never_used,
            "failed_tool_refs": [t for t in failed if _REF_OK(t)],
            "denied_tool_refs": [t for t in denied if _REF_OK(t)],
            "loaded_skill_refs": sorted(t for t in self.loaded_skills if _REF_OK(t)),
            "missing_hook_refs": missing_hooks,
            "schema_serialized_bytes": latest.get("schema_serialized_bytes"),
            "schema_estimated_tokens": latest.get("schema_estimated_tokens"),
            "estimator_ref": latest.get("estimator_ref"),
            "fingerprint_key_id": latest.get("fingerprint_key_id")
            or (
                self.configurations[-1].get("fingerprint_key_id")
                if self.configurations
                else "fpk_" + "0" * 32
            ),
        }

    def model_context_economics(self, flow: dict[str, Any]) -> dict[str, Any]:
        buckets = {
            "input_tokens": None,
            "output_tokens": None,
            "cache_read_tokens": None,
            "cache_write_tokens": None,
            "reasoning_tokens": None,
            "total_tokens": None,
        }
        coverages = set()
        finish_reasons = Counter()
        duration = 0
        compression = overflow = 0
        request_attempts: dict[tuple[str, str], int] = {}
        request_final_state: dict[tuple[str, str], tuple[int, str]] = {}
        for request in self.model_requests:
            coverages.add(request.get("usage_coverage", "unavailable"))
            for name in buckets:
                value = request.get(name)
                if isinstance(value, int):
                    buckets[name] = (buckets[name] or 0) + value
            if isinstance(request.get("duration_ms"), int):
                duration += request["duration_ms"]
            state = str(request.get("state") or "unknown")
            request_ref = request.get("request_ref")
            if state in ("completed", "failed") and isinstance(request_ref, str):
                ordinal = request.get("attempt_count")
                ordinal = ordinal if isinstance(ordinal, int) and ordinal > 0 else 1
                request_key = (str(request.get("_session_id") or ""), request_ref)
                request_attempts[request_key] = max(ordinal, request_attempts.get(request_key, 0))
                previous = request_final_state.get(request_key)
                if previous is None or ordinal >= previous[0]:
                    request_final_state[request_key] = (ordinal, state)
            if state == "context_compressed":
                compression += 1
            elif state == "context_overflow":
                overflow += 1
            reason = request.get("finish_reason")
            if isinstance(reason, str):
                finish_reasons[reason] += 1

        if not self.model_requests:
            token_coverage = "not_applicable"
        elif coverages == {"exact"}:
            token_coverage = "exact"
        elif "exact" in coverages or "partial" in coverages:
            token_coverage = "partial"
        else:
            token_coverage = "unavailable"

        # The locked runtime exposes no dedicated context lifecycle observer, so these
        # remain unavailable rather than inferred from error text (research 7.2.2).
        context_coverage = "exact" if (compression or overflow) else "unavailable"
        return {
            "request_count": len(request_attempts),
            "failed_request_count": sum(
                state == "failed" for _, state in request_final_state.values()
            ),
            "attempt_count": sum(request_attempts.values()),
            "duration_ms": duration,
            "turns": len(self.turns),
            "turns_without_semantic_delta": max(0, len(self.turns) - len(self.turns_with_delta)),
            "tokens": buckets,
            "token_coverage": token_coverage,
            "finish_reasons": dict(sorted(finish_reasons.items())),
            "context_compression_count": compression if context_coverage == "exact" else None,
            "context_overflow_count": overflow if context_coverage == "exact" else None,
            "context_signal_coverage": context_coverage,
            "protocol_violation_count": self.protocol_violations,
            "invalid_argument_count": None,
            "invalid_argument_coverage": "unavailable",
        }

    def bottlenecks(self) -> list[dict[str, Any]]:
        from aether_agents.observation.reduce.attribution import build_bottlenecks

        return build_bottlenecks(self)

    def defects(self) -> list[dict[str, Any]]:
        from aether_agents.observation.reduce.attribution import build_defects

        return build_defects(self)


_TOOL_STATUSES = (
    "completed",
    "failed",
    "blocked",
    "cancelled",
    "timed_out",
    "interrupted",
    "unknown",
)


def _REF_OK(value: str) -> bool:
    import re

    return bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", value))


def _tool_bucket(name: str, counts: Counter, duration_ms: int) -> dict[str, Any]:
    return {
        "name": name,
        "calls": counts.get("calls", 0),
        **{status: counts.get(status, 0) for status in _TOOL_STATUSES},
        "duration_ms": duration_ms,
    }


def _unit_runtime_state(record: dict[str, Any], as_of: datetime | None) -> dict[str, Any]:
    status = record["task_status"]
    outcome = record["latest_run_outcome"]
    heartbeat = record.get("last_heartbeat_at")
    running = status == "running" or record.get("latest_run_status") == "running"
    if running and isinstance(heartbeat, datetime) and as_of is not None:
        age_ms = _ms(heartbeat, as_of)
        liveness = (
            "alive"
            if age_ms is not None and age_ms <= HEARTBEAT_STALE_AFTER_MS
            else "stale"
            if age_ms is not None
            else "unknown"
        )
    elif running:
        liveness = "unknown"
    elif outcome in ANOMALOUS_RUN_OUTCOMES:
        liveness = "dead"
    else:
        liveness = "unknown"
    return {
        "liveness": liveness,
        "activity": {
            "running": "working",
            "review": "reviewing",
            "blocked": "waiting",
            "done": "idle",
        }.get(status, "unknown"),
        "progress": "complete" if status == "done" else "unknown",
        "waiting": {"blocked": "dependency", "review": "review"}.get(status, "none"),
        "anomalies": "present" if outcome in ANOMALOUS_RUN_OUTCOMES else "clear",
        "termination": "completed" if status == "done" else "open",
    }


_HANDLERS: dict[str, Any] = {
    "trace.opened": _TraceState._on_trace,
    "trace.resumed": _TraceState._on_trace,
    "trace.closed": _TraceState._on_trace,
    "trace.cancelled": _TraceState._on_trace,
    "trace.abandoned": _TraceState._on_trace,
    "trace.failed": _TraceState._on_trace,
    "clarification.requested": _TraceState._on_clarification,
    "clarification.resolved": _TraceState._on_clarification,
    "contract.revision": _TraceState._on_contract,
    "contract.executable": _TraceState._on_contract,
    "contract.persisted": _TraceState._on_contract,
    "contract.execution_started": _TraceState._on_contract,
    "contract.completion_candidate": _TraceState._on_contract,
    "contract.completion_verified": _TraceState._on_contract,
    "decision.recorded": _TraceState._on_contract,
    "decision.superseded": _TraceState._on_contract,
    "decision.rejected": _TraceState._on_contract,
    "evidence.added": _TraceState._on_contract,
    "evidence.rejected": _TraceState._on_contract,
    "invariant.passed": _TraceState._on_invariant,
    "invariant.failed": _TraceState._on_invariant,
    "acceptance.declared": _TraceState._on_acceptance,
    "acceptance.evaluated": _TraceState._on_acceptance,
    "wait.started": _TraceState._on_wait,
    "wait.ended": _TraceState._on_wait,
    "coverage.gap": _TraceState._on_coverage,
    "coverage.restored": _TraceState._on_coverage,
    "configuration.observed": _TraceState._on_configuration,
    "tool_surface.observed": _TraceState._on_tool_surface,
    "skill.loaded": _TraceState._on_skill,
    "dispatch.observed": _TraceState._on_dispatch,
    "bottleneck.attributed": _TraceState._on_attribution,
    "defect.attributed": _TraceState._on_attribution,
    "participant.joined": _TraceState._on_participant,
    "participant.left": _TraceState._on_participant,
}
