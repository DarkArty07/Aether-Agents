"""Trace origin correlation and work-graph binding rules.

Normative decisions: OBS-D-011, OBS-D-014, OBS-D-023; requirements OBS-FR-038, OBS-FR-039,
OBS-FR-048, OBS-FR-049, OBS-FR-050, OBS-FR-078.

Two questions live here, and both are answered by refusing to guess.

**Where did this contract start?** An owner message may open a new objective or continue
an existing one; session co-location and timestamp proximity cannot decide that semantic
boundary. So owner messages are *candidates* held in bounded process memory, and a trace
is materialized only when an authoritative contract persistence, an existing
trace/contract reference, or a root Kanban binding establishes the objective. An exact
message reference wins. Otherwise exactly one candidate inside the exact session-lineage
interval may be selected; zero or several leave ``started_at`` null.

**Does this task belong to the contract?** A root binds only through its observed create
result or a strict opaque correlation token. Descendants inherit only through a durable
parent edge from an already bound task in the same project. Everything else stays
unbound and visible, and nothing here can block or roll back native task creation.
"""

from __future__ import annotations

import re
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Final, Iterable

from aether_agents.observation.contracts import (
    WORK_UNIT_RELATIONS,
    is_native_message_id,
    is_opaque_ref,
)
from aether_agents.observation.identity import binding_ref, parse_correlation_token

__all__ = [
    "BindingDecision",
    "OwnerMessageCandidate",
    "OwnerMessageCandidates",
    "OriginSelection",
    "WorkGraphBinder",
]

#: Section 6.1 memory bounds. These limit measurement memory, not workflow or session
#: lifetime: an evicted candidate can still be reconciled later from native SessionDB.
MAX_TRACKED_SESSIONS: Final = 1_024
CANDIDATE_TTL: Final = timedelta(hours=24)
_TRACE_RE: Final = re.compile(r"^ctr_[a-f0-9]{32}$", re.ASCII)
_PROJECT_RE: Final = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.ASCII,
)


@dataclass(frozen=True, slots=True)
class OwnerMessageCandidate:
    """Bounded owner-message metadata. Never a journal event until a trace selects it.

    It holds identity, role, and timestamp only. No message content is read or stored.
    """

    session_id: str
    message_id: int
    occurred_at: datetime
    actor_id: str = "owner"


@dataclass(frozen=True, slots=True)
class OriginSelection:
    """Outcome of deterministic origin reconciliation."""

    candidate: OwnerMessageCandidate | None
    reason_code: str | None  # None on success; otherwise the coverage reason
    exact: bool = False

    @property
    def started_at(self) -> datetime | None:
        return self.candidate.occurred_at if self.candidate is not None else None

    @property
    def ambiguous(self) -> bool:
        return self.candidate is None


class OwnerMessageCandidates:
    """One bounded candidate per active session, in a time- and size-limited LRU."""

    def __init__(
        self,
        *,
        max_sessions: int = MAX_TRACKED_SESSIONS,
        ttl: timedelta = CANDIDATE_TTL,
    ) -> None:
        self._max_sessions = max_sessions
        self._ttl = ttl
        self._entries: OrderedDict[str, OwnerMessageCandidate] = OrderedDict()
        self.evictions = 0
        self.expirations = 0

    def __len__(self) -> int:
        return len(self._entries)

    def observe(self, session_id: str, message_id: int, occurred_at: datetime) -> None:
        """Record the latest owner-message candidate for one session."""
        if not is_opaque_ref(session_id, max_len=256) or not is_native_message_id(message_id):
            return
        self._entries[session_id] = OwnerMessageCandidate(
            session_id=session_id, message_id=message_id, occurred_at=occurred_at
        )
        self._entries.move_to_end(session_id)
        while len(self._entries) > self._max_sessions:
            self._entries.popitem(last=False)
            self.evictions += 1

    def expire(self, now: datetime) -> None:
        """Drop candidates older than the TTL. Eviction changes only health counters."""
        cutoff = now - self._ttl
        stale = [sid for sid, c in self._entries.items() if c.occurred_at < cutoff]
        for session_id in stale:
            del self._entries[session_id]
            self.expirations += 1

    def peek(self, session_id: str) -> OwnerMessageCandidate | None:
        return self._entries.get(session_id)

    def select(
        self,
        *,
        exact_message_id: int | None = None,
        session_lineage: Iterable[str] = (),
        after: datetime | None = None,
        not_later_than: datetime | None = None,
    ) -> OriginSelection:
        """Choose the originating owner message, or declare the origin ambiguous.

        An exact reference always wins. Without one, a candidate qualifies only when it
        sits in the same native session lineage, strictly after the previous bound trace
        action, and no later than the first authoritative materialization action. Exactly
        one qualifying candidate is selected; zero or several are ``reconciliation_ambiguous``
        and leave every origin-dependent duration null. The nearest timestamp is never chosen.
        """
        lineage = {sid for sid in session_lineage if is_opaque_ref(sid, max_len=256)}

        if exact_message_id is not None:
            if not is_native_message_id(exact_message_id):
                return OriginSelection(None, "ORIGIN_REFERENCE_INVALID", exact=True)
            for session_id in lineage or self._entries.keys():
                candidate = self._entries.get(session_id)
                if candidate is not None and candidate.message_id == exact_message_id:
                    return OriginSelection(candidate, None, exact=True)
            # The reference is authoritative even when the candidate was already evicted;
            # the reducer reconciles its timestamp from native SessionDB instead.
            return OriginSelection(None, "ORIGIN_REFERENCE_UNRESOLVED", exact=True)

        if not lineage:
            return OriginSelection(None, "ORIGIN_NO_SESSION_LINEAGE")

        qualifying = [
            candidate
            for session_id in lineage
            if (candidate := self._entries.get(session_id)) is not None
            and (after is None or candidate.occurred_at > after)
            and (not_later_than is None or candidate.occurred_at <= not_later_than)
        ]
        if len(qualifying) == 1:
            return OriginSelection(qualifying[0], None)
        if not qualifying:
            return OriginSelection(None, "ORIGIN_NO_CANDIDATE")
        return OriginSelection(None, "ORIGIN_MULTIPLE_CANDIDATES")


@dataclass(frozen=True, slots=True)
class BindingDecision:
    """Whether one native task joins a trace's bound work graph."""

    bound: bool
    trace_id: str | None
    task_ref: str | None
    relation: str
    parent_task_refs: tuple[str, ...] = ()
    binding: str | None = None
    reason_code: str | None = None

    @property
    def ambiguous(self) -> bool:
        return not self.bound and self.reason_code is not None


@dataclass
class WorkGraphBinder:
    """Deterministic root binding and descendant inheritance for one project.

    Binding history is append-only in the journal; this object is only the collector's
    in-process view. After a restart an unknown parent simply yields no binding, and
    reconciliation resolves it later from the strict token plus the durable parent graph.
    """

    project_id: str
    _bound_tasks: dict[str, str] = field(default_factory=dict, init=False)  # task -> trace
    _tokens: dict[tuple[str, str], list[str]] = field(default_factory=dict, init=False)
    _roots: dict[str, str] = field(default_factory=dict, init=False)  # trace -> root task
    ambiguities: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.project_id, str) or _PROJECT_RE.fullmatch(self.project_id) is None:
            raise ValueError("work graph project_id must be a canonical lower-case UUID")

    # -- root ---------------------------------------------------------------------
    def bind_root(
        self,
        *,
        trace_id: str,
        task_ref: str | None,
        token: Any = None,
        project_id: str | None = None,
    ) -> BindingDecision:
        """Bind a root from the observed create result plus the strict in-call token.

        Hermes documents that the idempotency lookup is not a uniqueness constraint and
        concurrent creators may both insert, so one token matching zero or several live
        tasks is refused rather than resolved by recency.
        """
        if project_id is not None and project_id != self.project_id:
            return self._ambiguous(task_ref, "root", "BINDING_CROSS_PROJECT")
        safe_task = task_ref if is_opaque_ref(task_ref) else None
        if safe_task is None:
            return self._ambiguous(None, "root", "BINDING_NO_TASK_RESULT")
        if not isinstance(trace_id, str) or _TRACE_RE.fullmatch(trace_id) is None:
            return self._ambiguous(safe_task, "root", "BINDING_TRACE_MALFORMED")

        parsed = parse_correlation_token(token) if token is not None else None
        if token is not None and parsed is None:
            # An ordinary arbitrary idempotency key is discarded, not journaled.
            return self._ambiguous(safe_task, "root", "BINDING_TOKEN_MALFORMED")
        if parsed is not None:
            if parsed[0] != trace_id:
                return self._ambiguous(safe_task, "root", "BINDING_TOKEN_TRACE_MISMATCH")
            key = parsed
            seen = self._tokens.setdefault(key, [])
            if safe_task not in seen:
                seen.append(safe_task)
            if len(seen) > 1:
                return self._ambiguous(safe_task, "root", "BINDING_TOKEN_REUSED")

        existing_root = self._roots.get(trace_id)
        if existing_root is not None and existing_root != safe_task:
            return self._ambiguous(safe_task, "root", "BINDING_CONFLICTING_ROOT")

        owner = self._bound_tasks.get(safe_task)
        if owner is not None and owner != trace_id:
            return self._ambiguous(safe_task, "root", "BINDING_TASK_ALREADY_BOUND")

        self._bound_tasks[safe_task] = trace_id
        self._roots[trace_id] = safe_task
        return BindingDecision(
            bound=True,
            trace_id=trace_id,
            task_ref=safe_task,
            relation="root",
            binding=binding_ref(trace_id, safe_task),
        )

    # -- descendants ---------------------------------------------------------------
    def inherit(
        self,
        *,
        task_ref: str | None,
        parent_task_refs: Iterable[str],
        relation: str = "unknown",
        project_id: str | None = None,
    ) -> BindingDecision:
        """Inherit trace membership through a durable parent edge.

        Every inherited edge stays visible and reversible by later reconciliation.
        Ambiguous or cross-project edges remain unbound; none of this blocks native work.
        """
        raw_parents = tuple(parent_task_refs)
        parents = tuple(p for p in raw_parents if is_opaque_ref(p))
        safe_task = task_ref if is_opaque_ref(task_ref) else None
        if project_id is not None and project_id != self.project_id:
            return self._ambiguous(safe_task, relation, "BINDING_CROSS_PROJECT", parents)
        if safe_task is None:
            return self._ambiguous(None, relation, "BINDING_NO_TASK_REF", parents)
        if len(parents) != len(raw_parents):
            return self._ambiguous(safe_task, relation, "BINDING_PARENT_REF_MALFORMED", parents)
        if not parents:
            return self._ambiguous(safe_task, relation, "BINDING_NO_PARENT_EDGE", parents)

        traces = {self._bound_tasks[p] for p in parents if p in self._bound_tasks}
        if not traces:
            return self._ambiguous(safe_task, relation, "BINDING_PARENT_UNBOUND", parents)
        if len(traces) > 1:
            return self._ambiguous(safe_task, relation, "BINDING_PARENT_CONFLICT", parents)

        trace_id = traces.pop()
        owner = self._bound_tasks.get(safe_task)
        if owner is not None and owner != trace_id:
            return self._ambiguous(safe_task, relation, "BINDING_TASK_ALREADY_BOUND", parents)

        self._bound_tasks[safe_task] = trace_id
        return BindingDecision(
            bound=True,
            trace_id=trace_id,
            task_ref=safe_task,
            relation=relation if relation in WORK_UNIT_RELATIONS else "unknown",
            parent_task_refs=parents,
            binding=binding_ref(trace_id, safe_task),
        )

    def unbind(self, task_ref: str) -> None:
        """Append-only in the journal; here it only forgets the in-process view."""
        if is_opaque_ref(task_ref):
            self._bound_tasks.pop(task_ref, None)

    def trace_for(self, task_ref: str) -> str | None:
        return self._bound_tasks.get(task_ref) if is_opaque_ref(task_ref) else None

    def restore(self, *, task_ref: str, trace_id: str, relation: str = "unknown") -> None:
        """Restore a previously journaled binding during process bootstrap.

        This does not emit or replace history; it only reconstructs the collector's
        in-process lookup from retained Aether-owned evidence.
        """
        if (
            not is_opaque_ref(task_ref)
            or not isinstance(trace_id, str)
            or _TRACE_RE.fullmatch(trace_id) is None
        ):
            raise ValueError("restored binding references are malformed")
        self._bound_tasks[task_ref] = trace_id
        if relation == "root":
            self._roots[trace_id] = task_ref

    def root_for(self, trace_id: str) -> str | None:
        return (
            self._roots.get(trace_id)
            if isinstance(trace_id, str) and _TRACE_RE.fullmatch(trace_id)
            else None
        )

    def _ambiguous(
        self,
        task_ref: str | None,
        relation: str,
        reason_code: str,
        parents: tuple[str, ...] = (),
    ) -> BindingDecision:
        self.ambiguities += 1
        return BindingDecision(
            bound=False,
            trace_id=None,
            task_ref=task_ref if is_opaque_ref(task_ref) else None,
            relation=relation if relation in WORK_UNIT_RELATIONS else "unknown",
            parent_task_refs=tuple(parent for parent in parents if is_opaque_ref(parent)),
            reason_code=reason_code,
        )
