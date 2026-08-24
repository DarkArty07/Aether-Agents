"""The optional bounded semantic checkpoint sink.

Normative sources: OBS-D-020, spec sections 6.6, 7.2, 13.2; requirements OBS-FR-063,
OBS-FR-036.

Mechanical lifecycle is reconstructable from native hooks, but some semantic facts are
not inferable from metadata alone. Those stay ``unknown``/``undeclared`` unless an
already-authorized action supplies a checkpoint.

This is deliberately **not** an agent-facing tool and **not** a workflow step. No role is
instructed to call it, its absence is never a pipeline violation, and it fails open. It is
called by Aether's own canonical contract writer or closing verifier *after* that
component's authoritative action has already succeeded — so it can never influence the
action it describes.

The caller cannot supply role, free text, content, or an arbitrary payload: the sink
accepts only a schema-enumerated kind and bounded opaque references, and derives profile
and role authority from the active Aether installation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Final, Mapping

from aether_agents.observation.capture.collector import Collector, reentrancy_guard
from aether_agents.observation.capture.journal import iter_segment_lines, list_segments
from aether_agents.observation.contracts import (
    WORK_UNIT_RELATIONS,
    CoverageClass,
    canonical_digest,
    validate_event,
)
from aether_agents.observation.identity import native_identity
from aether_agents.observation.privacy import ForbiddenPayload, assert_clean
from aether_agents.observation.reduce.process import causal_order

__all__ = [
    "AUTHORITY_CONTEXT_SCHEMA_VERSION",
    "CHECKPOINT_KINDS",
    "AuthorityContext",
    "AuthorityPrincipal",
    "CheckpointResult",
    "CheckpointSink",
    "authority_context_from_state_root",
]


AUTHORITY_CONTEXT_SCHEMA_VERSION: Final = "aether.authority-context.v1"


@dataclass(frozen=True, slots=True)
class AuthorityPrincipal:
    """One product-verified installation principal.

    Event actor strings identify which principal produced a fact; they never grant the
    permission.  Permission comes from this out-of-band record, materialized by Aether's
    active installation/lifecycle state and supplied to the reducer.
    """

    actor_id: str
    profile: str
    role: str
    assigned_review_refs: tuple[str, ...] = ()
    verified: bool = True

    def to_record(self) -> dict[str, Any]:
        return {
            "actor_id": self.actor_id,
            "profile": self.profile,
            "role": self.role,
            "assigned_review_refs": list(self.assigned_review_refs),
            "verified": self.verified,
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "AuthorityPrincipal":
        if not isinstance(record, Mapping):
            raise ValueError("invalid authority principal record")
        actor_id = record.get("actor_id")
        profile = record.get("profile")
        role = record.get("role")
        assignments = record.get("assigned_review_refs", ())
        verified = record.get("verified")
        if not all(isinstance(value, str) and value for value in (actor_id, profile, role)):
            raise ValueError("invalid authority principal identity")
        if not isinstance(assignments, (list, tuple)) or not all(
            isinstance(value, str) and value for value in assignments
        ):
            raise ValueError("invalid authority review assignments")
        if not isinstance(verified, bool):
            raise ValueError("invalid authority verification flag")
        return cls(
            actor_id=actor_id,
            profile=profile,
            role=role,
            assigned_review_refs=tuple(sorted(set(assignments))),
            verified=verified,
        )

    def permits(self, event_type: str, *, task_ref: str | None = None) -> bool:
        if not self.verified:
            return False
        if event_type in {
            "contract.completion_verified",
            "trace.closed",
            "trace.cancelled",
            "trace.abandoned",
            "trace.failed",
        }:
            return self.role == "verification"
        if event_type == "review.requested":
            return self.role in {"verification", "supervision", "review"}
        if event_type.startswith("review."):
            return self.role in {"verification", "review", "supervision"} and task_ref is not None
        if event_type.startswith("acceptance."):
            return self.role == "verification" or (
                self.role in {"review", "supervision"}
                and task_ref is not None
                and ("*" in self.assigned_review_refs or task_ref in self.assigned_review_refs)
            )
        if event_type.startswith("handoff."):
            return self.role in {"verification", "supervision"}
        if event_type.startswith(("contract.", "decision.", "clarification.", "invariant.")):
            return self.role == "verification"
        # Evidence and bounded attribution may be supplied by any verified product role;
        # their provenance remains explicit and they do not resolve the whole objective.
        return self.role in {"verification", "supervision", "review", "implementation"}


@dataclass(frozen=True, slots=True)
class AuthorityContext:
    """Serializable, product-owned authority input for checkpoints and reduction."""

    principals: tuple[AuthorityPrincipal, ...] = ()
    source: str = "unavailable"
    schema_version: str = AUTHORITY_CONTEXT_SCHEMA_VERSION

    @classmethod
    def unavailable(cls) -> "AuthorityContext":
        return cls(principals=(), source="unavailable")

    @classmethod
    def product_default(cls) -> "AuthorityContext":
        """Explicit fixture/product default; production should persist this record.

        This is deliberately a trusted input object, never reconstructed from journal
        actor fields.  Lifecycle may replace it with an active-installation record via
        :meth:`from_record` without importing manager code into the Hermes plugin.
        """
        return cls(
            source="fixture_product_default",
            principals=(
                AuthorityPrincipal("morfeo", "morfeo", "verification"),
                AuthorityPrincipal("supervisor", "supervisor", "supervision", ("review",)),
                AuthorityPrincipal("implementer", "implementer", "implementation"),
            ),
        )

    @classmethod
    def for_active_release(cls, release_id: str) -> "AuthorityContext":
        """Return the exact A1 role bundle bound to one verified active release."""

        if not isinstance(release_id, str) or not release_id:
            raise ValueError("active release identity is required for authority")
        return cls(
            principals=(
                AuthorityPrincipal("morfeo", "morfeo", "verification"),
                AuthorityPrincipal("supervisor", "supervisor", "supervision"),
                AuthorityPrincipal("implementer", "implementer", "implementation"),
            ),
            source=f"active_release:{release_id}",
        )

    def to_record(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "source": self.source,
            "principals": [principal.to_record() for principal in self.principals],
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "AuthorityContext":
        if not isinstance(record, Mapping):
            raise ValueError("invalid authority context record")
        if record.get("schema_version") != AUTHORITY_CONTEXT_SCHEMA_VERSION:
            raise ValueError("unsupported authority context schema")
        source = record.get("source")
        principals = record.get("principals")
        if not isinstance(source, str) or not source:
            raise ValueError("invalid authority context source")
        if not isinstance(principals, (list, tuple)):
            raise ValueError("invalid authority context principals")
        parsed = tuple(AuthorityPrincipal.from_record(item) for item in principals)
        identities = [(item.actor_id, item.profile) for item in parsed]
        if len(identities) != len(set(identities)):
            raise ValueError("duplicate authority principal")
        return cls(principals=parsed, source=source)

    def resolve_principal(
        self,
        *,
        actor_id: str | None,
        profile: str | None,
        role: str | None = None,
    ) -> AuthorityPrincipal | None:
        matches = [
            principal
            for principal in self.principals
            if principal.verified
            and actor_id == principal.actor_id
            and profile == principal.profile
            and role == principal.role
        ]
        return matches[0] if len(matches) == 1 else None

    def permits(
        self,
        event_type: str,
        *,
        actor_id: str | None,
        profile: str | None,
        role: str | None = None,
        task_ref: str | None = None,
    ) -> bool:
        principal = self.resolve_principal(
            actor_id=actor_id,
            profile=profile,
            role=role,
        )
        return principal is not None and principal.permits(event_type, task_ref=task_ref)

    def assignment_principal(
        self,
        *,
        actor_id: str | None,
        profile: str | None,
        event_type: str,
        task_ref: str,
    ) -> AuthorityPrincipal | None:
        """Resolve a durable assignment against product-owned principals.

        A native assignment identifies the assignee, but its actor ``role`` is neither
        required nor trusted. The verified active-release context remains the sole
        source of that principal's role and permissions.
        """

        matches = [
            principal
            for principal in self.principals
            if principal.verified
            and actor_id == principal.actor_id
            and profile == principal.profile
            and principal.permits(event_type, task_ref=task_ref)
        ]
        return matches[0] if len(matches) == 1 else None

    def checkpoint_principal(
        self,
        event_type: str,
        *,
        task_ref: str | None = None,
    ) -> AuthorityPrincipal | None:
        """Resolve the sole product-routed principal for a checkpoint kind.

        The checkpoint caller supplies only the semantic kind and bounded references.
        Product configuration owns the route from that kind to an identity.  A missing
        or ambiguous route fails closed for the checkpoint and remains fail-open for the
        native workflow.
        """
        if event_type == "review.requested":
            routed_roles = {"supervision"}
        elif event_type.startswith("review."):
            routed_roles = {"review", "supervision"}
        elif event_type.startswith(("work_unit.", "handoff.")):
            routed_roles = {"supervision"}
        elif event_type.startswith(("bottleneck.", "defect.")):
            routed_roles = {"supervision"}
        else:
            routed_roles = {"verification"}
        matches = [
            principal
            for principal in self.principals
            if principal.role in routed_roles
            and principal.permits(event_type, task_ref=task_ref)
            and (
                not event_type.startswith("review.")
                or event_type == "review.requested"
                or (
                    task_ref is not None
                    and (
                        "*" in principal.assigned_review_refs
                        or task_ref in principal.assigned_review_refs
                    )
                )
            )
        ]
        return matches[0] if len(matches) == 1 else None


def authority_context_from_state_root(root: Any) -> AuthorityContext:
    """Load authority only through a coherent product-owned active release record.

    Observation remains fail-open: absent, malformed, mismatched, or partially written
    lifecycle state produces an unavailable context rather than trusting event strings.
    The lifecycle import stays lazy so the Hermes adapter remains the only Hermes-facing
    module and manager imports remain usable without Hermes installed.
    """

    try:
        from aether_agents.lifecycle import ReleaseStore
        from aether_agents.paths import data_root

        state = Path(root)
        # Compatibility fixtures historically colocated lifecycle and observation
        # roots. Production resolves immutable releases from XDG data while retaining
        # observer bytes beneath the explicit XDG state root.
        release_data = state if (state / "active.json").exists() else data_root()
        active = ReleaseStore(release_data, state_root=state).active()
        if active is None:  # pragma: no cover - ``required=True`` above
            return AuthorityContext.unavailable()
        context = AuthorityContext.from_record(active.authority_context)
        expected = AuthorityContext.for_active_release(active.release_id)
        if context != expected:
            return AuthorityContext.unavailable()
        return context
    except Exception:  # noqa: BLE001 - missing authority degrades observation only
        return AuthorityContext.unavailable()


#: The closed set of semantic facts an existing canonical write or closing verification
#: already owns. Anything outside this mapping is rejected and reported without copying
#: the offending payload.
CHECKPOINT_KINDS: Final[dict[str, tuple[str, str]]] = {
    # kind -> (event_type, status)
    "contract_executable": ("contract.executable", "passed"),
    "contract_revision": ("contract.revision", "reported"),
    "contract_persisted": ("contract.persisted", "completed"),
    "contract_execution_started": ("contract.execution_started", "started"),
    "contract_completion_candidate": ("contract.completion_candidate", "reported"),
    "contract_completion_verified": ("contract.completion_verified", "verified"),
    "clarification_requested": ("clarification.requested", "started"),
    "clarification_resolved": ("clarification.resolved", "completed"),
    "decision_recorded": ("decision.recorded", "reported"),
    "decision_superseded": ("decision.superseded", "superseded"),
    "decision_rejected": ("decision.rejected", "rejected"),
    "evidence_added": ("evidence.added", "reported"),
    "evidence_rejected": ("evidence.rejected", "rejected"),
    "invariant_passed": ("invariant.passed", "passed"),
    "invariant_failed": ("invariant.failed", "failed"),
    "acceptance_declared": ("acceptance.declared", "pending"),
    "acceptance_evaluated": ("acceptance.evaluated", "reported"),
    "handoff_started": ("handoff.started", "started"),
    "handoff_completed": ("handoff.completed", "completed"),
    "handoff_failed": ("handoff.failed", "failed"),
    "handoff_blocked": ("handoff.blocked", "blocked"),
    "review_requested": ("review.requested", "started"),
    "review_approved": ("review.approved", "passed"),
    "review_changes_requested": ("review.changes_requested", "rejected"),
    "work_unit_classified": ("work_unit.bound", "reported"),
    "trace_closed": ("trace.closed", "completed"),
    "trace_cancelled": ("trace.cancelled", "cancelled"),
    "trace_abandoned": ("trace.abandoned", "unknown"),
    "trace_failed": ("trace.failed", "failed"),
    "bottleneck_attributed": ("bottleneck.attributed", "reported"),
    "defect_attributed": ("defect.attributed", "reported"),
}


@dataclass(frozen=True, slots=True)
class CheckpointResult:
    """Fail-open outcome. Callers ignore it for workflow purposes."""

    accepted: bool
    reason_code: str | None = None

    def __bool__(self) -> bool:  # pragma: no cover - trivial
        return self.accepted


class CheckpointSink:
    """Bounded internal sink for one collector."""

    def __init__(self, collector: Collector) -> None:
        self._collector = collector
        self._authority_context = authority_context_from_state_root(collector.paths.root)

    def emit(
        self,
        kind: str,
        *,
        trace_id: str,
        occurred_at: datetime | None = None,
        contract_id: Any = None,
        task_ref: Any = None,
        run_id: Any = None,
        session_id: Any = None,
        **references: Any,
    ) -> CheckpointResult:
        """Record one semantic checkpoint after an authoritative action succeeded.

        Never raises. A rejected or failed checkpoint reduces semantic coverage and
        nothing else — it cannot modify its source and cannot fail the pipeline.
        """
        with reentrancy_guard() as entered:
            if not entered:
                # Observer-internal work never produces a nested span.
                return CheckpointResult(False, "REENTRANT")
            try:
                return self._emit_guarded(
                    kind,
                    trace_id=trace_id,
                    occurred_at=occurred_at,
                    contract_id=contract_id,
                    task_ref=task_ref,
                    run_id=run_id,
                    session_id=session_id,
                    references=references,
                )
            except ForbiddenPayload as rejection:
                self._reject(trace_id, rejection.reason_code)
                return CheckpointResult(False, rejection.reason_code)
            except Exception:  # noqa: BLE001 - fail-open is the contract
                self._reject(trace_id, "CHECKPOINT_FAILED")
                return CheckpointResult(False, "CHECKPOINT_FAILED")

    def _emit_guarded(
        self,
        kind: str,
        *,
        trace_id: str,
        occurred_at: datetime | None,
        contract_id: Any,
        task_ref: Any,
        run_id: Any,
        session_id: Any,
        references: dict[str, Any],
    ) -> CheckpointResult:
        mapping = CHECKPOINT_KINDS.get(kind)
        if mapping is None:
            self._reject(trace_id, "CHECKPOINT_KIND_UNKNOWN")
            return CheckpointResult(False, "CHECKPOINT_KIND_UNKNOWN")

        event_type, status = mapping
        task_text = task_ref if isinstance(task_ref, str) else None
        allowed = self._allowed_reference_keys(event_type)
        if any(key not in allowed for key in references):
            # The diagnostic deliberately omits the caller-controlled key name.
            self._reject(trace_id, "CHECKPOINT_REFERENCE_UNKNOWN")
            return CheckpointResult(False, "CHECKPOINT_REFERENCE_UNKNOWN")
        required = self._required_reference_keys(event_type)
        available = set(references)
        if task_ref is not None:
            available.add("task_ref")
        if not required.issubset(available):
            self._reject(trace_id, "CHECKPOINT_REFERENCE_MISSING")
            return CheckpointResult(False, "CHECKPOINT_REFERENCE_MISSING")
        if event_type == "work_unit.bound" and (
            not isinstance(references.get("required"), bool)
            or references.get("relation") not in WORK_UNIT_RELATIONS
            or references.get("relation") == "unknown"
        ):
            self._reject(trace_id, "CHECKPOINT_REFERENCE_INVALID")
            return CheckpointResult(False, "CHECKPOINT_REFERENCE_INVALID")

        # Reject content-bearing or secret-shaped values before scanning durable state
        # or performing any write, including diagnostics.
        block_references = dict(references)
        if task_ref is not None:
            block_references.setdefault("task_ref", task_ref)
        assert_clean(block_references)

        authority_task_ref = task_text
        authority_parent_event_id: str | None = None
        if event_type.startswith("acceptance."):
            authority_task_ref = next(
                (
                    value
                    for value in (
                        references.get("review_task_ref"),
                        references.get("assigned_task_ref"),
                        task_text,
                    )
                    if isinstance(value, str)
                ),
                None,
            )
        if event_type.startswith("review."):
            review_authority = self._durable_review_principal(
                event_type=event_type,
                trace_id=trace_id,
                task_ref=authority_task_ref,
                binding_ref=references.get("binding_ref"),
            )
            if review_authority is None:
                principal = None
            else:
                principal, authority_parent_event_id = review_authority
                if event_type != "review.requested":
                    authority_parent_event_id = self._durable_review_request_event(
                        trace_id=trace_id,
                        task_ref=authority_task_ref,
                        binding_ref=references.get("binding_ref"),
                        classification_event_id=authority_parent_event_id,
                        principal=principal,
                    )
                    if authority_parent_event_id is None:
                        principal = None
        elif event_type == "work_unit.bound":
            principal = self._authority_context.checkpoint_principal(
                event_type,
                task_ref=authority_task_ref,
            )
            authority_parent_event_id = self._durable_native_binding_parent(
                trace_id=trace_id,
                task_ref=authority_task_ref,
                binding_ref=references.get("binding_ref"),
            )
            if authority_parent_event_id is None:
                principal = None
        else:
            principal = self._authority_context.checkpoint_principal(
                event_type,
                task_ref=authority_task_ref,
            )
        if principal is None:
            self._reject(trace_id, "CHECKPOINT_AUTHORITY_UNVERIFIED")
            return CheckpointResult(False, "CHECKPOINT_AUTHORITY_UNVERIFIED")

        builder = self._collector.builder_for(trace_id)
        blocks = self._blocks(event_type, block_references)
        has_stable_reference = bool(
            blocks or contract_id is not None or task_ref is not None or run_id is not None
        )
        identity = (
            native_identity(
                kind="aether.checkpoint",
                digest=canonical_digest(
                    {
                        "event_type": event_type,
                        "trace_id": trace_id,
                        "contract_id": contract_id,
                        "task_ref": task_ref,
                        "run_id": run_id,
                        "parent_event_id": authority_parent_event_id,
                        "blocks": blocks,
                    }
                ),
            )
            if has_stable_reference
            else None
        )
        event = builder.build(
            event_type,
            status=status,
            source_kind="aether_checkpoint",
            occurred_at=occurred_at,
            timestamp_source="native" if occurred_at else "collector",
            actor_kind="agent",
            actor_id=principal.actor_id,
            profile=principal.profile,
            role=principal.role,
            contract_id=contract_id,
            task_id=task_ref,
            run_id=run_id,
            session_id=session_id,
            identity=identity,
            parent_event_id=authority_parent_event_id,
            **blocks,
        )
        try:
            validate_event(event)
            assert_clean(event)
        except Exception as error:
            raise ForbiddenPayload("CHECKPOINT_SCHEMA_INVALID", "$") from error

        # The checkpoint already follows an authoritative Aether action, so its
        # exact trace reference is sufficient to materialize/resume the observer.
        # Origin remains null unless the bounded candidate/reference can be resolved.
        session_text = str(session_id) if session_id is not None else ""
        if self._durable_trace_opened(trace_id):
            self._collector.restore_materialized_trace(trace_id)
        if not self._collector.ensure_trace_opened(
            trace_id,
            session_lineage=(session_text,) if session_text else (),
            exact_message_id=block_references.get("origin_message_id"),
            materialized_at=occurred_at,
            materialization_ref=identity["digest"] if identity is not None else None,
            contract_id=contract_id,
            source_kind="aether_checkpoint",
        ):
            return CheckpointResult(False, "TRACE_MATERIALIZATION_FAILED")

        outcome = self._collector.emit(event)
        return CheckpointResult(outcome.accepted, outcome.reason_code)

    def _durable_trace_events(self, trace_id: str) -> list[dict[str, Any]]:
        """Read only schema-valid, clean events already beyond the active segment."""

        events: list[dict[str, Any]] = []
        for segment in list_segments(self._collector.paths):
            if segment.state not in {"closed", "archive"}:
                continue
            for _, line in iter_segment_lines(segment.path):
                event = json.loads(line)
                validate_event(event)
                assert_clean(event)
                if (
                    event.get("trace_id") == trace_id
                    and event.get("project_id") == self._collector.paths.project_id
                ):
                    events.append(event)
        snapshot = self._collector.writer.durable_snapshot()
        if snapshot is not None:
            _, data = snapshot
            if not data.endswith(b"\n"):
                raise ValueError("durable active snapshot has an incomplete line")
            for line in data[:-1].split(b"\n"):
                if not line:
                    continue
                event = json.loads(line)
                validate_event(event)
                assert_clean(event)
                if (
                    event.get("trace_id") == trace_id
                    and event.get("project_id") == self._collector.paths.project_id
                ):
                    events.append(event)
        return events

    def _durable_trace_opened(self, trace_id: str) -> bool:
        try:
            return any(
                event.get("event_type") == "trace.opened"
                for event in self._durable_trace_events(trace_id)
            )
        except Exception:  # noqa: BLE001 - unverifiable state is not restored
            return False

    def _durable_native_binding_parent(
        self,
        *,
        trace_id: str,
        task_ref: str | None,
        binding_ref: Any,
    ) -> str | None:
        """Return the latest explicitly ordered native binding fact for classification."""

        if task_ref is None or not isinstance(binding_ref, str):
            return None
        try:
            native = [
                event
                for event in self._durable_trace_events(trace_id)
                if event.get("source_kind") in {"hermes_hook", "native_reconciliation"}
                and event.get("event_type") in {"work_unit.bound", "work_unit.unbound"}
                and (event.get("work_unit") or {}).get("task_ref") == task_ref
            ]
        except Exception:  # noqa: BLE001 - unverifiable binding fails closed
            return None
        if not native or any(
            (event.get("work_unit") or {}).get("binding_ref") != binding_ref for event in native
        ):
            return None
        if not any(event.get("event_type") == "work_unit.bound" for event in native):
            return None
        ordered = causal_order(native)
        event_id = ordered[-1].get("event_id") if ordered else None
        return event_id if isinstance(event_id, str) else None

    def _durable_review_request_event(
        self,
        *,
        trace_id: str,
        task_ref: str | None,
        binding_ref: Any,
        classification_event_id: str,
        principal: AuthorityPrincipal,
    ) -> str | None:
        """Resolve one durable request explicitly descended from the classification."""

        if task_ref is None or not isinstance(binding_ref, str):
            return None
        try:
            matches: list[str] = []
            for event in self._durable_trace_events(trace_id):
                unit = event.get("work_unit") or {}
                actor = event.get("actor") or {}
                if (
                    event.get("event_type") == "review.requested"
                    and event.get("source_kind") == "aether_checkpoint"
                    and event.get("status") == "started"
                    and event.get("parent_event_id") == classification_event_id
                    and unit.get("task_ref") == task_ref
                    and unit.get("binding_ref") == binding_ref
                    and actor.get("id") == principal.actor_id
                    and actor.get("profile") == principal.profile
                    and actor.get("role") == principal.role
                    and isinstance(event.get("event_id"), str)
                ):
                    matches.append(event["event_id"])
            return matches[0] if len(set(matches)) == 1 else None
        except Exception:  # noqa: BLE001 - unverifiable request fails closed
            return None

    def _durable_review_principal(
        self,
        *,
        event_type: str,
        trace_id: str,
        task_ref: str | None,
        binding_ref: Any,
    ) -> tuple[AuthorityPrincipal, str] | None:
        """Resolve native assignee plus exact product classification from durable evidence."""

        if task_ref is None or not isinstance(binding_ref, str):
            return None
        assignments: set[AuthorityPrincipal] = set()
        native_semantics: set[tuple[str, bool | None]] = set()
        native_event_ids: set[str] = set()
        classifications: dict[tuple[str, str, bool], set[str]] = {}
        try:
            relevant = [
                event
                for event in self._durable_trace_events(trace_id)
                if event.get("event_type") in {"work_unit.bound", "work_unit.unbound"}
                and (event.get("work_unit") or {}).get("task_ref") == task_ref
            ]
            for event in relevant:
                work_unit = event.get("work_unit") or {}
                if event.get("source_kind") in {"hermes_hook", "native_reconciliation"}:
                    if (
                        event.get("event_type") != "work_unit.bound"
                        or event.get("status") != "reported"
                        or work_unit.get("binding_ref") != binding_ref
                    ):
                        return None
                    actor = event.get("actor") or {}
                    principal = self._authority_context.assignment_principal(
                        actor_id=actor.get("id"),
                        profile=actor.get("profile"),
                        event_type=event_type,
                        task_ref=task_ref,
                    )
                    event_id = event.get("event_id")
                    if principal is None or not isinstance(event_id, str):
                        return None
                    assignments.add(principal)
                    native_event_ids.add(event_id)
                    native_semantics.add((work_unit.get("relation"), work_unit.get("required")))
            for event in relevant:
                work_unit = event.get("work_unit") or {}
                if event.get("source_kind") == "aether_checkpoint":
                    required = work_unit.get("required")
                    if (
                        event.get("event_type") != "work_unit.bound"
                        or event.get("status") != "reported"
                        or work_unit.get("binding_ref") != binding_ref
                        or work_unit.get("relation") != "review"
                        or not isinstance(required, bool)
                    ):
                        return None
                    actor = event.get("actor") or {}
                    routed = self._authority_context.checkpoint_principal(
                        "work_unit.bound",
                        task_ref=task_ref,
                    )
                    classifier = self._authority_context.resolve_principal(
                        actor_id=actor.get("id"),
                        profile=actor.get("profile"),
                        role=actor.get("role"),
                    )
                    classification_event_id = event.get("event_id")
                    if (
                        routed is None
                        or classifier != routed
                        or not isinstance(classification_event_id, str)
                        or event.get("parent_event_id") not in native_event_ids
                    ):
                        return None
                    classifications.setdefault((binding_ref, "review", required), set()).add(
                        classification_event_id
                    )
        except Exception:  # noqa: BLE001 - unverifiable assignment fails closed
            return None
        if len(assignments) != 1 or len(classifications) != 1:
            return None
        classification, classification_event_ids = next(iter(classifications.items()))
        if len(classification_event_ids) != 1:
            return None
        _, classified_relation, classified_required = classification
        if any(
            (relation != "unknown" and relation != classified_relation)
            or (required is not None and required != classified_required)
            for relation, required in native_semantics
        ):
            return None
        return next(iter(assignments)), next(iter(classification_event_ids))

    @staticmethod
    def _allowed_reference_keys(event_type: str) -> frozenset[str]:
        contract = frozenset(
            {
                "origin_message_id",
                "revision",
                "artifact_ref",
                "before_sha256",
                "after_sha256",
                "decision_refs",
                "supersedes_decision_ref",
                "evidence_refs",
                "ambiguity_ref",
                "invariant_key",
                "semantic_delta",
            }
        )
        if event_type in ("acceptance.declared", "acceptance.evaluated"):
            return frozenset(
                {
                    "criterion_ref",
                    "state",
                    "evidence_refs",
                    "assigned_task_ref",
                    "review_task_ref",
                }
            )
        if event_type in ("bottleneck.attributed", "defect.attributed"):
            return frozenset(
                {
                    "attribution_class",
                    "provenance",
                    "started_at",
                    "ended_at",
                    "precision_ms",
                    "evidence_refs",
                }
            )
        if event_type.startswith("review.") or event_type.startswith("work_unit."):
            return frozenset(
                {
                    "relation",
                    "required",
                    "parent_task_refs",
                    "task_status",
                    "run_status",
                    "run_outcome",
                    "binding_ref",
                }
            )
        return contract

    @staticmethod
    def _required_reference_keys(event_type: str) -> frozenset[str]:
        if event_type in ("acceptance.declared", "acceptance.evaluated"):
            return frozenset({"criterion_ref"})
        if event_type in ("bottleneck.attributed", "defect.attributed"):
            return frozenset({"attribution_class"})
        if event_type.startswith("review."):
            return frozenset({"task_ref", "binding_ref"})
        if event_type.startswith("work_unit."):
            return frozenset({"task_ref", "binding_ref", "relation", "required"})
        return frozenset()

    @staticmethod
    def _blocks(event_type: str, references: dict[str, Any]) -> dict[str, Any]:
        """Map bounded references onto the schema block the event type requires."""
        from aether_agents.observation.capture.projectors import to_utc_text

        if event_type in ("acceptance.declared", "acceptance.evaluated"):
            return {
                "acceptance": {
                    "criterion_ref": references["criterion_ref"],
                    "state": references.get("state", "pending"),
                    "evidence_refs": list(references.get("evidence_refs", ())),
                    "assigned_task_ref": references.get("assigned_task_ref"),
                    "review_task_ref": references.get("review_task_ref"),
                }
            }
        if event_type in ("bottleneck.attributed", "defect.attributed"):
            return {
                "attribution": {
                    "kind": "bottleneck" if event_type.startswith("bottleneck") else "defect",
                    "class": references["attribution_class"],
                    # A checkpoint-sourced attribution is a declaration or Morfeo's
                    # judgment. It is never presented as a native measurement.
                    "provenance": references.get("provenance", "actor_declared"),
                    "started_at": to_utc_text(references.get("started_at")),
                    "ended_at": to_utc_text(references.get("ended_at")),
                    "precision_ms": references.get("precision_ms"),
                    "evidence_refs": list(references.get("evidence_refs", ())),
                }
            }
        if event_type in (
            "work_unit.bound",
            "work_unit.unbound",
            "work_unit.status",
            "review.requested",
            "review.approved",
            "review.changes_requested",
        ):
            exact_classification = event_type.startswith("work_unit.")
            return {
                "work_unit": {
                    "task_ref": references["task_ref"],
                    "relation": (
                        references["relation"]
                        if exact_classification
                        else references.get("relation", "review")
                    ),
                    "required": (
                        references["required"]
                        if exact_classification
                        else references.get("required")
                    ),
                    "parent_task_refs": list(references.get("parent_task_refs", ())),
                    "task_status": references.get("task_status"),
                    "run_status": references.get("run_status"),
                    "run_outcome": references.get("run_outcome"),
                    "binding_ref": references["binding_ref"],
                }
            }
        contract_keys = {
            "origin_message_id",
            "revision",
            "artifact_ref",
            "before_sha256",
            "after_sha256",
            "decision_refs",
            "supersedes_decision_ref",
            "evidence_refs",
            "ambiguity_ref",
            "invariant_key",
            "semantic_delta",
        }
        block = {k: v for k, v in references.items() if k in contract_keys}
        if block:
            block.setdefault("decision_refs", [])
            block.setdefault("evidence_refs", [])
            block["decision_refs"] = list(block["decision_refs"])
            block["evidence_refs"] = list(block["evidence_refs"])
            return {"contract": block}
        return {}

    def _reject(self, trace_id: str, reason_code: str) -> None:
        """Report the rejection without copying the offending payload."""
        try:
            self._collector.health.increment(reason_code)
            builder = self._collector.builder_for(trace_id)
            self._collector.writer.append_nonblocking(
                builder.coverage_gap(
                    gap_class=CoverageClass.FORBIDDEN_PAYLOAD_REJECTED
                    if reason_code.startswith(("FORBIDDEN", "SECRET", "ABSOLUTE", "OVERSIZED"))
                    else CoverageClass.OTHER,
                    reason_code=reason_code,
                ),
                critical=True,
            )
        except Exception:  # noqa: BLE001
            pass
