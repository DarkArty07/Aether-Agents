"""Hermes-independent collection core.

The adapter in :mod:`aether_agents.observation.capture.hermes_plugin` extracts allowlisted
scalars from native payloads and hands them here. Nothing in this module knows what Hermes
is, which keeps the manager environment importable with no runtime installed (OBS-FR-074).

Responsibilities, all bounded:

* own one journal writer, one supervised flusher, and one event builder per trace;
* guarantee the synchronous path is projection + serialization + one append (OBS-D-027);
* keep every failure fail-open and turn it into visible coverage instead of an exception;
* prevent recursive self-observation (OBS-FR-036).
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterator

from aether_agents.observation.capture.flusher import Flusher
from aether_agents.observation.capture.journal import AppendOutcome, JournalWriter
from aether_agents.observation.capture.projectors import EventBuilder
from aether_agents.observation.context import HealthCounters
from aether_agents.observation.contracts import COLLECTOR_VERSION, CoverageClass
from aether_agents.observation.correlation import OwnerMessageCandidates, WorkGraphBinder
from aether_agents.observation.fingerprints import FingerprintKeyring
from aether_agents.observation.identity import native_identity, new_producer_epoch
from aether_agents.paths import ObservationPaths

__all__ = ["Collector", "CollectorStats", "reentrancy_guard"]

#: Process-local re-entrancy guard. Observer-internal serialization, ingestion,
#: reconciliation, and CLI queries must produce no nested model or tool span, and a direct
#: journal write must never call back through the Hermes tool registry.
_GUARD = threading.local()


class _Reentrant:
    def __init__(self) -> None:
        self.active = False

    def __enter__(self) -> bool:
        if getattr(_GUARD, "active", False):
            return False
        _GUARD.active = True
        self.active = True
        return True

    def __exit__(self, *_exc: object) -> None:
        if self.active:
            _GUARD.active = False
            self.active = False


def reentrancy_guard() -> _Reentrant:
    """Enter observer-internal work. Returns ``False`` from ``__enter__`` when nested."""
    return _Reentrant()


def observing() -> bool:
    """True while the observer is already inside its own callback or query."""
    return bool(getattr(_GUARD, "active", False))


@dataclass(slots=True)
class CollectorStats:
    """Content-free counters surfaced by ``aether doctor``."""

    appended: int = 0
    rejected: int = 0
    io_failures: int = 0
    reentrant_skips: int = 0
    callback_errors: int = 0
    unresolved_context: int = 0


#: Contract-critical facts ask the flusher to run sooner; they never make a caller wait.
CRITICAL_EVENT_TYPES = frozenset(
    {
        "contract.persisted",
        "contract.completion_verified",
        "contract.completion_candidate",
        "handoff.completed",
        "work_unit.bound",
        "acceptance.evaluated",
        "trace.closed",
        "trace.cancelled",
        "trace.abandoned",
        "trace.failed",
        "coverage.gap",
    }
)


@dataclass
class Collector:
    """One project's collection pipeline."""

    paths: ObservationPaths
    runtime_fingerprint: str
    normalizer_ref: str | None = None
    producer_epoch: str = field(default_factory=new_producer_epoch)
    stats: CollectorStats = field(default_factory=CollectorStats)

    writer: JournalWriter = field(init=False)
    flusher: Flusher = field(init=False)
    keyring: FingerprintKeyring = field(init=False)
    binder: WorkGraphBinder = field(init=False)
    candidates: OwnerMessageCandidates = field(init=False)
    health: HealthCounters = field(init=False)
    _builders: dict[str, EventBuilder] = field(default_factory=dict, init=False, repr=False)
    _materialized: set[str] = field(default_factory=set, init=False, repr=False)
    _announced_fingerprint_epochs: set[str] = field(default_factory=set, init=False, repr=False)
    _fingerprint_key_ready: bool = field(default=False, init=False, repr=False)
    _started: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        self.paths.ensure()
        self.writer = JournalWriter(paths=self.paths, producer_epoch=self.producer_epoch)
        self.health = HealthCounters(self.paths.root)
        self.flusher = Flusher(
            writer=self.writer,
            failure_notifier=self.health.increment,
        )
        self.keyring = FingerprintKeyring(self.paths)
        self.binder = WorkGraphBinder(project_id=self.paths.project_id)
        self.candidates = OwnerMessageCandidates()

    # -- lifecycle ------------------------------------------------------------------
    def start(self, spawn_task: Any = None) -> None:
        if self._started:
            return
        self.writer.open()
        try:
            self.keyring.load_or_create()
            self._fingerprint_key_ready = True
        except Exception:  # key loss degrades configuration evidence, never capture
            self.health.increment("FINGERPRINT_KEY_UNAVAILABLE")
        self.flusher.start(spawn_task)
        self._started = True

    def stop(self) -> None:
        """Close buffers, cancel only plugin-owned tasks, preserve flushed segments."""
        if not self._started:
            return
        try:
            self.flusher.stop()
        finally:
            failures_before_close = self.writer.io_failure_count
            self.writer.close_bounded(self.flusher.teardown_timeout_s)
            close_failures = self.writer.io_failure_count - failures_before_close
            if close_failures > 0:
                self.health.increment("JOURNAL_CLOSE_FAILED", close_failures)
            self._started = False

    # -- emission -------------------------------------------------------------------
    def builder_for(self, trace_id: str) -> EventBuilder:
        builder = self._builders.get(trace_id)
        if builder is None:
            builder = EventBuilder(
                trace_id=trace_id,
                project_id=self.paths.project_id,
                collector_version=COLLECTOR_VERSION,
                runtime_fingerprint=self.runtime_fingerprint,
                normalizer_ref=self.normalizer_ref,
            )
            self._builders[trace_id] = builder
        return builder

    @property
    def fingerprint_key_ready(self) -> bool:
        return self._fingerprint_key_ready

    def ensure_trace_opened(
        self,
        trace_id: str,
        *,
        session_lineage: tuple[str, ...] = (),
        exact_message_id: int | str | None = None,
        materialized_at: datetime | None = None,
        materialization_ref: Any = None,
        contract_id: Any = None,
        source_kind: str = "aether_checkpoint",
        source_hook: str | None = None,
    ) -> bool:
        """Materialize one trace exactly once per process, without guessing origin.

        A deterministic ``trace.opened`` identity makes repeated materialization
        attempts across producer epochs idempotent at ingest.  When no exact owner
        candidate can be selected, the event still records authoritative
        materialization but carries no origin message; the reducer therefore keeps
        ``started_at`` and every origin-dependent duration null.
        """
        if trace_id in self._materialized:
            return True
        moment = materialized_at or datetime.now(timezone.utc)
        selection = self.candidates.select(
            exact_message_id=exact_message_id,
            session_lineage=session_lineage,
            not_later_than=moment,
        )
        origin = selection.candidate
        origin_message_id = origin.message_id if origin is not None else exact_message_id
        # The allocated trace ID is itself the complete stable identity of the one
        # opening fact.  A restart may first observe a different authoritative
        # materialization hook; it must still deduplicate to this same opening.
        identity = native_identity(kind="trace.opened", trace=trace_id)
        event = self.builder_for(trace_id).contract(
            event_type="trace.opened",
            status="started",
            origin_message_id=origin_message_id,
            occurred_at=origin.occurred_at if origin is not None else moment,
            timestamp_source="native" if origin is not None else "collector",
            source_kind=source_kind,
            source_hook=source_hook,
            contract_id=contract_id,
            actor_kind="owner" if origin is not None else "system",
            actor_id=origin.actor_id if origin is not None else "observer",
            session_id=origin.session_id if origin is not None else None,
            identity=identity,
        )
        outcome = self.emit(event)
        if not outcome.accepted:
            return False
        self._materialized.add(trace_id)
        if selection.reason_code is not None:
            self._record_gap(
                trace_id=trace_id,
                gap_class=CoverageClass.RECONCILIATION_AMBIGUOUS,
                reason_code=selection.reason_code,
            )
        return True

    def restore_materialized_trace(self, trace_id: str) -> None:
        """Mark a retained trace as materialized in this process without emitting."""
        self._materialized.add(trace_id)

    def emit(self, event: dict[str, Any]) -> AppendOutcome:
        """Append one already-projected event. Never raises."""
        critical = event.get("event_type") in CRITICAL_EVENT_TYPES
        outcome = self.writer.append(event, critical=critical)
        if outcome.accepted:
            self.stats.appended += 1
            return outcome

        if outcome.coverage_class == CoverageClass.FORBIDDEN_PAYLOAD_REJECTED:
            self.stats.rejected += 1
        else:
            self.stats.io_failures += 1
        # Record the loss as visible coverage. The diagnostic itself is bounded and is
        # never allowed to recurse: if it also fails, only a health counter changes.
        self._record_gap(
            trace_id=event.get("trace_id", ""),
            gap_class=outcome.coverage_class or CoverageClass.OTHER,
            reason_code=outcome.reason_code or "APPEND_REJECTED",
        )
        return outcome

    def _record_gap(self, *, trace_id: str, gap_class: str, reason_code: str) -> None:
        self.health.increment(reason_code)
        if not trace_id:
            return
        try:
            gap = self.builder_for(trace_id).coverage_gap(
                gap_class=gap_class, reason_code=reason_code
            )
            # Direct write: emit() would recurse if this append also failed.
            self.writer.append_nonblocking(gap, critical=True)
        except Exception:  # noqa: BLE001 - diagnostics are best effort by contract
            self.stats.callback_errors += 1

    def record_unresolved_context(self, reason_code: str) -> None:
        """No project could be safely selected: count it, write nothing project-scoped."""
        self.stats.unresolved_context += 1
        self.health.increment(reason_code)

    def record_fingerprint_epoch_boundary(
        self, trace_id: str, *, parent_event_id: str | None = None
    ) -> None:
        """Materialize a detected key loss/rotation once, without exposing key bytes.

        Initial project-key creation is not a comparison boundary. A later rotation or
        loss is: configurations on opposite sides cannot be compared, so the first
        active trace that observes the new epoch receives an explicit coverage fact.
        """
        change = self.keyring.last_change
        if (
            change is None
            or change.reason == "created"
            or change.key_id in self._announced_fingerprint_epochs
        ):
            return
        reason_code = {
            "rotated": "FINGERPRINT_KEY_ROTATED",
            "key_lost": "FINGERPRINT_KEY_LOST",
        }.get(change.reason, "FINGERPRINT_KEY_EPOCH_BOUNDARY")
        outcome = self.emit(
            self.builder_for(trace_id).coverage_gap(
                gap_class=CoverageClass.OTHER,
                reason_code=reason_code,
                parent_event_id=parent_event_id,
            )
        )
        if outcome.accepted:
            self._announced_fingerprint_epochs.add(change.key_id)

    def note_expired_candidates(self, now: datetime) -> None:
        before = len(self.candidates)
        self.candidates.expire(now)
        dropped = before - len(self.candidates)
        if dropped:
            self.health.increment("ORIGIN_CANDIDATE_EXPIRED", dropped)

    # -- health ---------------------------------------------------------------------
    def health_snapshot(self) -> dict[str, int]:
        return {
            "appended": self.stats.appended,
            "rejected": self.stats.rejected,
            "io_failures": self.stats.io_failures + self.writer.io_failure_count,
            "reentrant_skips": self.stats.reentrant_skips,
            "callback_errors": self.stats.callback_errors,
            "unresolved_context": self.stats.unresolved_context,
            "flusher_flushes": self.flusher.stats.flushes,
            "flusher_failures": self.flusher.stats.failures,
            "candidate_evictions": self.candidates.evictions,
            "binding_ambiguities": self.binder.ambiguities,
        }

    def __enter__(self) -> "Collector":
        self.start()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.stop()


def iter_critical_types() -> Iterator[str]:
    yield from sorted(CRITICAL_EVENT_TYPES)
