"""Causal process reconstruction: semantic steps, parallel waves, execution rounds.

Normative sources: OBS-D-015, OBS-FR-051..057, research section 7.2.5.

Aggregate totals cannot answer the question the owner actually asks — *how* was this
contract developed, what ran at the same time, and could a different sequence have
delivered sooner. So three separate units are modelled and never collapsed:

* a **step** is an instance of a typed semantic or native transition (not a task ID, and
  not a tool call — tool calls are evidence nested under a step);
* a **wave** is a set of work steps sharing an explicit durable parent inside one
  evidenced round; timestamps measure overlap only after that membership is known;
* a **round** starts at an initial dispatch or an evidenced review/retry/resume/redispatch/
  protocol-correction/direction-change trigger and ends at its next barrier.

Order comes from explicit parent/dependency edges, task/run/review transitions, typed
handoff/checkpoint references, and matching native identifiers. Cross-process wall-clock
proximity never assigns a step, wave, or round order; UTC time is only a final,
deterministic presentation tie-breaker inside an already causal partial order.

The critical path is descriptive evidence about where wall time accumulated. It is never
a counterfactual claim that adding agents would have helped.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable

from aether_agents.observation.contracts import (
    ANOMALOUS_RUN_OUTCOMES,
    WORK_UNIT_RELATIONS,
)

__all__ = [
    "Step",
    "build_process",
    "causal_order",
    "parse_timestamp",
]


def parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _ms_between(start: datetime | None, end: datetime | None) -> int | None:
    if start is None or end is None:
        return None
    delta = int((end - start).total_seconds() * 1000)
    # A negative interval is a clock/causality anomaly. It is surfaced, never repaired.
    return delta if delta >= 0 else None


def _sort_key(event: dict[str, Any]) -> tuple:
    """Deterministic tie-breaker used only *within* an already causal partial order."""
    return (
        event.get("producer_epoch") or "",
        event.get("producer_seq") if isinstance(event.get("producer_seq"), int) else 0,
        event.get("event_id") or "",
        # UTC is presentation metadata only. Stable producer/event identity wins for
        # causally independent producers, so changing clock skew cannot change meaning.
        event.get("occurred_at") or "",
    )


def causal_order(events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Stable topological order over explicit causal edges.

    Edges are (a) ``parent_event_id`` references and (b) producer-local sequence inside one
    epoch, which is authoritative for that process. Everything else is a tie-break, so two
    reductions of the same event set always produce the same order.
    """
    items = list(events)
    by_id = {e.get("event_id"): e for e in items if e.get("event_id")}
    indegree: dict[str, int] = {}
    successors: dict[str, list[str]] = {}

    def _add_edge(before: str, after: str) -> None:
        successors.setdefault(before, []).append(after)
        indegree[after] = indegree.get(after, 0) + 1

    for event in items:
        indegree.setdefault(event.get("event_id") or "", 0)

    for event in items:
        event_id = event.get("event_id") or ""
        parent = event.get("parent_event_id")
        if isinstance(parent, str) and parent in by_id and parent != event_id:
            _add_edge(parent, event_id)

    # Producer-local sequence is authoritative inside one epoch.
    per_epoch: dict[str, list[dict[str, Any]]] = {}
    for event in items:
        epoch = event.get("producer_epoch")
        if isinstance(epoch, str):
            per_epoch.setdefault(epoch, []).append(event)
    for epoch_events in per_epoch.values():
        by_sequence: dict[int, list[dict[str, Any]]] = {}
        for event in epoch_events:
            sequence = event.get("producer_seq")
            if isinstance(sequence, int):
                by_sequence.setdefault(sequence, []).append(event)
        ordered_sequences = sorted(by_sequence)
        for previous_sequence, following_sequence in zip(ordered_sequences, ordered_sequences[1:]):
            previous = by_sequence[previous_sequence]
            following = by_sequence[following_sequence]
            # A duplicated sequence is contradictory producer evidence. It cannot be
            # resolved into a predecessor by list order or event ID.
            if len(previous) != 1 or len(following) != 1:
                continue
            before = previous[0].get("event_id") or ""
            after = following[0].get("event_id") or ""
            if before and after and before != after:
                _add_edge(before, after)

    ready = sorted(
        (e for e in items if indegree.get(e.get("event_id") or "", 0) == 0), key=_sort_key
    )
    ordered: list[dict[str, Any]] = []
    seen: set[str] = set()
    while ready:
        event = ready.pop(0)
        event_id = event.get("event_id") or ""
        if event_id in seen:
            continue
        seen.add(event_id)
        ordered.append(event)
        changed = False
        for successor_id in successors.get(event_id, ()):
            indegree[successor_id] -= 1
            if indegree[successor_id] == 0 and successor_id in by_id:
                ready.append(by_id[successor_id])
                changed = True
        if changed:
            ready.sort(key=_sort_key)

    # A cycle would mean contradictory causal claims; keep the events, ordered by tie-break.
    if len(ordered) < len(items):
        remaining = sorted(
            (e for e in items if (e.get("event_id") or "") not in seen), key=_sort_key
        )
        ordered.extend(remaining)
    return ordered


@dataclass
class Step:
    """One causally bounded, human-auditable transition."""

    index: int
    kind: str
    participant_ref: str | None
    order_hint: int = 0
    task_refs: list[str] = field(default_factory=list)
    run_refs: list[str] = field(default_factory=list)
    predecessors: list[str] = field(default_factory=list)
    round_id: str | None = None
    wave_id: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    outcome: str = "unknown"
    semantic_delta: bool | None = None
    evidence: list[str] = field(default_factory=list)
    coverage: str = "exact"

    @property
    def step_id(self) -> str:
        return f"stp-{self.index:04d}"

    def to_json(self) -> dict[str, Any]:
        duration = _ms_between(self.started_at, self.ended_at)
        coverage = self.coverage
        if self.started_at is None or self.ended_at is None:
            coverage = "partial"
        return {
            "step_id": self.step_id,
            "index": self.index,
            "kind": self.kind,
            "participant_ref": self.participant_ref,
            "task_refs": sorted(set(self.task_refs)),
            "run_refs": sorted(set(self.run_refs)),
            "predecessor_step_ids": sorted(set(self.predecessors)),
            "round_id": self.round_id,
            "wave_id": self.wave_id,
            "started_at": _iso(self.started_at),
            "ended_at": _iso(self.ended_at),
            "duration_ms": duration,
            "outcome": self.outcome,
            "semantic_delta": self.semantic_delta,
            "evidence_event_ids": sorted(set(self.evidence)),
            "coverage": coverage,
        }


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.strftime("%Y-%m-%dT%H:%M:%S.") + f"{value.microsecond // 1000:03d}Z"


#: Contract-phase event types that each become one semantic step.
_CONTRACT_STEP_KINDS = {
    "contract.revision": "contract_revision",
    "contract.executable": "contract_executable",
    "contract.persisted": "contract_persistence",
    "contract.execution_started": "execution_start",
    "contract.completion_candidate": "completion_candidate",
    "contract.completion_verified": "terminal_verification",
    "decision.recorded": "decision",
    "decision.superseded": "decision_supersession",
    "decision.rejected": "decision_rejection",
    "evidence.added": "evidence",
    "evidence.rejected": "evidence_rejection",
    "invariant.passed": "invariant_check",
    "invariant.failed": "invariant_check",
    "clarification.requested": "owner_clarification",
    "clarification.resolved": "owner_clarification_resolved",
    "trace.closed": "closure",
    "trace.cancelled": "closure",
    "trace.abandoned": "closure",
    "trace.failed": "closure",
}

_RELATION_TO_STEP_KIND = {
    "root": "implementation",
    "decomposition": "decomposition",
    "implementation": "implementation",
    "review": "review",
    "qa": "qa",
    "integration": "integration",
    "release": "release",
    "follow_up": "follow_up",
    "other": "other",
    "unknown": "unknown",
}


def build_process(
    events: list[dict[str, Any]],
    *,
    verified_review_event_ids: frozenset[str] | None = None,
    verified_completion_event_ids: frozenset[str] | None = None,
) -> dict[str, Any]:
    """Reconstruct steps, waves, rounds, and the critical path from ordered events."""
    ordered = [event for event in causal_order(events) if _work_envelope_consistent(event)]
    steps: list[Step] = []
    relations: dict[str, str] = {}

    for event in ordered:
        unit = event.get("work_unit") or {}
        task_ref = unit.get("task_ref")
        if isinstance(task_ref, str):
            relation = unit.get("relation")
            relations.setdefault(
                task_ref,
                relation if relation in WORK_UNIT_RELATIONS else "unknown",
            )
    parents = _durable_task_parents(ordered)

    steps.extend(
        _contract_steps(
            ordered,
            len(steps),
            verified_completion_event_ids=verified_completion_event_ids,
        )
    )
    steps.extend(_handoff_steps(ordered, len(steps)))
    steps.extend(_run_steps(ordered, relations, len(steps)))
    steps.extend(
        _review_steps(
            ordered,
            len(steps),
            verified_review_event_ids=verified_review_event_ids,
        )
    )
    steps.extend(_wait_steps(ordered, len(steps)))

    # Re-index in causal presentation order so `index` is stable and monotonic.
    steps.sort(key=lambda s: (s.order_hint, s.kind, sorted(s.task_refs), s.index))
    for position, step in enumerate(steps):
        step.index = position

    _link_predecessors(steps, ordered, parents)
    rounds = _build_rounds(ordered, steps, parents)
    waves = _build_waves(steps, rounds, parents)
    critical = _critical_path(steps)

    return {
        "steps": [step.to_json() for step in steps],
        "waves": waves,
        "rounds": rounds,
        "critical_path": critical,
    }


def _work_envelope_consistent(event: dict[str, Any]) -> bool:
    unit = event.get("work_unit")
    if not isinstance(unit, dict):
        return True
    envelope_task = event.get("task_id")
    unit_task = unit.get("task_ref")
    return not (
        isinstance(envelope_task, str) and isinstance(unit_task, str) and envelope_task != unit_task
    )


def _durable_task_parents(events: list[dict[str, Any]]) -> dict[str, tuple[str, ...]]:
    """Keep only unambiguous explicit parent-task claims.

    An empty parent list does not contradict a later durable binding, but two distinct
    non-empty lists do. Their order is not semantic, so claims are normalized before
    cardinality is checked.
    """
    claims: dict[str, set[tuple[str, ...]]] = {}
    for event in events:
        unit = event.get("work_unit") or {}
        task_ref = unit.get("task_ref")
        parent_refs = unit.get("parent_task_refs")
        if not isinstance(task_ref, str) or not isinstance(parent_refs, list) or not parent_refs:
            continue
        if not all(isinstance(parent, str) for parent in parent_refs):
            continue
        claims.setdefault(task_ref, set()).add(tuple(sorted(set(parent_refs))))
    return {
        task_ref: next(iter(parent_claims))
        for task_ref, parent_claims in claims.items()
        if len(parent_claims) == 1
    }


def _actor_ref(event: dict[str, Any]) -> str | None:
    actor = event.get("actor") or {}
    identifier = actor.get("id")
    return identifier if isinstance(identifier, str) else None


def _contract_steps(
    events: list[dict[str, Any]],
    base: int,
    *,
    verified_completion_event_ids: frozenset[str] | None,
) -> list[Step]:
    produced: list[Step] = []
    for event_index, event in enumerate(events):
        kind = _CONTRACT_STEP_KINDS.get(event.get("event_type") or "")
        if kind is None:
            continue
        moment = parse_timestamp(event.get("occurred_at"))
        contract = event.get("contract") or {}
        delta = contract.get("semantic_delta")
        step = Step(
            index=event_index,
            kind=kind,
            participant_ref=_actor_ref(event),
            order_hint=event_index,
            started_at=moment,
            ended_at=moment,
            outcome=str(event.get("status") or "unknown"),
            # A contract step's delta is stated by the contract block itself, so it is
            # observed rather than inferred.
            semantic_delta=(delta not in (None, "none")) if delta is not None else None,
            evidence=[event.get("event_id") or ""],
        )
        if (
            event.get("event_type") == "contract.completion_verified"
            and verified_completion_event_ids is not None
            and event.get("event_id") not in verified_completion_event_ids
        ):
            step.outcome = "unverified"
            step.semantic_delta = None
            step.coverage = "partial"
        produced.append(step)
    return produced


def _handoff_steps(events: list[dict[str, Any]], base: int) -> list[Step]:
    produced: list[Step] = []
    open_handoff: Step | None = None
    for event_index, event in enumerate(events):
        event_type = event.get("event_type") or ""
        if event_type == "handoff.started":
            open_handoff = Step(
                index=event_index,
                kind="handoff",
                participant_ref=_actor_ref(event),
                order_hint=event_index,
                started_at=parse_timestamp(event.get("occurred_at")),
                outcome="started",
                evidence=[event.get("event_id") or ""],
            )
            produced.append(open_handoff)
        elif event_type.startswith("handoff.") and open_handoff is not None:
            open_handoff.ended_at = parse_timestamp(event.get("occurred_at"))
            open_handoff.outcome = event_type.split(".", 1)[1]
            open_handoff.semantic_delta = event_type == "handoff.completed"
            open_handoff.evidence.append(event.get("event_id") or "")
            open_handoff = None
    return produced


def _run_steps(events: list[dict[str, Any]], relations: dict[str, str], base: int) -> list[Step]:
    """One step per run attempt. A retry is a NEW step linked to the prior attempt."""
    produced: list[Step] = []
    open_runs: dict[tuple[str, Any], Step] = {}
    for event_index, event in enumerate(events):
        event_type = event.get("event_type") or ""
        if event_type not in ("run.started", "run.finished"):
            continue
        unit = event.get("work_unit") or {}
        task_ref = unit.get("task_ref")
        run_id = event.get("run_id")
        if not isinstance(task_ref, str):
            continue
        key = (task_ref, run_id)
        moment = parse_timestamp(event.get("occurred_at"))
        if event_type == "run.started":
            step = Step(
                index=event_index,
                kind=_RELATION_TO_STEP_KIND.get(relations.get(task_ref, "unknown"), "unknown"),
                participant_ref=_actor_ref(event),
                order_hint=event_index,
                task_refs=[task_ref],
                run_refs=[str(run_id)] if run_id is not None else [],
                started_at=moment,
                outcome="running",
                evidence=[event.get("event_id") or ""],
            )
            produced.append(step)
            open_runs[key] = step
        else:
            step = open_runs.pop(key, None)
            if step is None:
                # A terminal without its start: the span is unpaired, not invented.
                step = Step(
                    index=event_index,
                    kind=_RELATION_TO_STEP_KIND.get(relations.get(task_ref, "unknown"), "unknown"),
                    participant_ref=_actor_ref(event),
                    order_hint=event_index,
                    task_refs=[task_ref],
                    run_refs=[str(run_id)] if run_id is not None else [],
                    coverage="partial",
                    evidence=[event.get("event_id") or ""],
                )
                produced.append(step)
            step.ended_at = moment
            outcome = unit.get("run_outcome") or event.get("status") or "unknown"
            step.outcome = str(outcome)
            step.semantic_delta = (
                True
                if outcome == "completed"
                else (False if outcome in ANOMALOUS_RUN_OUTCOMES else None)
            )
            step.evidence.append(event.get("event_id") or "")
    return produced


def _review_steps(
    events: list[dict[str, Any]],
    base: int,
    *,
    verified_review_event_ids: frozenset[str] | None,
) -> list[Step]:
    produced: list[Step] = []
    open_reviews: dict[str, Step] = {}
    for event_index, event in enumerate(events):
        event_type = event.get("event_type") or ""
        if not event_type.startswith("review."):
            continue
        unit = event.get("work_unit") or {}
        task_ref = unit.get("task_ref")
        if not isinstance(task_ref, str):
            continue
        event_verified = verified_review_event_ids is None or (
            event.get("event_id") in verified_review_event_ids
        )
        moment = parse_timestamp(event.get("occurred_at"))
        if event_type == "review.requested":
            step = Step(
                index=event_index,
                kind="review",
                participant_ref=_actor_ref(event),
                order_hint=event_index,
                task_refs=[task_ref],
                started_at=moment,
                outcome="requested",
                evidence=[event.get("event_id") or ""],
            )
            produced.append(step)
            if not event_verified:
                step.outcome = "unverified"
                step.semantic_delta = None
                step.coverage = "partial"
            open_reviews[task_ref] = step
            continue
        step = open_reviews.pop(task_ref, None)
        if step is None:
            step = Step(
                index=event_index,
                kind="review",
                participant_ref=_actor_ref(event),
                order_hint=event_index,
                task_refs=[task_ref],
                started_at=moment,
                coverage="partial",
                evidence=[event.get("event_id") or ""],
            )
            produced.append(step)
        step.ended_at = moment
        if event_verified and step.coverage == "exact":
            step.outcome = "approved" if event_type == "review.approved" else "changes_requested"
            step.semantic_delta = True
        else:
            step.outcome = "unverified"
            step.semantic_delta = None
            step.coverage = "partial"
        step.evidence.append(event.get("event_id") or "")
    return produced


def _wait_steps(events: list[dict[str, Any]], base: int) -> list[Step]:
    """Evidenced waits are nodes on the path, not gaps between nodes."""
    produced: list[Step] = []
    open_waits: dict[str, Step] = {}
    for event_index, event in enumerate(events):
        event_type = event.get("event_type") or ""
        wait = event.get("wait") or {}
        wait_id = wait.get("wait_id")
        if not isinstance(wait_id, str):
            continue
        moment = parse_timestamp(event.get("occurred_at"))
        if event_type == "wait.started":
            step = Step(
                index=event_index,
                kind=f"wait_{wait.get('kind') or 'unknown'}",
                participant_ref=_actor_ref(event),
                order_hint=event_index,
                started_at=moment,
                outcome="waiting",
                semantic_delta=False,
                evidence=[event.get("event_id") or ""],
            )
            produced.append(step)
            open_waits[wait_id] = step
        elif event_type == "wait.ended":
            step = open_waits.pop(wait_id, None)
            if step is not None:
                step.ended_at = moment
                step.outcome = "ended"
                step.evidence.append(event.get("event_id") or "")
    return produced


def _link_predecessors(
    steps: list[Step],
    events: list[dict[str, Any]],
    parents: dict[str, tuple[str, ...]],
) -> None:
    """Link steps only through explicit event or unambiguous durable task edges."""
    step_by_event = {event_id: step for step in steps for event_id in step.evidence if event_id}
    event_by_id = {event.get("event_id"): event for event in events if event.get("event_id")}

    for step in steps:
        for evidence_id in step.evidence:
            parent_id = (event_by_id.get(evidence_id) or {}).get("parent_event_id")
            parent_step = step_by_event.get(parent_id)
            if parent_step is not None and parent_step is not step:
                step.predecessors.append(parent_step.step_id)

    steps_by_task: dict[str, list[Step]] = {}
    for candidate in steps:
        for task_ref in candidate.task_refs:
            steps_by_task.setdefault(task_ref, []).append(candidate)

    for step in steps:
        parent_refs = {
            parent_ref for task_ref in step.task_refs for parent_ref in parents.get(task_ref, ())
        }
        for parent_ref in sorted(parent_refs):
            candidates = [
                candidate
                for candidate in steps_by_task.get(parent_ref, ())
                if candidate is not step
            ]
            # A task edge establishes which work unit is upstream, but not which attempt.
            # Zero or multiple candidate steps remain unknown instead of being resolved by
            # timestamp, producer order, event ID, or list adjacency.
            if len(candidates) == 1:
                step.predecessors.append(candidates[0].step_id)


_TRIGGER_EVENTS = {
    "review.changes_requested": "review_rework",
    "trace.resumed": "resumption",
}


@dataclass(frozen=True)
class _RoundSeed:
    """A round boundary supported by explicit trigger event(s)."""

    key: str
    trigger: str
    event_ids: tuple[str, ...]
    moment: datetime | None

    @property
    def event_id(self) -> str:
        """Stable presentation anchor; every trigger ID remains round evidence."""
        return self.event_ids[0]


def _run_span_anchors(events: list[dict[str, Any]]) -> dict[str, str]:
    """Map native run-span events to their unique start without fuzzy pairing."""
    events_by_span: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for event in events:
        if event.get("event_type") not in ("run.started", "run.finished"):
            continue
        task_ref = (event.get("work_unit") or {}).get("task_ref")
        run_id = event.get("run_id")
        if isinstance(task_ref, str) and isinstance(run_id, int):
            events_by_span.setdefault((task_ref, run_id), []).append(event)

    anchors: dict[str, str] = {}
    for span_events in events_by_span.values():
        starts = [
            event.get("event_id")
            for event in span_events
            if event.get("event_type") == "run.started" and isinstance(event.get("event_id"), str)
        ]
        # More than one start makes the native span contradictory. Do not choose one by
        # producer order, wall clock, or event identity.
        if len(starts) != 1:
            continue
        start_id = starts[0]
        for event in span_events:
            event_id = event.get("event_id")
            if isinstance(event_id, str):
                anchors[event_id] = start_id
    return anchors


def _task_components(
    parents: dict[str, tuple[str, ...]],
) -> dict[str, frozenset[str]]:
    """Return connected components induced only by durable task-parent edges."""
    adjacency: dict[str, set[str]] = {}
    for task_ref, parent_refs in parents.items():
        adjacency.setdefault(task_ref, set())
        for parent in parent_refs:
            adjacency[task_ref].add(parent)
            adjacency.setdefault(parent, set()).add(task_ref)

    components: dict[str, frozenset[str]] = {}
    for task_ref in adjacency:
        if task_ref in components:
            continue
        pending = [task_ref]
        members: set[str] = set()
        while pending:
            candidate = pending.pop()
            if candidate in members:
                continue
            members.add(candidate)
            pending.extend(adjacency.get(candidate, ()))
        component = frozenset(members)
        for member in members:
            components[member] = component
    return components


def _non_initial_round_trigger(
    event: dict[str, Any], events_by_id: dict[str, dict[str, Any]]
) -> str | None:
    event_type = event.get("event_type") or ""
    if event_type == "run.started":
        parent = events_by_id.get(event.get("parent_event_id"))
        if parent is not None and parent.get("event_type") == "run.finished":
            outcome = (parent.get("work_unit") or {}).get("run_outcome")
            if outcome == "protocol_violation":
                return "protocol_correction"
            if outcome in ANOMALOUS_RUN_OUTCOMES:
                return "redispatch"
        return None
    if event_type in _TRIGGER_EVENTS:
        return _TRIGGER_EVENTS[event_type]
    if event_type == "decision.superseded":
        return "owner_direction_change"
    if event_type == "coverage.gap":
        reason = (event.get("coverage") or {}).get("reason_code") or ""
        if "PROTOCOL" in reason:
            return "protocol_correction"
    return None


def _build_rounds(
    events: list[dict[str, Any]],
    steps: list[Step],
    parents: dict[str, tuple[str, ...]],
) -> list[dict[str, Any]]:
    """Build round membership and predecessors from explicit edges/native spans only.

    The topological list is a presentation order. It is deliberately not used as a
    boundary: an independent trigger cannot partition unrelated work, and two adjacent
    rounds are not predecessors merely because a deterministic tie-break placed them next
    to one another.
    """
    events_by_id = {
        event.get("event_id"): event for event in events if isinstance(event.get("event_id"), str)
    }
    span_anchor = _run_span_anchors(events)

    seeds: dict[str, _RoundSeed] = {}
    trigger_seed: dict[str, str] = {}
    for event in events:
        event_id = event.get("event_id")
        if not isinstance(event_id, str):
            continue
        trigger = _non_initial_round_trigger(event, events_by_id)
        if trigger is None:
            continue
        seed = _RoundSeed(
            event_id,
            trigger,
            (event_id,),
            parse_timestamp(event.get("occurred_at")),
        )
        seeds[seed.key] = seed
        trigger_seed[event_id] = seed.key

    run_start_ids = {
        event.get("event_id")
        for event in events
        if event.get("event_type") == "run.started" and isinstance(event.get("event_id"), str)
    }

    def _has_evidenced_round_ancestor(event_id: str) -> bool:
        """A descendant dispatch stays in its ancestor round unless it is a retry seed."""
        seen: set[str] = set()
        parent_id = events_by_id.get(event_id, {}).get("parent_event_id")
        while isinstance(parent_id, str) and parent_id not in seen:
            seen.add(parent_id)
            if parent_id in trigger_seed:
                return True
            ancestor_start = span_anchor.get(parent_id)
            if ancestor_start in run_start_ids and ancestor_start != event_id:
                return True
            parent_id = events_by_id.get(parent_id, {}).get("parent_event_id")
        return False

    task_components = _task_components(parents)
    initial_groups: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    initial_candidates: list[tuple[dict[str, Any], frozenset[str]]] = []
    # Otherwise-unrelated native run starts are distinct initial dispatches. Explicit
    # sibling branches in one durable task component share their evidenced dispatch
    # round, which permits wave reconstruction without consulting time or producer order.
    for event in events:
        event_id = event.get("event_id")
        if (
            event.get("event_type") != "run.started"
            or not isinstance(event_id, str)
            or event_id in trigger_seed
            or _has_evidenced_round_ancestor(event_id)
        ):
            continue
        task_ref = (event.get("work_unit") or {}).get("task_ref")
        component = (
            task_components.get(task_ref, frozenset((task_ref,)))
            if isinstance(task_ref, str)
            else frozenset()
        )
        initial_candidates.append((event, component))

    starts_by_component: dict[tuple[str, ...], list[str]] = {}
    for event, component in initial_candidates:
        task_ref = (event.get("work_unit") or {}).get("task_ref")
        if isinstance(task_ref, str) and len(component) > 1:
            starts_by_component.setdefault(tuple(sorted(component)), []).append(task_ref)

    for event, component in initial_candidates:
        event_id = event["event_id"]
        component_key = tuple(sorted(component))
        component_starts = starts_by_component.get(component_key, [])
        # One durable parent component proves sibling eligibility only when it selects
        # one unambiguous attempt per task. If the same task has two unlinked starts,
        # the parent edge cannot say which attempt belongs to a shared dispatch; keep
        # every attempt in its own initial round instead of choosing by time/order.
        one_attempt_per_task = len(component_starts) == len(set(component_starts))
        group_key = (
            ("task-component", *component_key)
            if len(component) > 1 and one_attempt_per_task
            else ("run-event", event_id)
        )
        initial_groups.setdefault(group_key, []).append(event)

    for group in initial_groups.values():
        event_ids = tuple(sorted(event["event_id"] for event in group))
        moments = [
            moment
            for event in group
            if (moment := parse_timestamp(event.get("occurred_at"))) is not None
        ]
        seed = _RoundSeed(
            event_ids[0],
            "initial_dispatch",
            event_ids,
            min(moments) if moments else None,
        )
        seeds[seed.key] = seed
        for event_id in event_ids:
            trigger_seed[event_id] = seed.key

    if not seeds:
        return []

    task_seed_candidates: dict[str, set[str]] = {}
    for seed in seeds.values():
        if seed.trigger != "initial_dispatch":
            continue
        for event_id in seed.event_ids:
            unit = (events_by_id.get(event_id) or {}).get("work_unit") or {}
            task_ref = unit.get("task_ref")
            if not isinstance(task_ref, str):
                continue
            for member in task_components.get(task_ref, frozenset((task_ref,))):
                task_seed_candidates.setdefault(member, set()).add(seed.key)
    # A task transition can inherit a round only when its explicit task component selects
    # one initial seed. Multiple attempts/roots remain unassigned instead of tie-broken.
    task_seed = {
        task_ref: next(iter(candidates))
        for task_ref, candidates in task_seed_candidates.items()
        if len(candidates) == 1
    }

    owner_cache: dict[str, str | None] = {}

    def _event_owner(event_id: str, visiting: set[str] | None = None) -> str | None:
        if event_id in owner_cache:
            return owner_cache[event_id]
        if event_id in trigger_seed:
            owner_cache[event_id] = trigger_seed[event_id]
            return owner_cache[event_id]
        active = set() if visiting is None else visiting
        if event_id in active:
            return None
        active.add(event_id)
        event = events_by_id.get(event_id) or {}
        anchor = span_anchor.get(event_id)
        if isinstance(anchor, str) and anchor != event_id:
            owner = _event_owner(anchor, active)
            if owner is not None:
                owner_cache[event_id] = owner
                active.remove(event_id)
                return owner
        parent_id = event.get("parent_event_id")
        if isinstance(parent_id, str):
            owner = _event_owner(parent_id, active)
            if owner is not None:
                owner_cache[event_id] = owner
                active.remove(event_id)
                return owner
        task_ref = (event.get("work_unit") or {}).get("task_ref")
        owner = task_seed.get(task_ref) if isinstance(task_ref, str) else None
        owner_cache[event_id] = owner
        active.remove(event_id)
        return owner

    members_by_seed: dict[str, list[Step]] = {key: [] for key in seeds}
    step_by_event = {
        evidence_id: step for step in steps for evidence_id in step.evidence if evidence_id
    }
    for step in steps:
        anchor_id = next((event_id for event_id in step.evidence if event_id), None)
        owner = _event_owner(anchor_id) if isinstance(anchor_id, str) else None
        if owner in members_by_seed:
            members_by_seed[owner].append(step)

    predecessor_by_seed: dict[str, str | None] = {}
    for seed in seeds.values():
        candidates: set[str] = set()
        for trigger_event_id in seed.event_ids:
            event = events_by_id.get(trigger_event_id) or {}
            parent_id = event.get("parent_event_id")
            if isinstance(parent_id, str):
                owner = _event_owner(parent_id)
                if owner is not None and owner != seed.key:
                    candidates.add(owner)
        # A review terminal is both the prior span's barrier and the next round's
        # trigger. Matching that native review span is an explicit link; list adjacency
        # is not.
        for trigger_event_id in seed.event_ids:
            trigger_step = step_by_event.get(trigger_event_id)
            if trigger_step is not None:
                anchor_id = next((event_id for event_id in trigger_step.evidence if event_id), None)
                if isinstance(anchor_id, str) and anchor_id != trigger_event_id:
                    owner = _event_owner(anchor_id)
                    if owner is not None and owner != seed.key:
                        candidates.add(owner)
        predecessor_by_seed[seed.key] = next(iter(candidates)) if len(candidates) == 1 else None

    successors: dict[str, list[str]] = {}
    indegree = {key: 0 for key in seeds}
    for seed_key, predecessor in predecessor_by_seed.items():
        if predecessor in seeds and predecessor != seed_key:
            successors.setdefault(predecessor, []).append(seed_key)
            indegree[seed_key] += 1

    def _seed_sort_key(seed_key: str) -> tuple[str, str]:
        seed = seeds[seed_key]
        # Presentation only. It never controls membership or a predecessor edge.
        return seed.event_id, seed.trigger

    ready = sorted((key for key, degree in indegree.items() if degree == 0), key=_seed_sort_key)
    ordered_seed_keys: list[str] = []
    while ready:
        seed_key = ready.pop(0)
        ordered_seed_keys.append(seed_key)
        for successor in successors.get(seed_key, ()):
            indegree[successor] -= 1
            if indegree[successor] == 0:
                ready.append(successor)
        ready.sort(key=_seed_sort_key)
    if len(ordered_seed_keys) < len(seeds):
        cyclic = sorted((key for key in seeds if key not in ordered_seed_keys), key=_seed_sort_key)
        # Contradictory trigger cycles cannot prove a preceding round.
        for seed_key in cyclic:
            predecessor_by_seed[seed_key] = None
        ordered_seed_keys.extend(cyclic)

    round_id_by_seed = {
        seed_key: f"rnd-{position:04d}" for position, seed_key in enumerate(ordered_seed_keys)
    }
    rounds: list[dict[str, Any]] = []
    for position, seed_key in enumerate(ordered_seed_keys):
        seed = seeds[seed_key]
        members = members_by_seed[seed_key]
        round_id = round_id_by_seed[seed_key]
        for step in members:
            step.round_id = round_id
        ends = [s.ended_at for s in members if s.ended_at is not None]
        predecessor = predecessor_by_seed[seed_key]
        rounds.append(
            {
                "round_id": round_id,
                "index": position,
                "trigger": seed.trigger,
                "previous_round_id": round_id_by_seed.get(predecessor),
                "step_ids": sorted(s.step_id for s in members),
                "wave_ids": [],
                "participant_refs": sorted(
                    {s.participant_ref for s in members if s.participant_ref}
                ),
                "deployed_unit_count": len({t for s in members for t in s.task_refs}),
                "started_at": _iso(seed.moment),
                "ended_at": _iso(max(ends)) if ends else None,
                "duration_ms": _ms_between(seed.moment, max(ends)) if ends else None,
                "outcome": _round_outcome(members),
                "evidence_event_ids": sorted(
                    {*seed.event_ids, *(e for s in members for e in s.evidence if e)}
                ),
            }
        )
    return rounds


def _round_outcome(members: list[Step]) -> str:
    if not members:
        return "unknown"
    outcomes = {step.outcome for step in members}
    if outcomes & {"crashed", "timed_out", "failed", "spawn_failed", "gave_up"}:
        return "anomalous"
    if outcomes & {"changes_requested"}:
        return "changes_requested"
    if outcomes & {"running", "requested", "waiting"}:
        return "open"
    return "settled"


def _build_waves(
    steps: list[Step],
    rounds: list[dict[str, Any]],
    parents: dict[str, tuple[str, ...]],
) -> list[dict[str, Any]]:
    """Group work by an explicit shared parent inside an evidenced round.

    Timestamps measure overlap *after* membership is established; they never create
    membership. A step without an explicit parent remains its own wave.
    """
    waves: list[dict[str, Any]] = []
    counter = 0

    for round_record in rounds:
        member_ids = set(round_record["step_ids"])
        candidates = [
            step
            for step in steps
            if step.step_id in member_ids and step.task_refs and step.started_at is not None
        ]
        candidates.sort(key=lambda s: s.index)
        groups: dict[tuple[str, ...], list[Step]] = {}
        for step in candidates:
            parent_refs = tuple(
                sorted(
                    {parent for task_ref in step.task_refs for parent in parents.get(task_ref, ())}
                )
            )
            key = ("parents", *parent_refs) if parent_refs else ("step", step.step_id)
            groups.setdefault(key, []).append(step)
        for _, members in sorted(
            groups.items(), key=lambda item: min(step.index for step in item[1])
        ):
            wave_id = f"wav-{counter:04d}"
            counter += 1
            for step in members:
                step.wave_id = wave_id
            starts = [m.started_at for m in members if m.started_at is not None]
            ends = [m.ended_at for m in members if m.ended_at is not None]
            started = min(starts) if starts else None
            ended = max(ends) if ends else None
            waves.append(
                {
                    "wave_id": wave_id,
                    "round_id": round_record["round_id"],
                    "step_ids": sorted(m.step_id for m in members),
                    "work_unit_refs": sorted({t for m in members for t in m.task_refs}),
                    "participant_refs": sorted(
                        {m.participant_ref for m in members if m.participant_ref}
                    ),
                    "deployed_unit_count": len({t for m in members for t in m.task_refs}),
                    "peak_parallelism": _peak_parallelism(members),
                    # Dispatch pressure is sampled at tick cadence; the reducer fills these
                    # from dispatch events, and leaves them null rather than guessing.
                    "eligible_unit_count_observed": None,
                    "ready_but_not_running_count_observed": None,
                    "ready_but_not_running_ms_observed": None,
                    "global_limit": None,
                    "per_profile_limit": None,
                    "barrier": _wave_barrier(members),
                    "sampling_precision_ms": None,
                    "started_at": _iso(started),
                    "ended_at": _iso(ended),
                    "duration_ms": _ms_between(started, ended),
                    "evidence_event_ids": sorted({e for m in members for e in m.evidence if e}),
                }
            )
            round_record["wave_ids"].append(wave_id)
    return waves


def _peak_parallelism(members: list[Step]) -> int:
    grouped: dict[datetime, list[int]] = {}
    for step in members:
        if step.started_at is None:
            continue
        bucket = grouped.setdefault(step.started_at, [0, 0, 0])
        if step.ended_at == step.started_at:
            bucket[1] += 1  # instantaneous observation
        else:
            bucket[2] += 1  # opening boundary
            if step.ended_at is not None:
                grouped.setdefault(step.ended_at, [0, 0, 0])[0] += 1
    if not grouped:
        return 0
    peak = current = 0
    for moment in sorted(grouped):
        closes, instantaneous, opens = grouped[moment]
        # Intervals are half-open: a span ending exactly when another starts is not
        # parallel with it. Zero-duration observed steps still count at their instant.
        current = max(0, current - closes)
        peak = max(peak, current + opens + instantaneous)
        current += opens
    return peak


def _wave_barrier(members: list[Step]) -> str:
    outcomes = {step.outcome for step in members}
    kinds = {step.kind for step in members}
    if "changes_requested" in outcomes or "review" in kinds:
        return "review"
    if outcomes & {"blocked"}:
        return "dependency"
    if any(kind.startswith("wait_owner") for kind in kinds):
        return "owner"
    if "integration" in kinds:
        return "integration"
    if outcomes & {"completed", "approved"} and len(outcomes) == 1:
        return "dependency"
    return "unknown"


def _critical_path(steps: list[Step]) -> dict[str, Any]:
    """Longest causally ordered chain of observed steps and evidenced waits."""
    by_id = {step.step_id: step for step in steps}
    order = sorted(steps, key=lambda s: (s.order_hint, s.index))
    best_total: dict[str, int] = {}
    best_prev: dict[str, str | None] = {}

    for step in order:
        duration = _ms_between(step.started_at, step.ended_at) or 0
        candidates = [(best_total.get(p, 0), p) for p in step.predecessors if p in by_id]
        if candidates:
            total, previous = max(candidates, key=lambda item: (item[0], item[1]))
        else:
            total, previous = 0, None
        best_total[step.step_id] = total + duration
        best_prev[step.step_id] = previous

    if not best_total:
        return {
            "step_ids": [],
            "duration_ms": None,
            "dispatch_wait_ms": None,
            "dependency_wait_ms": None,
            "review_wait_ms": None,
            "rework_ms": None,
            "coverage": "unavailable",
        }

    terminal = max(best_total.items(), key=lambda item: (item[1], item[0]))[0]
    chain: list[str] = []
    cursor: str | None = terminal
    while cursor is not None:
        chain.append(cursor)
        cursor = best_prev.get(cursor)
    chain.reverse()

    path_steps = [by_id[s] for s in chain]
    incomplete = any(s.started_at is None or s.ended_at is None for s in path_steps)
    return {
        "step_ids": chain,
        "duration_ms": best_total[terminal],
        "dispatch_wait_ms": _sum_kind(path_steps, prefix="wait_process"),
        "dependency_wait_ms": _sum_kind(path_steps, prefix="wait_dependency"),
        "review_wait_ms": _sum_kind(path_steps, kinds={"review"}),
        "rework_ms": _sum_rework(path_steps),
        "coverage": "partial" if incomplete else "exact",
    }


def _sum_kind(
    steps: list[Step], *, prefix: str | None = None, kinds: set[str] | None = None
) -> int:
    total = 0
    for step in steps:
        matches = (prefix is not None and step.kind.startswith(prefix)) or (
            kinds is not None and step.kind in kinds
        )
        if matches:
            total += _ms_between(step.started_at, step.ended_at) or 0
    return total


def _sum_rework(steps: list[Step]) -> int:
    """Time in an explicitly linked attempt after a prior attempt on the same task."""
    seen: dict[str, set[str]] = {}
    total = 0
    for step in steps:
        for task_ref in step.task_refs:
            prior_steps = seen.get(task_ref, set())
            if prior_steps.intersection(step.predecessors):
                total += _ms_between(step.started_at, step.ended_at) or 0
                break
            seen.setdefault(task_ref, set()).add(step.step_id)
    return total
