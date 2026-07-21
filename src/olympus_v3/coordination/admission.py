"""Pure, deterministic admission decisions for default-off coordination.

This module validates semantic work proposals against an immutable execution
contract and caller-supplied runtime snapshot. It deliberately owns no process,
session, transport, database, or effect lifecycle.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping

from .contracts import ContractState, ExecutionContract, GateState
from .protocol import MAX_PAYLOAD_BYTES, ValidationError

_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,127}$")
_TOKEN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_MAX_TEXT = 4096
_MAX_ITEMS = 128


class AdmissionStatus(StrEnum):
    """A closed set of deterministic admission outcomes."""

    ADMITTED = "admitted"
    REJECTED = "rejected"
    ESCALATED = "escalated"


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or value != value.strip() or not _ID.fullmatch(value):
        raise ValidationError(f"invalid {label}")
    return value


def _token(value: Any, label: str) -> str:
    if not isinstance(value, str) or value != value.strip() or not _TOKEN.fullmatch(value):
        raise ValidationError(f"invalid {label}")
    return value


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip() or len(value) > _MAX_TEXT:
        raise ValidationError(f"invalid {label}")
    return value


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValidationError(f"invalid {label}")
    return value


def _tuple(
    values: Any,
    label: str,
    validator: Any,
    *,
    allow_empty: bool = True,
) -> tuple[str, ...]:
    if (
        not isinstance(values, tuple)
        or (not allow_empty and not values)
        or len(values) > _MAX_ITEMS
        or len(set(values)) != len(values)
    ):
        raise ValidationError(f"invalid {label}")
    return tuple(validator(value, label) for value in values)


def _scope(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > 512
        or "\x00" in value
    ):
        raise ValidationError(f"invalid {label}")
    return value


@dataclass(frozen=True, slots=True)
class AdmissionProposal:
    """One immutable, fully costed subtask proposed for admission."""

    task_id: str
    objective: str
    objective_source: str
    scopes: tuple[str, ...]
    dependencies: tuple[str, ...]
    role: str
    permission: str
    evidence: tuple[str, ...]
    model_cost: int
    tool_cost: int
    time_cost_seconds: int
    retries: int
    effect_class: str
    fan_out: int
    payload_bytes: int
    lease_resources: tuple[str, ...]
    ambiguities: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "task_id", _identifier(self.task_id, "task id"))
        object.__setattr__(self, "objective", _text(self.objective, "objective"))
        object.__setattr__(self, "objective_source", _text(self.objective_source, "objective source"))
        object.__setattr__(self, "scopes", _tuple(self.scopes, "scopes", _scope, allow_empty=False))
        dependencies = _tuple(self.dependencies, "dependencies", _identifier)
        if self.task_id in dependencies:
            raise ValidationError("task cannot depend on itself")
        object.__setattr__(self, "dependencies", dependencies)
        object.__setattr__(self, "role", _identifier(self.role, "role"))
        object.__setattr__(self, "permission", _token(self.permission, "permission"))
        object.__setattr__(self, "evidence", _tuple(self.evidence, "evidence", _identifier))
        object.__setattr__(self, "model_cost", _integer(self.model_cost, "model cost"))
        object.__setattr__(self, "tool_cost", _integer(self.tool_cost, "tool cost"))
        object.__setattr__(self, "time_cost_seconds", _integer(self.time_cost_seconds, "time cost seconds"))
        object.__setattr__(self, "retries", _integer(self.retries, "retries"))
        object.__setattr__(self, "effect_class", _token(self.effect_class, "effect class"))
        object.__setattr__(self, "fan_out", _integer(self.fan_out, "fan out", minimum=1))
        object.__setattr__(self, "payload_bytes", _integer(self.payload_bytes, "payload bytes"))
        object.__setattr__(
            self,
            "lease_resources",
            _tuple(self.lease_resources, "lease resources", _identifier),
        )
        object.__setattr__(self, "ambiguities", _tuple(self.ambiguities, "ambiguities", _text))


@dataclass(frozen=True, slots=True)
class AdmissionSnapshot:
    """Caller-owned immutable usage and lease facts used by one evaluation."""

    active_task_ids: tuple[str, ...] = ()
    completed_task_ids: tuple[str, ...] = ()
    model_cost_used: int = 0
    tool_cost_used: int = 0
    time_seconds_used: int = 0
    active_leases: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        active = _tuple(self.active_task_ids, "active task ids", _identifier)
        completed = _tuple(self.completed_task_ids, "completed task ids", _identifier)
        if set(active) & set(completed):
            raise ValidationError("active and completed tasks overlap")
        object.__setattr__(self, "active_task_ids", active)
        object.__setattr__(self, "completed_task_ids", completed)
        object.__setattr__(self, "model_cost_used", _integer(self.model_cost_used, "used model cost"))
        object.__setattr__(self, "tool_cost_used", _integer(self.tool_cost_used, "used tool cost"))
        object.__setattr__(self, "time_seconds_used", _integer(self.time_seconds_used, "used time seconds"))
        if not isinstance(self.active_leases, Mapping) or len(self.active_leases) > _MAX_ITEMS:
            raise ValidationError("invalid active leases")
        leases = {
            _identifier(resource, "lease resource"): _identifier(owner, "lease owner")
            for resource, owner in self.active_leases.items()
        }
        object.__setattr__(self, "active_leases", MappingProxyType(dict(sorted(leases.items()))))


@dataclass(frozen=True, slots=True)
class AdmissionDecision:
    """Machine-readable result for one proposal; reasons never contain payload data."""

    task_id: str
    status: AdmissionStatus
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "task_id", _identifier(self.task_id, "task id"))
        if not isinstance(self.status, AdmissionStatus):
            raise ValidationError("invalid admission status")
        object.__setattr__(self, "reasons", _tuple(self.reasons, "admission reasons", _token))
        if self.status is AdmissionStatus.ADMITTED and self.reasons:
            raise ValidationError("admitted decision cannot contain reasons")
        if self.status is not AdmissionStatus.ADMITTED and not self.reasons:
            raise ValidationError("non-admitted decision requires a reason")


def _inside(scope: str, boundary: str) -> bool:
    return scope == boundary or scope.startswith(boundary)


def _cycle_members(proposals: tuple[AdmissionProposal, ...]) -> set[str]:
    graph = {
        proposal.task_id: tuple(dependency for dependency in proposal.dependencies if dependency in {p.task_id for p in proposals})
        for proposal in proposals
    }

    def reaches_start(start: str, current: str, visited: set[str]) -> bool:
        for dependency in graph[current]:
            if dependency == start:
                return True
            if dependency not in visited and reaches_start(start, dependency, visited | {dependency}):
                return True
        return False

    return {task_id for task_id in graph if reaches_start(task_id, task_id, {task_id})}


class AdmissionEngine:
    """Evaluate proposals without dispatching or mutating any runtime state."""

    def __init__(self, *, enabled: bool = False):
        if not isinstance(enabled, bool):
            raise ValidationError("invalid admission enabled flag")
        self.enabled = enabled

    def evaluate(
        self,
        contract: ExecutionContract,
        proposals: tuple[AdmissionProposal, ...],
        snapshot: AdmissionSnapshot,
    ) -> tuple[AdmissionDecision, ...]:
        if not isinstance(contract, ExecutionContract):
            raise ValidationError("invalid execution contract")
        if (
            not isinstance(proposals, tuple)
            or not proposals
            or any(not isinstance(proposal, AdmissionProposal) for proposal in proposals)
        ):
            raise ValidationError("invalid admission proposals")
        if not isinstance(snapshot, AdmissionSnapshot):
            raise ValidationError("invalid admission snapshot")
        task_ids = tuple(proposal.task_id for proposal in proposals)
        if len(set(task_ids)) != len(task_ids):
            raise ValidationError("duplicate admission task id")

        ordered = tuple(sorted(proposals, key=lambda proposal: proposal.task_id))
        if not self.enabled:
            return tuple(
                AdmissionDecision(proposal.task_id, AdmissionStatus.REJECTED, ("coordination_disabled",))
                for proposal in ordered
            )

        cycles = _cycle_members(ordered)
        known_tasks = set(task_ids) | set(snapshot.active_task_ids) | set(snapshot.completed_task_ids)
        required_gates = {gate.name for gate in contract.evidence_gates if gate.required}
        unresolved_gates = {
            gate.name
            for gate in contract.evidence_gates
            if gate.required and gate.state not in {GateState.PASSED, GateState.WAIVED}
        }
        allocated_cost = snapshot.model_cost_used + snapshot.tool_cost_used
        allocated_time = snapshot.time_seconds_used
        protected_limit = contract.limits.model_budget - contract.limits.qa_reserve - contract.limits.recovery_reserve
        allocated_fan_out = len(snapshot.active_task_ids)
        decisions: list[AdmissionDecision] = []

        for proposal in ordered:
            reasons: list[str] = []
            if contract.status is not ContractState.ACTIVE:
                reasons.append("contract_not_active")
            if proposal.objective_source != contract.objective:
                reasons.append("objective_mismatch")
            if any(not any(_inside(scope, allowed) for allowed in contract.included_scopes) for scope in proposal.scopes):
                reasons.append("scope_outside_contract")
            if any(any(_inside(scope, excluded) for excluded in contract.excluded_scopes) for scope in proposal.scopes):
                reasons.append("scope_excluded")
            if any(dependency not in known_tasks for dependency in proposal.dependencies):
                reasons.append("unknown_dependency")
            if proposal.task_id in cycles:
                reasons.append("dependency_cycle")
            if proposal.permission not in contract.role_permissions.get(proposal.role, ()):
                reasons.append("role_ceiling_exceeded")
            if unresolved_gates:
                reasons.append("evidence_gate_unresolved")
            if not required_gates.issubset(proposal.evidence):
                reasons.append("required_evidence_missing")
            if proposal.retries > contract.limits.retries:
                reasons.append("retry_limit_exceeded")
            if proposal.effect_class != "none" and proposal.effect_class not in contract.side_effect_policy.allowed_effects:
                reasons.append("effect_not_allowed")
            if (
                proposal.effect_class != "none"
                and proposal.fan_out > contract.side_effect_policy.max_external_actions
            ):
                reasons.append("external_action_limit_exceeded")
            if proposal.fan_out > contract.limits.concurrency:
                reasons.append("fan_out_limit_exceeded")
            if proposal.payload_bytes > MAX_PAYLOAD_BYTES:
                reasons.append("payload_limit_exceeded")
            if (
                allocated_time + proposal.time_cost_seconds > contract.limits.time_seconds
            ):
                reasons.append("time_budget_exceeded")
            if any(
                resource in snapshot.active_leases
                and snapshot.active_leases[resource] != proposal.task_id
                for resource in proposal.lease_resources
            ):
                reasons.append("lease_contended")

            if reasons:
                decisions.append(AdmissionDecision(proposal.task_id, AdmissionStatus.REJECTED, tuple(reasons)))
                continue
            if proposal.ambiguities:
                decisions.append(AdmissionDecision(proposal.task_id, AdmissionStatus.ESCALATED, ("ambiguity",)))
                continue

            proposal_cost = proposal.model_cost + proposal.tool_cost
            if allocated_cost + proposal_cost > protected_limit:
                decisions.append(
                    AdmissionDecision(proposal.task_id, AdmissionStatus.REJECTED, ("protected_reserve_exceeded",))
                )
                continue
            if allocated_fan_out + proposal.fan_out > contract.limits.concurrency:
                decisions.append(
                    AdmissionDecision(proposal.task_id, AdmissionStatus.REJECTED, ("concurrency_limit_exceeded",))
                )
                continue

            allocated_cost += proposal_cost
            allocated_time += proposal.time_cost_seconds
            allocated_fan_out += proposal.fan_out
            decisions.append(AdmissionDecision(proposal.task_id, AdmissionStatus.ADMITTED, ()))

        return tuple(decisions)


__all__ = [
    "AdmissionDecision",
    "AdmissionEngine",
    "AdmissionProposal",
    "AdmissionSnapshot",
    "AdmissionStatus",
]
