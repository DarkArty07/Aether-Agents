"""Fixed, content-free observation fixtures shared by the telemetry tests."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Any

from aether_agents import product_version
from aether_agents.observation.capture.projectors import EventBuilder
from aether_agents.observation.checkpoint import AuthorityContext
from aether_agents.observation.contracts import validate_event, validate_summary
from aether_agents.observation.privacy import native_pseudonym_ref
from aether_agents.observation.reduce.reducer import ReductionInput, reduce_events

PROJECT_ID = "11111111-1111-4111-8111-111111111111"
TRACE_ID = "ctr_11111111111111111111111111111111"
EPOCH = "prd_22222222222222222222222222222222"
RUNTIME_FINGERPRINT = "3" * 64
BASE = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
PSEUDONYM_KEY_EPOCH = "fpk_" + "4" * 32


def project_marker(project_id: str, *, name: str = "Observation fixture") -> str:
    """Return the complete canonical local-forge marker required by active readers."""
    return "\n".join(
        (
            "schema_version = 1",
            f'project_id = "{project_id}"',
            f'name = "{name}"',
            'initialized_by = "1.0.0"',
            'forge = "local"',
            'contract_root = "specs"',
            'default_branch = "main"',
            "",
        )
    )


def native_pseudonym(kind: str, value: str) -> str:
    """Stable, syntactically valid keyed-identity fixture (never production HMAC)."""
    if native_pseudonym_ref(value, kind=kind) is not None:
        return value
    prefix = {
        "session": "sid",
        "turn": "trn",
        "api_request": "api",
        "tool_call": "call",
        "approval_request": "apr",
    }[kind]
    digest = sha256(f"aether-test-fixture:{kind}:{value}".encode()).hexdigest()
    return f"{prefix}_{PSEUDONYM_KEY_EPOCH}_{digest}"


class EventFactory:
    """Create schema-valid events with stable identities and causal order."""

    def __init__(
        self,
        *,
        project_id: str = PROJECT_ID,
        trace_id: str = TRACE_ID,
        epoch: str = EPOCH,
        collector_version: str | None = None,
        runtime_fingerprint: str = RUNTIME_FINGERPRINT,
    ) -> None:
        self.project_id = project_id
        self.trace_id = trace_id
        self.epoch = epoch
        self.builder = EventBuilder(
            trace_id=trace_id,
            project_id=project_id,
            collector_version=collector_version or product_version(),
            runtime_fingerprint=runtime_fingerprint,
            normalizer_ref="hermes.tool-category.v1",
        )
        self.events: list[dict[str, Any]] = []

    def at(self, seconds: float) -> datetime:
        return BASE + timedelta(seconds=seconds)

    def add(self, event: dict[str, Any], *, seconds: float | None = None) -> dict[str, Any]:
        seq = len(self.events)
        if seconds is not None:
            text = self.at(seconds).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            event["occurred_at"] = text
        # Stable golden identities; the journal normally stamps epoch and sequence.
        event["event_id"] = f"evt_{seq + 1:032x}"
        event["producer_epoch"] = self.epoch
        event["producer_seq"] = seq
        event["recorded_at"] = event["occurred_at"]
        event["monotonic_ns"] = seq + 1
        validate_event(event)
        self.events.append(event)
        return event

    def event(
        self,
        event_type: str,
        status: str,
        seconds: float,
        *,
        actor_kind: str = "agent",
        actor_id: str = "morfeo",
        profile: str | None = "morfeo",
        role: str | None = None,
        **values: Any,
    ) -> dict[str, Any]:
        source_kind = values.pop(
            "source_kind",
            "aether_checkpoint"
            if event_type.startswith(
                ("contract.", "acceptance.", "invariant.", "review.", "trace.")
            )
            or event_type.startswith("handoff.")
            else "hermes_hook",
        )
        if role is None and source_kind == "aether_checkpoint":
            role = {
                "morfeo": "verification",
                "supervisor": "supervision",
                "implementer": "implementation",
            }.get(profile)
        event = self.builder.build(
            event_type,
            status=status,
            occurred_at=self.at(seconds),
            actor_kind=actor_kind,
            actor_id=actor_id,
            profile=profile,
            role=role,
            source_kind=source_kind,
            **values,
        )
        return self.add(event)

    def opened(self, seconds: float = 0, *, origin: int | str | None = 7) -> dict[str, Any]:
        return self.add(
            self.builder.contract(
                event_type="trace.opened",
                status="started",
                origin_message_id=origin,
                occurred_at=self.at(seconds),
                timestamp_source="native" if origin is not None else "collector",
                actor_kind="owner" if origin is not None else "system",
                actor_id="owner" if origin is not None else "observer",
                profile=None,
            )
        )

    def contract(
        self,
        event_type: str,
        status: str,
        seconds: float,
        **values: Any,
    ) -> dict[str, Any]:
        values.setdefault("actor_kind", "agent")
        values.setdefault("actor_id", "morfeo")
        values.setdefault("profile", "morfeo")
        values.setdefault("role", "verification")
        return self.add(
            self.builder.contract(
                event_type=event_type,
                status=status,
                occurred_at=self.at(seconds),
                source_kind="aether_checkpoint",
                **values,
            )
        )

    def unit(
        self,
        event_type: str,
        status: str,
        seconds: float,
        *,
        task_ref: str,
        relation: str = "implementation",
        required: bool = True,
        parent_task_refs: tuple[str, ...] = (),
        task_status: str | None = None,
        run_status: str | None = None,
        run_outcome: str | None = None,
        run_id: int | None = None,
        actor_kind: str = "agent",
        actor_id: str = "supervisor",
        profile: str | None = "supervisor",
        role: str | None = None,
    ) -> dict[str, Any]:
        source_kind = "aether_checkpoint" if event_type.startswith("review.") else "hermes_hook"
        return self.add(
            self.builder.work_unit(
                event_type=event_type,
                status=status,
                task_ref=task_ref,
                relation=relation,
                required=required,
                binding="bnd_" + task_ref.replace("-", "_") + "_0123456789abcdef",
                parent_task_refs=parent_task_refs,
                task_status=task_status,
                run_status=run_status,
                run_outcome=run_outcome,
                run_id=run_id,
                occurred_at=self.at(seconds),
                actor_kind=actor_kind,
                actor_id=actor_id,
                profile=profile,
                role=(
                    role
                    if role is not None
                    else "supervision"
                    if source_kind == "aether_checkpoint" and profile == "supervisor"
                    else None
                ),
                source_kind=source_kind,
            )
        )

    def acceptance(
        self,
        seconds: float,
        *,
        criterion: str = "criterion-1",
        state: str = "passed",
        evidence: tuple[str, ...] = ("evidence-1",),
        event_type: str = "acceptance.evaluated",
    ) -> dict[str, Any]:
        return self.add(
            self.builder.acceptance(
                event_type=event_type,
                criterion_ref=criterion,
                state=state,
                evidence_refs=evidence,
                occurred_at=self.at(seconds),
                actor_kind="agent",
                actor_id="morfeo",
                profile="morfeo",
                role="verification",
                source_kind="aether_checkpoint",
            )
        )

    def pass_executable_invariants(self, start_seconds: float) -> None:
        for offset, number in enumerate(range(1, 11)):
            self.contract(
                "invariant.passed",
                "passed",
                start_seconds + (offset / 100),
                invariant_key=f"OBS-INV-{number:03d}",
            )

    def summary(self, *, derived_gaps: list[dict[str, str]] | None = None) -> dict[str, Any]:
        events = deepcopy(self.events)
        summary = reduce_events(
            ReductionInput(
                trace_id=self.trace_id,
                project_id=self.project_id,
                events=events,
                derived_gaps=list(derived_gaps or ()),
                producer_count=len({event["producer_epoch"] for event in events}) or 1,
                authority_context=AuthorityContext.product_default(),
            )
        )
        validate_summary(summary)
        return summary


def complete_trace() -> EventFactory:
    """Morfeo → Supervisor → Implementer → review → verification fixture."""
    f = EventFactory()
    f.opened(0)
    f.contract("contract.executable", "passed", 1, semantic_delta="invariant")
    f.contract(
        "contract.persisted",
        "completed",
        2,
        revision=1,
        artifact_ref="specs/contract.md",
        after_sha256="a" * 64,
        semantic_delta="revision",
    )
    f.event(
        "handoff.completed",
        "completed",
        3,
        actor_id="supervisor",
        profile="supervisor",
    )
    f.unit(
        "work_unit.bound", "reported", 4, task_ref="root", relation="root", task_status="running"
    )
    f.unit(
        "work_unit.bound",
        "reported",
        5,
        task_ref="impl",
        parent_task_refs=("root",),
        task_status="running",
    )
    f.unit(
        "run.started",
        "started",
        6,
        task_ref="impl",
        parent_task_refs=("root",),
        task_status="running",
        run_status="running",
        run_id=1,
        actor_kind="subagent",
        actor_id="implementer-1",
        profile="implementer",
    )
    f.unit(
        "run.finished",
        "completed",
        10,
        task_ref="impl",
        parent_task_refs=("root",),
        task_status="done",
        run_status="done",
        run_outcome="completed",
        run_id=1,
        actor_kind="subagent",
        actor_id="implementer-1",
        profile="implementer",
    )
    f.unit(
        "work_unit.bound",
        "reported",
        11,
        task_ref="review",
        relation="review",
        parent_task_refs=("impl",),
        task_status="review",
    )
    f.unit(
        "review.requested",
        "started",
        12,
        task_ref="review",
        relation="review",
        parent_task_refs=("impl",),
        task_status="review",
    )
    f.unit(
        "review.approved",
        "passed",
        14,
        task_ref="review",
        relation="review",
        parent_task_refs=("impl",),
        task_status="done",
        actor_id="supervisor",
        profile="supervisor",
    )
    f.unit(
        "work_unit.status", "completed", 15, task_ref="root", relation="root", task_status="done"
    )
    f.acceptance(16)
    f.pass_executable_invariants(16.01)
    f.contract(
        "contract.completion_verified",
        "verified",
        17,
        evidence_refs=("evidence-1",),
        semantic_delta="evidence",
        actor_kind="agent",
        actor_id="morfeo",
        profile="morfeo",
    )
    f.contract(
        "trace.closed", "completed", 18, actor_kind="agent", actor_id="morfeo", profile="morfeo"
    )
    return f
