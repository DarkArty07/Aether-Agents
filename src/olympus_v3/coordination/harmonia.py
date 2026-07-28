"""Default-off logical coordination over admission and advisory projections.

Harmonia produces immutable plans. It does not dispatch work or own process,
session, contract, transport, approval, or effect lifecycle.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .admission import AdmissionDecision, AdmissionEngine, AdmissionProposal, AdmissionSnapshot, AdmissionStatus
from .contracts import ExecutionContract, GateState, TaskState
from .presence import PresenceProjection, PresenceState
from .protocol import ParticipantCard, Principal, ValidationError

_REASON = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_MAX_INT = (1 << 63) - 1
_ACTIVE_STATES = {TaskState.READY, TaskState.DISPATCHED, TaskState.RUNNING, TaskState.REVIEW}


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= _MAX_INT:
        raise ValidationError(f"invalid {label}")
    return value


def _reasons(values: Any) -> tuple[str, ...]:
    if not isinstance(values, tuple) or len(values) > 32 or len(set(values)) != len(values):
        raise ValidationError("invalid Harmonia reasons")
    if any(not isinstance(value, str) or not _REASON.fullmatch(value) for value in values):
        raise ValidationError("invalid Harmonia reasons")
    return values


@dataclass(frozen=True, slots=True)
class AnycastAssignment:
    task_id: str
    participant: Principal

    def __post_init__(self) -> None:
        if not isinstance(self.task_id, str) or not self.task_id or not isinstance(self.participant, Principal):
            raise ValidationError("invalid anycast assignment")


@dataclass(frozen=True, slots=True)
class HarmoniaEscalation:
    task_id: str
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.task_id, str) or not self.task_id or not _REASON.fullmatch(self.reason):
            raise ValidationError("invalid Harmonia escalation")


@dataclass(frozen=True, slots=True)
class HarmoniaTask:
    proposal: AdmissionProposal
    state: TaskState
    assignee: Principal | None
    last_progress_at: int
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.proposal, AdmissionProposal) or not isinstance(self.state, TaskState):
            raise ValidationError("invalid Harmonia task")
        if self.assignee is not None and not isinstance(self.assignee, Principal):
            raise ValidationError("invalid Harmonia assignee")
        object.__setattr__(self, "last_progress_at", _integer(self.last_progress_at, "last progress"))
        object.__setattr__(self, "reasons", _reasons(self.reasons))
        if self.state in _ACTIVE_STATES and self.assignee is None:
            raise ValidationError("active Harmonia task requires assignee")
        if self.state is TaskState.BLOCKED and not self.reasons:
            raise ValidationError("blocked Harmonia task requires reason")

    @property
    def task_id(self) -> str:
        return self.proposal.task_id


@dataclass(frozen=True, slots=True)
class HarmoniaProjection:
    revision: int = 0
    tasks: tuple[HarmoniaTask, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "revision", _integer(self.revision, "projection revision"))
        if not isinstance(self.tasks, tuple) or any(not isinstance(task, HarmoniaTask) for task in self.tasks):
            raise ValidationError("invalid Harmonia projection")
        task_ids = tuple(task.task_id for task in self.tasks)
        if len(set(task_ids)) != len(task_ids):
            raise ValidationError("duplicate Harmonia task")
        object.__setattr__(self, "tasks", tuple(sorted(self.tasks, key=lambda task: task.task_id)))


@dataclass(frozen=True, slots=True)
class HarmoniaPlan:
    admissions: tuple[AdmissionDecision, ...]
    assignments: tuple[AnycastAssignment, ...]
    escalations: tuple[HarmoniaEscalation, ...]
    projection: HarmoniaProjection

    def __post_init__(self) -> None:
        if (
            not isinstance(self.admissions, tuple)
            or any(not isinstance(item, AdmissionDecision) for item in self.admissions)
            or not isinstance(self.assignments, tuple)
            or any(not isinstance(item, AnycastAssignment) for item in self.assignments)
            or not isinstance(self.escalations, tuple)
            or any(not isinstance(item, HarmoniaEscalation) for item in self.escalations)
            or not isinstance(self.projection, HarmoniaProjection)
        ):
            raise ValidationError("invalid Harmonia plan")


class HarmoniaCoordinator:
    """Create deterministic logical plans without executing them."""

    def __init__(self, *, enabled: bool = False, stall_after_seconds: int = 300):
        if not isinstance(enabled, bool):
            raise ValidationError("invalid Harmonia enabled flag")
        self.enabled = enabled
        self.stall_after_seconds = _integer(stall_after_seconds, "stall threshold", minimum=1)

    def plan(
        self,
        contract: ExecutionContract,
        proposals: tuple[AdmissionProposal, ...],
        admission_snapshot: AdmissionSnapshot,
        cards: tuple[ParticipantCard, ...],
        presences: tuple[PresenceProjection, ...],
        *,
        now: int,
        previous: HarmoniaProjection | None = None,
    ) -> HarmoniaPlan:
        now = _integer(now, "now")
        previous = previous if previous is not None else HarmoniaProjection()
        if not isinstance(previous, HarmoniaProjection):
            raise ValidationError("invalid previous Harmonia projection")
        if not isinstance(cards, tuple) or any(not isinstance(card, ParticipantCard) for card in cards):
            raise ValidationError("invalid participant cards")
        if not isinstance(presences, tuple) or any(not isinstance(item, PresenceProjection) for item in presences):
            raise ValidationError("invalid presence projections")
        if len({card.principal for card in cards}) != len(cards):
            raise ValidationError("duplicate participant card")
        if len({item.identity_id for item in presences}) != len(presences):
            raise ValidationError("duplicate presence projection")
        if any(card.principal.project_id != contract.project_id for card in cards):
            raise ValidationError("participant card project mismatch")
        if any(item.project_id != contract.project_id for item in presences):
            raise ValidationError("presence project mismatch")

        existing = {task.task_id: task for task in previous.tasks}
        proposed_ids = {proposal.task_id for proposal in proposals}
        if proposed_ids & set(existing):
            raise ValidationError("replayed Harmonia task")

        admissions = AdmissionEngine(enabled=self.enabled).evaluate(contract, proposals, admission_snapshot)
        decisions = {decision.task_id: decision for decision in admissions}
        presence_by_identity = {item.identity_id: item for item in presences}
        completed = set(admission_snapshot.completed_task_ids) | {
            task.task_id for task in previous.tasks if task.state is TaskState.COMPLETED
        }
        used = {
            task.assignee
            for task in previous.tasks
            if task.state in _ACTIVE_STATES and task.assignee is not None
        }
        assignments: list[AnycastAssignment] = []
        escalations: list[HarmoniaEscalation] = []
        projected = dict(existing)

        required_gate_pending = any(
            gate.required and gate.state not in {GateState.PASSED, GateState.WAIVED}
            for gate in contract.evidence_gates
        )
        for task in previous.tasks:
            if task.state is TaskState.RUNNING and now - task.last_progress_at >= self.stall_after_seconds:
                escalations.append(HarmoniaEscalation(task.task_id, "stall"))
            if task.state is TaskState.REVIEW and required_gate_pending:
                escalations.append(HarmoniaEscalation(task.task_id, "gate_pending"))

        cards_ordered = tuple(
            sorted(cards, key=lambda card: (card.principal.owner_id, card.principal.actor_id, card.role))
        )
        for proposal in sorted(proposals, key=lambda item: item.task_id):
            decision = decisions[proposal.task_id]
            if decision.status is AdmissionStatus.REJECTED:
                projected[proposal.task_id] = HarmoniaTask(proposal, TaskState.BLOCKED, None, now, decision.reasons)
                continue
            if decision.status is AdmissionStatus.ESCALATED:
                escalation = HarmoniaEscalation(proposal.task_id, "ambiguity")
                escalations.append(escalation)
                projected[proposal.task_id] = HarmoniaTask(proposal, TaskState.BLOCKED, None, now, ("ambiguity",))
                continue
            if any(dependency not in completed for dependency in proposal.dependencies):
                projected[proposal.task_id] = HarmoniaTask(proposal, TaskState.ADMITTED, None, now, ())
                continue

            eligible: list[Principal] = []
            for candidate in cards_ordered:
                principal = candidate.principal
                status = presence_by_identity.get(principal.owner_id)
                if (
                    candidate.role != proposal.role
                    or principal not in contract.participants
                    or principal in used
                    or status is None
                    or status.stale
                    or status.state is not PresenceState.IDLE
                    or (proposal.permission == "review" and principal == contract.owner)
                ):
                    continue
                eligible.append(principal)
            if not eligible:
                escalations.append(HarmoniaEscalation(proposal.task_id, "no_eligible_target"))
                projected[proposal.task_id] = HarmoniaTask(
                    proposal, TaskState.BLOCKED, None, now, ("no_eligible_target",)
                )
                continue

            assignee = eligible[0]
            used.add(assignee)
            assignments.append(AnycastAssignment(proposal.task_id, assignee))
            projected[proposal.task_id] = HarmoniaTask(proposal, TaskState.READY, assignee, now, ())

        return HarmoniaPlan(
            admissions,
            tuple(sorted(assignments, key=lambda item: (item.task_id, item.participant.owner_id))),
            tuple(sorted(escalations, key=lambda item: (item.task_id, item.reason))),
            HarmoniaProjection(previous.revision + 1, tuple(projected.values())),
        )


__all__ = [
    "AnycastAssignment",
    "HarmoniaCoordinator",
    "HarmoniaEscalation",
    "HarmoniaPlan",
    "HarmoniaProjection",
    "HarmoniaTask",
]
